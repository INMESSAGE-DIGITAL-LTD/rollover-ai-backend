"""
Core daily picks: Banker of the Day (1 single) and Safe Double (2 legs).

Design goal: a daily product that wins most days. A 4-leg slip at 79% per
leg wins ~39% of days; a single at ~86% or a double of two ~88% legs wins
far more often. So we pick few, very likely, standard-market selections.

A selection qualifies only when BOTH agree:
  * the bookmaker consensus — margin-free probability from the full market
    (1X2, over/under pair, BTTS pair); Double Chance derived from 1X2
  * our model's raw probability (captured before the qualifier gates)
and they don't disagree by more than MAX_DISAGREEMENT (a big gap usually
means bad data, not an edge). Final probability leans on the market, which
is better calibrated than the model on its own.

Only whitelisted leagues; women's/reserve/youth sides and friendlies are
excluded. Reuses the cron's fixtures — zero extra API calls.

Firestore: daily_core/{date} -> {matches: [...]} with each entry tagged
product='banker'|'double', so result_updater grades them like other tabs.
"""
from datetime import datetime, timedelta

from firebase_config import get_firestore_client
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from utils.league_quality import is_junk, is_whitelisted

STANDARD_MARKETS = {
    'Over 1.5 Goals', 'Over 2.5 Goals', 'Under 3.5 Goals',
    'Double Chance (1X)', 'Double Chance (X2)', 'Double Chance (12)',
    'Home Win', 'Away Win', 'Both Teams to Score', 'BTTS No',
}

MARKET_WEIGHT = 0.65
MAX_DISAGREEMENT = 0.15
MIN_MODEL = 0.70
MIN_ODDS = 1.12

# (min market prob, max odds) — strict first, then one relaxed pass.
BANKER_TIERS = [(0.84, 1.45), (0.80, 1.50)]
DOUBLE_TIERS = [(0.80, 1.45), (0.77, 1.55)]


def _pair(a, b):
    """Margin-free probability of the first outcome of a two-way market."""
    if not a or not b:
        return None
    ia, ib = 1.0 / a, 1.0 / b
    return ia / (ia + ib)


def market_probability(fix, label):
    """Bookmaker consensus probability for a market label, or None."""
    markets = fix.get('markets') or {}
    ftr = markets.get('fulltime_result') or {}
    h, d, a = ftr.get('home'), ftr.get('draw'), ftr.get('away')
    p1x2 = None
    if h and d and a:
        ih, idr, ia = 1 / h, 1 / d, 1 / a
        s = ih + idr + ia
        p1x2 = (ih / s, idr / s, ia / s)

    if label == 'Home Win' and p1x2:
        return p1x2[0]
    if label == 'Away Win' and p1x2:
        return p1x2[2]
    if label == 'Double Chance (1X)' and p1x2:
        return p1x2[0] + p1x2[1]
    if label == 'Double Chance (X2)' and p1x2:
        return p1x2[2] + p1x2[1]
    if label == 'Double Chance (12)' and p1x2:
        return p1x2[0] + p1x2[2]

    btts = markets.get('btts') or {}
    if label == 'Both Teams to Score':
        return _pair(btts.get('yes'), btts.get('no'))
    if label == 'BTTS No':
        return _pair(btts.get('no'), btts.get('yes'))

    for point, line in (fix.get('lines') or {}).items():
        over = line.get('over_odds') or line.get('over')
        under = line.get('under_odds') or line.get('under')
        if label == f'Over {point} Goals':
            return _pair(over, under)
        if label == f'Under {point} Goals':
            return _pair(under, over)
    return None


def score_candidates(options, fixtures):
    """Attach consensus probabilities and keep qualifying standard picks."""
    by_id = {f.get('fixture_id'): f for f in fixtures if f.get('fixture_id')}
    out = []
    for o in options:
        if o.get('market') not in STANDARD_MARKETS:
            continue
        if not is_whitelisted(o) or is_junk(o):
            continue
        fix = by_id.get(o.get('fixture_id'))
        if not fix:
            continue
        p_mkt = market_probability(fix, o['market'])
        p_model = float(o.get('ai_prob') or 0)
        odds = float(o.get('odds') or 0)
        if p_mkt is None or odds < MIN_ODDS or p_model < MIN_MODEL:
            continue
        if abs(p_model - p_mkt) > MAX_DISAGREEMENT:
            continue
        p = MARKET_WEIGHT * p_mkt + (1 - MARKET_WEIGHT) * p_model
        out.append(dict(o, market_prob=p_mkt, model_prob=p_model, ai_prob=p))
    return out


def pick_core(candidates):
    """Return (banker, [double legs]) — distinct fixtures, best first."""
    def fid(o):
        return o.get('fixture_id') or f"{o.get('home_team')}_{o.get('away_team')}"

    # Best market per fixture.
    best = {}
    for o in candidates:
        k = fid(o)
        if k not in best or o['ai_prob'] > best[k]['ai_prob']:
            best[k] = o
    ranked = sorted(best.values(), key=lambda o: (o['market_prob'], o['ai_prob']),
                    reverse=True)

    banker = None
    for min_mkt, max_odds in BANKER_TIERS:
        banker = next((o for o in ranked
                       if o['market_prob'] >= min_mkt and o['odds'] <= max_odds), None)
        if banker:
            break

    double = []
    for min_mkt, max_odds in DOUBLE_TIERS:
        double = [o for o in ranked
                  if o is not banker and o['market_prob'] >= min_mkt
                  and o['odds'] <= max_odds][:2]
        if len(double) == 2:
            break
    if len(double) < 2:
        double = []
    return banker, double


def generate_core_picks(fixtures, predictor, stats_calculator, date_str=None):
    from utils.fixture_fetcher import (
        _generate_match_options as generate_match_options,
        _format_slip_matches as format_slip_matches,
    )

    target_date = date_str or datetime.utcnow().strftime('%Y-%m-%d')
    if not fixtures:
        return {'status': 'no_fixtures', 'date': target_date,
                'message': 'No fixtures for core picks.'}

    collector = []
    generate_match_options(fixtures, predictor, stats_calculator,
                           af_stats=None, free_mode=False,
                           value_collector=collector)
    candidates = score_candidates(collector, fixtures)
    banker, double = pick_core(candidates)
    print(f"🏦 Core picks: {len(collector)} priced markets → {len(candidates)} qualified; "
          f"banker={'yes' if banker else 'no'}, double={len(double)} legs")

    chosen = ([banker] if banker else []) + double
    for o in chosen:
        o['confidence'] = 'HIGH' if o['ai_prob'] >= 0.82 else 'MEDIUM'
        o['edge'] = o['ai_prob'] - 1.0 / o['odds']
    formatted = format_slip_matches(chosen)
    for f, o in zip(formatted, chosen):
        f['product'] = 'banker' if o is banker else 'double'
        f['market_probability'] = round(o['market_prob'] * 100, 1)
        f['model_probability'] = round(o['model_prob'] * 100, 1)
        if o.get('fixture_id'):
            f['fixture_id'] = o['fixture_id']

    db = get_firestore_client()
    db.collection('daily_core').document(target_date).set({
        'date': target_date,
        'matches': formatted,
        'match_count': len(formatted),
        'candidates': len(candidates),
        'generated_at': SERVER_TIMESTAMP,
    })

    try:
        cutoff = (datetime.utcnow() - timedelta(days=90)).strftime('%Y-%m-%d')
        for doc in db.collection('daily_core').where('date', '<', cutoff).stream():
            doc.reference.delete()
    except Exception as e:
        print(f"⚠️ Core picks cleanup failed (non-fatal): {e}")

    return {'status': 'success', 'date': target_date, 'match_count': len(formatted),
            'message': f"banker={'yes' if banker else 'no'}, double={len(double)} legs "
                       f"from {len(candidates)} qualified"}

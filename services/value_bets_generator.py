"""
Value Bets generator.

A value bet is a selection where our model's probability is higher than the
probability implied by the real bookmaker price:

    edge = p_model - 1 / odds          EV = p_model * odds - 1

Reuses the fixtures already fetched by the daily cron — zero extra API calls.
Probabilities come from the raw model output captured *before* the
odds-safety and qualifier gates (those blend implied odds back in, which
would make every edge positive by construction).

Writes Firestore daily_value_bets/{date} with the same `matches` shape as the
other tabs so result_updater grades each selection.
"""
from datetime import datetime, timedelta

from firebase_config import get_firestore_client
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

MIN_ODDS = 1.55
MAX_ODDS = 4.50
MIN_PROB = 0.40          # no long shots
MIN_EDGE = 0.05          # 5 percentage points over the bookmaker
MAX_EDGE = 0.25          # bigger "edges" are almost always model error
MIN_EV = 0.08
MAX_PICKS = 10

JUNK_KEYWORDS = ('II', ' B ', 'U18', 'U19', 'U20', 'U21', 'U23',
                 'Women', 'Reserves', 'Youth')


def _is_junk(o):
    fields = (o.get('home_team', ''), o.get('away_team', ''), o.get('league_name', ''))
    return any(k in f for k in JUNK_KEYWORDS for f in fields)


def _confidence(p):
    return 'HIGH' if p >= 0.70 else 'MEDIUM' if p >= 0.55 else 'LOW'


def select_value_bets(candidates):
    """Pure selection logic (unit-testable): best EV per fixture, top N."""
    best = {}
    for o in candidates:
        odds = float(o.get('odds') or 0)
        p = float(o.get('ai_prob') or 0)
        if not (MIN_ODDS <= odds <= MAX_ODDS) or p < MIN_PROB:
            continue
        if 'half' in o.get('market', '').lower():
            continue
        edge = p - 1.0 / odds
        ev = p * odds - 1.0
        if edge < MIN_EDGE or edge > MAX_EDGE or ev < MIN_EV:
            continue
        if _is_junk(o):
            continue
        key = o.get('fixture_id') or f"{o.get('home_team')}_{o.get('away_team')}"
        o = dict(o, edge=edge, ev=ev, confidence=_confidence(p))
        if key not in best or ev > best[key]['ev']:
            best[key] = o
    return sorted(best.values(), key=lambda o: (o['ev'], o['ai_prob']), reverse=True)[:MAX_PICKS]


def generate_value_bets(fixtures, predictor, stats_calculator, date_str=None):
    from utils.fixture_fetcher import (
        _generate_match_options as generate_match_options,
        _format_slip_matches as format_slip_matches,
    )

    target_date = date_str or datetime.utcnow().strftime('%Y-%m-%d')
    if not fixtures:
        return {'status': 'no_fixtures', 'date': target_date, 'match_count': 0,
                'message': 'No fixtures available for Value Bets.'}

    collector = []
    generate_match_options(fixtures, predictor, stats_calculator,
                           af_stats=None, free_mode=False,
                           value_collector=collector)
    print(f"💎 Value Bets: {len(collector)} priced markets scanned")

    picks = select_value_bets(collector)
    formatted = format_slip_matches(picks)
    for f, o in zip(formatted, picks):
        f['ev'] = round(o['ev'] * 100, 1)
        f['implied_probability'] = round(100.0 / o['odds'], 1)
        if o.get('fixture_id'):
            f['fixture_id'] = o['fixture_id']

    db = get_firestore_client()
    db.collection('daily_value_bets').document(target_date).set({
        'date': target_date,
        'matches': formatted,
        'match_count': len(formatted),
        'markets_scanned': len(collector),
        'generated_at': SERVER_TIMESTAMP,
    })
    print(f"💎 Value Bets: wrote {len(formatted)} picks to daily_value_bets/{target_date}")

    try:
        cutoff = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
        for doc in db.collection('daily_value_bets').where('date', '<', cutoff).stream():
            doc.reference.delete()
    except Exception as e:
        print(f"⚠️ Value Bets cleanup failed (non-fatal): {e}")

    return {'status': 'success', 'date': target_date, 'match_count': len(formatted),
            'message': f'{len(formatted)} value bets from {len(collector)} priced markets'}

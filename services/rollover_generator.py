"""
Rollover-specific prediction generator — Safety First.

Strategy:
  - Pick exactly 2 of the SUREST bets each day
  - 2 picks at ~80% each = ~64% daily win rate
  - Only the safest, highest-probability markets are allowed:
      Over 1.5 Goals, Over 2.5 Goals, Double Chance (1X), Double Chance (X2)
      + Under 2.5 Goals / Under 3.5 Goals ONLY for confirmed low-scoring leagues
  - No risky markets: no BTTS, no Away Win, no Draw, no half-time bets
  - Searches ALL leagues (no league filter)
  - Strict probability gates: minimum 80% AI probability
  - Market penalties applied to avoid repeating losing patterns
  - Single pick odds capped at 1.60 → combined max ~2.60 per day
  - Weekly total target ≤ 18 odds (2.6/day × 7 days)
  - NEVER duplicates a fixture already used in Free or AI Pro tabs
  - Stores results in Firestore daily_rollover/{date_str} (separate from AI Pro)
"""
from datetime import datetime, timedelta
from firebase_config import get_firestore_client
from google.cloud.firestore_v1 import SERVER_TIMESTAMP


# Only the SAFEST markets allowed in Rollover
ROLLOVER_ALLOWED_MARKETS = {
    'Over 1.5 Goals',
    'Over 2.5 Goals',
    'Double Chance (1X)',
    'Double Chance (X2)',
}

# Minimum AI probability required per market — raised for higher win rate
ROLLOVER_MIN_PROB = {
    'Over 1.5 Goals':     0.82,
    'Over 2.5 Goals':     0.80,
    'Double Chance (1X)': 0.83,
    'Double Chance (X2)': 0.81,
    'Under 2.5 Goals':    0.80,
    'Under 3.5 Goals':    0.82,
}

# Minimum composite score per market
ROLLOVER_MIN_COMPOSITE = {
    'Over 1.5 Goals':     0.38,
    'Over 2.5 Goals':     0.36,
    'Double Chance (1X)': 0.39,
    'Double Chance (X2)': 0.37,
    'Under 2.5 Goals':    0.36,
    'Under 3.5 Goals':    0.34,
}

# Minimum edge required for rollover picks (model_prob - implied_prob)
ROLLOVER_MIN_EDGE = 0.04

# Min/Max single-pick odds for Rollover
ROLLOVER_MIN_SINGLE_ODDS = 1.20
ROLLOVER_MAX_SINGLE_ODDS = 1.60

# Hard cap on combined slip odds
ROLLOVER_MAX_COMBINED_ODDS = 2.60

# Exactly 2 picks — the 2 surest bets
ROLLOVER_MAX_PICKS = 2

# Max 1 pick of the same market type in one slip (force diversity)
ROLLOVER_MAX_SAME_MARKET = 1


def _is_rollover_market_ok(opt):
    """Allow standard markets plus Under markets for confirmed low-scoring leagues."""
    market = opt.get('market', '')
    if market in ROLLOVER_ALLOWED_MARKETS:
        return True
    if market in ('Under 2.5 Goals', 'Under 3.5 Goals'):
        try:
            from utils.league_dna import get_league_dna
            return get_league_dna(opt.get('league_name', '')).is_low_scoring
        except Exception:
            return False
    return False


def generate_rollover_picks(
    fixtures,
    predictor,
    stats_calculator,
    sm_stats,
    *,
    sm_proxy=None,
    date_str=None,
    num_picks=None,
    market_penalties=None,
    excluded_match_keys=None,
):
    """
    Generate safety-first rollover picks from fixtures.

    Picks the 2 SUREST bets from fixtures NOT already used in Free or AI Pro.
    Uses strict market filtering, 80%+ probability thresholds, edge requirements,
    and a hard combined-odds cap of 2.60 per day (target weekly ≤ 18).

    Args:
        fixtures:             List of fixture dicts from API-Football.
        predictor:            Loaded MultiMarketPredictor instance.
        stats_calculator:     TeamStatsCalculator instance.
        sm_stats:             Stats proxy.
        date_str:             Target date (YYYY-MM-DD). Defaults to today UTC.
        num_picks:            Max number of picks (default ROLLOVER_MAX_PICKS).
        market_penalties:     Dict of {market: multiplier} from market_tracker.
        excluded_match_keys:  Set of "HomeTeam_AwayTeam" strings already used in
                              Free or AI Pro tabs — rollover will skip these.

    Returns:
        dict with keys: status, date, match_count, combined_odds, message
    """
    from utils.fixture_fetcher import _generate_match_options as generate_match_options, _format_slip_matches as format_slip_matches, _slip_confidence as slip_confidence
    from utils.apifootball_stats import clear_cache

    target_date = date_str if date_str else datetime.utcnow().strftime('%Y-%m-%d')
    max_picks = num_picks if num_picks else ROLLOVER_MAX_PICKS

    if not fixtures:
        return {
            'status': 'no_fixtures',
            'date': target_date,
            'match_count': 0,
            'message': 'No fixtures available for rollover.',
        }

    clear_cache()
    excluded = excluded_match_keys or set()

    _JUNK_KEYWORDS = ('II', ' B ', 'U18', 'U19', 'U20', 'U21', 'U23', 'Women', 'Reserves', 'Youth')
    fixtures = [
        f for f in fixtures
        if not any(k in f.get('home_team', '') or k in f.get('away_team', '') or k in f.get('league_name', '')
                   for k in _JUNK_KEYWORDS)
    ]

    print(f"🛡️ Rollover Generator: Analyzing {len(fixtures)} fixtures for {target_date}...")
    if excluded:
        print(f"🛡️ Rollover Generator: Excluding {len(excluded)} fixtures already used in Free/AI Pro")

    # Generate all market options using the full AI + stat qualification pipeline
    all_options = generate_match_options(
        fixtures, predictor, stats_calculator, af_stats=None, free_mode=False
    )

    print(f"🛡️ Rollover Generator: {len(all_options)} total options before safety filter")

    # ── Safety filter: allowed markets with strict thresholds ─────────────────
    safe_options = [
        o for o in all_options
        if _is_rollover_market_ok(o)
        and o['ai_prob'] >= ROLLOVER_MIN_PROB.get(o['market'], 0.78)
        and o['composite_score'] >= ROLLOVER_MIN_COMPOSITE.get(o['market'], 0.50)
        and o.get('edge', 0) >= ROLLOVER_MIN_EDGE
        and o['odds'] >= ROLLOVER_MIN_SINGLE_ODDS
        and o['odds'] <= ROLLOVER_MAX_SINGLE_ODDS
    ]

    # Apply market penalties from recent performance tracking
    if market_penalties:
        for opt in safe_options:
            mkt = opt['market']
            if mkt in market_penalties:
                penalty = market_penalties[mkt]
                opt['composite_score'] *= penalty
        safe_options = [
            o for o in safe_options
            if o['composite_score'] >= ROLLOVER_MIN_COMPOSITE.get(o['market'], 0.53)
        ]

    # ── Exclude fixtures already used in Free or AI Pro tabs ─────────────────
    if excluded:
        before = len(safe_options)
        safe_options = [
            o for o in safe_options
            if f"{o['home_team']}_{o['away_team']}" not in excluded
        ]
        skipped = before - len(safe_options)
        if skipped:
            print(f"🛡️ Rollover Generator: Skipped {skipped} duplicate fixture(s) from Free/AI Pro")

    print(f"🛡️ Rollover Generator: {len(safe_options)} safe options after filtering")

    if not safe_options:
        return {
            'status': 'no_safe_options',
            'date': target_date,
            'match_count': 0,
            'message': 'No qualifying picks met rollover safety standards today.',
        }

    # Sort by value score: composite_score × log(odds) — rewards confidence AND good odds
    import math
    safe_options.sort(key=lambda x: x.get('composite_score', 0) * math.log(max(x['odds'], 1.01)), reverse=True)

    # ── Select the 2 surest bets: one pick per match, market diversity ────────
    slip_matches = []
    combined_odds = 1.0
    used_matches = set()
    market_type_count = {}

    for opt in safe_options:
        if len(slip_matches) >= max_picks:
            break

        potential_combined = combined_odds * opt['odds']
        if potential_combined > ROLLOVER_MAX_COMBINED_ODDS and len(slip_matches) >= 1:
            continue

        match_key = f"{opt['home_team']}_{opt['away_team']}"
        if match_key in used_matches:
            continue
        mkt = opt['market']
        if market_type_count.get(mkt, 0) >= ROLLOVER_MAX_SAME_MARKET:
            continue

        slip_matches.append(opt)
        combined_odds *= opt['odds']
        used_matches.add(match_key)
        market_type_count[mkt] = market_type_count.get(mkt, 0) + 1

    if not slip_matches:
        return {
            'status': 'no_matches',
            'date': target_date,
            'match_count': 0,
            'message': 'Could not build rollover slip from available picks.',
        }

    # ── Enforce combined odds cap ─────────────────────────────────────────────
    while len(slip_matches) > 1:
        combined_odds = 1.0
        for o in slip_matches:
            combined_odds *= o['odds']
        if combined_odds <= ROLLOVER_MAX_COMBINED_ODDS:
            break
        slip_matches.sort(key=lambda x: x['odds'], reverse=True)
        slip_matches.pop(0)

    combined_odds = 1.0
    for o in slip_matches:
        combined_odds *= o['odds']

    formatted = format_slip_matches(slip_matches)
    conf = slip_confidence(slip_matches)

    print(f"🛡️ Rollover Generator: {len(formatted)} picks, "
          f"combined odds {round(combined_odds, 2)}, confidence {conf}")

    # ── Write to Firestore daily_rollover collection ──────────────────────────
    db = get_firestore_client()
    doc_data = {
        'date': target_date,
        'matches': formatted,
        'combined_odds': round(combined_odds, 2),
        'match_count': len(formatted),
        'slip_confidence': conf,
        'generated_at': SERVER_TIMESTAMP,
    }
    db.collection('daily_rollover').document(target_date).set(doc_data)
    print(f"✅ Rollover Generator: Wrote to Firestore daily_rollover/{target_date}")

    # ── Cleanup old rollover docs (> 7 days) ─────────────────────────────────
    try:
        cutoff = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
        old_docs = (
            db.collection('daily_rollover')
            .where('date', '<', cutoff)
            .stream()
        )
        deleted = sum(1 for doc in old_docs if doc.reference.delete() or True)
        if deleted:
            print(f"🗑️ Rollover Generator: Deleted {deleted} old docs (before {cutoff})")
    except Exception as e:
        print(f"⚠️ Rollover Generator: Cleanup failed (non-fatal): {e}")

    return {
        'status': 'success',
        'date': target_date,
        'match_count': len(formatted),
        'combined_odds': round(combined_odds, 2),
        'message': f'Generated {len(formatted)} rollover picks for {target_date}',
    }

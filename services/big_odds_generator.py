"""
Big Odds daily accumulator generator — High Value, Quality Picks.

Strategy:
  - 3–10 picks per day, each with odds ≥ 1.50
  - Combined slip odds target: 6.0 – 15.0
  - All mainstream markets allowed (Home Win, Away Win, Draw, BTTS,
    Over/Under 1.5/2.5/3.5/4.5, Double Chance variants)
  - AI probability thresholds relaxed vs Rollover (50–65% vs 80%+)
    but still quality-gated — not random guesses
  - Market penalties applied to avoid repeating losing patterns
  - NEVER duplicates a fixture already in Free, AI Pro, or Rollover tabs
  - Stores results in Firestore daily_big_odds/{date_str}
"""
import math
from datetime import datetime, timedelta
from firebase_config import get_firestore_client
from google.cloud.firestore_v1 import SERVER_TIMESTAMP


# All mainstream markets allowed — includes 1st/2nd half, team goals, BTTS
BIG_ODDS_ALLOWED_MARKETS = {
    # Full-time result
    'Home Win',
    'Away Win',
    'Draw',
    # Double Chance
    'Double Chance (1X)',
    'Double Chance (X2)',
    'Double Chance (12)',
    # BTTS
    'Both Teams to Score',
    'BTTS No',
    # Full-time Over/Under goals
    'Over 0.5 Goals',
    'Over 1.5 Goals',
    'Over 2.5 Goals',
    'Over 3.5 Goals',
    'Over 4.5 Goals',
    'Under 2.5 Goals',
    'Under 3.5 Goals',
    # Team goals (Home/Away)
    'Home Over 0.5 Goals',
    'Home Over 1.5 Goals',
    'Home Over 2.5 Goals',
    'Away Over 0.5 Goals',
    'Away Over 1.5 Goals',
    'Away Over 2.5 Goals',
    'Home to Score',
    'Away to Score',
    # 1st Half / 2nd Half goals
    '1st Half Over 0.5',
    '2nd Half Over 0.5',
    '1st Half Under 0.5',
    '2nd Half Under 0.5',
}

# Minimum AI probability per market — relaxed but still meaningful gates
BIG_ODDS_MIN_PROB = {
    'Home Win':                0.55,
    'Away Win':                0.50,
    'Draw':                    0.48,
    'Double Chance (1X)':      0.65,
    'Double Chance (X2)':      0.62,
    'Double Chance (12)':      0.62,
    'Both Teams to Score':     0.58,
    'BTTS No':                 0.52,
    'Over 0.5 Goals':          0.75,
    'Over 1.5 Goals':          0.65,
    'Over 2.5 Goals':          0.58,
    'Over 3.5 Goals':          0.50,
    'Over 4.5 Goals':          0.45,
    'Under 2.5 Goals':         0.55,
    'Under 3.5 Goals':         0.60,
    'Home Over 0.5 Goals':     0.68,
    'Home Over 1.5 Goals':     0.60,
    'Home Over 2.5 Goals':     0.50,
    'Away Over 0.5 Goals':     0.65,
    'Away Over 1.5 Goals':     0.55,
    'Away Over 2.5 Goals':     0.48,
    'Home to Score':           0.68,
    'Away to Score':           0.62,
    '1st Half Over 0.5':       0.62,
    '2nd Half Over 0.5':       0.62,
    '1st Half Under 0.5':      0.55,
    '2nd Half Under 0.5':      0.55,
}

# Minimum composite score per market
BIG_ODDS_MIN_COMPOSITE = {
    'Home Win':                0.35,
    'Away Win':                0.32,
    'Draw':                    0.30,
    'Double Chance (1X)':      0.42,
    'Double Chance (X2)':      0.40,
    'Double Chance (12)':      0.40,
    'Both Teams to Score':     0.36,
    'BTTS No':                 0.33,
    'Over 0.5 Goals':          0.48,
    'Over 1.5 Goals':          0.42,
    'Over 2.5 Goals':          0.38,
    'Over 3.5 Goals':          0.33,
    'Over 4.5 Goals':          0.28,
    'Under 2.5 Goals':         0.36,
    'Under 3.5 Goals':         0.40,
    'Home Over 0.5 Goals':     0.42,
    'Home Over 1.5 Goals':     0.38,
    'Home Over 2.5 Goals':     0.32,
    'Away Over 0.5 Goals':     0.40,
    'Away Over 1.5 Goals':     0.35,
    'Away Over 2.5 Goals':     0.30,
    'Home to Score':           0.42,
    'Away to Score':           0.38,
    '1st Half Over 0.5':       0.38,
    '2nd Half Over 0.5':       0.38,
    '1st Half Under 0.5':      0.35,
    '2nd Half Under 0.5':      0.35,
}

# Minimum edge over bookmaker implied probability
BIG_ODDS_MIN_EDGE = 0.02

# Single-pick odds range: 1.50 minimum, 5.00 maximum
BIG_ODDS_MIN_SINGLE_ODDS = 1.50
BIG_ODDS_MAX_SINGLE_ODDS = 5.00

# Combined slip odds range
BIG_ODDS_MIN_COMBINED = 4.0
BIG_ODDS_MAX_COMBINED = 8.0

# Pick count range
BIG_ODDS_MIN_PICKS = 2
BIG_ODDS_MAX_PICKS = 6

# Max 2 picks of the same market type per slip (more flexible than rollover)
BIG_ODDS_MAX_SAME_MARKET = 2


def generate_big_odds_picks(
    fixtures,
    predictor,
    stats_calculator,
    sm_stats,
    *,
    sm_proxy=None,
    date_str=None,
    market_penalties=None,
    excluded_match_keys=None,
):
    """
    Generate high-value Big Odds accumulator picks from fixtures.

    Targets 3–10 picks with individual odds ≥1.50 and combined 6–15.
    Uses relaxed probability thresholds vs Rollover for better odds.

    Args:
        fixtures:             List of fixture dicts from API-Football.
        predictor:            Loaded MultiMarketPredictor instance.
        stats_calculator:     TeamStatsCalculator instance.
        sm_stats:             Stats proxy.
        date_str:             Target date (YYYY-MM-DD). Defaults to today UTC.
        market_penalties:     Dict of {market: multiplier} from market_tracker.
        excluded_match_keys:  Set of "HomeTeam_AwayTeam" strings already used
                              in Free, AI Pro, or Rollover tabs.

    Returns:
        dict with keys: status, date, match_count, combined_odds, message
    """
    from utils.fixture_fetcher import (
        _generate_match_options as generate_match_options,
        _format_slip_matches as format_slip_matches,
        _slip_confidence as slip_confidence,
    )
    from utils.apifootball_stats import clear_cache

    target_date = date_str if date_str else datetime.utcnow().strftime('%Y-%m-%d')

    if not fixtures:
        return {
            'status': 'no_fixtures',
            'date': target_date,
            'match_count': 0,
            'message': 'No fixtures available for Big Odds.',
        }

    clear_cache()
    excluded = excluded_match_keys or set()

    # Drop reserve/youth/women fixtures — unreliable data, inflates odds artificially
    _JUNK_KEYWORDS = ('II', ' B ', 'U18', 'U19', 'U20', 'U21', 'U23', 'Women', 'Reserves', 'Youth')
    fixtures = [
        f for f in fixtures
        if not any(k in f.get('home_team', '') or k in f.get('away_team', '') or k in f.get('league_name', '')
                   for k in _JUNK_KEYWORDS)
    ]

    print(f"🎯 Big Odds Generator: Analyzing {len(fixtures)} fixtures for {target_date}...")
    if excluded:
        print(f"🎯 Big Odds Generator: Excluding {len(excluded)} fixtures already used in other tabs")

    # Generate all market options through the full AI + stats pipeline
    all_options = generate_match_options(
        fixtures, predictor, stats_calculator, af_stats=None, free_mode=False
    )

    print(f"🎯 Big Odds Generator: {len(all_options)} total options before filter")

    # ── Quality filter: allowed markets + relaxed thresholds ──────────────────
    safe_options = [
        o for o in all_options
        if o['market'] in BIG_ODDS_ALLOWED_MARKETS
        and o['ai_prob'] >= BIG_ODDS_MIN_PROB.get(o['market'], 0.50)
        and o['composite_score'] >= BIG_ODDS_MIN_COMPOSITE.get(o['market'], 0.32)
        and o.get('edge', 0) >= BIG_ODDS_MIN_EDGE
        and o['odds'] >= BIG_ODDS_MIN_SINGLE_ODDS
        and o['odds'] <= BIG_ODDS_MAX_SINGLE_ODDS
    ]

    # Apply market penalties from recent performance tracking
    if market_penalties:
        for opt in safe_options:
            mkt = opt['market']
            if mkt in market_penalties:
                opt['composite_score'] *= market_penalties[mkt]
        safe_options = [
            o for o in safe_options
            if o['composite_score'] >= BIG_ODDS_MIN_COMPOSITE.get(o['market'], 0.28)
        ]

    # ── Exclude fixtures already used in other tabs ───────────────────────────
    if excluded:
        before = len(safe_options)
        safe_options = [
            o for o in safe_options
            if f"{o['home_team']}_{o['away_team']}" not in excluded
        ]
        skipped = before - len(safe_options)
        if skipped:
            print(f"🎯 Big Odds Generator: Skipped {skipped} duplicate fixture(s)")

    print(f"🎯 Big Odds Generator: {len(safe_options)} quality options after filtering")

    if not safe_options:
        return {
            'status': 'no_safe_options',
            'date': target_date,
            'match_count': 0,
            'message': 'No qualifying picks met Big Odds quality standards today.',
        }

    # Sort by value score: composite_score × log(odds) — rewards confidence AND good odds
    safe_options.sort(
        key=lambda x: x.get('composite_score', 0) * math.log(max(x['odds'], 1.01)),
        reverse=True,
    )

    # ── Build slip greedily: fill until combined > MAX or count = MAX ─────────
    slip_matches = []
    combined_odds = 1.0
    used_matches = set()
    market_type_count = {}

    for opt in safe_options:
        if len(slip_matches) >= BIG_ODDS_MAX_PICKS:
            break

        potential_combined = combined_odds * opt['odds']

        # Skip if adding this would push combined over MAX (unless we need more picks)
        if potential_combined > BIG_ODDS_MAX_COMBINED and len(slip_matches) >= BIG_ODDS_MIN_PICKS:
            continue

        match_key = f"{opt['home_team']}_{opt['away_team']}"
        if match_key in used_matches:
            continue

        mkt = opt['market']
        if market_type_count.get(mkt, 0) >= BIG_ODDS_MAX_SAME_MARKET:
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
            'message': 'Could not build Big Odds slip from available picks.',
        }

    # ── Enforce MAX combined: remove highest-odds picks until within range ────
    while len(slip_matches) > BIG_ODDS_MIN_PICKS:
        combined_odds = 1.0
        for o in slip_matches:
            combined_odds *= o['odds']
        if combined_odds <= BIG_ODDS_MAX_COMBINED:
            break
        slip_matches.sort(key=lambda x: x['odds'], reverse=True)
        slip_matches.pop(0)

    # ── Try to reach MIN combined by adding lower-odds picks from pool ────────
    combined_odds = 1.0
    for o in slip_matches:
        combined_odds *= o['odds']

    if combined_odds < BIG_ODDS_MIN_COMBINED:
        for opt in safe_options:
            if len(slip_matches) >= BIG_ODDS_MAX_PICKS:
                break
            match_key = f"{opt['home_team']}_{opt['away_team']}"
            if match_key in used_matches:
                continue
            mkt = opt['market']
            if market_type_count.get(mkt, 0) >= BIG_ODDS_MAX_SAME_MARKET:
                continue
            test_combined = combined_odds * opt['odds']
            if test_combined <= BIG_ODDS_MAX_COMBINED:
                slip_matches.append(opt)
                combined_odds = test_combined
                used_matches.add(match_key)
                market_type_count[mkt] = market_type_count.get(mkt, 0) + 1
                if combined_odds >= BIG_ODDS_MIN_COMBINED:
                    break

    # Final combined odds recalculation
    combined_odds = 1.0
    for o in slip_matches:
        combined_odds *= o['odds']

    # Require minimum picks
    if len(slip_matches) < BIG_ODDS_MIN_PICKS:
        return {
            'status': 'insufficient_picks',
            'date': target_date,
            'match_count': len(slip_matches),
            'message': (
                f'Only {len(slip_matches)} qualifying picks found; '
                f'minimum is {BIG_ODDS_MIN_PICKS}.'
            ),
        }

    formatted = format_slip_matches(slip_matches)
    conf = slip_confidence(slip_matches)

    print(
        f"🎯 Big Odds Generator: {len(formatted)} picks, "
        f"combined odds {round(combined_odds, 2)}, confidence {conf}"
    )

    # ── Write to Firestore daily_big_odds collection ──────────────────────────
    db = get_firestore_client()
    doc_data = {
        'date': target_date,
        'matches': formatted,
        'combined_odds': round(combined_odds, 2),
        'match_count': len(formatted),
        'slip_confidence': conf,
        'generated_at': SERVER_TIMESTAMP,
    }
    db.collection('daily_big_odds').document(target_date).set(doc_data)
    print(f"✅ Big Odds Generator: Wrote to Firestore daily_big_odds/{target_date}")

    # ── Cleanup old docs (> 14 days) ─────────────────────────────────────────
    try:
        cutoff = (datetime.utcnow() - timedelta(days=14)).strftime('%Y-%m-%d')
        old_docs = (
            db.collection('daily_big_odds')
            .where('date', '<', cutoff)
            .stream()
        )
        deleted = sum(1 for doc in old_docs if doc.reference.delete() or True)
        if deleted:
            print(f"🗑️ Big Odds Generator: Deleted {deleted} old docs (before {cutoff})")
    except Exception as e:
        print(f"⚠️ Big Odds Generator: Cleanup failed (non-fatal): {e}")

    return {
        'status': 'success',
        'date': target_date,
        'match_count': len(formatted),
        'combined_odds': round(combined_odds, 2),
        'message': f'Generated {len(formatted)} Big Odds picks for {target_date}',
    }

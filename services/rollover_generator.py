"""
Rollover-specific prediction generator — Safety First.

Strategy:
  - Only the safest, highest-probability markets are allowed:
      Over 1.5 Goals, Over 2.5 Goals, Double Chance (1X), Double Chance (X2)
  - No risky markets: no BTTS, no Away Win, no Draw, no half-time bets
  - Searches ALL leagues (no league filter) so dominant-team vs weak-team
    fixtures in ANY league can be included (e.g. PSG vs small club → Over 1.5)
  - DYNAMIC pick count: only include picks that truly qualify (1-3 max)
  - Strict probability gates per market
  - Market penalties applied to avoid repeating losing patterns
  - Combined odds capped at 2.20 to keep daily slip safe
  - Stores results in Firestore daily_rollover/{date_str} (separate from AI Pro)
"""
from datetime import datetime, timedelta
from firebase_config import get_firestore_client
from google.cloud.firestore_v1 import SERVER_TIMESTAMP


# Only these markets are allowed in Rollover — the safest available
ROLLOVER_ALLOWED_MARKETS = {
    'Over 1.5 Goals',
    'Over 2.5 Goals',
    'Double Chance (1X)',
    'Double Chance (X2)',
}

# Minimum AI probability required per market for Rollover inclusion
# Balanced: strict enough to win, but relaxed enough to find 1-3 picks
ROLLOVER_MIN_PROB = {
    'Over 1.5 Goals':     0.74,
    'Over 2.5 Goals':     0.68,
    'Double Chance (1X)': 0.76,
    'Double Chance (X2)': 0.74,
}

# Minimum composite score per market (edge + prob + stability blend)
ROLLOVER_MIN_COMPOSITE = {
    'Over 1.5 Goals':     0.50,
    'Over 2.5 Goals':     0.48,
    'Double Chance (1X)': 0.51,
    'Double Chance (X2)': 0.50,
}

# Minimum edge required for rollover picks (model_prob - implied_prob)
ROLLOVER_MIN_EDGE = 0.05

# Max single-pick odds for Rollover — keeps each pick very safe
ROLLOVER_MAX_SINGLE_ODDS = 1.45

# Max combined odds for the entire slip — prevents risky accumulation
ROLLOVER_MAX_COMBINED_ODDS = 2.20

# Max picks per slip — reduced from 5 to 3 for higher daily win rate
ROLLOVER_MAX_PICKS = 3

# Max 1 pick of the same market type in one slip (force diversity)
ROLLOVER_MAX_SAME_MARKET = 1


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
):
    """
    Generate safety-first rollover picks from fixtures.

    Uses the same fixture pipeline as the main generator but applies strict
    market filtering, higher probability thresholds, edge requirements, and
    market penalties, then stores results in the separate daily_rollover
    Firestore collection.

    DYNAMIC PICK COUNT: Returns only picks that truly qualify (1 to ROLLOVER_MAX_PICKS).
    If no picks meet the strict safety standards, returns 0 picks rather than
    lowering the bar.

    Args:
        fixtures:          List of fixture dicts from SportMonks (all leagues).
        predictor:         Loaded MultiMarketPredictor instance.
        stats_calculator:  TeamStatsCalculator instance.
        sm_stats:          SportMonks stats proxy.
        date_str:          Target date (YYYY-MM-DD). Defaults to today UTC.
        num_picks:         Max number of picks (default ROLLOVER_MAX_PICKS).
        market_penalties:  Dict of {market: multiplier} from market_tracker.

    Returns:
        dict with keys: status, date, match_count, combined_odds, message
    """
    from utils.fixture_fetcher import generate_match_options, format_slip_matches, slip_confidence
    from utils.sportmonks_stats import clear_cache

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
    print(f"🛡️ Rollover Generator: Analyzing {len(fixtures)} fixtures for {target_date}...")

    # Generate all market options using the full AI + stat qualification pipeline
    all_options = generate_match_options(
        fixtures, predictor, stats_calculator, sm_stats, free_mode=False
    )

    print(f"🛡️ Rollover Generator: {len(all_options)} total options before safety filter")

    # ── Safety filter: only the allowed markets with strict thresholds ────────
    safe_options = [
        o for o in all_options
        if o['market'] in ROLLOVER_ALLOWED_MARKETS
        and o['ai_prob'] >= ROLLOVER_MIN_PROB.get(o['market'], 0.74)
        and o['composite_score'] >= ROLLOVER_MIN_COMPOSITE.get(o['market'], 0.50)
        and o.get('edge', 0) >= ROLLOVER_MIN_EDGE
        and o['odds'] >= 1.10
        and o['odds'] <= ROLLOVER_MAX_SINGLE_ODDS
    ]

    # Apply market penalties from recent performance tracking
    if market_penalties:
        for opt in safe_options:
            mkt = opt['market']
            if mkt in market_penalties:
                penalty = market_penalties[mkt]
                opt['composite_score'] *= penalty
                # Re-check composite threshold after penalty
        safe_options = [
            o for o in safe_options
            if o['composite_score'] >= ROLLOVER_MIN_COMPOSITE.get(o['market'], 0.50)
        ]

    print(f"🛡️ Rollover Generator: {len(safe_options)} safe options after filtering")

    if not safe_options:
        return {
            'status': 'no_safe_options',
            'date': target_date,
            'match_count': 0,
            'message': 'No qualifying picks met rollover safety standards today.',
        }

    # Sort by composite_score descending (most confident first)
    safe_options.sort(key=lambda x: x.get('composite_score', 0), reverse=True)

    # ── Select slip: one pick per match, max max_picks, market diversity ──────
    # DYNAMIC: Only include picks that qualify. Could be 1, 2, or 3.
    slip_matches = []
    combined_odds = 1.0
    used_matches = set()
    market_type_count = {}

    for opt in safe_options:
        if len(slip_matches) >= max_picks:
            break

        # Check if adding this pick would exceed combined odds cap
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

    # ── Enforce combined odds 1.50–2.20 ──────────────────────────────────────
    ROLLOVER_MIN_COMBINED = 1.50

    # Cap: remove highest-odds pick until combined ≤ max
    while len(slip_matches) > 1:
        combined_odds = 1.0
        for o in slip_matches:
            combined_odds *= o['odds']
        if combined_odds <= ROLLOVER_MAX_COMBINED_ODDS:
            break
        slip_matches.sort(key=lambda x: x['odds'], reverse=True)
        slip_matches.pop(0)

    # Recalculate combined_odds after enforcement
    combined_odds = 1.0
    for o in slip_matches:
        combined_odds *= o['odds']

    # Floor: if combined < min, try adding more safe options
    if combined_odds < ROLLOVER_MIN_COMBINED:
        used_matches_final = {f"{o['home_team']}_{o['away_team']}" for o in slip_matches}
        for opt in safe_options:
            match_key = f"{opt['home_team']}_{opt['away_team']}"
            if match_key in used_matches_final:
                continue
            test_combined = combined_odds * opt['odds']
            if test_combined <= ROLLOVER_MAX_COMBINED_ODDS:
                slip_matches.append(opt)
                combined_odds = test_combined
                used_matches_final.add(match_key)
                if combined_odds >= ROLLOVER_MIN_COMBINED:
                    break

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

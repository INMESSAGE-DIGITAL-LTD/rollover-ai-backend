"""
Rollover-specific prediction generator — Safety First.

Strategy:
  - Only the safest, highest-probability markets are allowed:
      Over 1.5 Goals, Over 2.5 Goals, Double Chance (1X), Double Chance (X2)
  - No risky markets: no BTTS, no Away Win, no Draw, no half-time bets
  - Searches ALL leagues (no league filter) so dominant-team vs weak-team
    fixtures in ANY league can be included (e.g. PSG vs small club → Over 1.5)
  - Strict probability gates per market
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
ROLLOVER_MIN_PROB = {
    'Over 1.5 Goals':     0.70,
    'Over 2.5 Goals':     0.65,
    'Double Chance (1X)': 0.75,
    'Double Chance (X2)': 0.73,
}

# Minimum composite score per market
ROLLOVER_MIN_COMPOSITE = {
    'Over 1.5 Goals':     0.49,
    'Over 2.5 Goals':     0.47,
    'Double Chance (1X)': 0.50,
    'Double Chance (X2)': 0.49,
}

# Max single-pick odds for Rollover — keeps each pick very safe
ROLLOVER_MAX_SINGLE_ODDS = 1.57

# Max 2 picks of the same market type in one slip (diversity)
ROLLOVER_MAX_SAME_MARKET = 2


def generate_rollover_picks(
    fixtures,
    predictor,
    stats_calculator,
    sm_stats,
    *,
    sm_proxy=None,
    date_str=None,
    num_picks=5,
):
    """
    Generate safety-first rollover picks from fixtures.

    Uses the same fixture pipeline as the main generator but applies strict
    market filtering and higher probability thresholds, then stores results in
    the separate daily_rollover Firestore collection.

    Args:
        fixtures:          List of fixture dicts from SportMonks (all leagues).
        predictor:         Loaded MultiMarketPredictor instance.
        stats_calculator:  TeamStatsCalculator instance.
        sm_stats:          SportMonks stats proxy.
        date_str:          Target date (YYYY-MM-DD). Defaults to today UTC.
        num_picks:         Max number of picks to include (default 5).

    Returns:
        dict with keys: status, date, match_count, combined_odds, message
    """
    from utils.fixture_fetcher import generate_match_options, format_slip_matches, slip_confidence
    from utils.sportmonks_stats import clear_cache

    target_date = date_str if date_str else datetime.utcnow().strftime('%Y-%m-%d')

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
        and o['ai_prob'] >= ROLLOVER_MIN_PROB.get(o['market'], 0.70)
        and o['composite_score'] >= ROLLOVER_MIN_COMPOSITE.get(o['market'], 0.49)
        and o['odds'] >= 1.10
        and o['odds'] <= ROLLOVER_MAX_SINGLE_ODDS
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

    # ── Select slip: one pick per match, max num_picks, market diversity ─────
    slip_matches = []
    combined_odds = 1.0
    used_matches = set()
    market_type_count = {}

    for opt in safe_options:
        if len(slip_matches) >= num_picks:
            break
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

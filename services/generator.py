"""
Daily prediction generator — shared service layer.

Used by:
  - app.py (POST /api/generate-daily — manual trigger)
  - cron_generate.py (Render cron job — scheduled daily)

No HTTP, no Flask, no routing. Pure business logic.
"""
from datetime import datetime, timedelta
from firebase_config import get_firestore_client
from google.cloud.firestore_v1 import SERVER_TIMESTAMP


def generate_and_store(
    fixtures,
    predictor,
    stats_calculator,
    sm_stats,
    *,
    num_matches=10,
    min_odds=1.10,
    max_odds=1.60,
    save_sqlite_fn=None,
    sm_proxy=None,
):
    """
    Run AI predictions on fixtures and write results to Firestore.

    Args:
        fixtures: List of fixture dicts from SportMonks.
        predictor: Loaded MultiMarketPredictor instance.
        stats_calculator: TeamStatsCalculator instance.
        sm_stats: SportMonks stats proxy.
        num_matches: Max matches to generate (default 10).
        min_odds: Minimum odds filter (default 1.10).
        max_odds: Maximum odds filter (default 1.60).
        save_sqlite_fn: Optional callable(date_str, picks_list) for SQLite backup.

    Returns:
        dict with keys: status, date, match_count, combined_odds, message
    """
    from utils.sportmonks_stats import clear_cache
    from utils.fixture_fetcher import build_parlay_slip
    from utils.market_tracker import get_market_penalties

    today_str = datetime.utcnow().strftime('%Y-%m-%d')

    if not fixtures:
        return {
            'status': 'no_fixtures',
            'date': today_str,
            'match_count': 0,
            'message': 'No fixtures available for today.',
        }

    # Analyse last 7 days of results to penalise underperforming markets.
    # This is the pseudo-learning layer: the model won't blindly repeat a market
    # that has lost ≥50% of picks in the past week.
    market_penalties = {}
    if sm_proxy is not None:
        try:
            market_penalties = get_market_penalties(sm_proxy, lookback_days=7, min_picks=3)
            if market_penalties:
                print(f"📊 Generator: Applied market penalties for {len(market_penalties)} market(s)")
        except Exception as e:
            print(f"⚠️ Generator: Market tracker failed (non-fatal): {e}")

    # Run AI
    print(f"🧠 Generator: Running AI on {len(fixtures)} fixtures (max={num_matches})...")
    clear_cache()
    result = build_parlay_slip(
        fixtures, predictor, stats_calculator,
        num_matches=num_matches,
        min_odds=min_odds,
        max_odds=max_odds,
        sm_stats=sm_stats,
        free_mode=False,
        market_penalties=market_penalties,
    )

    slip = result.get('slip', {})
    matches = slip.get('matches', [])

    if not matches:
        return {
            'status': 'no_matches',
            'date': today_str,
            'match_count': 0,
            'message': 'AI could not generate matches for today.',
        }

    print(f"✅ Generator: {len(matches)} matches, combined odds: {slip.get('combined_odds', 0)}")

    # Write to Firestore
    db = get_firestore_client()

    doc_data = {
        'date': today_str,
        'total_fixtures_analyzed': result.get('total_fixtures_analyzed', len(fixtures)),
        'matches': matches,
        'combined_odds': slip.get('combined_odds', 0),
        'slip_confidence': slip.get('slip_confidence', 'NONE'),
        'match_count': len(matches),
        'generated_at': SERVER_TIMESTAMP,
    }

    db.collection('daily_predictions').document(today_str).set(doc_data)
    print(f"✅ Generator: Wrote to Firestore daily_predictions/{today_str}")

    # Cleanup old docs (> 7 days)
    _cleanup_old_predictions(db)

    # Optional SQLite backup
    if save_sqlite_fn:
        try:
            picks_for_history = [
                {
                    "home_team": m.get("home_team", ""),
                    "away_team": m.get("away_team", ""),
                    "market": m.get("market", ""),
                    "odds": m.get("odds", 0),
                    "confidence": m.get("ai_probability", 0),
                    "result": "pending",
                    "league": m.get("league", ""),
                    "home_logo": m.get("home_logo"),
                    "away_logo": m.get("away_logo"),
                    "league_logo": m.get("league_logo"),
                    "home_short_code": m.get("home_short_code"),
                    "away_short_code": m.get("away_short_code"),
                    "kickoff": m.get("kickoff"),
                }
                for m in matches
            ]
            save_sqlite_fn(today_str, picks_for_history)
            print(f"💾 Generator: Saved to SQLite history")
        except Exception as e:
            print(f"⚠️ Generator: SQLite save failed (non-fatal): {e}")

    return {
        'status': 'success',
        'date': today_str,
        'match_count': len(matches),
        'combined_odds': slip.get('combined_odds', 0),
        'message': f'Generated {len(matches)} predictions for {today_str}',
    }


def _cleanup_old_predictions(db):
    """Delete daily_predictions docs older than 7 days."""
    try:
        cutoff = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
        old_docs = (
            db.collection('daily_predictions')
            .where('date', '<', cutoff)
            .stream()
        )
        deleted = 0
        for doc in old_docs:
            doc.reference.delete()
            deleted += 1
        if deleted:
            print(f"🗑️ Generator: Deleted {deleted} old docs (before {cutoff})")
    except Exception as e:
        print(f"⚠️ Generator: Cleanup failed (non-fatal): {e}")

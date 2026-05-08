"""
Render Cron Job: Generate daily predictions and write to Firestore.
Runs daily at 00:00 WAT (23:00 UTC) via Render's built-in cron scheduler.

No HTTP. No Flask. Pure worker script.
Imports the shared generator service for all business logic.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from utils.fixture_fetcher import fetch_fixtures_by_date
from utils.apifootball_stats import ApiFootballStats
from utils.apifootball_proxy import ApiFootballProxy
from models.multi_market_predictor import MultiMarketPredictor
from utils.team_stats import TeamStatsCalculator
from history import init_history_db, save_daily_picks
from services.generator import generate_and_store


def main():
    # Cron runs at 23:00 UTC = 00:00 WAT. We generate picks for the NEXT UTC
    # day so that WAT users see their "today" picks ready at midnight.
    target_str = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"🕛 Cron worker started — generating picks for {target_str}")

    # Load models
    print("🔄 Loading models...")
    predictor = MultiMarketPredictor()
    predictor.load_models('models/trained')
    stats_calculator = TeamStatsCalculator('data/raw/all_matches.csv')
    af_stats = ApiFootballStats()
    af_proxy = ApiFootballProxy()
    print("✅ Models loaded")

    # Fetch fixtures for the target date
    fixtures = fetch_fixtures_by_date(target_str, no_league_filter=True)

    # Init SQLite for backup
    init_history_db()

    # Step 1: Update results for the last 3 days before generating new picks.
    try:
        from utils.result_updater import update_past_results
        update_past_results(af_proxy, days_back=3)
    except Exception as e:
        print(f"⚠️ Result updater failed (non-fatal): {e}")

    # Step 2: Run generator service (AI → market tracker → Firestore → cleanup)
    result = generate_and_store(
        fixtures, predictor, stats_calculator, af_stats,
        sm_proxy=af_proxy,
        date_str=target_str,
    )

    print(f"🎉 AI Pro generation complete: {result['message']}")

    # Step 3: Generate Rollover picks — reuse same fixtures, no extra API calls
    try:
        from services.rollover_generator import generate_rollover_picks
        from utils.market_tracker import get_market_penalties as _get_cron_mp
        _cron_mp = {}
        try:
            _cron_mp = _get_cron_mp(af_proxy, lookback_days=7, min_picks=3)
        except Exception:
            pass
        rollover_result = generate_rollover_picks(
            fixtures, predictor, stats_calculator, af_stats,
            sm_proxy=af_proxy,
            date_str=target_str,
            market_penalties=_cron_mp,
        )
        print(f"🛡️ Rollover generation complete: {rollover_result['message']}")
    except Exception as e:
        print(f"⚠️ Rollover generation failed (non-fatal): {e}")

    # Step 4: Generate AI Pro tips
    try:
        from services.ai_pro_generator import generate_ai_pro_picks
        ai_pro_result = generate_ai_pro_picks(
            fixtures, predictor, stats_calculator, af_stats,
            sm_proxy=af_proxy,
            date_str=target_str,
            market_penalties=_cron_mp,
        )
        print(f"🧠 AI Pro generation complete: {ai_pro_result['message']}")
    except Exception as e:
        print(f"⚠️ AI Pro generation failed (non-fatal): {e}")

    print(f"🎉 Cron complete for {target_str}")


if __name__ == '__main__':
    main()


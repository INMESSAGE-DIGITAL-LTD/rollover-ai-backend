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
from utils.sportmonks_stats import fetch_team_stats, fetch_h2h
from utils.sportmonks_proxy import SportMonksProxy
from models.multi_market_predictor import MultiMarketPredictor
from utils.team_stats import TeamStatsCalculator
from history import init_history_db, save_daily_picks
from services.generator import generate_and_store


class _SmStatsProxy:
    def fetch_team_stats(self, team_id):
        return fetch_team_stats(team_id)
    def fetch_h2h(self, team1_id, team2_id):
        return fetch_h2h(team1_id, team2_id)


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
    sm_stats = _SmStatsProxy()
    sm_proxy = SportMonksProxy()
    print("✅ Models loaded")

    # Fetch fixtures for the target date
    fixtures = fetch_fixtures_by_date(target_str)

    # Init SQLite for backup
    init_history_db()

    # Step 1: Update results for the last 3 days before generating new picks.
    # This marks past picks as won/lost so the app can show history and the
    # market tracker has accurate data to penalise underperforming markets.
    try:
        from utils.result_updater import update_past_results
        update_past_results(sm_proxy, days_back=3)
    except Exception as e:
        print(f"⚠️ Result updater failed (non-fatal): {e}")

    # Step 2: Run generator service (AI → market tracker → Firestore → cleanup)
    result = generate_and_store(
        fixtures, predictor, stats_calculator, sm_stats,
        sm_proxy=sm_proxy,
        date_str=target_str,
    )

    print(f"🎉 Cron complete: {result['message']}")


if __name__ == '__main__':
    main()

"""
Render Cron Job: Backup pick generation — runs at 07:30 UTC daily.

Only generates picks if the primary 00:05 UTC cron failed or produced no
results. Skips silently if all tabs already have picks for today.
This handles cases where the primary cron ran before API-Football published
today's fixtures, or the Render instance was cold-starting.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone
from firebase_config import get_firestore_client


def _has_picks_today(db, date_str):
    """Return True if ALL main tabs already have picks for today."""
    checks = [
        ('daily_predictions', 'matches'),
        ('daily_ai_pro', 'tips'),
    ]
    for collection, key in checks:
        try:
            doc = db.collection(collection).document(date_str).get()
            if not doc.exists:
                return False
            data = doc.to_dict() or {}
            if len(data.get(key, [])) == 0:
                return False
        except Exception:
            return False
    return True


def main():
    target_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    print(f"🔁 Backup cron started — checking picks for {target_str}")

    try:
        db = get_firestore_client()
    except Exception as e:
        print(f"❌ Firestore unavailable: {e}")
        return

    if _has_picks_today(db, target_str):
        print(f"✅ Picks already exist for {target_str} — skipping generation")
        return

    print(f"⚠️ Missing picks for {target_str} — running full generation now")

    # Delegate to the primary generation script
    from utils.fixture_fetcher import fetch_fixtures_by_date
    from utils.apifootball_stats import ApiFootballStats
    from utils.apifootball_proxy import ApiFootballProxy
    from models.multi_market_predictor import MultiMarketPredictor
    from utils.team_stats import TeamStatsCalculator
    from history import init_history_db

    predictor = MultiMarketPredictor()
    predictor.load_models('models/trained')
    stats_calculator = TeamStatsCalculator('data/raw/all_matches.csv')
    af_stats = ApiFootballStats()
    af_proxy = ApiFootballProxy()

    fixtures = fetch_fixtures_by_date(target_str, no_league_filter=True)

    init_history_db()

    # Update results first
    try:
        from utils.result_updater import update_past_results
        update_past_results(af_proxy, days_back=3)
    except Exception as e:
        print(f"⚠️ Result updater failed (non-fatal): {e}")

    from utils.market_tracker import get_market_penalties
    market_penalties = {}
    try:
        market_penalties = get_market_penalties(af_proxy, lookback_days=7, min_picks=3)
    except Exception:
        pass

    # Free picks
    from services.generator import generate_and_store
    r = generate_and_store(
        fixtures, predictor, stats_calculator, af_stats,
        sm_proxy=af_proxy, date_str=target_str,
    )
    print(f"🎉 Free picks: {r['message']}")

    # AI Pro
    try:
        from services.ai_pro_generator import generate_ai_pro_picks
        r = generate_ai_pro_picks(
            fixtures, predictor, stats_calculator, af_stats,
            sm_proxy=af_proxy, date_str=target_str, market_penalties=market_penalties,
        )
        print(f"🧠 AI Pro: {r['message']}")
    except Exception as e:
        print(f"⚠️ AI Pro failed: {e}")

    # Rollover
    try:
        from services.rollover_generator import generate_rollover_picks
        r = generate_rollover_picks(
            fixtures, predictor, stats_calculator, af_stats,
            sm_proxy=af_proxy, date_str=target_str, market_penalties=market_penalties,
        )
        print(f"🛡️ Rollover: {r['message']}")
    except Exception as e:
        print(f"⚠️ Rollover failed: {e}")

    # Big Odds
    try:
        from services.big_odds_generator import generate_big_odds_picks
        excluded = set()
        for col, key in [('daily_ai_pro', 'tips'), ('daily_predictions', 'matches'), ('daily_rollover', 'matches')]:
            try:
                doc = db.collection(col).document(target_str).get()
                if doc.exists:
                    for m in (doc.to_dict() or {}).get(key, []):
                        h, a = m.get('home_team', ''), m.get('away_team', '')
                        if h and a:
                            excluded.add(f"{h}_{a}")
            except Exception:
                pass
        r = generate_big_odds_picks(
            fixtures, predictor, stats_calculator, af_stats,
            sm_proxy=af_proxy, date_str=target_str,
            market_penalties=market_penalties, excluded_match_keys=excluded,
        )
        print(f"🎯 Big Odds: {r['message']}")
    except Exception as e:
        print(f"⚠️ Big Odds failed: {e}")

    print(f"✅ Backup generation complete for {target_str}")


if __name__ == '__main__':
    main()

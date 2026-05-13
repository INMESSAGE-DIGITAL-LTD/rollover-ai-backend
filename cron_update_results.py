"""
Render Cron Job: Resolve past pick results from API-Football scores.
Runs daily at 23:30 UTC — after European games finish.

No HTTP. No Flask. Pure worker script.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.result_updater import update_past_results
from utils.apifootball_proxy import ApiFootballProxy


def main():
    print("🔄 Result updater cron started")
    af_proxy = ApiFootballProxy()
    summary = update_past_results(af_proxy, days_back=4)
    print(f"✅ Done — {summary.get('updated', 0)} resolved, {summary.get('errors', 0)} void")


if __name__ == '__main__':
    main()

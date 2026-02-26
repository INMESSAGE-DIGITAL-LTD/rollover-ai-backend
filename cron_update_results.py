"""
Render Cron Job: Resolve past pick results from SportMonks scores.
Runs daily at 23:30 UTC — after European games finish.

No HTTP. No Flask. Pure worker script.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.result_updater import update_past_results
from utils.sportmonks_proxy import SportMonksProxy


def main():
    print("🔄 Result updater cron started")
    sm_proxy = SportMonksProxy()
    summary = update_past_results(sm_proxy, days_back=3)
    print(f"✅ Done — {summary['updated']} resolved, {summary['errors']} void")


if __name__ == '__main__':
    main()

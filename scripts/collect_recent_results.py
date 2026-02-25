"""
Recent Results Collector.

Fetches finished fixtures from SportMonks for the last N days and appends
them to data/raw/all_matches.csv in the same schema the training script
expects. This keeps the training dataset fresh.

Run this script locally (or as a monthly Render job) before retraining:
    python scripts/collect_recent_results.py --days 30

After collection, retrain models locally:
    python scripts/train.py

Then push the updated model .json files to GitHub so Render picks them up:
    git add models/trained/*.json
    git commit -m "Retrain models with recent results"
    git push origin main

NOTE: This script is designed to run LOCALLY with pandas installed.
      It does NOT run on Render's production server (pandas not in requirements.txt).
"""
import sys
import os
import json
import urllib.request
import argparse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SPORTMONKS_TOKEN = os.environ.get(
    'SPORTMONKS_TOKEN',
    'b7EFSY6Bmrxisf6OswWjYArQUHMakSEDRMTJVoFiH56sbHsxaJxFRpVrOuoL',
)
SPORTMONKS_BASE = 'https://api.sportmonks.com/v3/football'


def fetch_finished_fixtures(date_str):
    """Fetch finished fixtures for a date from SportMonks."""
    url = (
        f"{SPORTMONKS_BASE}/fixtures/date/{date_str}"
        f"?api_token={SPORTMONKS_TOKEN}"
        f"&include=participants;scores;league"
        f"&per_page=100"
    )
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode())
        return body.get('data', [])
    except Exception as e:
        print(f"  ⚠️ Failed to fetch {date_str}: {e}")
        return []


def _parse_score(scores, location):
    """Extract final score for home or away from SportMonks scores array."""
    for s in scores:
        if s.get('description', '') == 'CURRENT':
            score_data = s.get('score', {})
            if score_data.get('participant') == location:
                goals = score_data.get('goals')
                if goals is not None:
                    return int(goals)
    return None


def fixture_to_csv_row(event, date_str):
    """Convert a SportMonks fixture event to a CSV row dict."""
    participants = event.get('participants', [])
    home_team = away_team = ''
    home_id = away_id = None

    for p in participants:
        loc = (p.get('meta') or {}).get('location', '')
        if loc == 'home':
            home_team = p.get('name', '')
            home_id = p.get('id')
        elif loc == 'away':
            away_team = p.get('name', '')
            away_id = p.get('id')

    if not home_team or not away_team:
        return None

    scores = event.get('scores', [])
    home_goals = _parse_score(scores, 'home')
    away_goals = _parse_score(scores, 'away')

    # Only include finished matches
    state_id = event.get('state_id', 0)
    finished_states = {5, 7, 8, 14, 15, 17}
    if state_id not in finished_states:
        return None
    if home_goals is None or away_goals is None:
        return None

    league_data = event.get('league') or {}
    league_name = league_data.get('name', 'Unknown')

    # Determine FTR (full time result)
    if home_goals > away_goals:
        ftr = 'H'
    elif away_goals > home_goals:
        ftr = 'A'
    else:
        ftr = 'D'

    # Format date as DD/MM/YYYY to match existing CSV format
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        formatted_date = dt.strftime('%d/%m/%Y')
    except Exception:
        formatted_date = date_str

    return {
        'Div': '',
        'Date': formatted_date,
        'Time': event.get('starting_at', '')[-8:-3] if event.get('starting_at') else '',
        'HomeTeam': home_team,
        'AwayTeam': away_team,
        'FTHG': home_goals,
        'FTAG': away_goals,
        'FTR': ftr,
        'HTHG': '',   # Half-time not available from this endpoint
        'HTAG': '',
        'HTR': '',
        'Season': dt.year if 'dt' in dir() else '',
        'League': league_name,
    }


def collect_recent_results(days=30, output_csv='data/raw/all_matches.csv'):
    """
    Fetch the last `days` days of finished fixtures and append to the CSV.
    Skips dates already in the CSV (deduplication by Date+HomeTeam+AwayTeam).
    """
    try:
        import pandas as pd
    except ImportError:
        print("❌ pandas is required. Install with: pip install pandas")
        sys.exit(1)

    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        output_csv
    )

    # Load existing data to check for duplicates
    print(f"📂 Loading existing CSV: {output_path}")
    try:
        existing = pd.read_csv(output_path, low_memory=False)
        print(f"   Found {len(existing)} existing rows")
    except Exception:
        existing = pd.DataFrame()
        print("   No existing CSV found — will create fresh")

    # Build set of existing match keys
    existing_keys = set()
    if not existing.empty and 'HomeTeam' in existing.columns:
        for _, row in existing.iterrows():
            key = f"{row.get('Date', '')}|{row.get('HomeTeam', '')}|{row.get('AwayTeam', '')}"
            existing_keys.add(key)

    new_rows = []
    today = datetime.now(timezone.utc)

    for i in range(1, days + 1):
        target = today - timedelta(days=i)
        date_str = target.strftime('%Y-%m-%d')

        print(f"  📅 Fetching {date_str}…", end=' ', flush=True)
        events = fetch_finished_fixtures(date_str)

        day_new = 0
        for event in events:
            row = fixture_to_csv_row(event, date_str)
            if row is None:
                continue
            key = f"{row['Date']}|{row['HomeTeam']}|{row['AwayTeam']}"
            if key in existing_keys:
                continue
            new_rows.append(row)
            existing_keys.add(key)
            day_new += 1

        print(f"{day_new} new")

    if not new_rows:
        print("✅ No new matches to add.")
        return 0

    # Append to CSV
    new_df = pd.DataFrame(new_rows)

    if existing.empty:
        new_df.to_csv(output_path, index=False)
    else:
        # Align columns then append
        for col in existing.columns:
            if col not in new_df.columns:
                new_df[col] = ''
        new_df = new_df.reindex(columns=existing.columns, fill_value='')
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined.to_csv(output_path, index=False)

    print(f"\n✅ Added {len(new_rows)} new rows → {output_path}")
    print(f"   Total rows now: {len(existing) + len(new_rows)}")
    print()
    print("Next steps:")
    print("  1. python scripts/train.py          ← retrain models")
    print("  2. git add models/trained/*.json")
    print("  3. git commit -m 'Retrain models with recent results'")
    print("  4. git push origin main              ← Render auto-deploys new models")
    return len(new_rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Collect recent match results from SportMonks')
    parser.add_argument('--days', type=int, default=30,
                        help='Number of past days to collect (default: 30)')
    parser.add_argument('--output', default='data/raw/all_matches.csv',
                        help='Output CSV path relative to project root')
    args = parser.parse_args()

    print(f"🔄 Collecting last {args.days} days of results from SportMonks…")
    count = collect_recent_results(days=args.days, output_csv=args.output)
    print(f"\nDone. {count} new matches collected.")

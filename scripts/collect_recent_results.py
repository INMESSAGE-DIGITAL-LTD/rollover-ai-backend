"""
Collect recent finished match results from API-Football and append them to
data/raw/all_matches.csv so the bi-weekly retrain ingests fresh data.

Called by .github/workflows/retrain.yml:
    python scripts/collect_recent_results.py --days 30

Replaces the old SportMonks collector (key retired 2026-07). Only leagues
already present in the CSV are appended, so the training distribution stays
consistent with the football-data.co.uk base data. Rows are deduped on
(Date, HomeTeam, AwayTeam).
"""
import argparse
import csv
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

APIFOOTBALL_KEY = os.environ.get('APIFOOTBALL_KEY', 'da7a6fc2f03e7fb7994995143d29358f')
APIFOOTBALL_BASE = 'https://v3.football.api-sports.io'

REPO_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = REPO_ROOT / 'data' / 'raw' / 'all_matches.csv'


def _get(path, params):
    query = '&'.join(f'{k}={v}' for k, v in params.items())
    url = f'{APIFOOTBALL_BASE}/{path}?{query}'
    req = urllib.request.Request(url, headers={'x-apisports-key': APIFOOTBALL_KEY})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch_finished(date_str):
    """All finished fixtures for one UTC date (paged)."""
    fixtures, page = [], 1
    while True:
        try:
            body = _get('fixtures', {'date': date_str, 'timezone': 'UTC', 'page': page})
        except Exception as e:
            print(f'  ⚠️ {date_str} p{page}: {e}')
            break
        for item in body.get('response', []):
            status = ((item.get('fixture') or {}).get('status') or {}).get('short', '')
            if status not in ('FT', 'AET', 'PEN'):
                continue
            goals = item.get('goals') or {}
            if goals.get('home') is None or goals.get('away') is None:
                continue
            fixtures.append(item)
        paging = body.get('paging') or {}
        if paging.get('current', 1) >= paging.get('total', 1):
            break
        page += 1
    return fixtures


def load_existing():
    """Existing (date, home, away) keys + known league names + fieldnames."""
    keys, leagues = set(), set()
    with open(CSV_PATH, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            keys.add((row.get('Date', ''), row.get('HomeTeam', ''), row.get('AwayTeam', '')))
            league = (row.get('League') or '').strip()
            if league:
                leagues.add(league)
    return keys, leagues, fieldnames


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=30)
    args = parser.parse_args()

    if not CSV_PATH.exists():
        print(f'❌ {CSV_PATH} not found')
        sys.exit(1)

    existing, known_leagues, fieldnames = load_existing()
    print(f'📄 CSV has {len(existing)} matches across {len(known_leagues)} leagues')

    new_rows = []
    today = datetime.now(timezone.utc).date()
    for i in range(1, args.days + 1):
        day = today - timedelta(days=i)
        date_api = day.strftime('%Y-%m-%d')
        date_csv = day.strftime('%d/%m/%Y')
        fixtures = fetch_finished(date_api)
        added = 0
        for item in fixtures:
            league = ((item.get('league') or {}).get('name') or '').strip()
            if league not in known_leagues:
                continue
            teams = item.get('teams') or {}
            home = ((teams.get('home') or {}).get('name') or '').strip()
            away = ((teams.get('away') or {}).get('name') or '').strip()
            if not home or not away:
                continue
            key = (date_csv, home, away)
            if key in existing:
                continue

            goals = item.get('goals') or {}
            fthg, ftag = int(goals['home']), int(goals['away'])
            ht = ((item.get('score') or {}).get('halftime') or {})
            hthg, htag = ht.get('home'), ht.get('away')
            kickoff = ((item.get('fixture') or {}).get('date') or '')
            time_str = kickoff[11:16] if len(kickoff) >= 16 else ''
            season = (item.get('league') or {}).get('season') or day.year

            row = {k: '' for k in fieldnames}
            row.update({
                'Date': date_csv,
                'Time': time_str,
                'HomeTeam': home,
                'AwayTeam': away,
                'FTHG': fthg,
                'FTAG': ftag,
                'FTR': 'H' if fthg > ftag else ('A' if ftag > fthg else 'D'),
                'Season': season,
                'League': league,
            })
            if hthg is not None and htag is not None:
                row['HTHG'] = hthg
                row['HTAG'] = htag
                row['HTR'] = 'H' if hthg > htag else ('A' if htag > hthg else 'D')

            new_rows.append(row)
            existing.add(key)
            added += 1
        print(f'  📅 {date_api}: {len(fixtures)} finished, {added} new in known leagues')

    if not new_rows:
        print('✅ No new matches to append')
        return

    with open(CSV_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerows(new_rows)
    print(f'✅ Appended {len(new_rows)} new matches to {CSV_PATH.name}')


if __name__ == '__main__':
    main()

"""
Football-data.org fallback — used when API-Football quota is exhausted.
Free tier covers major European leagues + Copa Libertadores.
No daily quota limit. Used as emergency backup source.
"""
import os
import json
import urllib.request
import urllib.error
from datetime import datetime

FOOTBALL_DATA_TOKEN = os.environ.get('FOOTBALL_DATA_TOKEN', 'd09de38c27b546d592d286fe94a4cd2f')
FOOTBALL_DATA_BASE = 'https://api.football-data.org/v4'

# All free-tier (TIER_ONE) competitions — no API key restrictions
FALLBACK_COMPETITIONS = {
    'PL':  'English Premier League',
    'BL1': 'Bundesliga',
    'SA':  'Serie A',
    'FL1': 'Ligue 1',
    'PD':  'La Liga',
    'DED': 'Eredivisie',
    'ELC': 'Championship',
    'PPL': 'Liga Portugal',
    'CL':  'UEFA Champions League',
    'CLI': 'Copa Libertadores',
    'BSA': 'Brasileirao Serie A',
}

# Conservative default lines used when bookmaker odds are unavailable.
# Higher than typical so implied probability is lower → easier for XGBoost to show edge.
_DEFAULT_LINES = {
    1.5: {'over_odds': 1.44, 'under_odds': 2.60},
    2.5: {'over_odds': 1.85, 'under_odds': 1.90},
}


def fetch_fallback_fixtures(date_str):
    """
    Fetch fixtures from football-data.org for competitions not in SportMonks.
    Returns list of fixture dicts matching SportMonks format.
    """
    fixtures = []
    for comp_code, comp_name in FALLBACK_COMPETITIONS.items():
        try:
            matches = _fetch_competition_matches(comp_code, date_str)
            for m in matches:
                fixture = _parse_match(m, comp_name)
                if fixture:
                    fixtures.append(fixture)
        except Exception as e:
            print(f"⚠️ football-data.org fallback error ({comp_code}): {e}")

    fixtures.sort(key=lambda f: f.get('commence_time', ''))
    if fixtures:
        print(f"✅ Fallback: {len(fixtures)} UEFA fixtures from football-data.org")
    return fixtures


def _fetch_competition_matches(comp_code, date_str):
    """Fetch matches for a competition on a specific date."""
    url = f"{FOOTBALL_DATA_BASE}/competitions/{comp_code}/matches?dateFrom={date_str}&dateTo={date_str}"

    headers = {'X-Auth-Token': FOOTBALL_DATA_TOKEN} if FOOTBALL_DATA_TOKEN else {}

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
        return body.get('matches', [])
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print(f"  ⚠️ {comp_code}: not accessible on current plan")
        elif e.code == 429:
            print(f"  ⚠️ {comp_code}: rate limited")
        else:
            print(f"  ⚠️ {comp_code}: HTTP {e.code}")
        return []
    except Exception as e:
        print(f"  ⚠️ {comp_code}: {e}")
        return []


def _parse_match(match, comp_name):
    """
    Parse a football-data.org match into our fixture format.
    Generates estimated odds from team strength when bookmaker odds unavailable.
    """
    try:
        home = match.get('homeTeam', {})
        away = match.get('awayTeam', {})
        home_name = home.get('name', '')
        away_name = away.get('name', '')

        if not home_name or not away_name:
            return None

        # football-data.org uses UTC timestamps
        utc_date = match.get('utcDate', '')

        # Extract odds if available (football-data.org sometimes provides them)
        odds = match.get('odds', {})
        home_win_odds = odds.get('homeWin')
        draw_odds = odds.get('draw')
        away_win_odds = odds.get('awayWin')

        # Build markets from available odds
        markets = {}
        if home_win_odds and draw_odds and away_win_odds:
            markets['fulltime_result'] = {
                'home': home_win_odds,
                'draw': draw_odds,
                'away': away_win_odds,
            }
            # Derive double chance from 1X2
            markets['double_chance'] = {
                'home_draw': _dc_odds(home_win_odds, draw_odds),
                'away_draw': _dc_odds(away_win_odds, draw_odds),
                'home_away': _dc_odds(home_win_odds, away_win_odds),
            }
        else:
            markets['fulltime_result'] = {
                'home': 2.20,
                'draw': 3.30,
                'away': 3.20,
            }
            markets['double_chance'] = {
                'home_draw': 1.35,
                'away_draw': 1.50,
                'home_away': 1.40,
            }

        # BTTS typical odds for top leagues
        markets['btts'] = {'yes': 1.80, 'no': 1.95}

        # Use competition ID as league_id (negative to avoid collision with SportMonks)
        comp_id = match.get('competition', {}).get('id', 0)
        league_id = -comp_id if comp_id else -9999

        home_crest = home.get('crest', '')
        away_crest = away.get('crest', '')

        return {
            'home_team': home_name,
            'away_team': away_name,
            'home_team_id': home.get('id'),
            'away_team_id': away.get('id'),
            'season_id': None,
            'commence_time': utc_date,
            'league': league_id,
            'league_name': comp_name,
            'league_logo': '',
            'home_logo': home_crest,
            'away_logo': away_crest,
            'home_short_code': home.get('tla', ''),
            'away_short_code': away.get('tla', ''),
            'lines': dict(_DEFAULT_LINES),
            'markets': markets,
            'source': 'football-data.org',
        }
    except Exception:
        return None


def _dc_odds(a, b):
    """Calculate double chance odds from two single outcomes."""
    try:
        prob = (1 / a) + (1 / b)
        return round(1 / prob, 2) if prob > 0 else 1.20
    except (ZeroDivisionError, TypeError):
        return 1.20

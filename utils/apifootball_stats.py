"""
API-Football team stats, H2H, and standings.
Replaces sportmonks_stats.py — same return structure so fixture_fetcher.py
and stat_qualifier.py need zero changes beyond the import line.
"""
import os
import json
import urllib.request
from datetime import datetime

APIFOOTBALL_KEY = os.environ.get('APIFOOTBALL_KEY', 'da7a6fc2f03e7fb7994995143d29358f')
APIFOOTBALL_BASE = 'https://v3.football.api-sports.io'

_team_stats_cache = {}   # (team_id, league_id, season) -> stats dict
_h2h_cache = {}          # "id1_id2" -> h2h dict
_standings_cache = {}    # (league_id, season) -> list


def _get(path, params):
    qs = '&'.join(f"{k}={v}" for k, v in params.items())
    url = f"{APIFOOTBALL_BASE}/{path}?{qs}"
    req = urllib.request.Request(url, headers={'x-apisports-key': APIFOOTBALL_KEY})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def get_current_season():
    now = datetime.now()
    return now.year if now.month >= 8 else now.year - 1


# ── Team Statistics ──────────────────────────────────────────────────────────

class ApiFootballStats:
    """Stateless wrapper — caches at module level."""

    def fetch_team_stats(self, team_id, league_id=None, season=None):
        return fetch_team_stats(team_id, league_id, season)

    def fetch_h2h(self, team1_id, team2_id):
        return fetch_h2h(team1_id, team2_id)


def fetch_team_stats(team_id, league_id=None, season=None):
    """
    Fetch season stats for a team via /teams/statistics.
    Returns the same dict structure as the old SportMonks version so
    _build_features_from_live() works unchanged.
    Half-time goals are derived from the minute-breakdown buckets.
    """
    if season is None:
        season = get_current_season()

    cache_key = (team_id, league_id, season)
    if cache_key in _team_stats_cache:
        return _team_stats_cache[cache_key]

    params = {'team': team_id, 'season': season}
    if league_id:
        params['league'] = league_id

    try:
        body = _get('teams/statistics', params)
        data = body.get('response', {})
        if not data:
            return None

        stats = _parse_team_stats(team_id, data)
        if stats:
            _team_stats_cache[cache_key] = stats
        return stats

    except Exception as e:
        print(f"⚠️ API-Football team stats error for {team_id}: {e}")
        return None


def _parse_team_stats(team_id, data):
    """Parse /teams/statistics response into the stat dict the model expects."""
    fixtures = data.get('fixtures', {})
    goals = data.get('goals', {})
    clean_sheet = data.get('clean_sheet', {})
    failed = data.get('failed_to_score', {})

    played_home = fixtures.get('played', {}).get('home', 0) or 0
    played_away = fixtures.get('played', {}).get('away', 0) or 0
    played_total = fixtures.get('played', {}).get('total', 0) or 0
    if played_total == 0:
        return None

    wins_total = fixtures.get('wins', {}).get('total', 0) or 0
    wins_home = fixtures.get('wins', {}).get('home', 0) or 0

    # Goals for
    gf_home = goals.get('for', {}).get('total', {}).get('home', 0) or 0
    gf_away = goals.get('for', {}).get('total', {}).get('away', 0) or 0
    gf_total = goals.get('for', {}).get('total', {}).get('total', 0) or 0

    # Goals against
    ga_home = goals.get('against', {}).get('total', {}).get('home', 0) or 0
    ga_away = goals.get('against', {}).get('total', {}).get('away', 0) or 0
    ga_total = goals.get('against', {}).get('total', {}).get('total', 0) or 0

    avg_scored = gf_total / played_total
    avg_conceded = ga_total / played_total
    home_avg_scored = gf_home / played_home if played_home else avg_scored
    away_avg_scored = gf_away / played_away if played_away else avg_scored
    home_avg_conceded = ga_home / played_home if played_home else avg_conceded
    away_avg_conceded = ga_away / played_away if played_away else avg_conceded

    # Half-time goals from minute buckets (API-Football provides 0-15/16-30/31-45/46-60/61-75/76-90)
    minute_for = goals.get('for', {}).get('minute', {})
    first_half_goals_total = sum(
        (minute_for.get(k) or {}).get('total', 0) or 0
        for k in ('0-15', '16-30', '31-45')
    )
    second_half_goals_total = sum(
        (minute_for.get(k) or {}).get('total', 0) or 0
        for k in ('46-60', '61-75', '76-90')
    )
    avg_first_half = first_half_goals_total / played_total
    avg_second_half = second_half_goals_total / played_total

    # Derived rates
    cs_total = clean_sheet.get('total', 0) or 0
    fts_total = failed.get('total', 0) or 0
    scored_in_count = played_total - fts_total
    clean_sheet_rate = cs_total / played_total
    scored_in_rate = scored_in_count / played_total

    # over15 and over25: approximate from avg goals per game
    # (no direct per-match over rate from /teams/statistics, use heuristic)
    over15_rate = min(0.95, max(0.20, (avg_scored + avg_conceded - 1.0) / 2.5))
    over25_rate = min(0.90, max(0.10, (avg_scored + avg_conceded - 1.8) / 2.0))

    # BTTS rate: approximate — both teams scoring requires both to not have 0 goals
    # Use scored_in_rate as proxy (both teams scored heuristic)
    btts_rate = min(0.85, scored_in_rate * (1.0 - clean_sheet_rate))

    win_rate = wins_total / played_total
    home_win_rate = wins_home / played_home if played_home else win_rate

    return {
        'team_id': team_id,
        'matches_played': played_total,
        'avg_goals_scored': avg_scored,
        'avg_goals_conceded': avg_conceded,
        'home_avg_scored': home_avg_scored,
        'away_avg_scored': away_avg_scored,
        'home_avg_conceded': home_avg_conceded,
        'away_avg_conceded': away_avg_conceded,
        'avg_first_half_goals': avg_first_half,
        'avg_second_half_goals': avg_second_half,
        'home_win_rate': home_win_rate,
        'over25_rate': over25_rate,
        'over15_rate': over15_rate,
        'btts_rate': btts_rate,
        'scored_in_rate': scored_in_rate,
        'clean_sheet_rate': clean_sheet_rate,
    }


# ── H2H ──────────────────────────────────────────────────────────────────────

def fetch_h2h(team1_id, team2_id, last=10):
    """Fetch H2H between two teams. Returns same structure as old SportMonks version."""
    ck = f"{team1_id}_{team2_id}"
    ck_rev = f"{team2_id}_{team1_id}"
    if ck in _h2h_cache:
        return _h2h_cache[ck]
    if ck_rev in _h2h_cache:
        return _h2h_cache[ck_rev]

    try:
        body = _get('fixtures/headtohead', {'h2h': f"{team1_id}-{team2_id}", 'last': last})
        items = body.get('response', [])
        if not items:
            return None

        h2h = _compute_h2h(team1_id, team2_id, items)
        if h2h:
            _h2h_cache[ck] = h2h
        return h2h

    except Exception as e:
        print(f"⚠️ API-Football H2H error {team1_id} vs {team2_id}: {e}")
        return None


def _compute_h2h(team1_id, team2_id, items):
    over25 = over15 = btts = t1_wins = t2_wins = draws = 0
    total_goals = 0.0
    total_ht_goals = 0.0
    total_matches = 0

    for item in items:
        teams = item.get('teams', {})
        score = item.get('score', {})
        status = item.get('fixture', {}).get('status', {}).get('short', '')

        if status not in ('FT', 'AET', 'PEN'):
            continue

        home_id = teams.get('home', {}).get('id')
        goals = item.get('goals', {})
        home_g = goals.get('home')
        away_g = goals.get('away')
        if home_g is None or away_g is None:
            continue

        ht = score.get('halftime', {})
        ht_home = ht.get('home') or 0
        ht_away = ht.get('away') or 0

        total = home_g + away_g
        total_matches += 1
        total_goals += total
        total_ht_goals += ht_home + ht_away

        if total >= 3:
            over25 += 1
        if total >= 2:
            over15 += 1
        if home_g > 0 and away_g > 0:
            btts += 1

        if home_g > away_g:
            (t1_wins if home_id == team1_id else t2_wins).__iadd__ if False else None
            if home_id == team1_id:
                t1_wins += 1
            else:
                t2_wins += 1
        elif away_g > home_g:
            if home_id == team1_id:
                t2_wins += 1
            else:
                t1_wins += 1
        else:
            draws += 1

    if total_matches == 0:
        return None

    return {
        'over25_count': over25,
        'over15_count': over15,
        'btts_count': btts,
        'team1_wins': t1_wins,
        'team2_wins': t2_wins,
        'draws': draws,
        'avg_goals': total_goals / total_matches,
        'avg_first_half_goals': total_ht_goals / total_matches,
        'total_matches': total_matches,
    }


# ── Standings ────────────────────────────────────────────────────────────────

def fetch_standings(league_id, season):
    """Fetch league standings. Returns list of team standing dicts."""
    ck = (league_id, season)
    if ck in _standings_cache:
        return _standings_cache[ck]

    try:
        body = _get('standings', {'league': league_id, 'season': season})
        response = body.get('response', [])
        if not response:
            return []

        standings = []
        for item in response:
            for group in item.get('league', {}).get('standings', []):
                for entry in group:
                    team = entry.get('team', {})
                    standings.append({
                        'team_id': team.get('id'),
                        'team_name': team.get('name', ''),
                        'position': entry.get('rank', 0),
                        'points': entry.get('points', 0),
                        'played': entry.get('all', {}).get('played', 0),
                        'wins': entry.get('all', {}).get('win', 0),
                        'draws': entry.get('all', {}).get('draw', 0),
                        'losses': entry.get('all', {}).get('lose', 0),
                        'goals_for': entry.get('all', {}).get('goals', {}).get('for', 0),
                        'goals_against': entry.get('all', {}).get('goals', {}).get('against', 0),
                        'form': entry.get('form', ''),
                    })

        if standings:
            _standings_cache[ck] = standings
        return standings

    except Exception as e:
        print(f"⚠️ Standings error for league {league_id} season {season}: {e}")
        return []


def get_team_standing(league_id, team_id, season=None):
    """
    Get team's position, points, and zone in a league.
    Returns dict compatible with old sportmonks_stats.get_team_standing output.
    """
    if season is None:
        season = get_current_season()

    standings = fetch_standings(league_id, season)
    if not standings:
        return None

    total_teams = len(standings)

    for entry in standings:
        if entry.get('team_id') == team_id:
            position = entry['position']
            points = entry['points']

            zone = 'mid'
            if position <= 1:
                zone = 'leader'
            elif position <= max(2, total_teams // 6):
                zone = 'title_race'
            elif position <= max(4, total_teams // 3):
                zone = 'european'
            elif position >= total_teams - max(2, total_teams // 6):
                zone = 'relegation'
            elif position >= total_teams - max(4, total_teams // 3):
                zone = 'relegation_threat'

            leader_pts = second_pts = relegation_pts = 0
            for s in standings:
                if s['position'] == 1:
                    leader_pts = s['points']
                if s['position'] == 2:
                    second_pts = s['points']
                if s['position'] == total_teams - 2:
                    relegation_pts = min(relegation_pts or 999, s['points'])

            return {
                'position': position,
                'points': points,
                'total_teams': total_teams,
                'zone': zone,
                'gap_to_leader': leader_pts - points,
                'gap_to_second': points - second_pts if position == 1 else second_pts - points,
                'gap_to_relegation': points - (relegation_pts or 0),
                'is_leader': position == 1,
                'title_race': position <= 2 and (leader_pts - points) <= 6,
                'relegation_battle': zone in ('relegation', 'relegation_threat'),
            }

    return None


def clear_cache():
    global _team_stats_cache, _h2h_cache, _standings_cache
    _team_stats_cache = {}
    _h2h_cache = {}
    _standings_cache = {}

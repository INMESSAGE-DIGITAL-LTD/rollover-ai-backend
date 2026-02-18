"""
Fetch live team stats and H2H from SportMonks API.
Replaces static CSV-based stats for teams not in historical data.
Results are cached in-memory per session.
"""
import json
import urllib.request
import urllib.error
import os

SPORTMONKS_TOKEN = os.environ.get(
    'SPORTMONKS_TOKEN',
    'b7EFSY6Bmrxisf6OswWjYArQUHMakSEDRMTJVoFiH56sbHsxaJxFRpVrOuoL',
)
SPORTMONKS_BASE = 'https://api.sportmonks.com/v3/football'

# In-memory caches
_team_stats_cache = {}
_h2h_cache = {}


def fetch_team_stats(team_id, last_n=10):
    """Fetch last N results for a team and compute stats."""
    if team_id in _team_stats_cache:
        return _team_stats_cache[team_id]

    url = (
        f"{SPORTMONKS_BASE}/teams/{team_id}"
        f"?api_token={SPORTMONKS_TOKEN}"
        f"&include=latest.participants;latest.scores"
    )

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())

        team_data = body.get('data', {})
        latest = team_data.get('latest', [])
        if not latest:
            return None

        matches = latest[:last_n]
        stats = _compute_team_stats(team_id, matches)
        if stats:
            _team_stats_cache[team_id] = stats
        return stats

    except Exception as e:
        print(f"⚠️ SportMonks team stats error for {team_id}: {e}")
        return None


def fetch_h2h(team1_id, team2_id):
    """Fetch last 5 H2H matches between two teams."""
    cache_key = f"{team1_id}_{team2_id}"
    cache_key_rev = f"{team2_id}_{team1_id}"
    if cache_key in _h2h_cache:
        return _h2h_cache[cache_key]
    if cache_key_rev in _h2h_cache:
        return _h2h_cache[cache_key_rev]

    url = (
        f"{SPORTMONKS_BASE}/fixtures/head-to-head/{team1_id}/{team2_id}"
        f"?api_token={SPORTMONKS_TOKEN}"
        f"&include=scores;participants"
        f"&per_page=5"
    )

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())

        fixtures = body.get('data', [])
        if not fixtures:
            return None

        h2h = _compute_h2h(team1_id, team2_id, fixtures[:5])
        if h2h:
            _h2h_cache[cache_key] = h2h
        return h2h

    except Exception as e:
        print(f"⚠️ SportMonks H2H error for {team1_id} vs {team2_id}: {e}")
        return None


def _compute_team_stats(team_id, matches):
    """Compute stats from a list of match data."""
    played = 0
    total_scored = 0.0
    total_conceded = 0.0
    over25_count = 0
    over15_count = 0
    btts_count = 0
    scored_in_count = 0
    clean_sheet_count = 0
    home_wins = 0
    home_matches = 0
    away_losses = 0
    away_matches = 0
    home_scored = 0.0
    home_conceded = 0.0
    away_scored = 0.0
    away_conceded = 0.0

    for match in matches:
        participants = match.get('participants', [])
        scores = match.get('scores', [])

        is_home = False
        for p in participants:
            meta = p.get('meta', {})
            if p.get('id') == team_id:
                is_home = meta.get('location') == 'home'

        team_goals = None
        opp_goals = None
        for s in scores:
            if s.get('description') != 'CURRENT':
                continue
            score_data = s.get('score', {})
            participant = score_data.get('participant', '')
            goals = score_data.get('goals')
            if goals is None:
                continue
            g = int(goals) if isinstance(goals, int) else int(goals)

            if (is_home and participant == 'home') or (not is_home and participant == 'away'):
                team_goals = g
            else:
                opp_goals = g

        if team_goals is None or opp_goals is None:
            continue

        played += 1
        total_scored += team_goals
        total_conceded += opp_goals

        total = team_goals + opp_goals
        if total >= 3:
            over25_count += 1
        if total >= 2:
            over15_count += 1
        if team_goals > 0 and opp_goals > 0:
            btts_count += 1
        if team_goals > 0:
            scored_in_count += 1
        if opp_goals == 0:
            clean_sheet_count += 1

        if is_home:
            home_matches += 1
            home_scored += team_goals
            home_conceded += opp_goals
            if team_goals > opp_goals:
                home_wins += 1
        else:
            away_matches += 1
            away_scored += team_goals
            away_conceded += opp_goals
            if team_goals < opp_goals:
                away_losses += 1

    if played == 0:
        return None

    return {
        'team_id': team_id,
        'matches_played': played,
        'avg_goals_scored': total_scored / played,
        'avg_goals_conceded': total_conceded / played,
        'home_win_rate': home_wins / home_matches if home_matches > 0 else 0.0,
        'away_loss_rate': away_losses / away_matches if away_matches > 0 else 0.0,
        'over25_rate': over25_count / played,
        'over15_rate': over15_count / played,
        'btts_rate': btts_count / played,
        'scored_in_rate': scored_in_count / played,
        'clean_sheet_rate': clean_sheet_count / played,
        'home_avg_scored': home_scored / home_matches if home_matches > 0 else total_scored / played,
        'away_avg_scored': away_scored / away_matches if away_matches > 0 else total_scored / played,
        'home_avg_conceded': home_conceded / home_matches if home_matches > 0 else total_conceded / played,
        'away_avg_conceded': away_conceded / away_matches if away_matches > 0 else total_conceded / played,
    }


def _compute_h2h(team1_id, team2_id, fixtures):
    """Compute H2H stats from fixtures."""
    over25 = 0
    over15 = 0
    btts = 0
    t1_wins = 0
    t2_wins = 0
    draws = 0
    total_goals = 0.0
    total_matches = 0

    for fix in fixtures:
        participants = fix.get('participants', [])
        scores = fix.get('scores', [])

        home_id = None
        home_goals = None
        away_goals = None

        for p in participants:
            meta = p.get('meta', {})
            if meta.get('location') == 'home':
                home_id = p.get('id')

        for s in scores:
            if s.get('description') != 'CURRENT':
                continue
            score_data = s.get('score', {})
            participant = score_data.get('participant', '')
            goals = score_data.get('goals')
            if goals is None:
                continue
            g = int(goals)
            if participant == 'home':
                home_goals = g
            elif participant == 'away':
                away_goals = g

        if home_goals is None or away_goals is None:
            continue

        total_matches += 1
        match_total = home_goals + away_goals
        total_goals += match_total

        if match_total >= 3:
            over25 += 1
        if match_total >= 2:
            over15 += 1
        if home_goals > 0 and away_goals > 0:
            btts += 1

        if home_goals > away_goals:
            if home_id == team1_id:
                t1_wins += 1
            else:
                t2_wins += 1
        elif away_goals > home_goals:
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
        'total_matches': total_matches,
    }


_standings_cache = {}  # season_id -> standings list


def fetch_standings_for_season(season_id):
    """Fetch league standings for a season. Returns list of team standings."""
    if season_id in _standings_cache:
        return _standings_cache[season_id]

    url = (
        f"{SPORTMONKS_BASE}/standings/seasons/{season_id}"
        f"?api_token={SPORTMONKS_TOKEN}"
    )

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())

        data = body.get('data', [])
        standings = []
        for group in data:
            for entry in group.get('standings', group.get('details', [])):
                if isinstance(entry, dict):
                    standings.append(entry)
            # Some API versions nest differently
            if isinstance(group, dict) and 'participant_id' in group:
                standings.append(group)

        if standings:
            _standings_cache[season_id] = standings
            print(f"✅ Standings cached for season {season_id}: {len(standings)} teams")
        return standings

    except Exception as e:
        print(f"⚠️ Standings fetch error for season {season_id}: {e}")
        return []


def get_team_standing(season_id, team_id):
    """
    Get a team's league position, points, and context.
    Returns dict with position, points, total_teams, zone info, or None.
    """
    standings = fetch_standings_for_season(season_id)
    if not standings:
        return None

    total_teams = len(standings)

    for entry in standings:
        pid = entry.get('participant_id') or entry.get('team_id')
        if pid == team_id:
            position = entry.get('position', entry.get('ranking', 0))
            points = entry.get('points', 0)

            # Determine zone
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

            # Check points gap to leader and to relegation
            leader_pts = 0
            relegation_pts = 999
            second_pts = 0
            for s in standings:
                s_pos = s.get('position', s.get('ranking', 0))
                s_pts = s.get('points', 0)
                if s_pos == 1:
                    leader_pts = s_pts
                if s_pos == 2:
                    second_pts = s_pts
                if s_pos == total_teams - 2:
                    relegation_pts = min(relegation_pts, s_pts)

            return {
                'position': position,
                'points': points,
                'total_teams': total_teams,
                'zone': zone,
                'gap_to_leader': leader_pts - points,
                'gap_to_second': points - second_pts if position == 1 else second_pts - points,
                'gap_to_relegation': points - relegation_pts,
                'is_leader': position == 1,
                'title_race': position <= 2 and (leader_pts - points) <= 6,
                'relegation_battle': zone in ('relegation', 'relegation_threat'),
            }

    return None


def clear_cache():
    """Clear in-memory caches (call at start of each day)."""
    global _team_stats_cache, _h2h_cache, _standings_cache
    _team_stats_cache = {}
    _h2h_cache = {}
    _standings_cache = {}

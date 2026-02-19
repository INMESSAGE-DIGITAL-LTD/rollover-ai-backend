"""
Fetch today's fixtures from SportMonks API and generate AI predictions + slip
Supports mixed markets: Over/Under, 1X2, BTTS, Double Chance, Team Goals, Half Goals
"""
import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta


SPORTMONKS_TOKEN = os.environ.get(
    'SPORTMONKS_TOKEN',
    'b7EFSY6Bmrxisf6OswWjYArQUHMakSEDRMTJVoFiH56sbHsxaJxFRpVrOuoL',
)
SPORTMONKS_BASE = 'https://api.sportmonks.com/v3/football'

# League IDs — leagues available in the SportMonks Standard plan
LEAGUE_IDS = {
    # UEFA Competitions
    2: 'Champions League',
    5: 'Europa League',
    2286: 'Conference League',
    1371: 'Europa League Play-offs',
    # England
    8: 'Premier League',
    9: 'Championship',
    24: 'FA Cup',
    27: 'Carabao Cup',
    # Netherlands
    72: 'Eredivisie',
    # Germany
    82: 'Bundesliga',
    # Austria
    181: 'Austrian Bundesliga',
    # Belgium
    208: 'Pro League',
    # Croatia
    244: '1. HNL',
    # Denmark
    271: 'Superliga',
    # France
    301: 'Ligue 1',
    # Italy
    384: 'Serie A',
    387: 'Serie B',
    390: 'Coppa Italia',
    # Norway
    444: 'Eliteserien',
    # Poland
    453: 'Ekstraklasa',
    # Portugal
    462: 'Liga Portugal',
    # Other
    486: 'Premier League (Other)',
    609: 'Premier League (Ukraine)',
    # Scotland
    501: 'Premiership',
    # Spain
    564: 'La Liga',
    567: 'La Liga 2',
    570: 'Copa Del Rey',
    # Sweden
    573: 'Allsvenskan',
    # Greece
    591: 'Super League',
    # Turkey
    600: 'Super Lig',
}

# No cup rejection — cups in our plan are safe to use
LEAGUE_FILTER = ','.join(str(lid) for lid in LEAGUE_IDS)

# Map bookmaker lines to our AI markets
LINE_TO_AI_MARKET = {
    0.5: 'fh_over_05',   # Over 0.5 → First Half Over 0.5 (closest model)
    1.5: 'ft_over_15',   # Over 1.5 → Full Time Over 1.5
    2.5: 'ft_over_25',   # Over 2.5 → dedicated model if available, fallback ft_over_15
    3.5: 'ft_over_25',   # Over 3.5 → ft_over_25 proxy
}

LINE_LABELS = {
    0.5: 'Over 0.5 Goals',
    1.5: 'Over 1.5 Goals',
    2.5: 'Over 2.5 Goals',
    3.5: 'Over 3.5 Goals',
}

# AI model mapping — uses dedicated models when retrained, falls back to proxies
AI_MARKET_MAP = {
    'home_to_score_yes': 'home_over_05',
    'away_to_score_yes': 'away_over_05',
    'fh_over_05': 'fh_over_05',
    'sh_over_05': 'sh_over_05',
    'home_over_05': 'home_over_05',
    'away_over_05': 'away_over_05',
    'btts_yes': 'btts_yes',
    'home_win': 'home_win',
    'away_win': 'away_win',
    'double_chance_home_draw': 'dc_home_draw',
    'double_chance_away_draw': 'dc_away_draw',
    'double_chance_home_away': 'dc_home_away',
    'draw': 'draw',
    'btts_no': 'btts_no',
    'home_over_15': 'home_over_15',
    'away_over_15': 'away_over_15',
    'fh_under_05': 'fh_under_05',
    'sh_under_05': 'sh_under_05',
}

# Fallback mapping when expanded models aren't trained yet
AI_MARKET_FALLBACK = {
    'btts_yes': 'ft_over_15',
    'home_win': 'home_over_15',
    'away_win': 'away_over_15',
    'dc_home_draw': 'home_over_05',
    'dc_away_draw': 'away_over_05',
    'dc_home_away': 'ft_over_15',
    'ft_over_25': 'ft_over_15',
    'draw': 'ft_over_15',
    'btts_no': 'ft_over_15',
    'home_over_15': 'ft_over_15',
    'away_over_15': 'ft_over_15',
    'fh_under_05': 'fh_over_05',
    'sh_under_05': 'sh_over_05',
}


def fetch_todays_fixtures():
    """Fetch today's fixtures with over/under odds from SportMonks API."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    return fetch_fixtures_by_date(today)

def fetch_fixtures_by_date(date_str):
    """Fetch fixtures for a given date with odds from SportMonks API.
    Falls back to football-data.org for UEFA competitions when SportMonks returns 0."""
    fixtures = _fetch_fixtures_for_date(date_str)

    # Fallback: if SportMonks has no fixtures, try football-data.org for UEFA
    if not fixtures:
        try:
            from utils.football_data_fallback import fetch_fallback_fixtures
            fixtures = fetch_fallback_fixtures(date_str)
        except Exception as e:
            print(f"⚠️ Fallback import/fetch error: {e}")

    fixtures.sort(key=lambda f: f.get('commence_time', ''))
    print(f"✅ Fetched {len(fixtures)} fixtures for {date_str}")
    return fixtures


def _fetch_fixtures_for_date(date_str):
    """Fetch fixtures for a single date from SportMonks."""
    url = (
        f"{SPORTMONKS_BASE}/fixtures/date/{date_str}"
        f"?api_token={SPORTMONKS_TOKEN}"
        f"&include=participants;league;odds.market"
        f"&filters=fixtureLeagues:{LEAGUE_FILTER}"
        f"&per_page=50"
    )

    fixtures = []
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode())

        events = body.get('data', [])
        for event in events:
            fixture = _parse_fixture(event)
            if fixture:
                fixtures.append(fixture)

        # Handle pagination
        pagination = body.get('pagination', {})
        if pagination.get('has_more') or (pagination.get('last_page') and pagination.get('current_page', 1) < pagination['last_page']):
            page2_url = url + '&page=2'
            req2 = urllib.request.Request(page2_url)
            with urllib.request.urlopen(req2, timeout=20) as resp2:
                body2 = json.loads(resp2.read().decode())
            for event in body2.get('data', []):
                fixture = _parse_fixture(event)
                if fixture:
                    fixtures.append(fixture)

    except urllib.error.URLError as e:
        print(f"⚠️ Error fetching fixtures for {date_str}: {e}")
    except Exception as e:
        print(f"⚠️ Unexpected error for {date_str}: {e}")

    print(f"  📅 {date_str}: {len(fixtures)} fixtures")
    return fixtures


def _parse_fixture(event):
    """Parse a single SportMonks fixture, extracting over/under lines and all markets"""
    try:
        participants = event.get('participants', [])
        home_team = away_team = ''
        home_logo = away_logo = ''
        home_short = away_short = ''
        home_id = away_id = None

        for p in participants:
            loc = (p.get('meta') or {}).get('location', '')
            if loc == 'home':
                home_team = p.get('name', '')
                home_logo = p.get('image_path', '')
                home_short = p.get('short_code', '')
                home_id = p.get('id')
            elif loc == 'away':
                away_team = p.get('name', '')
                away_logo = p.get('image_path', '')
                away_short = p.get('short_code', '')
                away_id = p.get('id')

        if not home_team or not away_team:
            return None

        league_data = event.get('league') or {}
        league_id = league_data.get('id', event.get('league_id', 0))
        league_name = _league_name(league_id)
        league_logo = league_data.get('image_path', '')
        season_id = event.get('season_id')

        starting_at = event.get('starting_at', '')

        odds_list = event.get('odds', [])

        # Parse over/under odds — collect best (lowest) Over odds per line
        lines = {}  # {total_float: {'over': best_odds, 'under': best_odds}}
        # Additional markets
        fulltime_result = {}    # {'home': best, 'draw': best, 'away': best}
        double_chance = {}      # {'home_draw': best, 'away_draw': best, 'home_away': best}
        btts = {}               # {'yes': best, 'no': best}
        home_to_score = {}      # {'yes': best, 'no': best}
        away_to_score = {}      # {'yes': best, 'no': best}
        first_half_goals = {}   # {total: {'over': best, 'under': best}}
        second_half_goals = {}  # {total: {'over': best, 'under': best}}
        home_goals = {}         # {total: {'over': best, 'under': best}}
        away_goals = {}         # {total: {'over': best, 'under': best}}

        for odd in odds_list:
            market = odd.get('market') or {}
            dev_name = market.get('developer_name', '')
            mkt_name = market.get('name', '')
            label = (odd.get('label') or '').strip()
            value_str = odd.get('value')
            total_str = odd.get('total')

            if value_str is None:
                continue
            try:
                value = float(value_str)
            except (ValueError, TypeError):
                continue

            # --- Fulltime Over/Under ---
            if 'OVER_UNDER' in dev_name or 'Over/Under' in mkt_name:
                if total_str is None:
                    continue
                try:
                    total = float(total_str)
                except (ValueError, TypeError):
                    continue
                if total not in lines:
                    lines[total] = {}
                if label == 'Over':
                    if 'over' not in lines[total] or value < lines[total]['over']:
                        lines[total]['over'] = value
                elif label == 'Under':
                    if 'under' not in lines[total] or value < lines[total]['under']:
                        lines[total]['under'] = value

            # --- Fulltime Result (1X2) ---
            elif dev_name == 'FULLTIME_RESULT' or (market.get('id') == 1 and '1X2' in mkt_name.upper()):
                _update_best_low(fulltime_result, _normalize_1x2_label(label), value)

            # --- Double Chance ---
            elif dev_name == 'DOUBLE_CHANCE' or market.get('id') == 2:
                dc_key = _normalize_dc_label(label)
                if dc_key:
                    _update_best_low(double_chance, dc_key, value)

            # --- Both Teams to Score ---
            elif dev_name == 'BOTH_TEAMS_TO_SCORE' or market.get('id') == 14:
                _update_best_low(btts, label.lower(), value)

            # --- Home Team to Score ---
            elif dev_name == 'HOME_TEAM_TO_SCORE' or market.get('id') == 36:
                _update_best_low(home_to_score, label.lower(), value)

            # --- Away Team to Score ---
            elif dev_name == 'AWAY_TEAM_TO_SCORE' or market.get('id') == 35:
                _update_best_low(away_to_score, label.lower(), value)

            # --- 1st Half Goals Over/Under ---
            elif dev_name == '1ST_HALF_GOALS' or market.get('id') == 28:
                _parse_ou_market(first_half_goals, label, total_str, value)

            # --- 2nd Half Goals Over/Under ---
            elif dev_name == '2ND_HALF_GOALS' or market.get('id') == 53:
                _parse_ou_market(second_half_goals, label, total_str, value)

            # --- Home Team Goals Over/Under ---
            elif dev_name == 'HOME_TEAM_GOALS' or market.get('id') == 20:
                _parse_ou_market(home_goals, label, total_str, value)

            # --- Away Team Goals Over/Under ---
            elif dev_name == 'AWAY_TEAM_GOALS' or market.get('id') == 21:
                _parse_ou_market(away_goals, label, total_str, value)

        # Filter to useful lines with reasonable odds
        available_lines = {}
        for point in [0.5, 1.5, 2.5, 3.5]:
            if point in lines and 'over' in lines[point]:
                odd = lines[point]['over']
                if 1.01 <= odd <= 5.0:
                    available_lines[point] = {
                        'over_odds': odd,
                        'under_odds': lines[point].get('under', 3.0),
                    }

        # Build markets dict
        markets = {}
        if fulltime_result:
            markets['fulltime_result'] = fulltime_result
        if double_chance:
            markets['double_chance'] = double_chance
        if btts:
            markets['btts'] = btts
        if home_to_score:
            markets['home_to_score'] = home_to_score
        if away_to_score:
            markets['away_to_score'] = away_to_score
        if first_half_goals:
            markets['first_half_goals'] = first_half_goals
        if second_half_goals:
            markets['second_half_goals'] = second_half_goals
        if home_goals:
            markets['home_goals'] = home_goals
        if away_goals:
            markets['away_goals'] = away_goals

        # Need at least over/under lines OR some other markets
        if not available_lines and not markets:
            return None

        return {
            'home_team': home_team,
            'away_team': away_team,
            'home_team_id': home_id,
            'away_team_id': away_id,
            'season_id': season_id,
            'commence_time': starting_at,
            'league': league_id,
            'league_name': league_name,
            'league_logo': league_logo,
            'home_logo': home_logo,
            'away_logo': away_logo,
            'home_short_code': home_short,
            'away_short_code': away_short,
            'lines': available_lines,
            'markets': markets,
        }
    except Exception:
        return None


def _update_best_low(d, key, value):
    """Update dict with value only if it's lower (best odds for bettor)"""
    if key and value > 1.0:
        if key not in d or value < d[key]:
            d[key] = value


def _normalize_1x2_label(label):
    """Normalize 1X2 label to home/draw/away"""
    l = label.lower().strip()
    if l in ('home', '1'):
        return 'home'
    if l in ('draw', 'x'):
        return 'draw'
    if l in ('away', '2'):
        return 'away'
    return ''


def _normalize_dc_label(label):
    """Normalize Double Chance label"""
    l = label.lower().strip()
    if 'home' in l and 'draw' in l or l in ('1x', 'x1'):
        return 'home_draw'
    if 'away' in l and 'draw' in l or l in ('x2', '2x'):
        return 'away_draw'
    if 'home' in l and 'away' in l or l in ('12', '1 or 2'):
        return 'home_away'
    return ''


def _parse_ou_market(target, label, total_str, value):
    """Parse an over/under sub-market into target dict"""
    if total_str is None:
        return
    try:
        total = float(total_str)
    except (ValueError, TypeError):
        return
    if total not in target:
        target[total] = {}
    lab = label.strip().lower()
    if lab == 'over':
        if 'over' not in target[total] or value < target[total]['over']:
            target[total]['over'] = value
    elif lab == 'under':
        if 'under' not in target[total] or value < target[total]['under']:
            target[total]['under'] = value


def _generate_match_options(fixtures, predictor, stats_calculator, sm_stats=None, free_mode=False):
    """
    Generate all match options from all markets for a list of fixtures.
    Now integrates live SportMonks stats + standings + statistical qualification + edge calculation.
    """
    from utils.stat_qualifier import passes_odds_safety, qualify_and_score, confidence_label
    from utils.sportmonks_stats import get_team_standing

    match_options = []

    for fix in fixtures:
        home = fix['home_team']
        away = fix['away_team']
        markets = fix.get('markets', {})

        # --- Fetch live team stats from SportMonks ---
        home_id = fix.get('home_team_id')
        away_id = fix.get('away_team_id')
        season_id = fix.get('season_id')
        home_live = None
        away_live = None
        h2h_data = None
        standings_ctx = None

        if sm_stats and home_id and away_id:
            try:
                home_live = sm_stats.fetch_team_stats(home_id)
                away_live = sm_stats.fetch_team_stats(away_id)
                h2h_data = sm_stats.fetch_h2h(home_id, away_id)
            except Exception as e:
                print(f"⚠️ Live stats error for {home} vs {away}: {e}")

        # --- Fetch league standings for context ---
        if season_id and home_id and away_id:
            try:
                home_standing = get_team_standing(season_id, home_id)
                away_standing = get_team_standing(season_id, away_id)
                if home_standing or away_standing:
                    standings_ctx = {
                        'home': home_standing,
                        'away': away_standing,
                    }
                    if home_standing and away_standing:
                        print(f"  📊 {home} #{home_standing['position']} ({home_standing['zone']}) vs {away} #{away_standing['position']} ({away_standing['zone']})")
            except Exception as e:
                print(f"⚠️ Standings error for {home} vs {away}: {e}")

        # --- Build 18-feature dict for XGBoost ---
        primary_line = next(iter(fix['lines'].values()), {})
        if home_live and away_live:
            features = _build_features_from_live(
                home_live, away_live,
                over15_odds=primary_line.get('over_odds', 1.5),
                under15_odds=primary_line.get('under_odds', 2.5),
            )
        else:
            features = stats_calculator.build_match_features(
                home, away,
                over15_odds=primary_line.get('over_odds', 1.5),
                under15_odds=primary_line.get('under_odds', 2.5),
            )

        # Run AI prediction for all 14 markets
        ai_pred = predictor.predict_match(features)

        base_info = {
            'home_team': home,
            'away_team': away,
            'commence_time': fix['commence_time'],
            'league': fix['league'],
            'league_name': fix.get('league_name', ''),
            'league_logo': fix.get('league_logo', ''),
            'home_logo': fix.get('home_logo', ''),
            'away_logo': fix.get('away_logo', ''),
            'home_short_code': fix.get('home_short_code', ''),
            'away_short_code': fix.get('away_short_code', ''),
            'all_predictions': {k: round(float(v), 3) for k, v in ai_pred.items()},
            # Match context for UI breakdown
            'home_form': _build_form_summary(home_live, 'home') if home_live else None,
            'away_form': _build_form_summary(away_live, 'away') if away_live else None,
            'h2h': h2h_data,
            'standings': standings_ctx,
        }

        # Helper to add a qualified option
        def _try_add(market_label, odds, ai_market_key, line=None, source='api'):
            if not passes_odds_safety(market_label, odds, free_mode=free_mode):
                return
            # Use dedicated model if available, fall back to proxy
            actual_key = ai_market_key
            if actual_key not in ai_pred:
                actual_key = AI_MARKET_FALLBACK.get(ai_market_key, ai_market_key)
            raw_ai_prob = float(ai_pred.get(actual_key, 0.5))
            qual = qualify_and_score(
                market_label, odds, raw_ai_prob,
                home_live, away_live, h2h_data,
                standings=standings_ctx,
            )
            if qual is None:
                return
            opt = dict(base_info)
            opt.update({
                'line': line,
                'market': market_label,
                'odds': odds,
                'ai_prob': qual['ai_prob'],
                'confidence': confidence_label(qual['edge']),
                'edge': qual['edge'],
                'stability': qual['stability'],
                'composite_score': qual['composite_score'],
                'source': source,
            })
            match_options.append(opt)

        # === Over/Under lines ===
        for point, line_data in fix['lines'].items():
            # Over market
            odds = line_data['over_odds']
            ai_market = LINE_TO_AI_MARKET.get(point, 'ft_over_15')
            label = LINE_LABELS.get(point, f'Over {point} Goals')
            _try_add(label, odds, ai_market, line=point)

            # Under market (3.5 and 4.5 are safe low-odds picks)
            under_odds = line_data.get('under_odds', 0)
            if under_odds > 0 and point >= 3.5:
                under_label = f'Under {point} Goals'
                _try_add(under_label, under_odds, ai_market, line=point)

        # === BTTS Yes ===
        btts_m = markets.get('btts', {})
        if 'yes' in btts_m:
            _try_add('Both Teams to Score', btts_m['yes'], AI_MARKET_MAP['btts_yes'])

        # === Fulltime Result ===
        ftr = markets.get('fulltime_result', {})

        if 'home' in ftr:
            _try_add('Home Win', ftr['home'], AI_MARKET_MAP['home_win'])
        if 'away' in ftr:
            _try_add('Away Win', ftr['away'], AI_MARKET_MAP['away_win'])

        # === Double Chance ===
        dc = markets.get('double_chance', {})
        if 'home_draw' in dc:
            _try_add('Double Chance (1X)', dc['home_draw'], AI_MARKET_MAP['double_chance_home_draw'])
        if 'away_draw' in dc:
            _try_add('Double Chance (X2)', dc['away_draw'], AI_MARKET_MAP['double_chance_away_draw'])
        if 'home_away' in dc:
            _try_add('Double Chance (12)', dc['home_away'], AI_MARKET_MAP['double_chance_home_away'])

        # === Team Goals ===
        hts = markets.get('home_to_score', {})
        if 'yes' in hts:
            _try_add('Home to Score', hts['yes'], AI_MARKET_MAP['home_to_score_yes'])
        ats = markets.get('away_to_score', {})
        if 'yes' in ats:
            _try_add('Away to Score', ats['yes'], AI_MARKET_MAP['away_to_score_yes'])

        # === Half Goals ===
        fhg = markets.get('first_half_goals', {})
        if 0.5 in fhg and 'over' in fhg[0.5]:
            _try_add('1st Half Over 0.5', fhg[0.5]['over'], AI_MARKET_MAP['fh_over_05'])
        shg = markets.get('second_half_goals', {})
        if 0.5 in shg and 'over' in shg[0.5]:
            _try_add('2nd Half Over 0.5', shg[0.5]['over'], AI_MARKET_MAP['sh_over_05'])

        # === Home/Away Goals Over 0.5 ===
        hg = markets.get('home_goals', {})
        if 0.5 in hg and 'over' in hg[0.5]:
            _try_add('Home Over 0.5 Goals', hg[0.5]['over'], AI_MARKET_MAP['home_over_05'])
        ag = markets.get('away_goals', {})
        if 0.5 in ag and 'over' in ag[0.5]:
            _try_add('Away Over 0.5 Goals', ag[0.5]['over'], AI_MARKET_MAP['away_over_05'])

        # === Draw (1X2) — high odds, valuable for free picks ===
        if 'draw' in ftr:
            _try_add('Draw', ftr['draw'], AI_MARKET_MAP['draw'])

        # === BTTS No ===
        if 'no' in btts_m:
            _try_add('BTTS No', btts_m['no'], AI_MARKET_MAP['btts_no'])

        # === 1st/2nd Half Under 0.5 ===
        if 0.5 in fhg and 'under' in fhg[0.5]:
            _try_add('1st Half Under 0.5', fhg[0.5]['under'], AI_MARKET_MAP['fh_under_05'])
        if 0.5 in shg and 'under' in shg[0.5]:
            _try_add('2nd Half Under 0.5', shg[0.5]['under'], AI_MARKET_MAP['sh_under_05'])

        # === Home/Away Over 1.5 & 2.5 Goals ===
        if 1.5 in hg and 'over' in hg[1.5]:
            _try_add('Home Over 1.5 Goals', hg[1.5]['over'], AI_MARKET_MAP['home_over_15'])
        if 2.5 in hg and 'over' in hg[2.5]:
            _try_add('Home Over 2.5 Goals', hg[2.5]['over'], 'ft_over_25')
        if 1.5 in ag and 'over' in ag[1.5]:
            _try_add('Away Over 1.5 Goals', ag[1.5]['over'], AI_MARKET_MAP['away_over_15'])
        if 2.5 in ag and 'over' in ag[2.5]:
            _try_add('Away Over 2.5 Goals', ag[2.5]['over'], 'ft_over_25')

    return match_options


def _build_features_from_live(home_stats, away_stats, over15_odds=1.5, under15_odds=2.5):
    """Build feature dict for XGBoost models, using live SportMonks stats.
    Provides both original 18 features and extended features when available."""
    home_attack = home_stats['avg_goals_scored'] / max(away_stats['avg_goals_conceded'], 0.3)
    away_attack = away_stats['avg_goals_scored'] / max(home_stats['avg_goals_conceded'], 0.3)
    
    features = {
        # Original 18 features
        'home_goals_per_game': home_stats['avg_goals_scored'],
        'home_goals_conceded_per_game': home_stats['avg_goals_conceded'],
        'home_over15_rate': home_stats['over15_rate'],
        'home_over05_rate': home_stats.get('scored_in_rate', 0.78),
        'home_first_half_goals': home_stats['avg_goals_scored'] * 0.45,
        'away_goals_per_game': away_stats['avg_goals_scored'],
        'away_goals_conceded_per_game': away_stats['avg_goals_conceded'],
        'away_over15_rate': away_stats['over15_rate'],
        'away_over05_rate': away_stats.get('scored_in_rate', 0.70),
        'away_first_half_goals': away_stats['avg_goals_scored'] * 0.42,
        'home_home_goals': home_stats['home_avg_scored'],
        'home_home_conceded': home_stats['home_avg_conceded'],
        'away_away_goals': away_stats['away_avg_scored'],
        'away_away_conceded': away_stats['away_avg_conceded'],
        'total_expected_goals': home_stats['home_avg_scored'] + away_stats['away_avg_scored'],
        'defensive_strength': home_stats['home_avg_conceded'] + away_stats['away_avg_conceded'],
        'over15_odds': over15_odds,
        'under15_odds': under15_odds,
        # Extended features (used by retrained models)
        'home_btts_rate': home_stats.get('btts_rate', 0.55),
        'away_btts_rate': away_stats.get('btts_rate', 0.55),
        'home_clean_sheet_rate': home_stats.get('clean_sheet_rate', 0.30),
        'away_clean_sheet_rate': away_stats.get('clean_sheet_rate', 0.25),
        'home_attack_strength': home_attack,
        'away_attack_strength': away_attack,
        'attack_vs_defense_ratio': home_attack / max(away_attack, 0.3),
        'home_momentum': 0.0,  # Not available from live stats
        'away_momentum': 0.0,
        'home_goals_std': 0.5,  # Default variance
        'away_goals_std': 0.5,
        'home_over25_rate': home_stats.get('over25_rate', 0.45),
        'away_over25_rate': away_stats.get('over25_rate', 0.40),
        'home_scored_in_rate': home_stats.get('scored_in_rate', 0.78),
        'away_scored_in_rate': away_stats.get('scored_in_rate', 0.70),
    }
    return features


def build_daily_slip(fixtures, predictor, stats_calculator, max_matches=4, max_odds=2.60, sm_stats=None, free_mode=False):
    """
    Build the best daily rollover slip using hybrid architecture.
    Tries multiple market options per fixture to find ideal combined odds.
    """
    from itertools import product

    match_options = _generate_match_options(fixtures, predictor, stats_calculator, sm_stats, free_mode=free_mode)

    if not match_options:
        return _empty_result(fixtures)

    # Sort by composite score descending
    match_options.sort(key=lambda x: x.get('composite_score', 0), reverse=True)

    # Group options by fixture (top 3 per match)
    fixture_options = {}
    for opt in match_options:
        key = f"{opt['home_team']}_{opt['away_team']}"
        if key not in fixture_options:
            fixture_options[key] = []
        if len(fixture_options[key]) < 3:
            fixture_options[key].append(opt)

    fixture_keys = list(fixture_options.keys())
    num_fixtures = len(fixture_keys)

    if num_fixtures == 0:
        return _empty_result(fixtures)

    best_slip = None
    best_score = -1
    best_count = 0

    # Try 4-match first (preferred), then 3, then 2
    for target_count in [4, 3, 2]:
        if num_fixtures < target_count:
            continue

        # If we already have a combo with more matches, skip smaller combos
        if best_slip and best_count > target_count:
            break

        from itertools import combinations as combs
        for fixture_combo in combs(range(num_fixtures), target_count):
            option_lists = [fixture_options[fixture_keys[i]] for i in fixture_combo]
            for market_combo in product(*option_lists):
                combined = 1.0
                for pick in market_combo:
                    combined *= pick['odds']

                if combined < 1.50 or combined > max_odds:
                    continue

                avg_composite = sum(p.get('composite_score', 0) for p in market_combo) / len(market_combo)
                # Prefer ideal odds range
                ideal_bonus = 1.0
                if 2.00 <= combined <= 2.30:
                    ideal_bonus = 1.25
                elif 1.90 <= combined <= 2.40:
                    ideal_bonus = 1.15
                elif 1.80 <= combined < 1.90:
                    ideal_bonus = 1.05
                elif 1.50 <= combined < 1.80:
                    ideal_bonus = 0.90  # Acceptable but not ideal

                score = avg_composite * ideal_bonus

                if score > best_score:
                    best_score = score
                    best_slip = list(market_combo)
                    best_count = target_count

    if not best_slip:
        # Fallback: any 2 picks hitting 1.50+
        for i, a in enumerate(match_options[:10]):
            for j, b in enumerate(match_options[:10]):
                if i >= j:
                    continue
                combined = a['odds'] * b['odds']
                if 1.50 <= combined <= max_odds:
                    best_slip = [a, b]
                    break
            if best_slip:
                break
        # Last resort: single strongest pick
        if not best_slip and match_options:
            best_slip = [match_options[0]]

    if not best_slip:
        return _empty_result(fixtures)

    combined_odds = 1.0
    for p in best_slip:
        combined_odds *= p['odds']

    return {
        'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'total_fixtures_analyzed': len(fixtures),
        'slip': {
            'matches': _format_slip_matches(best_slip),
            'match_count': len(best_slip),
            'combined_odds': round(combined_odds, 2),
            'slip_confidence': _slip_confidence(best_slip),
        },
        'all_predictions': _format_all_predictions(match_options),
    }


def _empty_result(fixtures):
    return {
        'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'total_fixtures_analyzed': len(fixtures) if fixtures else 0,
        'slip': {
            'matches': [],
            'match_count': 0,
            'combined_odds': 0,
            'slip_confidence': 'NONE',
        },
        'all_predictions': [],
        'message': 'No safe rollover picks today.',
    }


def build_parlay_slip(fixtures, predictor, stats_calculator, num_matches=5, min_odds=1.30, max_odds=3.00, sm_stats=None, free_mode=False):
    """
    Build a higher-odds parlay from ALL markets.
    User controls number of matches (2-20).
    Each match can use any market (1X2, BTTS, Over/Under, DC, etc.)
    Select matches with highest composite score within the odds range.
    """
    match_options = _generate_match_options(fixtures, predictor, stats_calculator, sm_stats, free_mode=free_mode)

    # Filter to options within odds range
    filtered = [o for o in match_options if min_odds <= o['odds'] <= max_odds]

    # Sort by composite score descending
    filtered.sort(key=lambda x: x.get('composite_score', 0), reverse=True)

    # Pick top num_matches unique matches (one market per match)
    slip_matches = []
    combined_odds = 1.0
    used_matches = set()

    for opt in filtered:
        match_key = f"{opt['home_team']}_{opt['away_team']}"
        if match_key in used_matches:
            continue
        slip_matches.append(opt)
        combined_odds *= opt['odds']
        used_matches.add(match_key)
        if len(slip_matches) >= num_matches:
            break

    return {
        'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'total_fixtures_analyzed': len(fixtures),
        'slip': {
            'matches': _format_slip_matches(slip_matches),
            'match_count': len(slip_matches),
            'combined_odds': round(combined_odds, 2),
            'slip_confidence': _slip_confidence(slip_matches),
        },
        'all_predictions': _format_all_predictions(match_options),
    }


def _format_slip_matches(matches):
    """Format slip matches for API response"""
    result = []
    for m in matches:
        entry = {
            'home_team': m['home_team'],
            'away_team': m['away_team'],
            'match': f"{m['home_team']} vs {m['away_team']}",
            'league': _league_name(m['league']),
            'league_logo': m.get('league_logo', ''),
            'home_logo': m.get('home_logo', ''),
            'away_logo': m.get('away_logo', ''),
            'home_short_code': m.get('home_short_code', ''),
            'away_short_code': m.get('away_short_code', ''),
            'kickoff': m['commence_time'],
            'market': m['market'],
            'odds': m['odds'],
            'ai_probability': round(m['ai_prob'] * 100, 1),
            'confidence': m['confidence'],
            'edge': round(m['edge'] * 100, 1),
            'source': m.get('source', 'api'),
            'all_markets': {
                k: {
                    'probability': round(v * 100, 1),
                    'confidence': 'HIGH' if v >= 0.75 else 'MEDIUM' if v >= 0.65 else 'LOW',
                }
                for k, v in m['all_predictions'].items()
            },
        }

        # Match context for breakdown UI
        if m.get('home_form'):
            entry['home_form'] = m['home_form']
        if m.get('away_form'):
            entry['away_form'] = m['away_form']

        h2h = m.get('h2h')
        if h2h:
            entry['h2h'] = {
                'played': h2h.get('total_matches', 0),
                'avg_goals': round(h2h.get('avg_goals', 0), 1),
                'btts_pct': round((h2h.get('btts_count', 0) / max(h2h.get('total_matches', 1), 1)) * 100),
                'over25_pct': round((h2h.get('over25_count', 0) / max(h2h.get('total_matches', 1), 1)) * 100),
            }

        standings = m.get('standings')
        if standings:
            s = {}
            if standings.get('home'):
                s['home_pos'] = standings['home'].get('position')
                s['home_pts'] = standings['home'].get('points')
                s['home_zone'] = standings['home'].get('zone')
            if standings.get('away'):
                s['away_pos'] = standings['away'].get('position')
                s['away_pts'] = standings['away'].get('points')
                s['away_zone'] = standings['away'].get('zone')
            if s:
                entry['standings'] = s

        result.append(entry)
    return result


def _format_all_predictions(predictions):
    """Format all analyzed matches for API response"""
    result = []
    for p in predictions[:20]:
        result.append({
            'home_team': p['home_team'],
            'away_team': p['away_team'],
            'match': f"{p['home_team']} vs {p['away_team']}",
            'league': _league_name(p['league']),
            'league_logo': p.get('league_logo', ''),
            'home_logo': p.get('home_logo', ''),
            'away_logo': p.get('away_logo', ''),
            'home_short_code': p.get('home_short_code', ''),
            'away_short_code': p.get('away_short_code', ''),
            'kickoff': p['commence_time'],
            'market': p['market'],
            'odds': p['odds'],
            'ai_probability': round(p['ai_prob'] * 100, 1),
            'confidence': p['confidence'],
            'edge': round(p['edge'] * 100, 1),
            'composite_score': round(p.get('composite_score', 0), 3),
        })
    return result


def _slip_confidence(matches):
    if not matches:
        return 'NONE'
    high_count = sum(1 for m in matches if m['confidence'] == 'HIGH')
    if high_count == len(matches):
        return 'HIGH'
    if high_count > 0:
        return 'MEDIUM'
    return 'LOW'


def _league_name(league_id):
    if league_id in LEAGUE_IDS:
        return LEAGUE_IDS[league_id]
    # Negative IDs = football-data.org fallback (name set in fixture dict)
    return f'League {league_id}'


def _build_form_summary(stats, side):
    """Build compact form summary from team stats for UI."""
    if not stats:
        return None
    return {
        'avg_scored': round(stats.get('avg_goals_scored', 0), 1),
        'avg_conceded': round(stats.get('avg_goals_conceded', 0), 1),
        'scored_in_pct': round(stats.get('scored_in_rate', 0) * 100),
        'clean_sheet_pct': round(stats.get('clean_sheet_rate', 0) * 100),
        'over15_pct': round(stats.get('over15_rate', 0) * 100),
        'btts_pct': round(stats.get('btts_rate', 0) * 100),
        'matches': stats.get('matches_played', 0),
    }

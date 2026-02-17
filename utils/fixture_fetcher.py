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

# League IDs — ONLY leagues available in the SportMonks plan
LEAGUE_IDS = {
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
    2.5: 'ft_over_15',   # Over 2.5 → Full Time Over 1.5 (best proxy)
    3.5: 'ft_over_15',   # Over 3.5 → Full Time Over 1.5
}

LINE_LABELS = {
    0.5: 'Over 0.5 Goals',
    1.5: 'Over 1.5 Goals',
    2.5: 'Over 2.5 Goals',
    3.5: 'Over 3.5 Goals',
}

# AI model mapping for new markets
AI_MARKET_MAP = {
    'home_to_score_yes': 'home_over_05',
    'away_to_score_yes': 'away_over_05',
    'fh_over_05': 'fh_over_05',
    'sh_over_05': 'sh_over_05',
    'home_over_05': 'home_over_05',
    'away_over_05': 'away_over_05',
    'btts_yes': 'ft_over_15',
    'home_win': 'home_over_15',
    'away_win': 'away_over_15',
    'double_chance_home_draw': 'home_over_05',
    'double_chance_away_draw': 'away_over_05',
    'double_chance_home_away': 'ft_over_15',
}


def fetch_todays_fixtures():
    """Fetch today's fixtures with over/under odds from SportMonks API."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    fixtures = _fetch_fixtures_for_date(today)

    # Sort by kickoff time
    fixtures.sort(key=lambda f: f.get('commence_time', ''))

    print(f"✅ Fetched {len(fixtures)} fixtures for {today}")
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


def _generate_match_options(fixtures, predictor, stats_calculator, sm_stats=None):
    """
    Generate all match options from all markets for a list of fixtures.
    Now integrates live SportMonks stats + statistical qualification + edge calculation.
    """
    from utils.stat_qualifier import passes_odds_safety, qualify_and_score, confidence_label

    match_options = []

    for fix in fixtures:
        home = fix['home_team']
        away = fix['away_team']
        markets = fix.get('markets', {})

        # --- Fetch live team stats from SportMonks ---
        home_id = fix.get('home_team_id')
        away_id = fix.get('away_team_id')
        home_live = None
        away_live = None
        h2h_data = None

        if sm_stats and home_id and away_id:
            try:
                home_live = sm_stats.fetch_team_stats(home_id)
                away_live = sm_stats.fetch_team_stats(away_id)
                h2h_data = sm_stats.fetch_h2h(home_id, away_id)
            except Exception as e:
                print(f"⚠️ Live stats error for {home} vs {away}: {e}")

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
        }

        # Helper to add a qualified option
        def _try_add(market_label, odds, ai_market_key, line=None, source='api'):
            if not passes_odds_safety(market_label, odds):
                return
            raw_ai_prob = float(ai_pred.get(ai_market_key, 0.5))
            qual = qualify_and_score(
                market_label, odds, raw_ai_prob,
                home_live, away_live, h2h_data,
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

    return match_options


def _build_features_from_live(home_stats, away_stats, over15_odds=1.5, under15_odds=2.5):
    """Build the 18-feature dict the XGBoost models expect, using live SportMonks stats."""
    return {
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
    }


def build_daily_slip(fixtures, predictor, stats_calculator, max_matches=4, max_odds=2.60, sm_stats=None):
    """
    Build the best daily rollover slip using hybrid architecture.
    Tries multiple market options per fixture to find ideal combined odds.
    """
    from itertools import product

    match_options = _generate_match_options(fixtures, predictor, stats_calculator, sm_stats)

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


def build_parlay_slip(fixtures, predictor, stats_calculator, num_matches=5, min_odds=1.30, max_odds=3.00, sm_stats=None):
    """
    Build a higher-odds parlay from ALL markets.
    User controls number of matches (2-20).
    Each match can use any market (1X2, BTTS, Over/Under, DC, etc.)
    Select matches with highest composite score within the odds range.
    """
    match_options = _generate_match_options(fixtures, predictor, stats_calculator, sm_stats)

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
        result.append({
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
        })
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
    return LEAGUE_IDS.get(league_id, f'League {league_id}')

"""
Fetch today's fixtures from SportMonks API and generate AI predictions + slip
Supports mixed markets: Over/Under, 1X2, BTTS, Double Chance, Team Goals, Half Goals
"""
import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone


SPORTMONKS_TOKEN = os.environ.get(
    'SPORTMONKS_TOKEN',
    'b7EFSY6Bmrxisf6OswWjYArQUHMakSEDRMTJVoFiH56sbHsxaJxFRpVrOuoL',
)
SPORTMONKS_BASE = 'https://api.sportmonks.com/v3/football'

# Top league IDs (expanded to ensure daily coverage)
LEAGUE_IDS = {
    # Top 5 European Leagues
    8: 'Premier League',
    564: 'La Liga',
    82: 'Bundesliga',
    384: 'Serie A',
    301: 'Ligue 1',
    # More European Leagues
    9: 'Championship',
    72: 'Eredivisie',
    462: 'Liga Portugal',
    600: 'Super Lig',
    271: 'Scottish Premiership',
    208: 'Belgian Pro League',
}
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
    """Fetch today's fixtures with over/under odds from SportMonks API"""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    url = (
        f"{SPORTMONKS_BASE}/fixtures/date/{today}"
        f"?api_token={SPORTMONKS_TOKEN}"
        f"&include=participants;league;odds.market"
        f"&filters=fixtureLeagues:{LEAGUE_FILTER}"
        f"&per_page=50"
    )

    all_fixtures = []
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode())

        events = body.get('data', [])
        for event in events:
            fixture = _parse_fixture(event)
            if fixture:
                all_fixtures.append(fixture)

    except urllib.error.URLError as e:
        print(f"⚠️ Error fetching SportMonks fixtures: {e}")
    except Exception as e:
        print(f"⚠️ Unexpected error fetching fixtures: {e}")

    print(f"✅ Fetched {len(all_fixtures)} fixtures with odds")
    return all_fixtures


def _parse_fixture(event):
    """Parse a single SportMonks fixture, extracting over/under lines and all markets"""
    try:
        participants = event.get('participants', [])
        home_team = away_team = ''
        home_logo = away_logo = ''
        home_short = away_short = ''

        for p in participants:
            loc = (p.get('meta') or {}).get('location', '')
            if loc == 'home':
                home_team = p.get('name', '')
                home_logo = p.get('image_path', '')
                home_short = p.get('short_code', '')
            elif loc == 'away':
                away_team = p.get('name', '')
                away_logo = p.get('image_path', '')
                away_short = p.get('short_code', '')

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


def _generate_match_options(fixtures, predictor, stats_calculator):
    """Generate all match options from all markets for a list of fixtures."""
    match_options = []

    for fix in fixtures:
        home = fix['home_team']
        away = fix['away_team']
        markets = fix.get('markets', {})

        # Build features
        primary_line = next(iter(fix['lines'].values()), {})
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

        # === Over/Under lines (existing) ===
        for point, line_data in fix['lines'].items():
            odds = line_data['over_odds']
            ai_market = LINE_TO_AI_MARKET.get(point, 'ft_over_15')
            ai_prob = float(ai_pred.get(ai_market, 0.5))

            if point == 0.5:
                ai_prob = min(ai_prob * 1.15, 0.99)
            elif point == 1.5:
                ai_prob = ai_prob * 1.05
            elif point == 2.5:
                ai_prob = ai_prob * 0.92
            elif point == 3.5:
                ai_prob = ai_prob * 0.75

            match_options.append(_build_option(
                base_info, odds, ai_prob,
                LINE_LABELS.get(point, f'Over {point} Goals'),
                line=point, source='api',
            ))

        # === Synthetic Over 1.5 market ===
        ft_over15 = float(ai_pred.get('ft_over_15', 0.5))
        if ft_over15 >= 0.70:
            synth_odds = round(1.0 / (ft_over15 * 0.95), 2)
            synth_odds = max(synth_odds, 1.10)
            match_options.append(_build_option(
                base_info, synth_odds, ft_over15,
                'Over 1.5 Goals', line=1.5, source='ai_model',
            ))

        # === Home to Score (Yes) ===
        hts = markets.get('home_to_score', {})
        if 'yes' in hts and 1.01 <= hts['yes'] <= 5.0:
            ai_prob = float(ai_pred.get(AI_MARKET_MAP['home_to_score_yes'], 0.5))
            match_options.append(_build_option(
                base_info, hts['yes'], ai_prob,
                'Home to Score', source='api',
            ))

        # === Away to Score (Yes) ===
        ats = markets.get('away_to_score', {})
        if 'yes' in ats and 1.01 <= ats['yes'] <= 5.0:
            ai_prob = float(ai_pred.get(AI_MARKET_MAP['away_to_score_yes'], 0.5))
            match_options.append(_build_option(
                base_info, ats['yes'], ai_prob,
                'Away to Score', source='api',
            ))

        # === BTTS Yes ===
        btts_m = markets.get('btts', {})
        if 'yes' in btts_m and 1.01 <= btts_m['yes'] <= 5.0:
            ai_prob = float(ai_pred.get(AI_MARKET_MAP['btts_yes'], 0.5))
            match_options.append(_build_option(
                base_info, btts_m['yes'], ai_prob,
                'Both Teams to Score', source='api',
            ))

        # === First Half Over 0.5 ===
        fhg = markets.get('first_half_goals', {})
        if 0.5 in fhg and 'over' in fhg[0.5] and 1.01 <= fhg[0.5]['over'] <= 5.0:
            ai_prob = float(ai_pred.get(AI_MARKET_MAP['fh_over_05'], 0.5))
            match_options.append(_build_option(
                base_info, fhg[0.5]['over'], ai_prob,
                '1H Over 0.5', source='api',
            ))

        # === Second Half Over 0.5 ===
        shg = markets.get('second_half_goals', {})
        if 0.5 in shg and 'over' in shg[0.5] and 1.01 <= shg[0.5]['over'] <= 5.0:
            ai_prob = float(ai_pred.get(AI_MARKET_MAP['sh_over_05'], 0.5))
            match_options.append(_build_option(
                base_info, shg[0.5]['over'], ai_prob,
                '2H Over 0.5', source='api',
            ))

        # === Fulltime Result: Home Win ===
        ftr = markets.get('fulltime_result', {})
        if 'home' in ftr and 1.01 <= ftr['home'] <= 5.0:
            ai_prob = float(ai_pred.get(AI_MARKET_MAP['home_win'], 0.5))
            match_options.append(_build_option(
                base_info, ftr['home'], ai_prob,
                'Home Win', source='api',
            ))

        # === Fulltime Result: Away Win ===
        if 'away' in ftr and 1.01 <= ftr['away'] <= 5.0:
            ai_prob = float(ai_pred.get(AI_MARKET_MAP['away_win'], 0.5))
            match_options.append(_build_option(
                base_info, ftr['away'], ai_prob,
                'Away Win', source='api',
            ))

        # === Double Chance: Home or Draw ===
        dc = markets.get('double_chance', {})
        if 'home_draw' in dc and 1.01 <= dc['home_draw'] <= 5.0:
            ai_prob = float(ai_pred.get(AI_MARKET_MAP['double_chance_home_draw'], 0.5))
            match_options.append(_build_option(
                base_info, dc['home_draw'], ai_prob,
                'Home or Draw', source='api',
            ))

        # === Double Chance: Draw or Away ===
        if 'away_draw' in dc and 1.01 <= dc['away_draw'] <= 5.0:
            ai_prob = float(ai_pred.get(AI_MARKET_MAP['double_chance_away_draw'], 0.5))
            match_options.append(_build_option(
                base_info, dc['away_draw'], ai_prob,
                'Draw or Away', source='api',
            ))

        # === Double Chance: Home or Away ===
        if 'home_away' in dc and 1.01 <= dc['home_away'] <= 5.0:
            ai_prob = float(ai_pred.get(AI_MARKET_MAP['double_chance_home_away'], 0.5))
            match_options.append(_build_option(
                base_info, dc['home_away'], ai_prob,
                'Home or Away', source='api',
            ))

        # === Home Goals Over 0.5 ===
        hg = markets.get('home_goals', {})
        if 0.5 in hg and 'over' in hg[0.5] and 1.01 <= hg[0.5]['over'] <= 5.0:
            ai_prob = float(ai_pred.get(AI_MARKET_MAP['home_over_05'], 0.5))
            match_options.append(_build_option(
                base_info, hg[0.5]['over'], ai_prob,
                'Home Over 0.5 Goals', source='api',
            ))

        # === Away Goals Over 0.5 ===
        ag = markets.get('away_goals', {})
        if 0.5 in ag and 'over' in ag[0.5] and 1.01 <= ag[0.5]['over'] <= 5.0:
            ai_prob = float(ai_pred.get(AI_MARKET_MAP['away_over_05'], 0.5))
            match_options.append(_build_option(
                base_info, ag[0.5]['over'], ai_prob,
                'Away Over 0.5 Goals', source='api',
            ))

    return match_options


def _build_option(base_info, odds, ai_prob, market_label, line=None, source='api'):
    """Build a single match option dict."""
    confidence = 'HIGH' if ai_prob >= 0.75 else 'MEDIUM' if ai_prob >= 0.65 else 'LOW'
    implied = 1.0 / odds if odds > 0 else 0.5
    edge = ai_prob - implied
    opt = dict(base_info)
    opt.update({
        'line': line,
        'market': market_label,
        'odds': odds,
        'ai_prob': ai_prob,
        'confidence': confidence,
        'edge': edge,
        'score': ai_prob * max(edge, 0) * 100,
        'source': source,
    })
    return opt


def build_daily_slip(fixtures, predictor, stats_calculator, max_matches=4, max_odds=2.10):
    """
    Build the best slip from today's fixtures using mixed markets.
    Uses AI probabilities to create fair odds for markets the API doesn't provide,
    enabling lower-odds selections that combine under the target.
    """
    match_options = _generate_match_options(fixtures, predictor, stats_calculator)

    # Sort by AI probability descending
    match_options.sort(key=lambda x: x['ai_prob'], reverse=True)

    # === SMART SLIP BUILDER ===
    slip_matches = []
    combined_odds = 1.0
    used_matches = set()

    # Phase 1: Try to add HIGH confidence matches with lower odds first
    for opt in match_options:
        match_key = f"{opt['home_team']}_{opt['away_team']}"
        if match_key in used_matches:
            continue
        if len(slip_matches) >= max_matches:
            break
        if opt['confidence'] != 'HIGH':
            continue

        new_odds = combined_odds * opt['odds']
        if new_odds <= max_odds:
            slip_matches.append(opt)
            combined_odds = new_odds
            used_matches.add(match_key)

    # Phase 2: If not enough, add MEDIUM confidence
    if len(slip_matches) < 2:
        for opt in match_options:
            match_key = f"{opt['home_team']}_{opt['away_team']}"
            if match_key in used_matches:
                continue
            if len(slip_matches) >= max_matches:
                break
            if opt['confidence'] == 'LOW':
                continue

            new_odds = combined_odds * opt['odds']
            if new_odds <= max_odds:
                slip_matches.append(opt)
                combined_odds = new_odds
                used_matches.add(match_key)

    # Phase 3: If still only 1 match, force-add lowest-odds high-prob match
    if len(slip_matches) < 2 and match_options:
        low_odds_options = sorted(
            [o for o in match_options
             if f"{o['home_team']}_{o['away_team']}" not in used_matches
             and o['ai_prob'] >= 0.65],
            key=lambda x: x['odds']
        )
        for opt in low_odds_options:
            match_key = f"{opt['home_team']}_{opt['away_team']}"
            if match_key in used_matches:
                continue
            if len(slip_matches) >= max_matches:
                break
            new_odds = combined_odds * opt['odds']
            if new_odds <= max_odds:
                slip_matches.append(opt)
                combined_odds = new_odds
                used_matches.add(match_key)

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


def build_parlay_slip(fixtures, predictor, stats_calculator, num_matches=5, min_odds=1.30, max_odds=3.00):
    """
    Build a higher-odds parlay from ALL markets.
    User controls number of matches (2-20).
    Each match can use any market (1X2, BTTS, Over/Under, DC, etc.)
    Select matches with highest AI probability within the odds range.
    """
    match_options = _generate_match_options(fixtures, predictor, stats_calculator)

    # Filter to options within odds range
    filtered = [o for o in match_options if min_odds <= o['odds'] <= max_odds]

    # Sort by AI probability descending
    filtered.sort(key=lambda x: x['ai_prob'], reverse=True)

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

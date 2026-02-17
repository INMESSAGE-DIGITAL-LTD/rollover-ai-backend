"""
Fetch today's fixtures from SportMonks API and generate AI predictions + slip
Supports mixed markets: Over 0.5, 1.5, 2.5, 3.5 goals
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

# Top-5 league IDs
LEAGUE_IDS = {
    8: 'Premier League',
    564: 'La Liga',
    82: 'Bundesliga',
    384: 'Serie A',
    301: 'Ligue 1',
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
    """Parse a single SportMonks fixture, extracting over/under lines"""
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

        # Parse over/under odds — collect best (lowest) Over odds per line
        odds_list = event.get('odds', [])
        lines = {}  # {total_float: {'over': best_odds, 'under': best_odds}}

        for odd in odds_list:
            market = odd.get('market') or {}
            dev_name = market.get('developer_name', '')
            mkt_name = market.get('name', '')
            if 'OVER_UNDER' not in dev_name and 'Over/Under' not in mkt_name:
                continue

            label = (odd.get('label') or '').strip()
            total_str = odd.get('total')
            value_str = odd.get('value')
            if total_str is None or value_str is None:
                continue

            try:
                total = float(total_str)
                value = float(value_str)
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

        if not available_lines:
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
        }
    except Exception:
        return None


def build_daily_slip(fixtures, predictor, stats_calculator, max_matches=4, max_odds=2.10):
    """
    Build the best slip from today's fixtures using mixed markets.
    Uses AI probabilities to create fair odds for markets the API doesn't provide,
    enabling lower-odds selections that combine under the target.
    """
    match_options = []

    for fix in fixtures:
        home = fix['home_team']
        away = fix['away_team']

        # Build features
        primary_line = next(iter(fix['lines'].values()), {})
        features = stats_calculator.build_match_features(
            home, away,
            over15_odds=primary_line.get('over_odds', 1.5),
            under15_odds=primary_line.get('under_odds', 2.5),
        )

        # Run AI prediction for all 14 markets
        ai_pred = predictor.predict_match(features)

        # Generate options for multiple markets per match
        # Real odds from API
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

            confidence = 'HIGH' if ai_prob >= 0.75 else 'MEDIUM' if ai_prob >= 0.65 else 'LOW'
            implied = 1.0 / odds if odds > 0 else 0.5
            edge = ai_prob - implied

            match_options.append({
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
                'line': point,
                'market': LINE_LABELS.get(point, f'Over {point} Goals'),
                'odds': odds,
                'ai_prob': ai_prob,
                'confidence': confidence,
                'edge': edge,
                'score': ai_prob * max(edge, 0) * 100,
                'source': 'api',
                'all_predictions': {k: round(float(v), 3) for k, v in ai_pred.items()},
            })

        # Synthetic Over 1.5 market (calculated from AI model)
        ft_over15 = float(ai_pred.get('ft_over_15', 0.5))
        if ft_over15 >= 0.70:
            # Fair odds = 1 / probability (with small margin)
            synth_odds = round(1.0 / (ft_over15 * 0.95), 2)
            synth_odds = max(synth_odds, 1.10)  # Floor at 1.10
            edge_15 = ft_over15 - (1.0 / synth_odds)

            match_options.append({
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
                'line': 1.5,
                'market': 'Over 1.5 Goals',
                'odds': synth_odds,
                'ai_prob': ft_over15,
                'confidence': 'HIGH' if ft_over15 >= 0.75 else 'MEDIUM',
                'edge': edge_15,
                'score': ft_over15 * max(edge_15, 0) * 100,
                'source': 'ai_model',
                'all_predictions': {k: round(float(v), 3) for k, v in ai_pred.items()},
            })

    # Sort by AI probability descending
    match_options.sort(key=lambda x: x['ai_prob'], reverse=True)

    # === SMART SLIP BUILDER ===
    # Strategy: Build the best combination of matches under max_odds
    # Prefer matches with highest AI confidence and positive edge
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

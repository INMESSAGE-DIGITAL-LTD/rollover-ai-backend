"""
Fetch today's fixtures from The Odds API and generate AI predictions + slip
Supports mixed markets: Over 0.5, 1.5, 2.5, 3.5 goals
"""
import os
import json
import urllib.request
import urllib.error
from datetime import datetime


ODDS_API_KEY = os.environ.get('ODDS_API_KEY', 'a3897783adea6774d79a4c5f1eff884c')
ODDS_API_BASE = 'https://api.the-odds-api.com/v4'

LEAGUES = [
    'soccer_epl',
    'soccer_spain_la_liga',
    'soccer_germany_bundesliga',
    'soccer_italy_serie_a',
    'soccer_france_ligue_one',
]

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
    """Fetch upcoming fixtures with ALL over/under lines from The Odds API"""
    all_fixtures = []

    for sport in LEAGUES:
        try:
            url = (
                f"{ODDS_API_BASE}/sports/{sport}/odds"
                f"?apiKey={ODDS_API_KEY}"
                f"&regions=uk,eu"
                f"&markets=totals"
                f"&oddsFormat=decimal"
            )
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            for event in data:
                fixture = _parse_fixture(event, sport)
                if fixture:
                    all_fixtures.append(fixture)

        except urllib.error.URLError as e:
            print(f"⚠️ Error fetching {sport}: {e}")
        except Exception as e:
            print(f"⚠️ Unexpected error for {sport}: {e}")

    print(f"✅ Fetched {len(all_fixtures)} fixtures with odds")
    return all_fixtures


def _parse_fixture(event, sport_key):
    """Parse a single event, extracting ALL over/under lines"""
    try:
        home = event.get('home_team', '')
        away = event.get('away_team', '')
        commence = event.get('commence_time', '')
        bookmakers = event.get('bookmakers', [])

        # Collect all available lines from first bookmaker
        lines = {}  # {point: {'over': price, 'under': price}}

        for bookie in bookmakers:
            markets = bookie.get('markets', [])
            for market in markets:
                if market.get('key') != 'totals':
                    continue
                outcomes = market.get('outcomes', [])
                for outcome in outcomes:
                    point = outcome.get('point')
                    price = outcome.get('price')
                    name = outcome.get('name')
                    if point is not None and price is not None:
                        if point not in lines:
                            lines[point] = {}
                        if name == 'Over':
                            lines[point]['over'] = float(price)
                        elif name == 'Under':
                            lines[point]['under'] = float(price)
            if lines:
                break  # Use first bookmaker with data

        if not lines:
            return None

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
            'home_team': home,
            'away_team': away,
            'commence_time': commence,
            'league': sport_key,
            'lines': available_lines,  # All available over/under lines
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
        'date': datetime.utcnow().strftime('%Y-%m-%d'),
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


def _league_name(key):
    names = {
        'soccer_epl': 'Premier League',
        'soccer_spain_la_liga': 'La Liga',
        'soccer_germany_bundesliga': 'Bundesliga',
        'soccer_italy_serie_a': 'Serie A',
        'soccer_france_ligue_one': 'Ligue 1',
    }
    return names.get(key, key)

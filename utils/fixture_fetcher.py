"""
Fetch today's fixtures from The Odds API and generate AI predictions + slip
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


def fetch_todays_fixtures():
    """Fetch upcoming fixtures with Over/Under odds from The Odds API"""
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
    """Parse a single event from Odds API response"""
    try:
        home = event.get('home_team', '')
        away = event.get('away_team', '')
        commence = event.get('commence_time', '')
        bookmakers = event.get('bookmakers', [])

        over15_odd = None
        under15_odd = None

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
                    if point == 2.5 and name == 'Over' and price:
                        over15_odd = float(price)
                    elif point == 2.5 and name == 'Under' and price:
                        under15_odd = float(price)
                if over15_odd:
                    break
            if over15_odd:
                break

        if not over15_odd or over15_odd < 1.10 or over15_odd > 3.0:
            return None

        return {
            'home_team': home,
            'away_team': away,
            'commence_time': commence,
            'league': sport_key,
            'over25_odds': over15_odd,
            'under25_odds': under15_odd or 2.5,
        }
    except Exception:
        return None


def build_daily_slip(fixtures, predictor, stats_calculator, max_matches=4, max_odds=2.10):
    """
    Build the best slip from today's fixtures:
    - Predict all 14 markets for each match
    - Pick matches with highest ft_over_15 probability
    - Combine 1-4 matches with total odds <= 2.10
    """
    predictions = []

    for fix in fixtures:
        home = fix['home_team']
        away = fix['away_team']

        # Build features from historical stats
        features = stats_calculator.build_match_features(
            home, away,
            over15_odds=fix['over25_odds'],
            under15_odds=fix['under25_odds'],
        )

        # Run AI prediction
        ai_pred = predictor.predict_match(features)

        ft_over15_prob = float(ai_pred.get('ft_over_15', 0.5))

        predictions.append({
            'home_team': home,
            'away_team': away,
            'commence_time': fix['commence_time'],
            'league': fix['league'],
            'over25_odds': fix['over25_odds'],
            'ft_over15_prob': ft_over15_prob,
            'all_predictions': {
                k: round(float(v), 3) for k, v in ai_pred.items()
            },
            'confidence': (
                'HIGH' if ft_over15_prob >= 0.75
                else 'MEDIUM' if ft_over15_prob >= 0.65
                else 'LOW'
            ),
        })

    # Sort by probability descending
    predictions.sort(key=lambda x: x['ft_over15_prob'], reverse=True)

    # Build best slip: greedily add high-confidence matches staying under max_odds
    slip_matches = []
    combined_odds = 1.0

    for pred in predictions:
        if pred['confidence'] == 'LOW':
            continue
        if len(slip_matches) >= max_matches:
            break

        new_odds = combined_odds * pred['over25_odds']
        if new_odds <= max_odds:
            slip_matches.append(pred)
            combined_odds = new_odds

    # If we got no MEDIUM+ picks, take the top 1-2 regardless
    if not slip_matches and predictions:
        for pred in predictions[:2]:
            new_odds = combined_odds * pred['over25_odds']
            if new_odds <= max_odds:
                slip_matches.append(pred)
                combined_odds = new_odds

    return {
        'date': datetime.utcnow().strftime('%Y-%m-%d'),
        'total_fixtures_analyzed': len(predictions),
        'slip': {
            'matches': _format_slip_matches(slip_matches),
            'match_count': len(slip_matches),
            'combined_odds': round(combined_odds, 2),
            'slip_confidence': _slip_confidence(slip_matches),
        },
        'all_predictions': _format_all_predictions(predictions),
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
            'market': 'Over 2.5 Goals',
            'odds': m['over25_odds'],
            'ai_probability': round(m['ft_over15_prob'] * 100, 1),
            'confidence': m['confidence'],
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
    for p in predictions[:20]:  # Limit to top 20
        result.append({
            'home_team': p['home_team'],
            'away_team': p['away_team'],
            'match': f"{p['home_team']} vs {p['away_team']}",
            'league': _league_name(p['league']),
            'kickoff': p['commence_time'],
            'odds': p['over25_odds'],
            'ai_probability': round(p['ft_over15_prob'] * 100, 1),
            'confidence': p['confidence'],
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

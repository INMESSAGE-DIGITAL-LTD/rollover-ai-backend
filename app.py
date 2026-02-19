"""
Flask API for AI Football Predictions — Hybrid Architecture
SportMonks data → XGBoost AI → Statistical Qualification → Risk Governor
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from models.multi_market_predictor import MultiMarketPredictor
from utils.team_stats import TeamStatsCalculator
from utils.sportmonks_stats import fetch_team_stats, fetch_h2h, clear_cache
from utils.fixture_fetcher import fetch_todays_fixtures, fetch_fixtures_by_date, build_daily_slip, build_parlay_slip
from utils.sportmonks_proxy import SportMonksProxy
from history import register_history_routes, init_history_db, save_daily_picks
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for Flutter app

# Initialize SportMonks proxy with caching + background polling
sm_proxy = SportMonksProxy()

# Initialize pick history database
init_history_db()
register_history_routes(app)

# Load trained models
print("🔄 Loading trained models...")
predictor = MultiMarketPredictor()
predictor.load_models('models/trained')
print("✅ Models loaded!")

# Load team stats from historical data (CSV fallback)
print("🔄 Loading team statistics (CSV fallback)...")
stats_calculator = TeamStatsCalculator('data/raw/all_matches.csv')
print("✅ Team stats ready!")

# SportMonks live stats module (imported as functions, no init needed)
class _SmStatsProxy:
    """Thin wrapper so we can pass sm_stats as an object."""
    def fetch_team_stats(self, team_id):
        return fetch_team_stats(team_id)
    def fetch_h2h(self, team1_id, team2_id):
        return fetch_h2h(team1_id, team2_id)

sm_stats = _SmStatsProxy()
print("✅ SportMonks live stats module ready!")

@app.route('/')
def home():
    return jsonify({
        "service": "Rollover AI Prediction API",
        "version": "2.2.0",
        "status": "running",
        "models_loaded": len(predictor.models),
        "engine": "hybrid (SportMonks + XGBoost + Statistical Qualification)",
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "models": len(predictor.models)})

@app.route('/api/predict', methods=['POST'])
def predict():
    """
    Predict all 14 markets for a single match
    
    POST /api/predict
    Body: {
        "home_team": "Man City",
        "away_team": "Arsenal",
        "home_goals_per_game": 2.1,
        "away_goals_per_game": 1.8,
        ... (all features)
    }
    """
    try:
        data = request.json
        
        # Prepare features
        features = {
            'home_goals_per_game': data.get('home_goals_per_game', 1.5),
            'home_goals_conceded_per_game': data.get('home_goals_conceded_per_game', 1.0),
            'home_over15_rate': data.get('home_over15_rate', 0.6),
            'home_over05_rate': data.get('home_over05_rate', 0.8),
            'home_first_half_goals': data.get('home_first_half_goals', 0.7),
            'away_goals_per_game': data.get('away_goals_per_game', 1.2),
            'away_goals_conceded_per_game': data.get('away_goals_conceded_per_game', 1.3),
            'away_over15_rate': data.get('away_over15_rate', 0.5),
            'away_over05_rate': data.get('away_over05_rate', 0.7),
            'away_first_half_goals': data.get('away_first_half_goals', 0.5),
            'home_home_goals': data.get('home_home_goals', 1.8),
            'home_home_conceded': data.get('home_home_conceded', 0.8),
            'away_away_goals': data.get('away_away_goals', 1.0),
            'away_away_conceded': data.get('away_away_conceded', 1.5),
            'total_expected_goals': data.get('total_expected_goals', 2.8),
            'defensive_strength': data.get('defensive_strength', 2.3),
            'over15_odds': data.get('over15_odds', 1.5),
            'under15_odds': data.get('under15_odds', 2.5),
        }
        
        # Predict
        predictions = predictor.predict_match(features)
        
        # Build response
        result = {
            "match": {
                "home_team": data.get('home_team', ''),
                "away_team": data.get('away_team', '')
            },
            "predictions": {}
        }
        
        for market, prob in predictions.items():
            prob_val = float(prob)  # Convert numpy float32 to Python float
            result["predictions"][market] = {
                "probability": round(prob_val * 100, 1),
                "confidence": "HIGH" if prob_val >= 0.75 else "MEDIUM" if prob_val >= 0.65 else "LOW",
                "pick": "YES" if prob_val >= 0.65 else "NO"
            }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/predictions/test', methods=['GET'])
def test_prediction():
    """
    Test endpoint with sample match
    """
    # Sample features (strong attacking teams)
    features = {
        'home_goals_per_game': 2.1,
        'home_goals_conceded_per_game': 1.0,
        'home_over15_rate': 0.7,
        'home_over05_rate': 0.85,
        'home_first_half_goals': 0.9,
        'away_goals_per_game': 1.8,
        'away_goals_conceded_per_game': 1.1,
        'away_over15_rate': 0.65,
        'away_over05_rate': 0.8,
        'away_first_half_goals': 0.7,
        'home_home_goals': 2.3,
        'home_home_conceded': 0.8,
        'away_away_goals': 1.5,
        'away_away_conceded': 1.3,
        'total_expected_goals': 3.8,
        'defensive_strength': 2.1,
        'over15_odds': 1.4,
        'under15_odds': 2.8,
    }
    
    predictions = predictor.predict_match(features)
    
    result = {
        "match": {
            "home_team": "Man City (sample)",
            "away_team": "Liverpool (sample)"
        },
        "predictions": {}
    }
    
    # Sort by probability descending
    sorted_markets = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
    
    for market, prob in sorted_markets:
        prob_val = float(prob)  # Convert numpy float32 to Python float
        result["predictions"][market] = {
            "probability": round(prob_val * 100, 1),
            "confidence": "HIGH" if prob_val >= 0.75 else "MEDIUM" if prob_val >= 0.65 else "LOW",
            "pick": "YES" if prob_val >= 0.65 else "NO"
        }
    
    return jsonify(result)

@app.route('/api/today', methods=['GET'])
def today_predictions():
    """
    Fetch today's real fixtures, run AI predictions, and return a smart slip.
    Results are cached for 5 minutes to avoid re-running AI for every request.
    """
    import time as _time
    try:
        max_matches = int(request.args.get('max_matches', 4))
        max_odds = float(request.args.get('max_odds', 2.60))
        
        max_matches = min(max(max_matches, 1), 4)
        max_odds = min(max(max_odds, 1.5), 3.0)

        # Check cache (keyed by params)
        cache_key = f"today_{max_matches}_{max_odds}"
        cached = sm_proxy.get_cache(cache_key, ttl=300)  # 5 min
        if cached is not None:
            print(f"⚡ Serving cached /api/today ({cache_key})")
            return jsonify(cached)
        
        print(f"🔄 Fetching today's fixtures...")
        fixtures = fetch_todays_fixtures()
        
        if not fixtures:
            return jsonify({
                'date': __import__('datetime').datetime.utcnow().strftime('%Y-%m-%d'),
                'total_fixtures_analyzed': 0,
                'slip': {
                    'matches': [],
                    'match_count': 0,
                    'combined_odds': 0,
                    'slip_confidence': 'NONE',
                },
                'all_predictions': [],
                'message': 'No fixtures available right now. Try again later.',
            })
        
        print(f"🧠 Running hybrid predictions on {len(fixtures)} fixtures...")
        clear_cache()
        result = build_daily_slip(
            fixtures, predictor, stats_calculator,
            max_matches=max_matches,
            max_odds=max_odds,
            sm_stats=sm_stats,
        )
        
        result['ai_model'] = {
            'version': '2.1.0',
            'engine': 'hybrid',
            'markets_analyzed': len(predictor.models),
            'features': len(predictor.feature_names),
            'teams_in_database': len(stats_calculator.get_all_teams()),
        }
        
        print(f"✅ Slip ready: {result['slip']['match_count']} matches, "
              f"odds {result['slip']['combined_odds']}")
        
        # Auto-save slip to history for cloud sync
        slip_matches = result.get('slip', {}).get('matches', [])
        if slip_matches:
            try:
                date_str = result.get('date', __import__('datetime').datetime.utcnow().strftime('%Y-%m-%d'))
                picks_for_history = [
                    {
                        "home_team": m.get("home_team", ""),
                        "away_team": m.get("away_team", ""),
                        "market": m.get("market", ""),
                        "odds": m.get("odds", 0),
                        "confidence": m.get("ai_probability", 0),
                        "result": "pending",
                        "league": m.get("league", ""),
                        "home_logo": m.get("home_logo"),
                        "away_logo": m.get("away_logo"),
                        "league_logo": m.get("league_logo"),
                        "home_short_code": m.get("home_short_code"),
                        "away_short_code": m.get("away_short_code"),
                        "kickoff": m.get("kickoff"),
                    }
                    for m in slip_matches
                ]
                save_daily_picks(date_str, picks_for_history)
                print(f"💾 Saved {len(picks_for_history)} picks to history for {date_str}")
            except Exception as he:
                print(f"⚠️ History save failed (non-fatal): {he}")
        
        # Cache the result
        sm_proxy.set_cache(cache_key, result)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error in /api/today: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/picks/<date_str>', methods=['GET'])
def picks_by_date(date_str):
    """
    Generate AI picks for any date (today or past).
    Uses cached results for 1 hour to avoid re-running AI.
    Past dates use fixture data from SportMonks.
    """
    from datetime import datetime as dt
    try:
        dt.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    try:
        max_matches = int(request.args.get('max_matches', 4))
        max_odds = float(request.args.get('max_odds', 2.60))
        max_matches = min(max(max_matches, 1), 4)
        max_odds = min(max(max_odds, 1.5), 3.0)

        cache_key = f"picks_{date_str}_{max_matches}_{max_odds}"
        cached = sm_proxy.get_cache(cache_key, ttl=3600)  # 1 hour
        if cached is not None:
            print(f"⚡ Serving cached /api/picks/{date_str}")
            return jsonify(cached)

        today = __import__('datetime').datetime.utcnow().strftime('%Y-%m-%d')
        if date_str == today:
            # Redirect to today logic
            fixtures = fetch_todays_fixtures()
        else:
            fixtures = fetch_fixtures_by_date(date_str)

        if not fixtures:
            return jsonify({
                'date': date_str,
                'total_fixtures_analyzed': 0,
                'slip': {
                    'matches': [],
                    'match_count': 0,
                    'combined_odds': 0,
                    'slip_confidence': 'NONE',
                },
            })

        print(f"🧠 Running predictions for {date_str} on {len(fixtures)} fixtures...")
        clear_cache()
        result = build_daily_slip(
            fixtures, predictor, stats_calculator,
            max_matches=max_matches,
            max_odds=max_odds,
            sm_stats=sm_stats,
        )
        result['date'] = date_str

        # Save to history
        slip_matches = result.get('slip', {}).get('matches', [])
        if slip_matches:
            try:
                picks_for_history = [
                    {
                        "home_team": m.get("home_team", ""),
                        "away_team": m.get("away_team", ""),
                        "market": m.get("market", ""),
                        "odds": m.get("odds", 0),
                        "confidence": m.get("ai_probability", 0),
                        "result": "pending",
                        "league": m.get("league", ""),
                        "home_logo": m.get("home_logo"),
                        "away_logo": m.get("away_logo"),
                        "league_logo": m.get("league_logo"),
                        "home_short_code": m.get("home_short_code"),
                        "away_short_code": m.get("away_short_code"),
                        "kickoff": m.get("kickoff"),
                    }
                    for m in slip_matches
                ]
                save_daily_picks(date_str, picks_for_history)
            except Exception as he:
                print(f"⚠️ History save failed: {he}")

        sm_proxy.set_cache(cache_key, result)
        return jsonify(result)

    except Exception as e:
        print(f"❌ Error in /api/picks/{date_str}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/free-picks/<date_str>', methods=['GET'])
def free_picks_by_date(date_str):
    """
    Free picks endpoint — higher odds, more matches (4-10).
    Uses the same AI engine as /api/picks but with riskier parameters
    to create a teaser for premium subscribers.

    GET /api/free-picks/2026-02-19?max_matches=8&max_odds=4.0
    """
    from datetime import datetime as dt
    try:
        dt.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    try:
        max_matches = int(request.args.get('max_matches', 8))
        max_odds = float(request.args.get('max_odds', 4.0))
        max_matches = min(max(max_matches, 4), 10)
        max_odds = min(max(max_odds, 2.0), 10.0)

        cache_key = f"free_picks_{date_str}_{max_matches}_{max_odds}"
        cached = sm_proxy.get_cache(cache_key, ttl=3600)  # 1 hour
        if cached is not None:
            print(f"⚡ Serving cached /api/free-picks/{date_str}")
            return jsonify(cached)

        today = __import__('datetime').datetime.utcnow().strftime('%Y-%m-%d')
        if date_str == today:
            fixtures = fetch_todays_fixtures()
        else:
            fixtures = fetch_fixtures_by_date(date_str)

        if not fixtures:
            return jsonify({
                'date': date_str,
                'total_fixtures_analyzed': 0,
                'slip': {
                    'matches': [],
                    'match_count': 0,
                    'combined_odds': 0,
                    'slip_confidence': 'NONE',
                },
            })

        print(f"🎯 Free picks for {date_str}: {len(fixtures)} fixtures, "
              f"max_matches={max_matches}, max_odds={max_odds}")
        clear_cache()
        result = build_daily_slip(
            fixtures, predictor, stats_calculator,
            max_matches=max_matches,
            max_odds=max_odds,
            sm_stats=sm_stats,
        )
        result['date'] = date_str

        sm_proxy.set_cache(cache_key, result)
        return jsonify(result)

    except Exception as e:
        print(f"❌ Error in /api/free-picks/{date_str}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/parlay', methods=['GET'])
def parlay_predictions():
    """
    AI Parlay - generate higher-odds multi-match slips.
    
    GET /api/parlay
    Query params:
        num_matches: int (2-20, default 5)
        min_odds: float (default 1.30)
        max_odds: float (default 3.00)
    """
    try:
        num_matches = int(request.args.get('num_matches', 5))
        min_odds = float(request.args.get('min_odds', 1.30))
        max_odds = float(request.args.get('max_odds', 3.00))

        num_matches = min(max(num_matches, 2), 20)
        min_odds = min(max(min_odds, 1.10), 5.0)
        max_odds = min(max(max_odds, min_odds + 0.1), 10.0)

        print(f"🎰 Parlay: {num_matches} matches, odds {min_odds}-{max_odds}")
        fixtures = fetch_todays_fixtures()

        if not fixtures:
            return jsonify({
                'date': __import__('datetime').datetime.utcnow().strftime('%Y-%m-%d'),
                'total_fixtures_analyzed': 0,
                'slip': {
                    'matches': [],
                    'match_count': 0,
                    'combined_odds': 0,
                    'slip_confidence': 'NONE',
                },
                'all_predictions': [],
                'message': 'No fixtures available right now.',
            })

        result = build_parlay_slip(
            fixtures, predictor, stats_calculator,
            num_matches=num_matches,
            min_odds=min_odds,
            max_odds=max_odds,
            sm_stats=sm_stats,
        )

        print(f"✅ Parlay: {result['slip']['match_count']} matches, "
              f"odds {result['slip']['combined_odds']}")

        return jsonify(result)

    except Exception as e:
        print(f"❌ Error in /api/parlay: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/teams', methods=['GET'])
def list_teams():
    """List all teams in the database"""
    teams = stats_calculator.get_all_teams()
    return jsonify({'teams': teams, 'count': len(teams)})

# ── SportMonks Proxy Endpoints (cached, token stays server-side) ──

@app.route('/api/livescores', methods=['GET'])
def livescores():
    """
    Return cached live scores. Backend polls SportMonks every 2 min.
    Clients call this instead of SportMonks directly.
    """
    try:
        data = sm_proxy.get_livescores()
        return jsonify(data)
    except Exception as e:
        print(f"❌ Error in /api/livescores: {e}")
        return jsonify({'error': str(e), 'fixtures': []}), 500

@app.route('/api/fixtures/<date_str>', methods=['GET'])
def fixtures_by_date(date_str):
    """
    Return cached fixtures for a date. 10-min cache TTL.
    Clients call this instead of SportMonks directly.
    """
    try:
        data = sm_proxy.get_fixtures(date_str)
        return jsonify(data)
    except Exception as e:
        print(f"❌ Error in /api/fixtures/{date_str}: {e}")
        return jsonify({'error': str(e), 'fixtures': []}), 500

@app.route('/api/leagues', methods=['GET'])
def leagues():
    """
    Return cached leagues from SportMonks. 24-hour cache TTL.
    """
    try:
        data = sm_proxy.get_leagues()
        return jsonify(data)
    except Exception as e:
        print(f"❌ Error in /api/leagues: {e}")
        return jsonify({'error': str(e), 'leagues': []}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)

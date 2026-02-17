"""
Flask API for AI Football Predictions
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from models.multi_market_predictor import MultiMarketPredictor
from utils.team_stats import TeamStatsCalculator
from utils.fixture_fetcher import fetch_todays_fixtures, build_daily_slip, build_parlay_slip
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for Flutter app

# Load trained models
print("🔄 Loading trained models...")
predictor = MultiMarketPredictor()
predictor.load_models('models/trained')
print("✅ Models loaded!")

# Load team stats from historical data
print("🔄 Loading team statistics...")
stats_calculator = TeamStatsCalculator('data/raw/all_matches.csv')
print("✅ Team stats ready!")

@app.route('/')
def home():
    return jsonify({
        "service": "Rollover AI Prediction API",
        "version": "1.0.0",
        "status": "running",
        "models_loaded": 14
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "models": 14})

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
    
    GET /api/today
    Optional query params:
        max_matches: int (1-4, default 4)
        max_odds: float (default 2.10)
    
    Returns:
        - Daily slip (1-4 best matches, combined odds <= 2.10)
        - All analyzed fixtures with AI probabilities
    """
    try:
        max_matches = int(request.args.get('max_matches', 4))
        max_odds = float(request.args.get('max_odds', 2.10))
        
        max_matches = min(max(max_matches, 1), 4)
        max_odds = min(max(max_odds, 1.5), 3.0)
        
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
        
        print(f"🧠 Running AI predictions on {len(fixtures)} fixtures...")
        result = build_daily_slip(
            fixtures, predictor, stats_calculator,
            max_matches=max_matches,
            max_odds=max_odds,
        )
        
        result['ai_model'] = {
            'version': '1.0.0',
            'markets_analyzed': 14,
            'teams_in_database': len(stats_calculator.get_all_teams()),
        }
        
        print(f"✅ Slip ready: {result['slip']['match_count']} matches, "
              f"odds {result['slip']['combined_odds']}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error in /api/today: {e}")
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)

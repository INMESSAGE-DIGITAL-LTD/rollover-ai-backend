"""
Flask API for AI Football Predictions
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from models.multi_market_predictor import MultiMarketPredictor
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for Flutter app

# Load trained models
print("🔄 Loading trained models...")
predictor = MultiMarketPredictor()
predictor.load_models('models/trained')
print("✅ Models loaded!")

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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)

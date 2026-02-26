"""
Flask API for AI Football Predictions — Hybrid Architecture
SportMonks data → XGBoost AI → Statistical Qualification → Risk Governor
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from models.multi_market_predictor import MultiMarketPredictor
from utils.team_stats import TeamStatsCalculator
from utils.sportmonks_stats import fetch_team_stats, fetch_h2h, clear_cache
from utils.fixture_fetcher import fetch_todays_fixtures, fetch_fixtures_by_date, build_parlay_slip
from utils.sportmonks_proxy import SportMonksProxy
from history import register_history_routes, init_history_db, save_daily_picks
from firebase_config import get_firestore_client
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for Flutter app

# Initialize SportMonks proxy with caching + background polling
sm_proxy = SportMonksProxy()

# Initialize pick history database (Firestore)
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
    Fetch today's predictions.
    1. READ from Firestore first (FAST).
    2. If missing, GENERATE via AI (SLOW) and save.
    """
    import datetime
    today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    return picks_by_date(today)


@app.route('/api/picks/<date_str>', methods=['GET'])
def picks_by_date(date_str):
    """
    Get picks for a specific date.
    Checks Firestore first. If missing, generates on-demand.
    """
    from datetime import datetime as dt
    try:
        dt.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    max_matches = request.args.get('max_matches', 10, type=int)
    max_matches = max(4, min(20, max_matches))

    try:
        # ─── 1. FAST PATH: Check Firestore ───
        db = get_firestore_client()
        doc = db.collection('daily_predictions').document(date_str).get()
        
        if doc.exists:
            data = doc.to_dict()
            matches = data.get('matches', [])
            
            if matches:
                # Slice to requested count
                matches = matches[:max_matches]
                
                # Calculate combined odds for the slice
                combined = 1.0
                for m in matches:
                    combined *= float(m.get('odds', 1.0))
                
                print(f"⚡ Serving Firestore picks for {date_str} ({len(matches)} matches)")
                return jsonify({
                    'date': date_str,
                    'slip': {
                        'matches': matches,
                        'match_count': len(matches),
                        'combined_odds': round(combined, 2),
                        'slip_confidence': data.get('slip_confidence', 'HIGH'),
                    },
                    'source': 'firestore'
                })

        # ─── 2. SLOW PATH: Generate On-Demand (Fallback) ───
        print(f"⚠️ No Firestore doc for {date_str}, generating on-demand...")
        
        today = __import__('datetime').datetime.utcnow().strftime('%Y-%m-%d')
        if date_str == today:
            fixtures = fetch_todays_fixtures()
        else:
            fixtures = fetch_fixtures_by_date(date_str)

        if not fixtures:
            return jsonify({
                'date': date_str,
                'slip': {'matches': [], 'match_count': 0},
                'message': 'No fixtures available.'
            })

        print(f"🧠 AI generating for {date_str} ({len(fixtures)} fixtures)...")
        clear_cache()

        # Apply market performance penalties for smarter on-demand generation
        from utils.market_tracker import get_market_penalties
        _mp = {}
        try:
            _mp = get_market_penalties(sm_proxy, lookback_days=7, min_picks=3)
        except Exception:
            pass

        # Generate full 10 matches standard
        result = build_parlay_slip(
            fixtures, predictor, stats_calculator,
            num_matches=10,  # Always generate 10 for storage
            min_odds=1.10,
            max_odds=1.60,
            sm_stats=sm_stats,
            free_mode=False,
            market_penalties=_mp,
        )
        
        # Save to Firestore for next time
        slip_matches = result.get('slip', {}).get('matches', [])
        if slip_matches:
            save_daily_picks(date_str, slip_matches)
            print(f"💾 Saved generated picks to Firestore")

        # Slice for response
        if len(slip_matches) > max_matches:
             result['slip']['matches'] = slip_matches[:max_matches]
             result['slip']['match_count'] = max_matches
             # Recalculate odds
             combined = 1.0
             for m in result['slip']['matches']:
                 combined *= float(m.get('odds', 1.0))
             result['slip']['combined_odds'] = round(combined, 2)

        return jsonify(result)

    except Exception as e:
        print(f"❌ Error in picks_by_date: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/free-picks/<date_str>', methods=['GET'])
def free_picks_by_date(date_str):
    """
    Free picks endpoint.
    AI Pro is SAFER than free. Free picks are riskier teasers.

    Rules:
      - 6 matches per day
      - Individual odds: 1.10 - 1.57
      - Combined odds: 1.99 - 4.50
      - Must NOT use same game as AI Pro (if same game, different market)
      - Top 2 safest picks LOCKED (is_free=false, blurred), rest unlocked (is_free=true)

    GET /api/free-picks/2026-02-19
    """
    from datetime import datetime as dt
    try:
        dt.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    try:
        cache_key = f"free_picks_v5_{date_str}"
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

        # ── Step 1: Get AI Pro picks — exclude same game (allow same match if different market) ──
        pro_cache_key = f"picks_pro_{date_str}"
        pro_cached = sm_proxy.get_cache(pro_cache_key, ttl=3600)
        exclude_match_markets = set()

        if pro_cached:
            pro_matches = pro_cached.get('slip', {}).get('matches', [])
            for pm in pro_matches:
                key = f"{pm.get('home_team', '')}_{pm.get('away_team', '')}_{pm.get('market', '')}"
                exclude_match_markets.add(key)
            print(f"🚫 Excluding {len(exclude_match_markets)} AI Pro match+market combos")
        else:
            print("⚠️ AI Pro picks not cached yet — free picks may overlap (will fix on next call)")

        # ── Step 2: Build free slip — odds 1.10-1.57, combined 1.99-4.50 ──
        print(f"🎯 Free picks for {date_str}: {len(fixtures)} fixtures, "
              f"odds 1.10-1.57, max 6 matches, combined 1.99-4.50")
        clear_cache()

        # Apply market performance penalties
        from utils.market_tracker import get_market_penalties
        _free_mp = {}
        try:
            _free_mp = get_market_penalties(sm_proxy, lookback_days=7, min_picks=3)
        except Exception:
            pass

        result = build_parlay_slip(
            fixtures, predictor, stats_calculator,
            num_matches=6,
            min_odds=1.10,
            max_odds=1.57,
            sm_stats=sm_stats,
            free_mode=False,  # Use strict safety rules
            exclude_match_markets=exclude_match_markets,
            market_penalties=_free_mp,
        )
        result['date'] = date_str

        # ── Step 3: Enforce combined odds 1.99-4.50 ──
        matches = result.get('slip', {}).get('matches', [])
        combined = result.get('slip', {}).get('combined_odds', 0)

        # If combined > 4.50, drop highest-odds picks until within range
        if combined > 4.50 and len(matches) > 4:
            indexed = sorted(enumerate(matches), key=lambda x: x[1].get('odds', 0), reverse=True)
            while combined > 4.50 and len(indexed) > 4:
                _, drop_match = indexed.pop(0)
                combined /= drop_match.get('odds', 1)
            keep_indices = {x[0] for x in indexed}
            matches = [m for i, m in enumerate(matches) if i in keep_indices]
            result['slip']['matches'] = matches
            result['slip']['match_count'] = len(matches)
            result['slip']['combined_odds'] = round(combined, 2)

        # ── Step 4: Lock top 2 safest, unlock the rest ──
        # Top 2 safest = LOCKED (blurred, need subscription)
        # Rest = unlocked (is_free=true, shown freely)
        sorted_by_safety = sorted(
            enumerate(matches),
            key=lambda x: x[1].get('ai_probability', 0),
            reverse=True,
        )

        for rank, (idx, _) in enumerate(sorted_by_safety):
            matches[idx]['is_free'] = rank >= 2  # Top 2 safest = LOCKED (is_free=false)

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

@app.route('/api/register-token', methods=['POST'])
def register_token():
    """
    Register a device FCM token for push notifications.
    Called by the Flutter app on startup after requesting notification permission.

    POST /api/register-token
    Body: {"token": "<fcm_token>", "platform": "android"|"ios"}
    """
    try:
        data = request.json or {}
        token = (data.get('token') or '').strip()
        platform = data.get('platform', 'unknown')

        if not token:
            return jsonify({'error': 'token is required'}), 400

        from utils.push_notifier import register_token as _reg
        success = _reg(token, platform)
        if success:
            return jsonify({'status': 'registered'})
        return jsonify({'error': 'failed to register token'}), 500
    except Exception as e:
        print(f"❌ register-token error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/update-results', methods=['POST'])
def update_results():
    """
    Manually trigger result resolution for recent picks.
    Protected by CRON_SECRET Bearer token.

    POST /api/update-results
    Header: Authorization: Bearer <CRON_SECRET>
    Body (optional): {"days_back": 3}
    """
    cron_secret = os.environ.get('CRON_SECRET', '').strip()
    auth_header = request.headers.get('Authorization', '')
    if not cron_secret or auth_header != f'Bearer {cron_secret}':
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        from utils.result_updater import update_past_results
        days_back = (request.json or {}).get('days_back', 3)
        summary = update_past_results(sm_proxy, days_back=days_back)
        return jsonify({'status': 'success', **summary})
    except Exception as e:
        print(f"❌ update-results error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-daily', methods=['POST'])
def generate_daily():
    """
    Manual trigger: Generate today's predictions and write to Firestore.
    Protected by CRON_SECRET Bearer token.
    The cron job uses cron_generate.py directly (no HTTP).
    This endpoint exists for manual/emergency triggers only.

    POST /api/generate-daily
    Header: Authorization: Bearer <CRON_SECRET>
    """
    # ── Auth check ──
    cron_secret = os.environ.get('CRON_SECRET', '').strip()
    auth_header = request.headers.get('Authorization', '')
    if not cron_secret or auth_header != f'Bearer {cron_secret}':
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        from services.generator import generate_and_store

        fixtures = fetch_todays_fixtures()
        result = generate_and_store(
            fixtures, predictor, stats_calculator, sm_stats,
            sm_proxy=sm_proxy,
        )
        status_code = 200 if result['status'] == 'success' else 200
        return jsonify(result), status_code

    except Exception as e:
        print(f"❌ Generate error: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)

"""
Flask API for AI Football Predictions — Hybrid Architecture
API-Football data → XGBoost AI → Statistical Qualification → Risk Governor
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from models.multi_market_predictor import MultiMarketPredictor
from utils.team_stats import TeamStatsCalculator
from utils.apifootball_stats import ApiFootballStats, clear_cache
from utils.fixture_fetcher import fetch_todays_fixtures, fetch_fixtures_by_date, build_parlay_slip
from utils.apifootball_proxy import ApiFootballProxy
from history import register_history_routes, init_history_db, save_daily_picks
from firebase_config import get_firestore_client
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for Flutter app

# Initialize API-Football proxy with caching + background polling
af_proxy = ApiFootballProxy()

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

# API-Football live stats module
af_stats = ApiFootballStats()
print("✅ API-Football live stats module ready!")

@app.route('/')
def home():
    return jsonify({
        "service": "Rollover AI Prediction API",
        "version": "2.4.0",
        "status": "running",
        "models_loaded": len(predictor.models),
        "engine": "hybrid (API-Football + XGBoost + Statistical Qualification)",
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
            'away_goals_per_game': data.get('away_goals_per_game', 1.2),
            'home_conceded_per_game': data.get('home_conceded_per_game', 1.0),
            'away_conceded_per_game': data.get('away_conceded_per_game', 1.3),
            'home_xg': data.get('home_xg', 1.4),
            'away_xg': data.get('away_xg', 1.1),
            'home_xga': data.get('home_xga', 1.1),
            'away_xga': data.get('away_xga', 1.4),
            'home_form': data.get('home_form', 0.5),
            'away_form': data.get('away_form', 0.5),
            'h2h_home_wins': data.get('h2h_home_wins', 2),
            'h2h_away_wins': data.get('h2h_away_wins', 2),
            'h2h_draws': data.get('h2h_draws', 1),
            'h2h_avg_goals': data.get('h2h_avg_goals', 2.5),
        }
        
        predictions = predictor.predict_all_markets(features)
        
        return jsonify({
            'home_team': data.get('home_team', 'Home'),
            'away_team': data.get('away_team', 'Away'),
            'predictions': predictions
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fixtures')
def get_fixtures():
    """Get today's fixtures with live scores from SportMonks proxy."""
    from datetime import datetime as dt
    try:
        today = dt.utcnow().strftime('%Y-%m-%d')
        result = af_proxy.get_fixtures(today)
        return jsonify({
            'date': today,
            'fixtures': result.get('fixtures', []),
            'count': result.get('count', 0),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/livescores')
def get_livescores():
    """Get currently in-play fixtures with live scores (polled every 2 min)."""
    try:
        result = af_proxy.get_livescores()
        return jsonify({
            'fixtures': result.get('fixtures', []),
            'count': result.get('count', 0),
        })
    except Exception as e:
        return jsonify({'error': str(e), 'fixtures': [], 'count': 0}), 500


@app.route('/api/fixtures/<date_str>')
def get_fixtures_by_date(date_str):
    """
    Get fixtures for a specific date WITH scores and match status.

    GET /api/fixtures/2026-02-15
    """
    from datetime import datetime as dt
    try:
        dt.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    try:
        # Use proxy which includes scores, match_status, ht scores
        result = af_proxy.get_fixtures(date_str)
        return jsonify({
            'date': date_str,
            'fixtures': result.get('fixtures', []),
            'count': result.get('count', 0),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/parlay')
def get_parlay():
    """
    Build optimal multi-match parlay from today's fixtures.
    
    Optional query params:
    - num_matches: Max matches (default 5)
    - min_odds: Minimum odds filter (default 1.10)
    - max_odds: Maximum odds filter (default 1.60)
    """
    try:
        # Get cached fixtures from proxy (fast)
        fixtures = af_proxy.get_fixtures(__import__("datetime").datetime.utcnow().strftime("%Y-%m-%d")).get('fixtures', [])
        
        # Default to 5 matches
        num_matches = int(request.args.get('num_matches', 5))
        min_odds = float(request.args.get('min_odds', 1.10))
        max_odds = float(request.args.get('max_odds', 1.57))
        
        result = build_parlay_slip(
            fixtures, predictor, stats_calculator,
            num_matches=num_matches,
            min_odds=min_odds,
            max_odds=max_odds,
            af_stats=None,  # disabled: saves ~1000 API calls/run
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/picks/<date_str>')
def get_daily_picks(date_str):
    """
    Get daily AI picks for a date (format: YYYY-MM-DD).
    
    Checks Firestore first. If missing, generates on-demand.
    
    GET /api/picks/2026-03-01
    """
    from datetime import datetime as dt
    try:
        dt.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    try:
        # ─── 1. Fast path: check Firestore for cached picks ───
        db = get_firestore_client()
        doc = db.collection('daily_predictions').document(date_str).get()

        if doc.exists:
            data = doc.to_dict()
            matches = data.get('matches', [])
            if len(matches) >= 4:
                combined_odds = 1.0
                for m in matches:
                    combined_odds *= float(m.get('odds', 1.0))

                print(f"⚡ Serving Firestore picks for {date_str} ({len(matches)} matches)")
                return jsonify({
                    'date': date_str,
                    'matches': matches,
                    'match_count': len(matches),
                    'combined_odds': round(combined_odds, 2),
                    'slip_confidence': data.get('slip_confidence', 'HIGH'),
                    'source': 'firestore',
                })

            # Doc exists but empty — throttle retries to once per 2 hours.
            # Prevents hammering the API when quota is exhausted or fixtures unavailable.
            from datetime import datetime as dt, timezone
            last_attempt = data.get('generated_at') or data.get('saved_at')
            if last_attempt:
                try:
                    if hasattr(last_attempt, 'timestamp'):
                        age_seconds = (dt.now(timezone.utc) - last_attempt).total_seconds()
                    else:
                        age_seconds = 0
                    if age_seconds < 7200:  # 2 hours
                        print(f"⏳ Empty doc for {date_str} tried {int(age_seconds/60)}m ago — skipping retry")
                        return jsonify({
                            'date': date_str,
                            'matches': [],
                            'match_count': 0,
                            'message': 'Predictions not yet available. Please check back later.',
                        })
                except Exception:
                    pass

        # ─── 2. Slow path: generate and store ───
        print(f"⚠️ No Firestore doc for {date_str}, generating on-demand...")
        
        # Fetch fixtures for requested date (uses a separate call — date-aware)
        fixtures = fetch_fixtures_by_date(date_str, no_league_filter=True) if date_str else fetch_todays_fixtures()

        if not fixtures:
            # Write placeholder so throttle prevents hammering quota on next request
            try:
                from google.cloud.firestore_v1 import SERVER_TIMESTAMP
                db.collection('daily_predictions').document(date_str).set({
                    'date': date_str, 'matches': [], 'match_count': 0,
                    'generated_at': SERVER_TIMESTAMP, 'status': 'no_fixtures',
                })
            except Exception:
                pass
            return jsonify({
                'date': date_str,
                'matches': [],
                'match_count': 0,
                'message': 'No fixtures available for this date.',
            })
        
        # Apply market performance penalties
        from utils.market_tracker import get_market_penalties
        market_penalties = {}
        try:
            _mp = get_market_penalties(af_proxy, lookback_days=7, min_picks=3)
        except Exception:
            pass

        # Generate and write to Firestore
        from services.generator import generate_and_store
        gen_result = generate_and_store(
            fixtures, predictor, stats_calculator, af_stats,
            num_matches=10,
            min_odds=1.10,
            max_odds=1.57,
            sm_proxy=af_proxy,
            date_str=date_str,
        )

        if gen_result.get('status') == 'success':
            doc2 = db.collection('daily_predictions').document(date_str).get()
            if doc2.exists:
                data = doc2.to_dict()
                matches = data.get('matches', [])
                combined_odds = 1.0
                for m in matches:
                    combined_odds *= float(m.get('odds', 1.0))
                return jsonify({
                    'date': date_str,
                    'matches': matches,
                    'match_count': len(matches),
                    'combined_odds': round(combined_odds, 2),
                    'slip_confidence': data.get('slip_confidence', 'HIGH'),
                    'source': 'generated',
                })

        return jsonify({
            'date': date_str,
            'matches': [],
            'match_count': 0,
            'message': gen_result.get('message', 'Could not generate picks.'),
        })
        
    except Exception as e:
        print(f"❌ get_daily_picks error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rollover-picks/<date_str>')
def rollover_picks_by_date(date_str):
    """
    Safety-first Rollover picks — generated INDEPENDENTLY from AI Pro.

    Strict market filter (Over 1.5, Over 2.5, DC only), high probability
    thresholds, dynamic 1-3 picks, combined odds capped at 2.20.

    GET /api/rollover-picks/2026-03-15
    """
    from datetime import datetime as dt
    try:
        dt.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    try:
        # ─── 1. Fast path: check Firestore daily_rollover collection ───
        db = get_firestore_client()
        doc = db.collection('daily_rollover').document(date_str).get()

        if doc.exists:
            data = doc.to_dict()
            matches = data.get('matches', [])
            if matches:
                # Recalculate combined odds from stored matches
                combined = 1.0
                for m in matches:
                    combined *= float(m.get('odds', 1.0))
                print(f"⚡ Serving Firestore rollover picks for {date_str} ({len(matches)} picks)")
                return jsonify({
                    'date': date_str,
                    'matches': matches,
                    'match_count': len(matches),
                    'combined_odds': round(combined, 2),
                    'slip_confidence': data.get('slip_confidence', 'VERY_HIGH'),
                    'source': 'firestore',
                })

        # ─── 2. Slow path: generate on-demand ───
        print(f"⚠️ No rollover doc for {date_str}, generating on-demand...")
        from services.rollover_generator import generate_rollover_picks

        fixtures = fetch_fixtures_by_date(date_str, no_league_filter=True) if date_str else fetch_todays_fixtures()

        if not fixtures:
            return jsonify({
                'date': date_str,
                'matches': [],
                'match_count': 0,
                'message': 'No fixtures available.',
            })

        # Apply market performance penalties
        from utils.market_tracker import get_market_penalties as _get_mp
        _mp = {}
        try:
            _rollover_mp = _get_mp(af_proxy, lookback_days=7, min_picks=3)
        except Exception:
            pass

        result = generate_rollover_picks(
            fixtures, predictor, stats_calculator, af_stats,
            sm_proxy=af_proxy,
            date_str=date_str,
            market_penalties=_mp,
        )

        if result['status'] == 'success':
            # Re-read fresh doc
            doc = db.collection('daily_rollover').document(date_str).get()
            if doc.exists:
                data = doc.to_dict()
                matches = data.get('matches', [])
                combined = 1.0
                for m in matches:
                    combined *= float(m.get('odds', 1.0))
                return jsonify({
                    'date': date_str,
                    'matches': matches,
                    'match_count': len(matches),
                    'combined_odds': round(combined, 2),
                    'slip_confidence': data.get('slip_confidence', 'VERY_HIGH'),
                    'source': 'generated',
                })

        return jsonify({
            'date': date_str,
            'matches': [],
            'match_count': 0,
            'message': result.get('message', 'No rollover picks available.'),
        })

    except Exception as e:
        print(f"❌ rollover_picks_by_date error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai-pro-picks/<date_str>', methods=['GET'])
def ai_pro_picks_by_date(date_str):
    """
    AI Pro Tips — server-side generation using XGBoost pipeline.

    Replaces the old client-side RapidAPI logic with smarter, server-controlled
    predictions. Dynamic 1-4 tips with real odds and strict quality gates.

    GET /api/ai-pro-picks/2026-03-15
    """
    from datetime import datetime as dt
    try:
        dt.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    try:
        # ─── 1. Fast path: check Firestore daily_ai_pro collection ───
        db = get_firestore_client()
        doc = db.collection('daily_ai_pro').document(date_str).get()

        if doc.exists:
            data = doc.to_dict()
            tips = data.get('tips', [])
            if tips:
                # Recalculate combined odds from stored tips
                combined = 1.0
                for t in tips:
                    combined *= float(t.get('odds', 1.0))
                print(f"⚡ Serving Firestore AI Pro tips for {date_str} ({len(tips)} tips)")
                return jsonify({
                    'date': date_str,
                    'tips': tips,
                    'tip_count': len(tips),
                    'combined_odds': round(combined, 2),
                    'confidence': data.get('confidence', 'HIGH'),
                    'source': 'firestore',
                })

        # ─── 2. Slow path: generate on-demand ───
        print(f"⚠️ No AI Pro doc for {date_str}, generating on-demand...")
        from services.ai_pro_generator import generate_ai_pro_picks

        fixtures = fetch_fixtures_by_date(date_str, no_league_filter=True) if date_str else fetch_todays_fixtures()

        if not fixtures:
            return jsonify({
                'date': date_str,
                'tips': [],
                'tip_count': 0,
                'combined_odds': 1.0,
                'message': 'No fixtures available.',
            })

        # Apply market performance penalties
        from utils.market_tracker import get_market_penalties as _get_ai_pro_mp
        _ai_pro_mp = {}
        try:
            _ai_pro_mp = _get_ai_pro_mp(af_proxy, lookback_days=7, min_picks=3)
        except Exception:
            pass

        result = generate_ai_pro_picks(
            fixtures, predictor, stats_calculator, af_stats,
            sm_proxy=af_proxy,
            date_str=date_str,
            market_penalties=_ai_pro_mp,
        )

        if result['status'] == 'success':
            return jsonify({
                'date': result['date'],
                'tips': result['tips'],
                'tip_count': result['tip_count'],
                'combined_odds': result['combined_odds'],
                'confidence': result['confidence'],
                'source': 'generated',
            })

        return jsonify({
            'date': date_str,
            'tips': [],
            'tip_count': 0,
            'combined_odds': 1.0,
            'message': result.get('message', 'No AI Pro tips available.'),
        })

    except Exception as e:
        print(f"❌ ai_pro_picks_by_date error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/free-picks/<date_str>')
def free_picks_by_date(date_str):
    """
    Free Tab picks — curated matches from daily_predictions (matches 5-10).
    Combined odds enforced to 1.60-2.00 range.

    GET /api/free-picks/2026-03-15
    """
    from datetime import datetime as dt
    try:
        dt.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    try:
        cache_key = f"free_picks_v5_{date_str}"
        cached = af_proxy.get_cache(cache_key, ttl=3600)  # 1 hour
        if cached is not None:
            print(f"⚡ Serving cached /api/free-picks/{date_str}")
            return jsonify(cached)

        # Always fetch fixtures — needed for build_parlay_slip below
        fixtures = fetch_fixtures_by_date(date_str, no_league_filter=True) if date_str else fetch_todays_fixtures()

        db = get_firestore_client()
        doc = db.collection('daily_predictions').document(date_str).get()

        if (not doc.exists or not doc.to_dict().get('matches')) and fixtures:
            from services.generator import generate_and_store
            generate_and_store(
                fixtures, predictor, stats_calculator, af_stats,
                sm_proxy=af_proxy,
                date_str=date_str,
            )
            doc = db.collection('daily_predictions').document(date_str).get()

        if not doc.exists:
            return jsonify({
                'date': date_str,
                'matches': [],
                'match_count': 0,
                'message': 'No predictions available.',
            })

        # ── Step 1: Get AI Pro picks — exclude same game (allow same match if different market) ──
        pro_cache_key = f"picks_pro_{date_str}"
        pro_cached = af_proxy.get_cache(pro_cache_key, ttl=3600)
        exclude_match_markets = set()

        if pro_cached:
            pro_matches = pro_cached.get('slip', {}).get('matches', [])
            for pm in pro_matches:
                key = f"{pm.get('home_team', '')}_{pm.get('away_team', '')}_{pm.get('market', '')}"
                exclude_match_markets.add(key)
            print(f"🚫 Excluding {len(exclude_match_markets)} AI Pro match+market combos")
        else:
            print("⚠️ AI Pro picks not cached yet — free picks may overlap (will fix on next call)")

        # ── Step 2: Build free slip — odds 1.10-1.30, combined 1.60-2.00 ──
        print(f"🎯 Free picks for {date_str}: {len(fixtures)} fixtures, "
              f"odds 1.10-1.30, max 6 matches, combined 1.60-2.00")
        clear_cache()

        # Apply market performance penalties
        from utils.market_tracker import get_market_penalties
        _free_mp = {}
        try:
            _free_mp = get_market_penalties(af_proxy, lookback_days=7, min_picks=3)
        except Exception:
            pass

        result = build_parlay_slip(
            fixtures, predictor, stats_calculator,
            num_matches=6,
            min_odds=1.10,
            max_odds=1.57,
            af_stats=None,  # disabled: saves ~1000 API calls/run
            free_mode=False,  # Use strict safety rules
            exclude_match_markets=exclude_match_markets,
            market_penalties=_free_mp,
        )
        result['date'] = date_str

        # ── Step 3: Enforce combined odds 1.60-2.00 ──
        MIN_FREE_COMBINED = 1.60
        MAX_FREE_COMBINED = 2.00

        def calc_combined(lst):
            odds = 1.0
            for m in lst:
                odds *= float(m.get('odds', 1.0))
            return odds

        free_matches = result.get('slip', {}).get('matches', [])
        all_matches = result.get('all_predictions', [])

        # Cap: remove highest-odds pick until combined ≤ max
        while len(free_matches) > 1 and calc_combined(free_matches) > MAX_FREE_COMBINED:
            free_matches.sort(key=lambda x: float(x.get('odds', 1.0)), reverse=True)
            free_matches.pop(0)

        # Floor: if combined < min, try adding from remaining pool
        if calc_combined(free_matches) < MIN_FREE_COMBINED:
            used_keys = {f"{m.get('home_team')}_{m.get('away_team')}" for m in free_matches}
            extras = [m for m in all_matches if f"{m.get('home_team')}_{m.get('away_team')}" not in used_keys]
            for extra in extras:
                test = free_matches + [extra]
                combined = calc_combined(test)
                if combined <= MAX_FREE_COMBINED:
                    free_matches = test
                    used_keys.add(f"{extra.get('home_team')}_{extra.get('away_team')}")
                    if combined >= MIN_FREE_COMBINED:
                        break

        af_proxy.set_cache(cache_key, result)
        return jsonify(result)

    except Exception as e:
        print(f"❌ free_picks_by_date error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/parlay/ai')
def ai_parlay():
    """
    AI Parlay - generate higher-odds multi-match slips.
    
    Query params:
    - num_matches: Max matches (default 3)
    """
    try:
        fixtures = af_proxy.get_fixtures(__import__("datetime").datetime.utcnow().strftime("%Y-%m-%d")).get('fixtures', [])
        num_matches = int(request.args.get('num_matches', 3))
        
        result = build_parlay_slip(
            fixtures, predictor, stats_calculator,
            num_matches=num_matches,
            min_odds=min_odds,
            max_odds=max_odds,
            af_stats=None,  # disabled: saves ~1000 API calls/run
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── API-Football Proxy Endpoints (cached, key stays server-side) ──

@app.route('/api/livescores', methods=['GET'])
def livescores():
    """
    Return cached live scores. Backend polls API-Football every 2 min.
    Clients call this instead of API-Football directly.
    """
    try:
        data = af_proxy.get_livescores()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fixtures/<date_str>', methods=['GET'])
def fixtures_by_date(date_str):
    """
    Return cached fixtures for a date. 10-min cache TTL.
    Clients call this instead of API-Football directly.
    """
    try:
        data = af_proxy.get_fixtures(date_str)
        return jsonify(data)
    except Exception as e:
        print(f"❌ Error in /api/fixtures/{date_str}: {e}")
        return jsonify({'error': str(e), 'fixtures': []}), 500

@app.route('/api/leagues', methods=['GET'])
def leagues():
    """
    Return cached leagues from API-Football. 24-hour cache TTL.
    """
    try:
        data = af_proxy.get_leagues()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/markets')
def list_markets():
    """List all supported betting markets"""
    from config import MARKET_DEFINITIONS
    return jsonify({
        'markets': list(MARKET_DEFINITIONS.keys()),
        'count': len(MARKET_DEFINITIONS)
    })


@app.route('/api/confidence-levels')
def confidence_levels():
    """Explain confidence level calculation"""
    return jsonify({
        'levels': {
            'VERY_HIGH': 'Composite score ≥ 0.55 — Strongest confidence',
            'HIGH': 'Composite score 0.50-0.55 — High confidence',
            'MEDIUM': 'Composite score 0.45-0.50 — Moderate confidence',
            'LOW': 'Composite score < 0.45 — Lower confidence',
        },
        'composite_score': 'Blend of AI probability, edge over bookmaker, and statistical stability'
    })


@app.route('/api/register-token', methods=['POST'])
def register_fcm_token():
    """
    Register an FCM token for push notifications.

    POST /api/register-token
    Body: {"token": "fcm_token_here", "device_id": "optional_device_id"}
    """
    try:
        data = request.json or {}
        token = data.get('token', '').strip()
        device_id = data.get('device_id', '')

        if not token:
            return jsonify({'error': 'Missing token'}), 400

        db = get_firestore_client()
        doc_id = device_id if device_id else token[:64]
        db.collection('fcm_tokens').document(doc_id).set({
            'token': token,
            'device_id': device_id,
            'updated_at': __import__('datetime').datetime.utcnow().isoformat(),
        }, merge=True)

        return jsonify({'status': 'registered', 'doc_id': doc_id})
    except Exception as e:
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
        summary = update_past_results(af_proxy, days_back=days_back)
        return jsonify({'status': 'success', 'code_version': 'v5', **summary})
    except Exception as e:
        print(f"❌ update-results error: {e}")
        return jsonify({'error': str(e), 'code_version': 'v5'}), 500


@app.route('/api/generate-daily', methods=['POST'])
def generate_daily():
    """
    Manual trigger: Generate today's predictions and write to Firestore.
    Protected by CRON_SECRET Bearer token.
    Returns 202 immediately and runs generation in a background thread so
    the request doesn't time out on Render's 30-second HTTP limit.

    POST /api/generate-daily
    Header: Authorization: Bearer <CRON_SECRET>
    """
    import threading

    # ── Auth check ──
    cron_secret = os.environ.get('CRON_SECRET', '').strip()
    auth_header = request.headers.get('Authorization', '')
    if not cron_secret or auth_header != f'Bearer {cron_secret}':
        return jsonify({'error': 'Unauthorized'}), 401

    def _run():
        try:
            from services.generator import generate_and_store
            fixtures = fetch_todays_fixtures()
            result = generate_and_store(
                fixtures, predictor, stats_calculator, af_stats,
                sm_proxy=af_proxy,
            )
            print(f"✅ Background generation done: {result.get('message', '')}")
        except Exception as e:
            print(f"❌ Background generation error: {e}")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return jsonify({
        'status': 'started',
        'message': 'Generation started in background. Picks will be ready in ~60s.',
    }), 202


@app.route('/api/regenerate', methods=['POST'])
def regenerate_picks():
    """
    Force regenerate today's picks with latest server settings.
    Deletes cached Firestore docs and regenerates fresh.
    Protected by CRON_SECRET Bearer token.

    POST /api/regenerate
    Header: Authorization: Bearer <CRON_SECRET>
    Body (optional): {"tabs": ["ai_pro", "rollover", "free"], "date": "2026-03-19"}
    
    Defaults to all tabs and today's date if not specified.
    """
    from datetime import datetime as dt
    import threading

    # ── Auth check ──
    cron_secret = os.environ.get('CRON_SECRET', '').strip()
    auth_header = request.headers.get('Authorization', '')
    if not cron_secret or auth_header != f'Bearer {cron_secret}':
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json or {}
    tabs = data.get('tabs', ['ai_pro', 'rollover', 'free'])
    date_str = data.get('date', dt.utcnow().strftime('%Y-%m-%d'))

    # Validate date
    try:
        dt.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    def _regenerate():
        db = get_firestore_client()
        results = {}

        # Get market penalties once
        from utils.market_tracker import get_market_penalties
        market_penalties = {}
        try:
            market_penalties = get_market_penalties(af_proxy, lookback_days=7, min_picks=3)
        except Exception:
            pass

        # Fetch fixtures once
        fixtures = fetch_fixtures_by_date(date_str, no_league_filter=True) if date_str else fetch_todays_fixtures()
        if not fixtures:
            print(f"❌ Regenerate: No fixtures for {date_str}")
            return

        # ── AI Pro ──
        if 'ai_pro' in tabs:
            try:
                # Delete old doc
                db.collection('daily_ai_pro').document(date_str).delete()
                print(f"🗑️ Deleted daily_ai_pro/{date_str}")

                # Regenerate
                from services.ai_pro_generator import generate_ai_pro_picks
                result = generate_ai_pro_picks(
                    fixtures, predictor, stats_calculator, af_stats,
                    sm_proxy=af_proxy,
                    date_str=date_str,
                    market_penalties=market_penalties,
                )
                results['ai_pro'] = result.get('status', 'unknown')
                print(f"✅ Regenerated AI Pro: {result.get('tip_count', 0)} tips, odds {result.get('combined_odds', 0)}")
            except Exception as e:
                results['ai_pro'] = f'error: {e}'
                print(f"❌ AI Pro regenerate error: {e}")

        # ── Rollover ──
        if 'rollover' in tabs:
            try:
                db.collection('daily_rollover').document(date_str).delete()
                print(f"🗑️ Deleted daily_rollover/{date_str}")

                from services.rollover_generator import generate_rollover_picks
                result = generate_rollover_picks(
                    fixtures, predictor, stats_calculator, af_stats,
                    sm_proxy=af_proxy,
                    date_str=date_str,
                    market_penalties=market_penalties,
                )
                results['rollover'] = result.get('status', 'unknown')
                print(f"✅ Regenerated Rollover: {result.get('match_count', 0)} picks, odds {result.get('combined_odds', 0)}")
            except Exception as e:
                results['rollover'] = f'error: {e}'
                print(f"❌ Rollover regenerate error: {e}")

        # ── Free (uses daily_predictions) ──
        if 'free' in tabs:
            try:
                db.collection('daily_predictions').document(date_str).delete()
                print(f"🗑️ Deleted daily_predictions/{date_str}")

                from services.generator import generate_and_store
                result = generate_and_store(
                    fixtures, predictor, stats_calculator, af_stats,
                    sm_proxy=af_proxy,
                    date_str=date_str,
                )
                results['free'] = result.get('status', 'unknown')
                print(f"✅ Regenerated Free/Daily: {result.get('match_count', 0)} matches")
            except Exception as e:
                results['free'] = f'error: {e}'
                print(f"❌ Free regenerate error: {e}")

        print(f"✅ Regeneration complete for {date_str}: {results}")

    # Run in background thread to avoid timeout
    thread = threading.Thread(target=_regenerate, daemon=True)
    thread.start()

    return jsonify({
        'status': 'started',
        'date': date_str,
        'tabs': tabs,
        'message': f'Regenerating {", ".join(tabs)} for {date_str}. Ready in ~30-60s.',
    }), 202


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)

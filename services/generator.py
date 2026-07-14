"""
Daily prediction generator — shared service layer.

Used by:
  - app.py (POST /api/generate-daily — manual trigger)
  - cron_generate.py (Render cron job — scheduled daily)

No HTTP, no Flask, no routing. Pure business logic.
"""
from datetime import datetime, timedelta
from firebase_config import get_firestore_client
from google.cloud.firestore_v1 import SERVER_TIMESTAMP


def generate_and_store(
    fixtures,
    predictor,
    stats_calculator,
    sm_stats,
    *,
    num_matches=7,
    min_odds=1.10,
    max_odds=2.00,
    save_sqlite_fn=None,
    sm_proxy=None,
    date_str=None,
):
    """
    Run AI predictions on fixtures and write results to Firestore.

    Args:
        fixtures: List of fixture dicts from SportMonks.
        predictor: Loaded MultiMarketPredictor instance.
        stats_calculator: TeamStatsCalculator instance.
        sm_stats: SportMonks stats proxy.
        num_matches: Max matches to generate (default 7).
        min_odds: Minimum odds filter (default 1.10).
        max_odds: Maximum odds filter (default 1.30).
        save_sqlite_fn: Optional callable(date_str, picks_list) for SQLite backup.

    Returns:
        dict with keys: status, date, match_count, combined_odds, message
    """
    from utils.apifootball_stats import clear_cache
    from utils.fixture_fetcher import (
        build_parlay_slip, generate_match_options, format_slip_matches,
        _format_all_predictions, _slip_confidence,
    )
    from utils.market_tracker import get_market_penalties
    from services.safe_slip_engine import build_safe_slip

    today_str = date_str if date_str else datetime.utcnow().strftime('%Y-%m-%d')

    if not fixtures:
        # Write placeholder so on-demand throttle can prevent repeated quota drain
        try:
            db = get_firestore_client()
            db.collection('daily_predictions').document(today_str).set({
                'date': today_str, 'matches': [], 'match_count': 0,
                'generated_at': SERVER_TIMESTAMP, 'status': 'no_fixtures',
            })
        except Exception:
            pass
        return {
            'status': 'no_fixtures',
            'date': today_str,
            'match_count': 0,
            'message': 'No fixtures available for today.',
        }

    # Analyse last 7 days of results to penalise underperforming markets.
    # This is the pseudo-learning layer: the model won't blindly repeat a market
    # that has lost ≥50% of picks in the past week.
    market_penalties = {}
    if sm_proxy is not None:
        try:
            market_penalties = get_market_penalties(sm_proxy, lookback_days=7, min_picks=3)
            if market_penalties:
                print(f"📊 Generator: Applied market penalties for {len(market_penalties)} market(s)")
        except Exception as e:
            print(f"⚠️ Generator: Market tracker failed (non-fatal): {e}")

    # Safe Slip Engine: probability-first, safe markets only
    # (Over 1.5 / Double Chance), real bookmaker odds, combined 2.00-2.20.
    print(f"🧠 Generator: Running Safe Slip Engine on {len(fixtures)} fixtures...")
    clear_cache()
    options = generate_match_options(
        fixtures, predictor, stats_calculator,
        af_stats=None,   # Disable live team stats API calls (saves ~1000 calls/run)
        free_mode=False, # CSV stats + AF predictions are sufficient for qualification
    )
    legs, combined = build_safe_slip(options, market_penalties=market_penalties)

    result = {
        'date': today_str,
        'total_fixtures_analyzed': len(fixtures),
        'all_predictions': _format_all_predictions(options),
    }

    if legs:
        slip = {
            'matches': format_slip_matches(legs),
            'match_count': len(legs),
            'combined_odds': combined,
            'slip_confidence': _slip_confidence(legs),
        }
        matches = slip['matches']
    else:
        # Fallback: no safe legs qualified today — fall back to the legacy
        # value-based slip so the app never shows an empty day.
        print("⚠️ Generator: Safe engine found nothing — legacy parlay fallback")
        legacy = build_parlay_slip(
            fixtures, predictor, stats_calculator,
            num_matches=3,
            min_odds=min_odds,
            max_odds=1.50,
            af_stats=None,
            free_mode=False,
            market_penalties=market_penalties,
        )
        result['all_predictions'] = legacy.get('all_predictions', result['all_predictions'])
        slip = legacy.get('slip', {})
        matches = slip.get('matches', [])

    if not matches:
        # Write placeholder so on-demand throttle can prevent repeated quota drain
        try:
            db = get_firestore_client()
            db.collection('daily_predictions').document(today_str).set({
                'date': today_str, 'matches': [], 'match_count': 0,
                'total_fixtures_analyzed': result.get('total_fixtures_analyzed', 0),
                'generated_at': SERVER_TIMESTAMP, 'status': 'no_matches',
            })
        except Exception:
            pass
        return {
            'status': 'no_matches',
            'date': today_str,
            'match_count': 0,
            'message': 'AI could not generate matches for today.',
        }

    # ── Cap to num_matches, write all qualifying picks directly ──────────────
    # No AI Pro/Free split here — Free tab gets the top picks by value score.
    # Combined odds cap: if combined > 15.0 (too exotic), drop the highest-odds
    # pick until it's within range or only 1 pick remains.
    while len(matches) > 1:
        combined = 1.0
        for m in matches:
            combined *= float(m.get('odds', 1.0))
        if combined <= 15.0:
            break
        matches = sorted(matches, key=lambda m: float(m.get('odds', 1.0)), reverse=True)
        matches.pop(0)

    matches = matches[:num_matches]
    slip['matches'] = matches
    slip['match_count'] = len(matches)

    overall = 1.0
    for m in matches:
        overall *= float(m.get('odds', 1.0))
    slip['combined_odds'] = round(overall, 2)

    print(f"✅ Generator: {len(matches)} matches, combined odds {slip['combined_odds']}")

    # Write to Firestore
    db = get_firestore_client()

    doc_data = {
        'date': today_str,
        'total_fixtures_analyzed': result.get('total_fixtures_analyzed', len(fixtures)),
        'matches': matches,
        'combined_odds': slip.get('combined_odds', 0),
        'slip_confidence': slip.get('slip_confidence', 'NONE'),
        'match_count': len(matches),
        'generated_at': SERVER_TIMESTAMP,
    }

    db.collection('daily_predictions').document(today_str).set(doc_data)
    print(f"✅ Generator: Wrote to Firestore daily_predictions/{today_str}")

    # Send push notification to all registered devices
    try:
        from utils.push_notifier import send_picks_ready
        notif_result = send_picks_ready(
            date_str=today_str,
            match_count=len(matches),
            combined_odds=slip.get('combined_odds', 0),
        )
        print(f"📲 Generator: Push notification sent to {notif_result.get('sent', 0)} device(s)")
    except Exception as e:
        print(f"⚠️ Generator: Push notification failed (non-fatal): {e}")

    # Cleanup old docs (> 7 days)
    _cleanup_old_predictions(db)

    # Optional SQLite backup
    if save_sqlite_fn:
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
                for m in matches
            ]
            save_sqlite_fn(today_str, picks_for_history)
            print(f"💾 Generator: Saved to SQLite history")
        except Exception as e:
            print(f"⚠️ Generator: SQLite save failed (non-fatal): {e}")

    return {
        'status': 'success',
        'date': today_str,
        'match_count': len(matches),
        'combined_odds': slip.get('combined_odds', 0),
        'message': f'Generated {len(matches)} predictions for {today_str}',
    }


def _cleanup_old_predictions(db):
    """Delete daily_predictions docs older than 7 days."""
    try:
        cutoff = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
        old_docs = (
            db.collection('daily_predictions')
            .where('date', '<', cutoff)
            .stream()
        )
        deleted = 0
        for doc in old_docs:
            doc.reference.delete()
            deleted += 1
        if deleted:
            print(f"🗑️ Generator: Deleted {deleted} old docs (before {cutoff})")
    except Exception as e:
        print(f"⚠️ Generator: Cleanup failed (non-fatal): {e}")


def _calc_combined(matches):
    """Calculate combined odds for a list of matches."""
    odds = 1.0
    for m in matches:
        odds *= float(m.get('odds', 1.0))
    return odds


def _enforce_combined_odds(picks, *, min_combined, max_combined, all_pool, exclude=None, max_count=None):
    """
    Enforce combined odds within [min_combined, max_combined].
    - If too high: drop the highest-odds pick.
    - If too low and max_count allows: add picks from all_pool that aren't already used.
    - max_count: hard cap on number of picks (won't add beyond this).
    """
    result = list(picks)
    exclude_keys = set()
    if exclude:
        exclude_keys = {f"{m.get('home_team')}_{m.get('away_team')}" for m in exclude}

    # Cap: remove highest-odds pick until combined ≤ max
    while len(result) > 1 and _calc_combined(result) > max_combined:
        result.sort(key=lambda m: float(m.get('odds', 1.0)), reverse=True)
        result.pop(0)

    # Floor: add picks from pool if combined < min (respecting max_count)
    if _calc_combined(result) < min_combined:
        if max_count is not None and len(result) >= max_count:
            pass  # Already at max count, don't add more picks
        else:
            used_keys = {f"{m.get('home_team')}_{m.get('away_team')}" for m in result}
            used_keys.update(exclude_keys)
            extras = [
                m for m in all_pool
                if f"{m.get('home_team')}_{m.get('away_team')}" not in used_keys
            ]
            for extra in extras:
                if max_count is not None and len(result) >= max_count:
                    break
                test = result + [extra]
                combined = _calc_combined(test)
                if combined <= max_combined:
                    result = test
                    used_keys.add(f"{extra.get('home_team')}_{extra.get('away_team')}")
                    if combined >= min_combined:
                        break

    return result

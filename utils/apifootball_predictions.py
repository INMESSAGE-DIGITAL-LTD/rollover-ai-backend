"""
API-Football /predictions endpoint wrapper.

Fetches win/draw/away % + predicted goals for fixtures. Used for:
  1. Deriving market odds when bookmaker odds are unavailable (non-top leagues)
  2. Blending with our XGBoost model output for stronger predictions
"""
import math
import time
import json
import os
import urllib.request

APIFOOTBALL_KEY  = os.environ.get('APIFOOTBALL_KEY', 'da7a6fc2f03e7fb7994995143d29358f')
APIFOOTBALL_BASE = 'https://v3.football.api-sports.io'

_PREDICTIONS_CACHE = {}   # fixture_id → {data, ts}
_CACHE_TTL         = 6 * 3600   # 6 hours

MAX_PREDICTIONS_CALLS = 150   # cap per run to protect daily quota


def fetch_predictions_for_fixtures(fixture_ids):
    """
    Fetch /predictions for a list of fixture IDs.
    Returns {fixture_id: parsed_prediction_dict}.
    In-memory cache with 6-hour TTL so re-runs in the same day skip refetch.
    Caps new network calls at MAX_PREDICTIONS_CALLS.
    """
    now    = time.time()
    result = {}
    to_fetch = []

    for fid in fixture_ids:
        if fid is None:
            continue
        cached = _PREDICTIONS_CACHE.get(fid)
        if cached and (now - cached['ts']) < _CACHE_TTL:
            result[fid] = cached['data']
        else:
            to_fetch.append(fid)

    to_fetch = to_fetch[:MAX_PREDICTIONS_CALLS]
    if to_fetch:
        print(f"🔮 Predictions: fetching {len(to_fetch)} fixtures "
              f"({len(result)} already cached)...")

    fetched = 0
    for fid in to_fetch:
        try:
            body = _get('predictions', {'fixture': fid})
            resp = body.get('response', [])
            if resp:
                parsed = _parse_prediction(resp[0])
                _PREDICTIONS_CACHE[fid] = {'data': parsed, 'ts': now}
                result[fid] = parsed
                fetched += 1
        except Exception:
            pass

    if to_fetch:
        print(f"🔮 Predictions: {fetched}/{len(to_fetch)} fetched successfully")
    return result


# ── Parsing ───────────────────────────────────────────────────────────────────

def _parse_prediction(data):
    """Parse one /predictions response item into a clean dict."""
    preds   = data.get('predictions', {})
    percent = preds.get('percent', {})
    goals   = preds.get('goals', {})

    home_p = _pct(percent.get('home', '33%'))
    draw_p = _pct(percent.get('draws', '33%'))
    away_p = _pct(percent.get('away', '33%'))

    # Normalise to sum = 1
    total = home_p + draw_p + away_p
    if total > 0:
        home_p /= total
        draw_p /= total
        away_p /= total
    else:
        home_p = draw_p = away_p = 1 / 3

    home_goals  = _safe_float(goals.get('home'), 1.3)
    away_goals  = _safe_float(goals.get('away'), 1.0)
    total_goals = max(0.1, home_goals + away_goals)

    # Poisson goal-count probabilities
    lam = total_goals
    p0  = math.exp(-lam)
    p1  = lam * p0
    p2  = (lam ** 2 / 2.0) * p0

    over05_prob = max(0.10, min(0.98, 1.0 - p0))
    over15_prob = max(0.10, min(0.97, 1.0 - p0 - p1))
    over25_prob = max(0.05, min(0.95, 1.0 - p0 - p1 - p2))

    return {
        'home_prob':            home_p,
        'draw_prob':            draw_p,
        'away_prob':            away_p,
        'over05_prob':          over05_prob,
        'over15_prob':          over15_prob,
        'over25_prob':          over25_prob,
        'predicted_home_goals': home_goals,
        'predicted_away_goals': away_goals,
        'under_over':           preds.get('under_over', ''),
        'advice':               preds.get('advice', ''),
        'winner':               (preds.get('winner') or {}).get('name', ''),
    }


# ── Odds derivation ───────────────────────────────────────────────────────────

def derive_market_odds(pred):
    """
    Convert prediction probabilities → (lines, markets) dicts.
    Format is identical to what _parse_bookmakers returns so _parse_fixture
    can use it as a drop-in when bookmaker odds are unavailable.
    """
    def odds(p):
        return round(1.0 / max(float(p), 0.04), 2)

    home_p = pred['home_prob']
    draw_p = pred['draw_prob']
    away_p = pred['away_prob']

    lines = {
        1.5: {
            'over':  odds(pred['over15_prob']),
            'under': odds(max(0.04, 1.0 - pred['over15_prob'])),
        },
        2.5: {
            'over':  odds(pred['over25_prob']),
            'under': odds(max(0.04, 1.0 - pred['over25_prob'])),
        },
    }

    markets = {
        'fulltime_result': {
            'home': odds(home_p),
            'draw': odds(draw_p),
            'away': odds(away_p),
        },
        'double_chance': {
            'home_draw': odds(min(0.97, home_p + draw_p)),
            'away_draw': odds(min(0.97, away_p + draw_p)),
            'home_away': odds(min(0.97, home_p + away_p)),
        },
    }

    return lines, markets


# ── AI blending ───────────────────────────────────────────────────────────────

def blend_ai_with_prediction(ai_pred, af_pred, weight=0.35):
    """
    Blend XGBoost model output with API-Football prediction probabilities.

    weight: how much to trust API-Football signal (default 35%).
    For fixtures without bookmaker odds (prediction-derived), use weight=0.50
    since API-Football's signal is the primary source.

    Returns an updated copy of ai_pred.
    """
    if not af_pred:
        return ai_pred

    blended = dict(ai_pred)
    w  = weight
    w2 = 1.0 - w

    _blend(blended, 'ft_over_15',  af_pred['over15_prob'], w, w2)
    _blend(blended, 'ft_over_25',  af_pred['over25_prob'], w, w2)
    _blend(blended, 'home_win',    af_pred['home_prob'],   w, w2)
    _blend(blended, 'away_win',    af_pred['away_prob'],   w, w2)
    _blend(blended, 'draw',        af_pred['draw_prob'],   w, w2)

    # Re-derive DC from the already-blended result probs
    h = blended.get('home_win', af_pred['home_prob'])
    d = blended.get('draw',     af_pred['draw_prob'])
    a = blended.get('away_win', af_pred['away_prob'])
    if 'dc_home_draw' in blended:
        blended['dc_home_draw'] = min(0.97, h + d)
    if 'dc_away_draw' in blended:
        blended['dc_away_draw'] = min(0.97, a + d)
    if 'dc_home_away' in blended:
        blended['dc_home_away'] = min(0.97, h + a)

    return blended


# ── Helpers ───────────────────────────────────────────────────────────────────

def _blend(d, key, af_val, w, w2):
    if key in d:
        d[key] = min(0.97, d[key] * w2 + float(af_val) * w)


def _pct(v):
    try:
        return float(str(v or '0').replace('%', '')) / 100.0
    except (ValueError, TypeError):
        return 0.0


def _safe_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _get(path, params):
    qs  = '&'.join(f"{k}={v}" for k, v in params.items())
    url = f"{APIFOOTBALL_BASE}/{path}?{qs}"
    req = urllib.request.Request(url, headers={'x-apisports-key': APIFOOTBALL_KEY})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())

"""
API-Football /predictions + /injuries wrapper.

Fetches:
  - /predictions: win/draw/away %, predicted goals, Poisson distribution,
    attack/defence ratings, H2H probability, form comparison
  - /injuries: injured players per fixture (reduces goal/result probabilities)

Used for:
  1. Deriving market odds when bookmaker odds are unavailable (non-top leagues)
  2. Blending with XGBoost model output — weighted by league tier:
       Top leagues (bookmaker odds): 50% XGBoost / 50% API-Football
       Non-top leagues (no odds):    25% XGBoost / 75% API-Football
  3. Injury adjustments applied after blending

Blend weight reasoning:
  - XGBoost trained on ~24k matches, mostly top European leagues.
    For non-top leagues it falls back to hardcoded default stats.
  - API-Football predictions use their full global database (all leagues)
    and include Poisson + attack/defence + H2H signals.
  - Giving API-Football more weight for non-top leagues is the correct call.
"""
import math
import time
import json
import os
import urllib.request

APIFOOTBALL_KEY  = os.environ.get('APIFOOTBALL_KEY', 'da7a6fc2f03e7fb7994995143d29358f')
APIFOOTBALL_BASE = 'https://v3.football.api-sports.io'

_PREDICTIONS_CACHE = {}   # fixture_id → {data, ts}
_INJURIES_CACHE    = {}   # fixture_id → {data, ts}
_CACHE_TTL         = 6 * 3600   # 6 hours

MAX_PREDICTIONS_CALLS = 50    # cap per run — only no-odds fixtures need predictions
MAX_INJURIES_CALLS    = 30


# ── Blend weights ─────────────────────────────────────────────────────────────

# For top-league games that have real bookmaker odds:
WEIGHT_API_BOOKMAKER = 0.50    # API-Football gets 50%, XGBoost gets 50%

# For non-top leagues where we derive odds from predictions:
# XGBoost uses hardcoded fallback stats for unknown teams → less trustworthy
WEIGHT_API_PREDICTION = 0.75   # API-Football gets 75%, XGBoost gets 25%


# ── Predictions fetch ─────────────────────────────────────────────────────────

def fetch_predictions_for_fixtures(fixture_ids):
    """
    Fetch /predictions for a list of fixture IDs.
    Returns {fixture_id: parsed_prediction_dict}.
    In-memory cache with 6-hour TTL. Caps new calls at MAX_PREDICTIONS_CALLS.
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
        print(f"🔮 Predictions: {fetched}/{len(to_fetch)} fetched, "
              f"{len(result)} total available")
    return result


# ── Injuries fetch ────────────────────────────────────────────────────────────

def fetch_injuries_for_fixtures(fixture_ids):
    """
    Fetch /injuries for a list of fixture IDs.
    Returns {fixture_id: injury_summary_dict}.
    injury_summary_dict keys:
      home_injured_count, away_injured_count,
      home_key_striker_out, away_key_striker_out,
      home_goalkeeper_out, away_goalkeeper_out
    """
    now    = time.time()
    result = {}
    to_fetch = []

    for fid in fixture_ids:
        if fid is None:
            continue
        cached = _INJURIES_CACHE.get(fid)
        if cached and (now - cached['ts']) < _CACHE_TTL:
            result[fid] = cached['data']
        else:
            to_fetch.append(fid)

    to_fetch = to_fetch[:MAX_INJURIES_CALLS]
    if to_fetch:
        print(f"🏥 Injuries: fetching {len(to_fetch)} fixtures "
              f"({len(result)} already cached)...")

    fetched = 0
    for fid in to_fetch:
        try:
            body = _get('injuries', {'fixture': fid})
            resp = body.get('response', [])
            if resp is not None:
                parsed = _parse_injuries(resp)
                _INJURIES_CACHE[fid] = {'data': parsed, 'ts': now}
                result[fid] = parsed
                fetched += 1
        except Exception:
            pass

    if to_fetch:
        print(f"🏥 Injuries: {fetched}/{len(to_fetch)} fetched")
    return result


# ── Parsing ───────────────────────────────────────────────────────────────────

def _parse_prediction(data):
    """
    Parse one /predictions response item into a clean dict.
    Uses ALL available signals: percent, Poisson from goals, AND the full
    comparison object (attack, defence, H2H, form, Poisson distribution).
    """
    preds      = data.get('predictions', {})
    percent    = preds.get('percent', {})
    goals      = preds.get('goals', {})
    comparison = data.get('comparison', {})

    # ── Win/draw/away percent ──
    home_p = _pct(percent.get('home', '33%'))
    draw_p = _pct(percent.get('draws', '33%'))
    away_p = _pct(percent.get('away', '33%'))

    total = home_p + draw_p + away_p
    if total > 0:
        home_p /= total
        draw_p /= total
        away_p /= total
    else:
        home_p = draw_p = away_p = 1 / 3

    # ── Predicted goals → Poisson probabilities ──
    home_goals  = _safe_float(goals.get('home'), 1.3)
    away_goals  = _safe_float(goals.get('away'), 1.0)
    total_goals = max(0.1, home_goals + away_goals)

    lam = total_goals
    p0  = math.exp(-lam)
    p1  = lam * p0
    p2  = (lam ** 2 / 2.0) * p0

    over05_prob = max(0.10, min(0.98, 1.0 - p0))
    over15_prob = max(0.10, min(0.97, 1.0 - p0 - p1))
    over25_prob = max(0.05, min(0.95, 1.0 - p0 - p1 - p2))

    # ── Comparison object ──────────────────────────────────────────────────────
    # API-Football's comparison section contains 6 independent rating signals.
    # We extract and normalise each so they can be used for blending.

    # Poisson distribution (their own Poisson model — separate signal)
    poisson = comparison.get('poisson_distribution', {})
    poisson_home = _pct(poisson.get('home', '0%'))
    poisson_draw = _pct(poisson.get('draw', '0%'))
    poisson_away = _pct(poisson.get('away', '0%'))

    # H2H-weighted probabilities
    h2h_cmp = comparison.get('h2h', {})
    h2h_home = _pct(h2h_cmp.get('home', '0%'))
    h2h_draw = _pct(h2h_cmp.get('draw', '0%'))
    h2h_away = _pct(h2h_cmp.get('away', '0%'))

    # Attack / Defence rating (0–100 scale)
    atk = comparison.get('att', comparison.get('attack', {}))
    dfc = comparison.get('def', comparison.get('defence', {}))
    home_attack  = _pct(atk.get('home', '50%'))
    away_attack  = _pct(atk.get('away', '50%'))
    home_defence = _pct(dfc.get('home', '50%'))
    away_defence = _pct(dfc.get('away', '50%'))

    # Goals comparison (higher = more goals expected from that side)
    goals_cmp   = comparison.get('goals', {})
    home_goals_r = _pct(goals_cmp.get('home', '50%'))
    away_goals_r = _pct(goals_cmp.get('away', '50%'))

    # Form comparison
    form_cmp   = comparison.get('form', {})
    home_form_r = _pct(form_cmp.get('home', '50%'))
    away_form_r = _pct(form_cmp.get('away', '50%'))

    # ── Blend comparison signals into an enhanced probability estimate ─────────
    # If Poisson distribution is available, blend it with percent-derived probs
    # to get a more robust final estimate. Both use different methods so they
    # complement each other.
    if poisson_home + poisson_draw + poisson_away > 0.3:
        ptotal = poisson_home + poisson_draw + poisson_away
        poisson_home /= ptotal
        poisson_draw /= ptotal
        poisson_away /= ptotal
        # Blend: 60% percent model + 40% Poisson model
        home_p = home_p * 0.60 + poisson_home * 0.40
        draw_p = draw_p * 0.60 + poisson_draw * 0.40
        away_p = away_p * 0.60 + poisson_away * 0.40

    # Attack-adjusted over goal probability:
    # High combined attack rating → more goals → boost over probs
    combined_attack = (home_attack + away_attack) / 2.0   # 0–1
    combined_defence = (home_defence + away_defence) / 2.0
    attack_boost = (combined_attack - 0.5) * 0.10   # ±0.05 max
    defence_damp = (combined_defence - 0.5) * 0.06  # ±0.03 max
    # High attack → more goals; high defence → fewer goals
    over15_prob = max(0.10, min(0.97, over15_prob + attack_boost - defence_damp))
    over25_prob = max(0.05, min(0.95, over25_prob + attack_boost - defence_damp))

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
        # Comparison signals (stored for injury adjustment & future use)
        'home_attack_r':        home_attack,
        'away_attack_r':        away_attack,
        'home_defence_r':       home_defence,
        'away_defence_r':       away_defence,
        'home_goals_r':         home_goals_r,
        'away_goals_r':         away_goals_r,
        'home_form_r':          home_form_r,
        'away_form_r':          away_form_r,
        'h2h_home':             h2h_home,
        'h2h_draw':             h2h_draw,
        'h2h_away':             h2h_away,
    }


def _parse_injuries(response):
    """
    Parse /injuries response for one fixture into a summary dict.
    Focuses on: striker absences (reduce goals), GK absences (boost goals).
    """
    home_injured = 0
    away_injured = 0
    home_striker_out = False
    away_striker_out = False
    home_gk_out      = False
    away_gk_out      = False

    home_team_id = None
    away_team_id = None

    # Determine home/away team IDs from first two entries
    team_ids = []
    for entry in response:
        tid = (entry.get('team') or {}).get('id')
        if tid and tid not in team_ids:
            team_ids.append(tid)
    if len(team_ids) >= 2:
        home_team_id, away_team_id = team_ids[0], team_ids[1]

    for entry in response:
        player = entry.get('player', {})
        tid    = (entry.get('team') or {}).get('id')
        pos    = (player.get('position') or '').lower()
        reason = (entry.get('reason') or '').lower()

        # Only count players actually out (not doubtful)
        if 'doubtful' in reason:
            continue

        if tid == home_team_id:
            home_injured += 1
            if 'forward' in pos or 'attacker' in pos:
                home_striker_out = True
            if 'goalkeeper' in pos:
                home_gk_out = True
        elif tid == away_team_id:
            away_injured += 1
            if 'forward' in pos or 'attacker' in pos:
                away_striker_out = True
            if 'goalkeeper' in pos:
                away_gk_out = True

    return {
        'home_injured_count':  home_injured,
        'away_injured_count':  away_injured,
        'home_striker_out':    home_striker_out,
        'away_striker_out':    away_striker_out,
        'home_gk_out':         home_gk_out,
        'away_gk_out':         away_gk_out,
    }


# ── Primary probability builder ───────────────────────────────────────────────

def af_prediction_to_ai_pred(af_pred):
    """
    Convert an API-Football prediction dict into the ai_pred format that
    _try_add expects (same keys as MultiMarketPredictor.predict_match).

    This replaces XGBoost as the primary probability source. Every market
    is derived from API-Football's predicted goals (Poisson) and win/draw/away
    percentages. XGBoost only runs when af_pred is None (fallback).
    """
    hg = max(0.1, af_pred.get('predicted_home_goals', 1.3))
    ag = max(0.1, af_pred.get('predicted_away_goals', 1.0))

    home_p = af_pred['home_prob']
    draw_p = af_pred['draw_prob']
    away_p = af_pred['away_prob']

    # Per-team Poisson (independent scoring model)
    home_p0 = math.exp(-hg)
    home_p1 = hg * home_p0
    away_p0 = math.exp(-ag)
    away_p1 = ag * away_p0

    home_over05 = _cap(1.0 - home_p0)
    home_over15 = _cap(1.0 - home_p0 - home_p1, hi=0.92)
    away_over05 = _cap(1.0 - away_p0)
    away_over15 = _cap(1.0 - away_p0 - away_p1, hi=0.92)

    btts     = _cap(home_over05 * away_over05, hi=0.92)
    btts_no  = _cap(1.0 - btts)

    # Total-goals Poisson (already computed in _parse_prediction but replicate here)
    over15   = af_pred.get('over15_prob', _cap(1.0 - math.exp(-(hg + ag)) - (hg + ag) * math.exp(-(hg + ag))))
    over25   = af_pred.get('over25_prob', 0.45)
    under25  = _cap(1.0 - over25)
    # Under 3.5 ≈ P(total goals ≤ 3)
    lam      = hg + ag
    lp0      = math.exp(-lam)
    lp1      = lam * lp0
    lp2      = (lam ** 2 / 2.0) * lp0
    lp3      = (lam ** 3 / 6.0) * lp0
    under35  = _cap(lp0 + lp1 + lp2 + lp3)

    # Half-time: ~42% of goals in first half, ~58% in second
    fh_lam  = (hg + ag) * 0.42
    sh_lam  = (hg + ag) * 0.58
    fh_p0   = math.exp(-max(0.05, fh_lam))
    sh_p0   = math.exp(-max(0.05, sh_lam))

    fh_over05  = _cap(1.0 - fh_p0)
    fh_under05 = _cap(1.0 - fh_over05)
    sh_over05  = _cap(1.0 - sh_p0)
    sh_under05 = _cap(1.0 - sh_over05)

    fh_p1      = fh_lam * fh_p0
    ht_over15  = _cap(1.0 - fh_p0 - fh_p1, hi=0.65)
    ht_under15 = _cap(1.0 - ht_over15)

    return {
        'ft_over_15':   over15,
        'ft_under_15':  _cap(1.0 - over15),
        'ft_over_25':   over25,
        'ft_under_25':  under25,
        'ft_under_35':  under35,
        'ht_over_15':   ht_over15,
        'ht_under_15':  ht_under15,
        'home_over_05': home_over05,
        'home_under_05': _cap(1.0 - home_over05),
        'home_over_15': home_over15,
        'home_under_15': _cap(1.0 - home_over15),
        'away_over_05': away_over05,
        'away_under_05': _cap(1.0 - away_over05),
        'away_over_15': away_over15,
        'away_under_15': _cap(1.0 - away_over15),
        'fh_over_05':   fh_over05,
        'fh_under_05':  fh_under05,
        'sh_over_05':   sh_over05,
        'sh_under_05':  sh_under05,
        'btts_yes':     btts,
        'btts_no':      btts_no,
        'home_win':     home_p,
        'draw':         draw_p,
        'away_win':     away_p,
        'dc_home_draw': _cap(home_p + draw_p),
        'dc_away_draw': _cap(away_p + draw_p),
        'dc_home_away': _cap(home_p + away_p),
    }


def _cap(v, lo=0.03, hi=0.97):
    return max(lo, min(hi, float(v)))




def derive_market_odds(pred):
    """
    Convert prediction probabilities → (lines, markets) dicts.
    Format is identical to what _parse_bookmakers returns.
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

def blend_ai_with_prediction(ai_pred, af_pred, weight=None, odds_source='bookmaker'):
    """
    Blend XGBoost model output with API-Football prediction probabilities.

    Weight logic:
      - odds_source='bookmaker': API-Football weight = WEIGHT_API_BOOKMAKER (0.50)
        Both sources are equally reliable for top leagues.
      - odds_source='prediction': API-Football weight = WEIGHT_API_PREDICTION (0.75)
        XGBoost uses hardcoded fallback stats for unknown teams → less reliable.

    Returns an updated copy of ai_pred.
    """
    if not af_pred:
        return ai_pred

    if weight is None:
        weight = (WEIGHT_API_PREDICTION
                  if odds_source == 'prediction'
                  else WEIGHT_API_BOOKMAKER)

    blended = dict(ai_pred)
    w  = weight
    w2 = 1.0 - w

    _blend(blended, 'ft_over_15',  af_pred['over15_prob'], w, w2)
    _blend(blended, 'ft_over_25',  af_pred['over25_prob'], w, w2)
    _blend(blended, 'home_win',    af_pred['home_prob'],   w, w2)
    _blend(blended, 'away_win',    af_pred['away_prob'],   w, w2)
    _blend(blended, 'draw',        af_pred['draw_prob'],   w, w2)

    # Re-derive DC from the blended result probs
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


def apply_injury_adjustment(ai_pred, injuries):
    """
    Adjust probabilities based on injury report.

    Rules (conservative — don't overcorrect):
    - Home/away striker out:  reduce that team's scoring probability → dampen over goals
    - Goalkeeper out:         opponent scores more easily → boost over goals
    - Heavy injury burden (3+ players):  small blanket dampen on over markets

    Returns updated ai_pred dict.
    """
    if not injuries:
        return ai_pred

    adjusted = dict(ai_pred)

    h_striker = injuries.get('home_striker_out', False)
    a_striker = injuries.get('away_striker_out', False)
    h_gk      = injuries.get('home_gk_out', False)
    a_gk      = injuries.get('away_gk_out', False)
    h_count   = injuries.get('home_injured_count', 0)
    a_count   = injuries.get('away_injured_count', 0)

    # Striker absences → dampen over markets
    if h_striker and a_striker:
        _scale(adjusted, 'ft_over_15', 0.93)
        _scale(adjusted, 'ft_over_25', 0.90)
    elif h_striker or a_striker:
        _scale(adjusted, 'ft_over_15', 0.96)
        _scale(adjusted, 'ft_over_25', 0.93)

    # GK absence → opponent likely scores → boost over markets
    if h_gk:
        _scale(adjusted, 'ft_over_15', 1.03)
        _scale(adjusted, 'ft_over_25', 1.04)
        _scale(adjusted, 'away_win',   1.04)
    if a_gk:
        _scale(adjusted, 'ft_over_15', 1.03)
        _scale(adjusted, 'ft_over_25', 1.04)
        _scale(adjusted, 'home_win',   1.04)

    # Heavy squad depletion (3+ absences per side)
    if h_count >= 3:
        _scale(adjusted, 'home_win', 0.94)
        _scale(adjusted, 'ft_over_15', 0.97)
    if a_count >= 3:
        _scale(adjusted, 'away_win', 0.94)
        _scale(adjusted, 'ft_over_15', 0.97)

    # Clamp all values
    for k in adjusted:
        if isinstance(adjusted[k], float):
            adjusted[k] = max(0.01, min(0.97, adjusted[k]))

    return adjusted


# ── Odds movement tracker ─────────────────────────────────────────────────────
# Stores the first-seen odds for each fixture+market. When we re-process the
# same fixture later in the day, we compare current odds to opening odds.
# Significant drops in Over 1.5 odds = sharp money moving in = stronger signal.

_OPENING_ODDS = {}   # key: "fixture_id_market" → float

def record_opening_odds(fixture_id, market, odds):
    """Call this when first parsing odds for a fixture. No-op if already recorded."""
    key = f"{fixture_id}_{market}"
    if key not in _OPENING_ODDS:
        _OPENING_ODDS[key] = float(odds)


def get_odds_movement(fixture_id, market, current_odds):
    """
    Returns movement as a multiplier to apply to composite_score.
    - Odds dropped significantly (sharp money in) → 1.10 boost
    - Odds drifted up (money going against) → 0.92 penalty
    - No movement data → 1.0 (neutral)
    """
    key = f"{fixture_id}_{market}"
    opening = _OPENING_ODDS.get(key)
    if opening is None or opening <= 0:
        return 1.0

    current = float(current_odds)
    change  = (opening - current) / opening   # positive = odds shortened (moved in)

    if change >= 0.12:    # odds dropped 12%+ (e.g. 1.50 → 1.32) — strong sharp move
        return 1.12
    if change >= 0.06:    # odds dropped 6–12% — moderate move
        return 1.06
    if change <= -0.10:   # odds drifted 10%+ (money going against)
        return 0.92
    if change <= -0.05:   # small drift
        return 0.96
    return 1.0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _blend(d, key, af_val, w, w2):
    if key in d:
        d[key] = min(0.97, d[key] * w2 + float(af_val) * w)


def _scale(d, key, factor):
    if key in d:
        d[key] = min(0.97, d[key] * factor)


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

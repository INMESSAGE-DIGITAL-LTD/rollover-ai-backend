"""
xgb_predictor.py
================
Loads the XGBoost models trained by train_xgboost.py (models/xgb_*.joblib)
and blends their calibrated probabilities into the ai_pred dict produced by
fixture_fetcher._generate_match_options().

The models use bookmaker-implied probabilities + league DNA as features,
so they only fire when real bookmaker odds are available.
"""
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_MODELS_DIR = Path(__file__).parent.parent / 'models'

FEATURE_COLS = [
    'implied_home',
    'implied_draw',
    'implied_away',
    'implied_over25',
    'implied_under25',
    'league_over25_rate',
    'league_over15_rate',
    'league_btts_rate',
    'league_avg_goals',
    'league_home_win_rate',
    'league_is_high_scoring',
    'league_is_low_scoring',
]

# Maps train_xgboost.py target name → ai_pred dict key used in fixture_fetcher
XGB_TO_AI_KEY = {
    'over15':   'ft_over_15',
    'over25':   'ft_over_25',
    'over35':   'ft_over_35',
    'under25':  'ft_under_25',
    'under35':  'ft_under_35',
    'btts':     'btts_yes',
    'home_win': 'home_win',
}

_models = {}
_load_attempted = False


def _load_models():
    global _models, _load_attempted
    if _load_attempted:
        return _models
    _load_attempted = True
    try:
        import joblib
        for target in XGB_TO_AI_KEY:
            path = _MODELS_DIR / f'xgb_{target}.joblib'
            if path.exists():
                _models[target] = joblib.load(path)
        if _models:
            log.info('XGBPredictor: loaded %d/%d models', len(_models), len(XGB_TO_AI_KEY))
        else:
            log.warning('XGBPredictor: no models found in %s', _MODELS_DIR)
    except Exception as e:
        log.warning('XGBPredictor: load failed: %s', e)
    return _models


def predict(implied_home, implied_draw, implied_away,
            implied_over25, implied_under25, league_name='Unknown'):
    """
    Returns {ai_pred_key: probability} for markets where XGBoost models exist.
    Falls back to {} if models not loaded or feature extraction fails.
    """
    models = _load_models()
    if not models:
        return {}

    try:
        import pandas as pd

        # League DNA features (safe defaults if module unavailable)
        dna_feats = {
            'league_over25_rate':    0.52,
            'league_over15_rate':    0.75,
            'league_btts_rate':      0.52,
            'league_avg_goals':      2.70,
            'league_home_win_rate':  0.45,
            'league_is_high_scoring': 0,
            'league_is_low_scoring':  0,
        }
        try:
            from utils.league_dna import get_league_dna
            dna = get_league_dna(league_name)
            dna_feats = {
                'league_over25_rate':    dna.over25_rate,
                'league_over15_rate':    dna.over15_rate,
                'league_btts_rate':      dna.btts_rate,
                'league_avg_goals':      dna.avg_goals_pg,
                'league_home_win_rate':  dna.home_win_rate,
                'league_is_high_scoring': 1 if dna.is_high_scoring else 0,
                'league_is_low_scoring':  1 if dna.is_low_scoring else 0,
            }
        except Exception:
            pass

        row = {
            'implied_home':    implied_home,
            'implied_draw':    implied_draw,
            'implied_away':    implied_away,
            'implied_over25':  implied_over25,
            'implied_under25': implied_under25,
            **dna_feats,
        }
        X = pd.DataFrame([row])[FEATURE_COLS]

        result = {}
        for target, model in models.items():
            ai_key = XGB_TO_AI_KEY.get(target)
            if ai_key:
                prob = float(model.predict_proba(X)[0][1])
                result[ai_key] = round(prob, 3)
        return result

    except Exception as e:
        log.warning('XGBPredictor.predict failed: %s', e)
        return {}


def _extract_implied_probs(fix):
    """Extract margin-normalised implied probabilities from a fixture dict."""
    markets = fix.get('markets', {})
    lines   = fix.get('lines', {})

    ftr = markets.get('fulltime_result', {})
    h_odds = float(ftr.get('home', 0) or 2.5)
    d_odds = float(ftr.get('draw', 0) or 3.3)
    a_odds = float(ftr.get('away', 0) or 3.0)

    line25     = lines.get(2.5, {})
    ov25_odds  = float(line25.get('over_odds',  0) or 1.90)
    un25_odds  = float(line25.get('under_odds', 0) or 1.95)

    # Normalise out bookmaker margin
    inv_1x2 = 1/h_odds + 1/d_odds + 1/a_odds
    inv_ou  = 1/ov25_odds + 1/un25_odds

    return (
        (1/h_odds)    / inv_1x2,   # implied_home
        (1/d_odds)    / inv_1x2,   # implied_draw
        (1/a_odds)    / inv_1x2,   # implied_away
        (1/ov25_odds) / inv_ou,    # implied_over25
        (1/un25_odds) / inv_ou,    # implied_under25
    )


def blend_xgb_predictions(ai_pred, fix):
    """
    Merge XGBoost probabilities into ai_pred.
    XGBoost values take priority for the markets they cover.
    """
    try:
        implied = _extract_implied_probs(fix)
        league_name = fix.get('league_name', 'Unknown')
        xgb_probs = predict(*implied, league_name=league_name)
        if xgb_probs:
            result = dict(ai_pred)
            result.update(xgb_probs)
            return result
    except Exception as e:
        log.warning('blend_xgb_predictions failed: %s', e)
    return ai_pred

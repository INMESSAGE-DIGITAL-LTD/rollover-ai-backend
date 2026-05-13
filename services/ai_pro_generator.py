"""
AI Pro Tips generator — server-side replacement for client-side RapidAPI logic.

Strategy:
  - Uses the SAME XGBoost multi-market prediction pipeline as Rollover
  - All markets supported: FT result, Double Chance, BTTS, Over/Under, team goals,
    1st/2nd half — any market passing quality gates qualifies
  - Dynamic pick count: 1-3 tips based on what qualifies (quality over quantity)
  - Odds limits: 1.40–2.50 per pick, combined 2.00–5.00
  - Real odds from API-Football (not hardcoded estimates)
  - Market penalties applied to avoid repeating losing patterns
  - Stores results in Firestore daily_ai_pro/{date_str}
  - Response format designed for direct consumption by Flutter app

This makes AI Pro fully server-controlled — no app update needed for
future threshold/strategy changes.
"""
from datetime import datetime, timedelta
from firebase_config import get_firestore_client
from google.cloud.firestore_v1 import SERVER_TIMESTAMP


# Minimum AI probability per market.
# Risky 1X2 markets raised significantly — they're harder to call and hurt streaks.
AI_PRO_MIN_PROB = {
    'Home Win':                0.72,  # raised: 1X2 too unpredictable below this
    'Away Win':                0.72,  # raised
    'Draw':                    0.65,  # raised: draw is hardest market
    'Double Chance (1X)':      0.74,
    'Double Chance (X2)':      0.72,
    'Double Chance (12)':      0.70,
    'Both Teams to Score':     0.68,
    'BTTS No':                 0.65,
    'Over 1.5 Goals':          0.72,
    'Over 2.5 Goals':          0.70,
    'Under 2.5 Goals':         0.66,
    'Under 3.5 Goals':         0.68,
    'Home Over 0.5 Goals':     0.74,
    'Home Over 1.5 Goals':     0.70,
    'Home Over 2.5 Goals':     0.63,
    'Away Over 0.5 Goals':     0.72,
    'Away Over 1.5 Goals':     0.67,
    'Away Over 2.5 Goals':     0.60,
    'Home to Score':           0.74,
    'Away to Score':           0.72,
    '1st Half Over 0.5':       0.70,
    '2nd Half Over 0.5':       0.70,
    '1st Half Under 0.5':      0.65,
    '2nd Half Under 0.5':      0.65,
}

# Safe markets get a scoring boost — prioritised over risky 1X2 picks.
SAFE_MARKET_BOOST = {
    'Over 1.5 Goals':          1.35,
    'Double Chance (1X)':      1.30,
    'Double Chance (X2)':      1.30,
    'Double Chance (12)':      1.25,
    'Home Over 0.5 Goals':     1.30,
    'Away Over 0.5 Goals':     1.25,
    'Home to Score':           1.25,
    'Away to Score':           1.20,
    'Both Teams to Score':     1.15,
}

# Risky markets get a scoring penalty to push them to the back of the queue.
RISKY_MARKET_PENALTY = {
    'Home Win':   0.75,
    'Away Win':   0.75,
    'Draw':       0.60,
}

# Minimum composite score per market — risky markets need higher bar
AI_PRO_MIN_COMPOSITE = {
    'Home Win':                0.52,  # raised
    'Away Win':                0.52,  # raised
    'Draw':                    0.48,  # raised
    'Double Chance (1X)':      0.49,
    'Double Chance (X2)':      0.48,
    'Double Chance (12)':      0.47,
    'Both Teams to Score':     0.47,
    'BTTS No':                 0.45,
    'Over 1.5 Goals':          0.48,
    'Over 2.5 Goals':          0.47,
    'Under 2.5 Goals':         0.45,
    'Under 3.5 Goals':         0.47,
    'Home Over 0.5 Goals':     0.48,
    'Home Over 1.5 Goals':     0.46,
    'Home Over 2.5 Goals':     0.42,
    'Away Over 0.5 Goals':     0.46,
    'Away Over 1.5 Goals':     0.44,
    'Away Over 2.5 Goals':     0.40,
    'Home to Score':           0.48,
    'Away to Score':           0.46,
    '1st Half Over 0.5':       0.45,
    '2nd Half Over 0.5':       0.45,
    '1st Half Under 0.5':      0.43,
    '2nd Half Under 0.5':      0.43,
}

# Minimum edge required (model_prob - implied_prob)
AI_PRO_MIN_EDGE = 0.05

# Odds limits per pick — raised floor to exclude low-value DC picks
AI_PRO_MIN_ODDS = 1.40
AI_PRO_MAX_ODDS = 2.50

# Max picks per day — dynamic 1-3 based on what qualifies
AI_PRO_MAX_PICKS = 3

# Combined odds range
AI_PRO_MIN_COMBINED_ODDS = 2.00
AI_PRO_MAX_COMBINED_ODDS = 5.00

# Max 1 pick of the same market type (force full diversity)
AI_PRO_MAX_SAME_MARKET = 1

# Map backend market names → Flutter app rule types
MARKET_TO_RULE_TYPE = {
    'Home Win':                'homeWin',
    'Away Win':                'awayWin',
    'Draw':                    'draw',
    'Double Chance (1X)':      'doubleChance',
    'Double Chance (X2)':      'doubleChance',
    'Double Chance (12)':      'doubleChance',
    'Both Teams to Score':     'btts',
    'BTTS No':                 'bttsNo',
    'Over 1.5 Goals':          'overGoals',
    'Over 2.5 Goals':          'overGoals',
    'Under 2.5 Goals':         'underGoals',
    'Under 3.5 Goals':         'underGoals',
    'Home Over 0.5 Goals':     'homeTeamGoals',
    'Home Over 1.5 Goals':     'homeTeamGoals',
    'Home Over 2.5 Goals':     'homeTeamGoals',
    'Away Over 0.5 Goals':     'awayTeamGoals',
    'Away Over 1.5 Goals':     'awayTeamGoals',
    'Away Over 2.5 Goals':     'awayTeamGoals',
    'Home to Score':           'homeToScore',
    'Away to Score':           'awayToScore',
    '1st Half Over 0.5':       'firstHalf',
    '2nd Half Over 0.5':       'secondHalf',
    '1st Half Under 0.5':      'firstHalf',
    '2nd Half Under 0.5':      'secondHalf',
}

# Extract goal line from market name
def _extract_goal_line(market):
    """Extract numeric goal line from market name, e.g. 'Over 1.5 Goals' → 1.5"""
    import re
    match = re.search(r'(\d+\.?\d*)', market)
    return float(match.group(1)) if match else None


def _build_advice_text(market, home_team, away_team):
    """Build user-friendly advice text matching Flutter app expectations."""
    if 'Over' in market:
        line = _extract_goal_line(market)
        return f'Advice: Over {line} Goals' if line else f'Advice: {market}'
    elif 'Under' in market:
        line = _extract_goal_line(market)
        return f'Advice: Under {line} Goals' if line else f'Advice: {market}'
    elif market == 'Home Win':
        return f'Advice: {home_team} to Win'
    elif market == 'Away Win':
        return f'Advice: {away_team} to Win'
    elif market == 'Double Chance (1X)':
        return f'Advice: {home_team} or Draw'
    elif market == 'Double Chance (X2)':
        return f'Advice: Draw or {away_team}'
    return f'Advice: {market}'


def generate_ai_pro_picks(
    fixtures,
    predictor,
    stats_calculator,
    sm_stats,
    *,
    sm_proxy=None,
    date_str=None,
    market_penalties=None,
):
    """
    Generate AI Pro tips using the full XGBoost pipeline.

    Returns ready-to-display tips with all fields the Flutter app needs:
    team names, logos, odds, advice text, rule type, goal line, etc.

    Args:
        fixtures:          List of fixture dicts from SportMonks.
        predictor:         Loaded MultiMarketPredictor instance.
        stats_calculator:  TeamStatsCalculator instance.
        sm_stats:          SportMonks stats proxy.
        date_str:          Target date (YYYY-MM-DD). Defaults to today UTC.
        market_penalties:  Dict of {market: multiplier} from market_tracker.

    Returns:
        dict with keys: status, date, tips, tip_count, combined_odds, confidence
    """
    from utils.fixture_fetcher import _generate_match_options as generate_match_options, _slip_confidence as slip_confidence
    from utils.apifootball_stats import clear_cache

    target_date = date_str if date_str else datetime.utcnow().strftime('%Y-%m-%d')

    if not fixtures:
        return {
            'status': 'no_fixtures',
            'date': target_date,
            'tips': [],
            'tip_count': 0,
            'combined_odds': 1.0,
            'message': 'No fixtures available for AI Pro.',
        }

    clear_cache()
    print(f"🧠 AI Pro Generator: Analyzing {len(fixtures)} fixtures for {target_date}...")

    # Drop cup/knockout fixtures — results are too unpredictable for AI Pro
    from utils.fixture_fetcher import CUP_LEAGUE_IDS
    safe_fixtures = [
        f for f in fixtures
        if f.get('league') not in CUP_LEAGUE_IDS
    ]
    dropped_cups = len(fixtures) - len(safe_fixtures)
    if dropped_cups:
        print(f"🧠 AI Pro Generator: Dropped {dropped_cups} cup fixtures")

    # Generate all market options using the full AI + stat qualification pipeline
    all_options = generate_match_options(
        safe_fixtures, predictor, stats_calculator, af_stats=None, free_mode=False
    )

    print(f"🧠 AI Pro Generator: {len(all_options)} total options before filtering")

    # ── Filter: all markets, strict quality thresholds ────────────────────────
    qualified = [
        o for o in all_options
        if o['ai_prob'] >= AI_PRO_MIN_PROB.get(o['market'], 0.65)
        and o['composite_score'] >= AI_PRO_MIN_COMPOSITE.get(o['market'], 0.46)
        and o.get('edge', 0) >= AI_PRO_MIN_EDGE
        and o['odds'] >= AI_PRO_MIN_ODDS
        and o['odds'] <= AI_PRO_MAX_ODDS
    ]

    # Apply market penalties from recent performance tracking
    if market_penalties:
        for opt in qualified:
            mkt = opt['market']
            if mkt in market_penalties:
                opt['composite_score'] *= market_penalties[mkt]
        qualified = [
            o for o in qualified
            if o['composite_score'] >= AI_PRO_MIN_COMPOSITE.get(o['market'], 0.46)
        ]

    print(f"🧠 AI Pro Generator: {len(qualified)} options after filtering")

    if not qualified:
        return {
            'status': 'no_qualified',
            'date': target_date,
            'tips': [],
            'tip_count': 0,
            'combined_odds': 1.0,
            'message': 'No picks met AI Pro quality standards today.',
        }

    # Sort: composite_score × log(odds) × safe/risky market multiplier
    # Safe markets float to top; risky 1X2 sink to bottom.
    import math
    def _sort_score(o):
        base = o.get('composite_score', 0) * math.log(max(o['odds'], 1.01))
        boost = SAFE_MARKET_BOOST.get(o['market'], 1.0)
        penalty = RISKY_MARKET_PENALTY.get(o['market'], 1.0)
        return base * boost * penalty
    qualified.sort(key=_sort_score, reverse=True)

    # ── Select tips: one per match, dynamic count, market diversity ───────────
    selected = []
    combined_odds = 1.0
    used_matches = set()
    market_type_count = {}

    for opt in qualified:
        if len(selected) >= AI_PRO_MAX_PICKS:
            break

        # Cap combined odds
        potential = combined_odds * opt['odds']
        if potential > AI_PRO_MAX_COMBINED_ODDS and len(selected) >= 1:
            continue

        match_key = f"{opt['home_team']}_{opt['away_team']}"
        if match_key in used_matches:
            continue

        mkt = opt['market']
        if market_type_count.get(mkt, 0) >= AI_PRO_MAX_SAME_MARKET:
            continue

        selected.append(opt)
        combined_odds *= opt['odds']
        used_matches.add(match_key)
        market_type_count[mkt] = market_type_count.get(mkt, 0) + 1

    if not selected:
        return {
            'status': 'no_picks',
            'date': target_date,
            'tips': [],
            'tip_count': 0,
            'combined_odds': 1.0,
            'message': 'Could not build AI Pro slip from available picks.',
        }

    # ── Enforce combined odds 1.80–2.50 ──────────────────────────────────────
    # Cap: remove highest-odds pick until combined ≤ max
    while len(selected) > 1:
        combined_odds = 1.0
        for o in selected:
            combined_odds *= o['odds']
        if combined_odds <= AI_PRO_MAX_COMBINED_ODDS:
            break
        selected.sort(key=lambda x: x['odds'], reverse=True)
        selected.pop(0)

    # Recalculate combined_odds after cap enforcement
    combined_odds = 1.0
    for o in selected:
        combined_odds *= o['odds']

    # Floor: if combined < min, try adding more qualified options
    if combined_odds < AI_PRO_MIN_COMBINED_ODDS:
        used_matches_final = {f"{o['home_team']}_{o['away_team']}" for o in selected}
        for opt in qualified:
            match_key = f"{opt['home_team']}_{opt['away_team']}"
            if match_key in used_matches_final:
                continue
            test_combined = combined_odds * opt['odds']
            if test_combined <= AI_PRO_MAX_COMBINED_ODDS:
                selected.append(opt)
                combined_odds = test_combined
                used_matches_final.add(match_key)
                if combined_odds >= AI_PRO_MIN_COMBINED_ODDS:
                    break

    # Final recalculation
    combined_odds = 1.0
    for o in selected:
        combined_odds *= o['odds']

    # ── Format tips for Flutter app consumption ──────────────────────────────
    tips = []
    for opt in selected:
        market = opt['market']
        goal_line = _extract_goal_line(market)
        rule_type = MARKET_TO_RULE_TYPE.get(market, 'overGoals')
        advice = _build_advice_text(market, opt['home_team'], opt['away_team'])

        tips.append({
            'home_team': opt['home_team'],
            'away_team': opt['away_team'],
            'home_team_logo': opt.get('home_logo', ''),
            'away_team_logo': opt.get('away_logo', ''),
            'league_name': opt.get('league_name', ''),
            'league_logo': opt.get('league_logo', ''),
            'country': opt.get('league_name', ''),
            'kickoff': opt.get('commence_time', ''),
            'market': market,
            'rule_type': rule_type,
            'goal_line': goal_line,
            'advice_text': advice,
            'odds': opt['odds'],
            'ai_probability': round(opt['ai_prob'] * 100, 1),
            'edge': round(opt.get('edge', 0) * 100, 1),
            'confidence': opt.get('confidence', 'MEDIUM'),
            'status': 'Scheduled',
        })

    conf = slip_confidence(selected)

    print(f"🧠 AI Pro Generator: {len(tips)} tips, "
          f"combined odds {round(combined_odds, 2)}, confidence {conf}")

    # ── Write to Firestore ────────────────────────────────────────────────────
    db = get_firestore_client()
    doc_data = {
        'date': target_date,
        'tips': tips,
        'tip_count': len(tips),
        'combined_odds': round(combined_odds, 2),
        'confidence': conf,
        'generated_at': SERVER_TIMESTAMP,
    }
    db.collection('daily_ai_pro').document(target_date).set(doc_data)
    print(f"✅ AI Pro Generator: Wrote to Firestore daily_ai_pro/{target_date}")

    # ── Cleanup old docs (> 7 days) ──────────────────────────────────────────
    try:
        cutoff = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
        old_docs = (
            db.collection('daily_ai_pro')
            .where('date', '<', cutoff)
            .stream()
        )
        deleted = sum(1 for doc in old_docs if doc.reference.delete() or True)
        if deleted:
            print(f"🗑️ AI Pro Generator: Deleted {deleted} old docs (before {cutoff})")
    except Exception as e:
        print(f"⚠️ AI Pro Generator: Cleanup failed (non-fatal): {e}")

    return {
        'status': 'success',
        'date': target_date,
        'tips': tips,
        'tip_count': len(tips),
        'combined_odds': round(combined_odds, 2),
        'confidence': conf,
        'message': f'Generated {len(tips)} AI Pro tips for {target_date}',
    }

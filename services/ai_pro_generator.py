"""
AI Pro Tips generator — server-side replacement for client-side RapidAPI logic.

Strategy:
  - Uses the SAME XGBoost multi-market prediction pipeline as Rollover
  - Broader market selection than Rollover: Over 1.5/2.5, Home Win, Away Win,
    Double Chance (1X/X2)
  - Dynamic pick count: 1-3 tips based on what qualifies (quality over quantity)
  - STRICT odds limits: per-pick ≤1.50, combined 1.80-2.50
  - Real odds from SportMonks (not hardcoded estimates)
  - Market penalties applied to avoid repeating losing patterns
  - Stores results in Firestore daily_ai_pro/{date_str}
  - Response format designed for direct consumption by Flutter app

This makes AI Pro fully server-controlled — no app update needed for
future threshold/strategy changes.
"""
from datetime import datetime, timedelta
from firebase_config import get_firestore_client
from google.cloud.firestore_v1 import SERVER_TIMESTAMP


# Markets allowed for AI Pro — broader than Rollover but still curated
AI_PRO_ALLOWED_MARKETS = {
    'Over 1.5 Goals',
    'Over 2.5 Goals',
    'Home Win',
    'Away Win',
    'Double Chance (1X)',
    'Double Chance (X2)',
}

# Minimum AI probability per market — balanced: strict enough to win, loose enough to find picks
AI_PRO_MIN_PROB = {
    'Over 1.5 Goals':     0.72,
    'Over 2.5 Goals':     0.68,
    'Home Win':           0.62,
    'Away Win':           0.62,
    'Double Chance (1X)': 0.74,
    'Double Chance (X2)': 0.72,
}

# Minimum composite score per market
AI_PRO_MIN_COMPOSITE = {
    'Over 1.5 Goals':     0.48,
    'Over 2.5 Goals':     0.46,
    'Home Win':           0.46,
    'Away Win':           0.46,
    'Double Chance (1X)': 0.49,
    'Double Chance (X2)': 0.48,
}

# Minimum edge required (model_prob - implied_prob)
AI_PRO_MIN_EDGE = 0.05

# Odds limits per pick — allows up to 1.50 for slightly more variety
AI_PRO_MIN_ODDS = 1.10
AI_PRO_MAX_ODDS = 1.50

# Max picks per day — dynamic 1-3 based on what qualifies
AI_PRO_MAX_PICKS = 3

# Combined odds range — user wants "2 odds or less" so cap at 2.50
AI_PRO_MIN_COMBINED_ODDS = 1.80
AI_PRO_MAX_COMBINED_ODDS = 2.50

# Max 1 pick of the same market type (force full diversity)
AI_PRO_MAX_SAME_MARKET = 1

# Map backend market names → Flutter app rule types
MARKET_TO_RULE_TYPE = {
    'Over 1.5 Goals':     'overGoals',
    'Over 2.5 Goals':     'overGoals',
    'Home Win':           'homeWin',
    'Away Win':           'awayWin',
    'Double Chance (1X)': 'doubleChance',
    'Double Chance (X2)': 'doubleChance',
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

    # Generate all market options using the full AI + stat qualification pipeline
    all_options = generate_match_options(
        fixtures, predictor, stats_calculator, af_stats=None, free_mode=False
    )

    print(f"🧠 AI Pro Generator: {len(all_options)} total options before filtering")

    # ── Filter: only allowed markets with strict thresholds ───────────────────
    qualified = [
        o for o in all_options
        if o['market'] in AI_PRO_ALLOWED_MARKETS
        and o['ai_prob'] >= AI_PRO_MIN_PROB.get(o['market'], 0.65)
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

    # Sort by composite_score descending
    qualified.sort(key=lambda x: x.get('composite_score', 0), reverse=True)

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

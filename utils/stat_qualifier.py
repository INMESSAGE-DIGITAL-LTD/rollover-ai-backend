"""
Statistical Qualification Engine + Edge Calculator.

Implements the 3-layer prediction architecture:
  Layer 2: Per-market qualification rules
  Layer 3: Feature engineering
  Layer 4: Edge calculation (model_prob vs implied_prob)

Only picks that pass ALL checks proceed to the slip builder.
"""
import math

# ═══════════════════════════════════════════════════════════
# Per-Market Safety Rules: (min_odds, sweet_max, absolute_max)
# No single pick exceeds 1.57
# ═══════════════════════════════════════════════════════════
SAFETY_RULES = {
    'Over 2.5 Goals':   (1.20, 1.45, 1.50),
    'Over 1.5 Goals':   (1.15, 1.40, 1.50),
    'Over 0.5 Goals':   (1.05, 1.20, 1.25),
    'Home Win':         (1.15, 1.45, 1.57),
    'Away Win':         (1.15, 1.45, 1.57),
    'Both Teams to Score': (1.30, 1.45, 1.50),
    'Home or Draw':     (1.10, 1.40, 1.45),
    'Draw or Away':     (1.10, 1.40, 1.45),
    'Home or Away':     (1.05, 1.25, 1.30),
    'Home to Score':    (1.10, 1.35, 1.40),
    'Away to Score':    (1.15, 1.45, 1.50),
    'Home Over 0.5 Goals': (1.10, 1.35, 1.40),
    'Away Over 0.5 Goals': (1.15, 1.45, 1.50),
    '1H Over 0.5':      (1.20, 1.50, 1.57),
    '2H Over 0.5':      (1.20, 1.50, 1.57),
}

# Default rule for markets not listed above
DEFAULT_RULE = (1.10, 1.50, 1.57)


def passes_odds_safety(market_label, odds):
    """Check if odds fall within the safety range for this market."""
    rule = SAFETY_RULES.get(market_label, DEFAULT_RULE)
    min_odds, _, abs_max = rule
    return min_odds <= odds <= abs_max


def is_in_sweet_spot(market_label, odds):
    """Check if odds are in the preferred sweet spot."""
    rule = SAFETY_RULES.get(market_label, DEFAULT_RULE)
    return rule[0] <= odds <= rule[1]


def qualify_and_score(market_label, odds, ai_prob, home_stats, away_stats, h2h):
    """
    Run statistical qualification + edge calculation for a single pick.

    Returns:
        dict with 'edge', 'ai_prob', 'stability', 'composite_score', 'qualified'
        or None if disqualified.
    """
    implied_prob = 1.0 / odds
    has_stats = home_stats is not None and away_stats is not None

    # Adjust AI probability using statistical qualification
    adjusted_prob = _qualify_by_market(
        market_label, ai_prob, implied_prob,
        home_stats, away_stats, h2h,
    )

    edge = adjusted_prob - implied_prob

    # Edge gate: relaxed thresholds per market safety level
    lab = market_label.lower()
    if 'double chance' in lab or 'or' in lab or 'home or' in lab or 'draw or' in lab:
        min_edge = 0.02 if has_stats else 0.01  # DC is inherently safe
    elif 'over 0.5' in lab:
        min_edge = 0.02 if has_stats else 0.01  # Very high base rate
    else:
        min_edge = 0.03 if has_stats else 0.02  # Standard markets

    if edge < min_edge:
        return None

    # Stability score
    stability = _compute_stability(market_label, home_stats, away_stats)

    # Composite score for risk governor sorting
    composite = edge * 0.40 + adjusted_prob * 0.35 + stability * 0.25

    return {
        'edge': edge,
        'ai_prob': adjusted_prob,
        'stability': stability,
        'composite_score': composite,
        'qualified': True,
    }


def confidence_label(edge):
    """Convert edge to confidence label."""
    if edge >= 0.08:
        return 'HIGH'
    if edge >= 0.04:
        return 'MEDIUM'
    return 'LOW'


# ═══════════════════════════════════════════════════════════
# Per-Market Qualification Rules
# ═══════════════════════════════════════════════════════════

def _qualify_by_market(label, ai_prob, implied_prob, home, away, h2h):
    """Adjust AI probability using statistical checks per market."""
    lab = label.lower()

    if 'over 2.5' in lab:
        return _qualify_over25(ai_prob, implied_prob, home, away, h2h)
    elif 'over 1.5' in lab:
        return _qualify_over15(ai_prob, implied_prob, home, away, h2h)
    elif 'over 0.5' in lab and ('home' in lab or 'away' in lab or '1h' in lab or '2h' in lab):
        return _qualify_team_goals(ai_prob, implied_prob, home, away)
    elif 'over 0.5' in lab:
        return _qualify_over05(ai_prob, implied_prob, home, away)
    elif lab == 'home win':
        return _qualify_home_win(ai_prob, implied_prob, home, away, h2h)
    elif lab == 'away win':
        return _qualify_away_win(ai_prob, implied_prob, home, away, h2h)
    elif 'both teams' in lab:
        return _qualify_btts(ai_prob, implied_prob, home, away, h2h)
    elif 'home or draw' in lab or 'draw or away' in lab or 'home or away' in lab:
        return _qualify_double_chance(label, ai_prob, implied_prob, home, away)
    else:
        # Generic: small boost if AI says so
        if home is None or away is None:
            return ai_prob
        return min(0.93, ai_prob * 1.02)


def _qualify_over25(ai_prob, implied, home, away, h2h):
    if home is None or away is None:
        return implied + 0.04

    checks, passed = 0, 0

    checks += 1
    if home['avg_goals_scored'] >= 1.4 and away['avg_goals_scored'] >= 1.4:
        passed += 1

    checks += 1
    combined = home['avg_goals_scored'] + away['avg_goals_scored']
    if combined >= 2.8:
        passed += 1

    checks += 1
    avg_o25 = (home['over25_rate'] + away['over25_rate']) / 2
    if avg_o25 >= 0.70:
        passed += 1

    if h2h and h2h['total_matches'] >= 3:
        checks += 1
        if h2h['over25_count'] >= 3:
            passed += 1

    if passed < checks:
        # Don't completely reject — reduce probability instead of killing it
        penalty = max(0.92, 1.0 - (checks - passed) * 0.03)
        return implied * penalty

    # Weighted: stats + AI model
    stats_prob = min(0.92, avg_o25 * 0.25 + combined / 5.0 * 0.20 + 0.15)
    return min(0.92, stats_prob * 0.5 + ai_prob * 0.5)


def _qualify_over15(ai_prob, implied, home, away, h2h):
    if home is None or away is None:
        return implied + 0.04

    checks, passed = 0, 0

    checks += 1
    if home['avg_goals_scored'] >= 1.2:
        passed += 1

    checks += 1
    if away['avg_goals_scored'] >= 1.0:
        passed += 1

    checks += 1
    combined = home['avg_goals_scored'] + away['avg_goals_scored']
    if combined >= 2.4:
        passed += 1

    checks += 1
    avg_o15 = (home['over15_rate'] + away['over15_rate']) / 2
    if avg_o15 >= 0.75:
        passed += 1

    if h2h and h2h['total_matches'] >= 3:
        checks += 1
        h2h_o15 = h2h['over15_count'] / h2h['total_matches']
        if h2h_o15 >= 0.60:
            passed += 1

    if passed < checks:
        penalty = max(0.93, 1.0 - (checks - passed) * 0.03)
        return implied * penalty

    stats_prob = min(0.93, avg_o15 * 0.30 + combined / 4.0 * 0.20 + 0.15)
    return min(0.93, stats_prob * 0.5 + ai_prob * 0.5)


def _qualify_over05(ai_prob, implied, home, away):
    """Over 0.5 — very high base rate, just sanity check."""
    if home is None or away is None:
        return ai_prob
    combined = home['avg_goals_scored'] + away['avg_goals_scored']
    if combined < 1.5:
        return implied * 0.96
    return min(0.95, ai_prob * 1.02)


def _qualify_team_goals(ai_prob, implied, home, away):
    """Home/Away to score, 1H/2H goals."""
    if home is None or away is None:
        return implied + 0.03
    if home['scored_in_rate'] >= 0.70 or away['scored_in_rate'] >= 0.70:
        return min(0.92, ai_prob * 1.03)
    return implied * 0.96


def _qualify_home_win(ai_prob, implied, home, away, h2h):
    if home is None or away is None:
        return implied + 0.03

    checks, passed = 0, 0

    checks += 1
    if home['home_win_rate'] >= 0.60:
        passed += 1

    checks += 1
    if away['away_loss_rate'] >= 0.50:
        passed += 1

    checks += 1
    if home['home_avg_scored'] >= 1.4:
        passed += 1

    checks += 1
    if away['away_avg_conceded'] >= 1.2:
        passed += 1

    if h2h and h2h['total_matches'] >= 3:
        checks += 1
        if h2h['team1_wins'] > h2h['team2_wins']:
            passed += 1

    if passed < checks:
        return implied * 0.96

    stats_prob = min(0.92, home['home_win_rate'] * 0.35 + away['away_loss_rate'] * 0.25 + 0.20)
    return min(0.92, stats_prob * 0.5 + ai_prob * 0.5)


def _qualify_away_win(ai_prob, implied, home, away, h2h):
    if home is None or away is None:
        return implied + 0.03

    if home['home_win_rate'] >= 0.60:
        return implied * 0.95
    if away['avg_goals_scored'] < 1.3:
        return implied * 0.95

    checks, passed = 0, 0
    checks += 1
    if home['home_win_rate'] < 0.50:
        passed += 1
    checks += 1
    if away['away_avg_scored'] >= 1.3:
        passed += 1

    if h2h and h2h['total_matches'] >= 3:
        checks += 1
        if h2h['team2_wins'] >= h2h['team1_wins']:
            passed += 1

    if passed < checks:
        return implied * 0.96

    stats_prob = min(0.90, (1.0 - home['home_win_rate']) * 0.35 + away['away_avg_scored'] / 3.0 * 0.25 + 0.15)
    return min(0.90, stats_prob * 0.5 + ai_prob * 0.5)


def _qualify_btts(ai_prob, implied, home, away, h2h):
    if home is None or away is None:
        return implied + 0.03

    checks, passed = 0, 0

    checks += 1
    if home['btts_rate'] >= 0.65:
        passed += 1

    checks += 1
    if away['btts_rate'] >= 0.65:
        passed += 1

    checks += 1
    if home['scored_in_rate'] >= 0.70 and away['scored_in_rate'] >= 0.70:
        passed += 1

    if h2h and h2h['total_matches'] >= 3:
        checks += 1
        if h2h['btts_count'] / h2h['total_matches'] >= 0.55:
            passed += 1

    if passed < checks:
        return implied * 0.96

    avg_btts = (home['btts_rate'] + away['btts_rate']) / 2
    stats_prob = min(0.91, avg_btts * 0.30 + home['scored_in_rate'] * 0.15 + away['scored_in_rate'] * 0.15 + 0.10)
    return min(0.91, stats_prob * 0.5 + ai_prob * 0.5)


def _qualify_double_chance(label, ai_prob, implied, home, away):
    if home is None or away is None:
        return implied + 0.04

    lab = label.lower()
    if 'home or draw' in lab:
        if home['home_win_rate'] < 0.30:
            return implied * 0.97
        return min(0.95, home['home_win_rate'] * 0.30 + (1.0 - away['away_loss_rate']) * 0.15 + implied * 0.25 + ai_prob * 0.20 + 0.10)
    elif 'draw or away' in lab:
        if away['away_loss_rate'] > 0.80:
            return implied * 0.97
        return min(0.95, (1.0 - away['away_loss_rate']) * 0.25 + implied * 0.30 + ai_prob * 0.25 + 0.10)
    else:
        # Home or Away (12) — very safe, only draw loses
        draw_unlikely = (home['home_win_rate'] >= 0.40 or away['away_loss_rate'] >= 0.40)
        if draw_unlikely:
            return min(0.96, implied + 0.06)
        return min(0.94, implied + 0.04)


# ═══════════════════════════════════════════════════════════
# Stability Scoring
# ═══════════════════════════════════════════════════════════

def _compute_stability(market_label, home, away):
    """Score how stable/consistent this prediction is (0-1)."""
    if home is None or away is None:
        return 0.50

    lab = market_label.lower()

    if 'over' in lab and 'goal' in lab:
        consistency = (home['scored_in_rate'] + away['scored_in_rate']) / 2.0
        volume = min(1.0, (home['avg_goals_scored'] + away['avg_goals_scored']) / 4.0)
        return consistency * 0.6 + volume * 0.4

    if lab in ('home win', 'away win'):
        team = home if lab == 'home win' else away
        return (
            team['home_win_rate'] * 0.5 +
            team['scored_in_rate'] * 0.3 +
            max(0, 1.0 - team['avg_goals_conceded'] / 3.0) * 0.2
        )

    if 'both teams' in lab:
        return (home['btts_rate'] + away['btts_rate']) / 2.0 * 0.5 + \
               (home['scored_in_rate'] + away['scored_in_rate']) / 2.0 * 0.5

    if 'double chance' in lab or 'or' in lab:
        return 0.65  # DC is inherently more stable

    return 0.50

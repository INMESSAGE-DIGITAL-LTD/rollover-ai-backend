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
# Single pick max 1.60 (relaxed from 1.57 for more options)
# ═══════════════════════════════════════════════════════════
SAFETY_RULES = {
    'Over 2.5 Goals':       (1.20, 1.50, 1.60),
    'Over 1.5 Goals':       (1.10, 1.45, 1.57),
    'Over 0.5 Goals':       (1.01, 1.20, 1.25),
    'Over 3.5 Goals':       (1.50, 1.60, 1.60),
    'Under 4.5 Goals':      (1.10, 1.40, 1.57),
    'Under 3.5 Goals':      (1.20, 1.55, 1.60),
    'Home Win':             (1.15, 1.50, 1.60),
    'Away Win':             (1.15, 1.50, 1.60),
    'Both Teams to Score':  (1.25, 1.50, 1.57),
    'Double Chance (1X)':   (1.05, 1.45, 1.50),
    'Double Chance (X2)':   (1.05, 1.45, 1.50),
    'Double Chance (12)':   (1.01, 1.30, 1.40),
    'Home or Draw':         (1.05, 1.45, 1.50),
    'Draw or Away':         (1.05, 1.45, 1.50),
    'Home or Away':         (1.01, 1.30, 1.40),
    'Home to Score':        (1.05, 1.40, 1.50),
    'Away to Score':        (1.10, 1.50, 1.57),
    'Home Over 0.5 Goals':  (1.05, 1.40, 1.50),
    'Away Over 0.5 Goals':  (1.10, 1.50, 1.57),
    '1st Half Over 0.5':    (1.15, 1.55, 1.60),
    '2nd Half Over 0.5':    (1.15, 1.55, 1.60),
}

# Default rule for markets not listed above
DEFAULT_RULE = (1.10, 1.55, 1.60)


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
    elif 'over 1.5' in lab or 'over 2.5' in lab:
        min_edge = 0.02 if has_stats else 0.02  # Core markets — keep accessible
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
    elif 'over 0.5' in lab and ('home' in lab or 'away' in lab or 'half' in lab):
        return _qualify_team_goals(ai_prob, implied_prob, home, away)
    elif 'over 0.5' in lab:
        return _qualify_over05(ai_prob, implied_prob, home, away)
    elif lab == 'home win':
        return _qualify_home_win(ai_prob, implied_prob, home, away, h2h)
    elif lab == 'away win':
        return _qualify_away_win(ai_prob, implied_prob, home, away, h2h)
    elif 'under 4.5' in lab or 'under 3.5' in lab:
        return _qualify_under(ai_prob, implied_prob, home, away)
    elif 'both teams' in lab:
        return _qualify_btts(ai_prob, implied_prob, home, away, h2h)
    elif 'double chance' in lab or 'home or draw' in lab or 'draw or away' in lab or 'home or away' in lab:
        return _qualify_double_chance(label, ai_prob, implied_prob, home, away)
    else:
        # Generic: small boost if AI says so
        if home is None or away is None:
            return ai_prob
        return min(0.93, ai_prob * 1.02)


def _qualify_over25(ai_prob, implied, home, away, h2h):
    if home is None or away is None:
        return max(ai_prob, implied + 0.03)

    combined = home['avg_goals_scored'] + away['avg_goals_scored']
    avg_o25 = (home['over25_rate'] + away['over25_rate']) / 2

    # Build stats-based probability
    stats_prob = avg_o25 * 0.30 + min(1.0, combined / 4.5) * 0.25 + 0.20
    if h2h and h2h['total_matches'] >= 3:
        h2h_rate = h2h['over25_count'] / h2h['total_matches']
        stats_prob = stats_prob * 0.75 + h2h_rate * 0.25

    # Blend AI model + stats (trust AI more)
    blended = ai_prob * 0.55 + stats_prob * 0.30 + implied * 0.15
    return min(0.93, max(blended, implied + 0.02))


def _qualify_over15(ai_prob, implied, home, away, h2h):
    if home is None or away is None:
        return max(ai_prob, implied + 0.03)

    combined = home['avg_goals_scored'] + away['avg_goals_scored']
    avg_o15 = (home['over15_rate'] + away['over15_rate']) / 2

    # Build stats-based probability
    stats_prob = avg_o15 * 0.30 + min(1.0, combined / 3.5) * 0.25 + 0.25
    if h2h and h2h['total_matches'] >= 3:
        h2h_o15 = h2h['over15_count'] / h2h['total_matches']
        stats_prob = stats_prob * 0.75 + h2h_o15 * 0.25

    # Blend AI model + stats (trust AI more)
    blended = ai_prob * 0.55 + stats_prob * 0.30 + implied * 0.15
    return min(0.95, max(blended, implied + 0.02))


def _qualify_over05(ai_prob, implied, home, away):
    """Over 0.5 — very high base rate, just sanity check."""
    if home is None or away is None:
        return max(ai_prob, implied + 0.02)
    combined = home['avg_goals_scored'] + away['avg_goals_scored']
    if combined < 1.0:
        return implied * 0.98
    return min(0.97, max(ai_prob * 1.02, implied + 0.02))


def _qualify_team_goals(ai_prob, implied, home, away):
    """Home/Away to score, 1H/2H goals."""
    if home is None or away is None:
        return max(ai_prob, implied + 0.03)
    score_rate = max(home['scored_in_rate'], away['scored_in_rate'])
    blended = ai_prob * 0.55 + score_rate * 0.25 + implied * 0.20
    return min(0.93, max(blended, implied + 0.02))


def _qualify_under(ai_prob, implied, home, away):
    """Under 3.5/4.5 — safe when teams don't score heavily."""
    if home is None or away is None:
        return max(ai_prob, implied + 0.03)

    combined = home['avg_goals_scored'] + away['avg_goals_scored']
    # Under 4.5 is very likely if combined avg < 3.5
    # Under 3.5 is likely if combined avg < 2.8
    defense_factor = 1.0 - min(1.0, combined / 5.0)
    clean_factor = (home.get('clean_sheet_rate', 0.3) + away.get('clean_sheet_rate', 0.3)) / 2.0

    stats_prob = defense_factor * 0.40 + clean_factor * 0.20 + 0.30
    blended = ai_prob * 0.45 + stats_prob * 0.30 + implied * 0.25
    return min(0.95, max(blended, implied + 0.02))


def _qualify_home_win(ai_prob, implied, home, away, h2h):
    if home is None or away is None:
        return max(ai_prob, implied + 0.03)

    stats_prob = home['home_win_rate'] * 0.35 + (1.0 - away.get('away_loss_rate', 0.5)) * 0.10 + \
                 min(1.0, home['home_avg_scored'] / 2.5) * 0.20 + 0.15
    if h2h and h2h['total_matches'] >= 3 and h2h['team1_wins'] > h2h['team2_wins']:
        stats_prob += 0.05

    blended = ai_prob * 0.50 + stats_prob * 0.30 + implied * 0.20
    return min(0.93, max(blended, implied + 0.02))


def _qualify_away_win(ai_prob, implied, home, away, h2h):
    if home is None or away is None:
        return max(ai_prob, implied + 0.03)

    # Away wins are inherently riskier
    if home['home_win_rate'] >= 0.70:
        return implied * 0.97

    stats_prob = (1.0 - home['home_win_rate']) * 0.25 + \
                 min(1.0, away['away_avg_scored'] / 2.0) * 0.25 + 0.20
    if h2h and h2h['total_matches'] >= 3 and h2h['team2_wins'] >= h2h['team1_wins']:
        stats_prob += 0.05

    blended = ai_prob * 0.50 + stats_prob * 0.30 + implied * 0.20
    return min(0.90, max(blended, implied + 0.02))


def _qualify_btts(ai_prob, implied, home, away, h2h):
    if home is None or away is None:
        return max(ai_prob, implied + 0.03)

    avg_btts = (home['btts_rate'] + away['btts_rate']) / 2
    score_rate = (home['scored_in_rate'] + away['scored_in_rate']) / 2

    stats_prob = avg_btts * 0.30 + score_rate * 0.25 + 0.20
    if h2h and h2h['total_matches'] >= 3:
        h2h_btts = h2h['btts_count'] / h2h['total_matches']
        stats_prob = stats_prob * 0.75 + h2h_btts * 0.25

    blended = ai_prob * 0.50 + stats_prob * 0.30 + implied * 0.20
    return min(0.92, max(blended, implied + 0.02))


def _qualify_double_chance(label, ai_prob, implied, home, away):
    if home is None or away is None:
        return max(ai_prob, implied + 0.04)

    lab = label.lower()
    if '1x' in lab or 'home or draw' in lab:
        if home['home_win_rate'] < 0.30:
            return implied * 0.97
        return min(0.95, home['home_win_rate'] * 0.30 + (1.0 - away.get('away_loss_rate', 0.5)) * 0.15 + implied * 0.25 + ai_prob * 0.20 + 0.10)
    elif 'x2' in lab or 'draw or away' in lab:
        if away.get('away_loss_rate', 0.5) > 0.80:
            return implied * 0.97
        return min(0.95, (1.0 - away.get('away_loss_rate', 0.5)) * 0.25 + implied * 0.30 + ai_prob * 0.25 + 0.10)
    else:
        # Double Chance (12) — only draw loses, very safe
        draw_unlikely = (home['home_win_rate'] >= 0.40 or away.get('away_loss_rate', 0.5) >= 0.40)
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

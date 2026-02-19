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

# ═══════════════════════════════════════════════════════════
# Free-mode Safety Rules: higher abs_max (up to 3.50) for riskier picks
# Used by /api/free-picks to produce higher-odds teaser picks
# ═══════════════════════════════════════════════════════════
FREE_SAFETY_RULES = {
    'Over 2.5 Goals':       (1.40, 2.50, 3.50),
    'Over 1.5 Goals':       (1.20, 1.80, 2.50),
    'Over 0.5 Goals':       (1.01, 1.30, 1.50),
    'Over 3.5 Goals':       (1.60, 2.50, 3.50),
    'Under 4.5 Goals':      (1.10, 1.50, 2.00),
    'Under 3.5 Goals':      (1.20, 1.80, 2.50),
    'Home Win':             (1.30, 2.00, 3.00),
    'Away Win':             (1.30, 2.00, 3.00),
    'Both Teams to Score':  (1.40, 2.00, 3.00),
    'Double Chance (1X)':   (1.05, 1.60, 2.00),
    'Double Chance (X2)':   (1.05, 1.60, 2.00),
    'Double Chance (12)':   (1.01, 1.40, 1.80),
    'Home or Draw':         (1.05, 1.60, 2.00),
    'Draw or Away':         (1.05, 1.60, 2.00),
    'Home or Away':         (1.01, 1.40, 1.80),
    'Home to Score':        (1.10, 1.60, 2.00),
    'Away to Score':        (1.20, 1.80, 2.50),
    'Home Over 0.5 Goals':  (1.10, 1.60, 2.00),
    'Away Over 0.5 Goals':  (1.20, 1.80, 2.50),
    '1st Half Over 0.5':    (1.20, 1.80, 2.50),
    '2nd Half Over 0.5':    (1.20, 1.80, 2.50),
}
FREE_DEFAULT_RULE = (1.20, 2.00, 3.00)


def passes_odds_safety(market_label, odds, free_mode=False):
    """Check if odds fall within the safety range for this market."""
    if free_mode:
        rule = FREE_SAFETY_RULES.get(market_label, FREE_DEFAULT_RULE)
    else:
        rule = SAFETY_RULES.get(market_label, DEFAULT_RULE)
    min_odds, _, abs_max = rule
    return min_odds <= odds <= abs_max


def is_in_sweet_spot(market_label, odds, free_mode=False):
    """Check if odds are in the preferred sweet spot."""
    if free_mode:
        rule = FREE_SAFETY_RULES.get(market_label, FREE_DEFAULT_RULE)
    else:
        rule = SAFETY_RULES.get(market_label, DEFAULT_RULE)
    return rule[0] <= odds <= rule[1]


def qualify_and_score(market_label, odds, ai_prob, home_stats, away_stats, h2h, standings=None):
    """
    Run statistical qualification + edge calculation for a single pick.

    Args:
        standings: dict with 'home' and 'away' team standing info (optional).

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

    # Apply standings-based adjustment
    if standings:
        adjusted_prob = _apply_standings_adjustment(
            market_label, adjusted_prob, standings)

    edge = adjusted_prob - implied_prob

    # Edge gate: calibrated thresholds per market risk level
    lab = market_label.lower()
    if 'double chance' in lab or 'home or' in lab or 'draw or' in lab:
        min_edge = 0.02 if has_stats else 0.01
    elif 'over 0.5' in lab:
        min_edge = 0.02 if has_stats else 0.01
    elif 'over 1.5' in lab:
        min_edge = 0.03 if has_stats else 0.02
    elif 'over 2.5' in lab:
        min_edge = 0.04 if has_stats else 0.03  # Higher bar for riskier market
    elif 'btts' in lab or 'both teams' in lab:
        min_edge = 0.04 if has_stats else 0.03
    elif lab in ('home win', 'away win'):
        min_edge = 0.05 if has_stats else 0.04  # Result markets need higher edge
    else:
        min_edge = 0.03 if has_stats else 0.02

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


# ═══════════════════════════════════════════════════════════
# Standings-Aware Adjustments
# ═══════════════════════════════════════════════════════════

def _apply_standings_adjustment(market_label, prob, standings):
    """
    Adjust probability based on league table position and motivation.

    Key insights:
    - Title contenders playing relegation teams: draws happen more than expected
      (pressure on top team + desperation defense from bottom team)
    - Home team fighting for title: Home Win gets a boost
    - Relegation team at home: they fight harder → upset risk increases
    - DC(12) in title vs relegation: penalty because draw risk is real
    - Over 1.5 goals in high-stakes games: slight boost (both teams motivated)
    """
    home_s = standings.get('home')
    away_s = standings.get('away')
    if not home_s or not away_s:
        return prob

    lab = market_label.lower()
    home_pos = home_s.get('position', 10)
    away_pos = away_s.get('position', 10)
    total = home_s.get('total_teams', 20)
    home_title = home_s.get('title_race', False)
    away_title = away_s.get('title_race', False)
    home_releg = home_s.get('relegation_battle', False)
    away_releg = away_s.get('relegation_battle', False)
    home_leader = home_s.get('is_leader', False)
    away_leader = away_s.get('is_leader', False)
    home_gap = home_s.get('gap_to_second', 99)

    # Position gap: large gap = mismatch (top vs bottom)
    pos_gap = abs(home_pos - away_pos)
    is_mismatch = pos_gap >= total * 0.5  # e.g. 1st vs 15th in 20-team league

    # ── Double Chance (12) — only draw loses ──
    if 'double chance' in lab and '12' in lab:
        # Title team vs relegation team: draw risk is HIGHER than stats suggest
        # Top teams under pressure drop points to low-block defenses
        if is_mismatch and (home_title or away_title):
            # Wolves vs Arsenal scenario: Arsenal at the top, Wolves near bottom
            # The bottom team parks the bus → draw risk ~15-20% even if DC(12) seems safe
            prob *= 0.94  # 6% penalty — nudges model toward safer markets
        if home_releg and away_title:
            # Relegation team at home vs title contender: desperate defense
            prob *= 0.93
        if away_releg and home_title:
            prob *= 0.95  # Slightly less risky when top team is at home
        return min(0.96, prob)

    # ── Double Chance (1X) — home win or draw ──
    if ('1x' in lab or 'home or draw' in lab):
        if home_title or home_leader:
            prob = min(0.95, prob * 1.03)  # Title team at home rarely loses
        if home_releg and away_title:
            prob = min(0.93, prob * 1.02)  # Relegation fight at home → they won't lose easily
        return prob

    # ── Double Chance (X2) — away win or draw ──
    if ('x2' in lab or 'draw or away' in lab):
        if away_title or away_leader:
            prob = min(0.95, prob * 1.03)  # Title contender away rarely loses outright
        return prob

    # ── Home Win ──
    if lab == 'home win':
        if home_title and away_releg:
            # Title team at home vs relegation: strong motivation boost
            prob = min(0.93, prob * 1.06)
        elif home_leader and home_gap <= 3:
            # Leader with small gap: MUST win at home
            prob = min(0.93, prob * 1.05)
        elif home_releg:
            # Relegation team at home: fights harder
            prob = min(0.90, prob * 1.03)
        return prob

    # ── Away Win ──
    if lab == 'away win':
        if away_title and home_releg:
            # Strong away team vs weak home team, but relegation teams fight at home
            prob *= 0.97  # Small penalty — upsets happen
        elif away_leader and away_s.get('gap_to_second', 99) <= 3:
            # Leader away, tight race: motivated
            prob = min(0.90, prob * 1.04)
        return prob

    # ── Over 1.5 Goals ──
    if 'over 1.5' in lab:
        if is_mismatch and (home_title or away_title):
            # High-stakes games between mismatched teams usually produce goals
            # Top team attacks, bottom team gets chances on counter
            prob = min(0.95, prob * 1.03)
        return prob

    # ── Over 2.5 Goals ──
    if 'over 2.5' in lab:
        if is_mismatch and (home_title or away_title):
            prob = min(0.93, prob * 1.02)
        # Relegation vs relegation: tight, defensive
        if home_releg and away_releg:
            prob *= 0.96
        return prob

    # ── Home/Away to Score ──
    if 'home to score' in lab or 'home over 0.5' in lab:
        if home_title:
            prob = min(0.95, prob * 1.02)
        return prob
    if 'away to score' in lab or 'away over 0.5' in lab:
        if away_title:
            prob = min(0.95, prob * 1.02)
        return prob

    return prob

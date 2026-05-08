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
    'Under 2.5 Goals':      (1.30, 1.60, 1.70),
    'Under 1.5 Goals':      (1.50, 1.70, 1.80),
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
    'Draw':                 (1.15, 1.50, 1.60),
    'BTTS No':              (1.10, 1.50, 1.60),
    '1st Half Under 0.5':   (1.15, 1.55, 1.60),
    '2nd Half Under 0.5':   (1.15, 1.55, 1.60),
    'Home Over 1.5 Goals':  (1.10, 1.50, 1.60),
    'Away Over 1.5 Goals':  (1.10, 1.50, 1.60),
    'Home Over 2.5 Goals':  (1.50, 1.60, 1.60),
    'Away Over 2.5 Goals':  (1.50, 1.60, 1.60),
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
    'Under 2.5 Goals':      (1.30, 2.00, 2.80),
    'Under 1.5 Goals':      (1.60, 2.20, 3.00),
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
    'Draw':                 (2.50, 3.50, 4.50),
    'BTTS No':              (1.40, 1.80, 2.50),
    '1st Half Under 0.5':   (1.50, 2.00, 2.50),
    '2nd Half Under 0.5':   (1.50, 2.00, 2.50),
    'Home Over 1.5 Goals':  (1.40, 2.00, 3.00),
    'Away Over 1.5 Goals':  (1.50, 2.20, 3.00),
    'Home Over 2.5 Goals':  (1.80, 2.50, 3.50),
    'Away Over 2.5 Goals':  (2.00, 2.80, 4.00),
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

    # Edge gate: raised thresholds to overcome bookmaker vig (~5-8%)
    # Without stats we require even MORE edge since we're less certain.
    lab = market_label.lower()
    if 'double chance' in lab or 'home or' in lab or 'draw or' in lab:
        min_edge = 0.04 if has_stats else 0.03
    elif 'home over 0.5' in lab or 'away over 0.5' in lab:
        min_edge = 0.05 if has_stats else 0.04
    elif 'over 0.5' in lab:
        min_edge = 0.04 if has_stats else 0.03
    elif 'under 3.5' in lab or 'under 4.5' in lab:
        min_edge = 0.04 if has_stats else 0.03
    elif 'over 1.5' in lab:
        min_edge = 0.05 if has_stats else 0.04
    elif 'over 2.5' in lab:
        min_edge = 0.06 if has_stats else 0.05
    elif 'btts' in lab or 'both teams' in lab:
        min_edge = 0.06 if has_stats else 0.05
    elif lab in ('home win', 'away win'):
        min_edge = 0.07 if has_stats else 0.06  # Result markets need highest edge
    elif lab == 'draw':
        min_edge = 0.08 if has_stats else 0.07  # Draw is very risky
    elif 'under 0.5' in lab:
        min_edge = 0.05 if has_stats else 0.04
    else:
        min_edge = 0.05 if has_stats else 0.04

    if edge < min_edge:
        return None

    # Stability score
    stability = _compute_stability(market_label, home_stats, away_stats)

    # Composite score for risk governor sorting
    # Stability (stats-derived) weighted highest — trust real data over model
    composite = edge * 0.30 + adjusted_prob * 0.30 + stability * 0.40

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
    elif 'under 0.5' in lab and 'half' in lab:
        return _qualify_under(ai_prob, implied_prob, home, away)
    elif 'over 0.5' in lab and ('home' in lab or 'away' in lab or 'half' in lab):
        return _qualify_team_goals(label, ai_prob, implied_prob, home, away)
    elif 'over 0.5' in lab:
        return _qualify_over05(ai_prob, implied_prob, home, away)
    elif lab == 'home win':
        return _qualify_home_win(ai_prob, implied_prob, home, away, h2h)
    elif lab == 'away win':
        return _qualify_away_win(ai_prob, implied_prob, home, away, h2h)
    elif lab == 'draw':
        return _qualify_draw(ai_prob, implied_prob, home, away, h2h)
    elif 'under 2.5' in lab or 'under 1.5' in lab:
        return _qualify_under_tight(ai_prob, implied_prob, home, away, h2h)
    elif 'under 4.5' in lab or 'under 3.5' in lab:
        return _qualify_under(ai_prob, implied_prob, home, away)
    elif lab == 'btts no':
        return _qualify_btts_no(ai_prob, implied_prob, home, away, h2h)
    elif 'both teams' in lab:
        return _qualify_btts(ai_prob, implied_prob, home, away, h2h)
    elif 'double chance' in lab or 'home or draw' in lab or 'draw or away' in lab or 'home or away' in lab:
        # Pass h2h so DC(12) can penalise draw-prone fixtures
        return _qualify_double_chance(label, ai_prob, implied_prob, home, away, h2h)
    else:
        # Generic: small boost if AI says so
        if home is None or away is None:
            return ai_prob
        return min(0.93, ai_prob * 1.02)


def _qualify_over25(ai_prob, implied, home, away, h2h):
    if home is None or away is None:
        return max(ai_prob, implied + 0.06)

    combined = home['avg_goals_scored'] + away['avg_goals_scored']
    avg_o25 = (home['over25_rate'] + away['over25_rate']) / 2

    # Build stats-based probability
    stats_prob = avg_o25 * 0.30 + min(1.0, combined / 4.5) * 0.25 + 0.20
    if h2h and h2h['total_matches'] >= 3:
        h2h_rate = h2h['over25_count'] / h2h['total_matches']
        stats_prob = stats_prob * 0.75 + h2h_rate * 0.25

    # Blend: trust stats MORE than AI model
    blended = ai_prob * 0.35 + stats_prob * 0.45 + implied * 0.20
    return min(0.93, max(blended, implied + 0.02))


def _qualify_over15(ai_prob, implied, home, away, h2h):
    if home is None or away is None:
        return max(ai_prob, implied + 0.05)

    combined = home['avg_goals_scored'] + away['avg_goals_scored']
    avg_o15 = (home['over15_rate'] + away['over15_rate']) / 2

    # Build stats-based probability
    stats_prob = avg_o15 * 0.30 + min(1.0, combined / 3.5) * 0.25 + 0.25
    if h2h and h2h['total_matches'] >= 3:
        h2h_o15 = h2h['over15_count'] / h2h['total_matches']
        stats_prob = stats_prob * 0.75 + h2h_o15 * 0.25

    # Blend: trust stats MORE than AI model
    blended = ai_prob * 0.35 + stats_prob * 0.45 + implied * 0.20
    return min(0.95, max(blended, implied + 0.02))


def _qualify_over05(ai_prob, implied, home, away):
    """Over 0.5 — very high base rate, just sanity check."""
    if home is None or away is None:
        return max(ai_prob, implied + 0.02)
    combined = home['avg_goals_scored'] + away['avg_goals_scored']
    if combined < 1.0:
        return implied * 0.98
    return min(0.97, max(ai_prob * 1.02, implied + 0.02))


def _qualify_team_goals(label, ai_prob, implied, home, away):
    """Home/Away to score, 1H/2H goals.

    Uses VENUE-SPECIFIC stats for team scoring markets so we don't inflate
    the probability of 'Home Over 0.5' using the away team's scoring rate.
    Also rejects when the opposing team has a strong clean sheet record.

    KEY INSIGHT: For big teams at home (avg scored >= 1.5), Home Over 0.5
    is almost certain — boost heavily. It's SAFER to pick Man City to score
    than to pick their weak opponent to score against them.
    """
    if home is None or away is None:
        return max(ai_prob, implied + 0.03)

    lab = label.lower()

    # Home team scoring markets: only the home team needs to score
    if 'home over 0.5' in lab or 'home to score' in lab:
        # Penalise if away team has a strong clean sheet record
        opp_cs = away.get('clean_sheet_rate', 0.25)
        if opp_cs >= 0.45:
            return implied * 0.97  # Very strong visiting defense → reject
        # Use home-venue scoring rate (how often they score at home)
        score_rate = home.get('scored_in_rate', 0.78)
        home_venue_avg = home.get('home_avg_scored', home['avg_goals_scored'])
        # Big teams at home: strong boost — they almost always score
        if home_venue_avg >= 1.8:
            blended = ai_prob * 0.25 + score_rate * 0.50 + implied * 0.25
            return min(0.95, max(blended, implied + 0.05))
        if home_venue_avg >= 1.3:
            blended = ai_prob * 0.30 + score_rate * 0.45 + implied * 0.25
            return min(0.94, max(blended, implied + 0.04))
        blended = ai_prob * 0.35 + score_rate * 0.40 + implied * 0.25
        if home_venue_avg < 1.0:  # Rarely score at home → dampen
            blended *= 0.97
        return min(0.93, max(blended, implied + 0.02))

    # Away team scoring markets: only the away team needs to score
    if 'away over 0.5' in lab or 'away to score' in lab:
        # Penalise if home team has a strong clean sheet record at home
        opp_cs = home.get('clean_sheet_rate', 0.30)
        if opp_cs >= 0.45:
            return implied * 0.97  # Very strong home defense → reject
        # Use away-venue scoring rate (how often they score away)
        score_rate = away.get('scored_in_rate', 0.70)
        away_venue_avg = away.get('away_avg_scored', away['avg_goals_scored'])
        # Strong away scorers: boost
        if away_venue_avg >= 1.5:
            blended = ai_prob * 0.25 + score_rate * 0.50 + implied * 0.25
            return min(0.94, max(blended, implied + 0.04))
        blended = ai_prob * 0.35 + score_rate * 0.40 + implied * 0.25
        if away_venue_avg < 0.8:  # Rarely score away → dampen more
            blended *= 0.96
        return min(0.93, max(blended, implied + 0.02))

    # 1st / 2nd half over 0.5 — both teams contribute, use average
    score_rate = (home['scored_in_rate'] + away['scored_in_rate']) / 2.0
    blended = ai_prob * 0.35 + score_rate * 0.40 + implied * 0.25
    return min(0.93, max(blended, implied + 0.02))


def _qualify_under(ai_prob, implied, home, away):
    """Under 3.5/4.5 — safe when teams don't score heavily."""
    if home is None or away is None:
        return max(ai_prob, implied + 0.03)

    combined = home['avg_goals_scored'] + away['avg_goals_scored']
    defense_factor = 1.0 - min(1.0, combined / 5.0)
    clean_factor = (home.get('clean_sheet_rate', 0.3) + away.get('clean_sheet_rate', 0.3)) / 2.0

    stats_prob = defense_factor * 0.40 + clean_factor * 0.20 + 0.30
    # Trust stats more for under markets — defensive patterns are stable
    blended = ai_prob * 0.30 + stats_prob * 0.45 + implied * 0.25
    return min(0.95, max(blended, implied + 0.02))


def _qualify_under_tight(ai_prob, implied, home, away, h2h):
    """Under 2.5 / Under 1.5 Goals — needs strong defensive evidence.

    Requires low combined scoring average AND H2H support when available.
    This is the market the model was missing — it now catches Brondby-type
    fixtures where both teams rarely score many goals.
    """
    if home is None or away is None:
        return max(ai_prob, implied + 0.03)

    combined = home['avg_goals_scored'] + away['avg_goals_scored']

    # Defense factor: higher when combined avg < 2.0 (tight games)
    defense_factor = 1.0 - min(1.0, combined / 3.5)
    clean_factor = (home.get('clean_sheet_rate', 0.3) + away.get('clean_sheet_rate', 0.3)) / 2.0

    # Base stats probability — requires stronger signal than Under 3.5
    stats_prob = defense_factor * 0.45 + clean_factor * 0.30 + 0.15

    # H2H is very informative for tight under markets — weight it heavily
    if h2h and h2h.get('total_matches', 0) >= 3:
        h2h_under25_rate = 1.0 - (h2h.get('over25_count', 0) / h2h['total_matches'])
        # Blend H2H rate prominently (40%)
        stats_prob = stats_prob * 0.60 + h2h_under25_rate * 0.40

    # Trust stats heavily — AI model has no dedicated Under 2.5 model
    blended = ai_prob * 0.25 + stats_prob * 0.50 + implied * 0.25
    return min(0.92, max(blended, implied + 0.02))


def _qualify_home_win(ai_prob, implied, home, away, h2h):
    if home is None or away is None:
        return max(ai_prob, implied + 0.03)

    stats_prob = home['home_win_rate'] * 0.35 + (1.0 - away.get('away_loss_rate', 0.5)) * 0.10 + \
                 min(1.0, home['home_avg_scored'] / 2.5) * 0.20 + 0.15
    if h2h and h2h['total_matches'] >= 3 and h2h['team1_wins'] > h2h['team2_wins']:
        stats_prob += 0.05

    # Trust stats more than AI for result markets
    blended = ai_prob * 0.35 + stats_prob * 0.40 + implied * 0.25
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

    # Trust stats more than AI for result markets
    blended = ai_prob * 0.35 + stats_prob * 0.40 + implied * 0.25
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

    # Trust stats more
    blended = ai_prob * 0.35 + stats_prob * 0.40 + implied * 0.25
    return min(0.92, max(blended, implied + 0.02))


def _qualify_draw(ai_prob, implied, home, away, h2h):
    """Draw — riskier market, needs strong statistical support."""
    if home is None or away is None:
        return max(ai_prob, implied + 0.03)

    # Draws are more likely when teams are evenly matched
    home_wr = home['home_win_rate']
    away_lr = away.get('away_loss_rate', 0.5)
    # Neither team dominant
    balance = 1.0 - abs(home_wr - (1.0 - away_lr))
    clean_factor = (home.get('clean_sheet_rate', 0.3) + away.get('clean_sheet_rate', 0.3)) / 2.0

    stats_prob = balance * 0.30 + clean_factor * 0.20 + 0.15
    if h2h and h2h['total_matches'] >= 3:
        draw_count = h2h['total_matches'] - h2h.get('team1_wins', 0) - h2h.get('team2_wins', 0)
        h2h_draw_rate = draw_count / h2h['total_matches']
        stats_prob = stats_prob * 0.70 + h2h_draw_rate * 0.30

    blended = ai_prob * 0.50 + stats_prob * 0.25 + implied * 0.25
    return min(0.55, max(blended, implied + 0.02))


def _qualify_btts_no(ai_prob, implied, home, away, h2h):
    """BTTS No — inverse of BTTS Yes, boosted by clean sheet rates."""
    if home is None or away is None:
        return max(ai_prob, implied + 0.03)

    avg_btts = (home['btts_rate'] + away['btts_rate']) / 2
    no_btts_rate = 1.0 - avg_btts
    clean_factor = (home.get('clean_sheet_rate', 0.3) + away.get('clean_sheet_rate', 0.3)) / 2.0

    stats_prob = no_btts_rate * 0.35 + clean_factor * 0.25 + 0.15
    if h2h and h2h['total_matches'] >= 3:
        h2h_btts = h2h['btts_count'] / h2h['total_matches']
        h2h_no = 1.0 - h2h_btts
        stats_prob = stats_prob * 0.70 + h2h_no * 0.30

    blended = ai_prob * 0.50 + stats_prob * 0.30 + implied * 0.20
    return min(0.75, max(blended, implied + 0.02))


def _qualify_double_chance(label, ai_prob, implied, home, away, h2h=None):
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
        # Double Chance (12) — only draw loses.
        # CRITICAL: Check H2H draw rate first. Teams that draw frequently make
        # DC(12) unreliable — Kudrivka 2-2 type scenarios.
        if h2h and h2h.get('total_matches', 0) >= 3:
            draw_count = (
                h2h['total_matches']
                - h2h.get('team1_wins', 0)
                - h2h.get('team2_wins', 0)
            )
            h2h_draw_rate = draw_count / h2h['total_matches']
            if h2h_draw_rate >= 0.40:
                # These teams draw very often — DC(12) is risky, reject
                return implied * 0.95
            if h2h_draw_rate >= 0.25:
                # Moderate draw risk — apply reduced boost (0.03 not 0.06)
                draw_unlikely = (
                    home['home_win_rate'] >= 0.40
                    or away.get('away_loss_rate', 0.5) >= 0.40
                )
                if draw_unlikely:
                    return min(0.95, implied + 0.03)
                return min(0.93, implied + 0.02)

        # Standard path: safe if either team has high home-win / away-loss rate
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
        if 'home over' in lab:
            # Only the home team needs to score — use their venue-specific stats
            consistency = home.get('scored_in_rate', 0.78)
            volume = min(1.0, home.get('home_avg_scored', home['avg_goals_scored']) / 2.0)
        elif 'away over' in lab:
            # Only the away team needs to score — use their venue-specific stats
            consistency = away.get('scored_in_rate', 0.70)
            volume = min(1.0, away.get('away_avg_scored', away['avg_goals_scored']) / 2.0)
        else:
            # General total goals / half goals — both teams contribute
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

    if 'both teams' in lab or lab == 'btts no':
        btts_rate = (home['btts_rate'] + away['btts_rate']) / 2.0
        scored_rate = (home['scored_in_rate'] + away['scored_in_rate']) / 2.0
        if lab == 'btts no':
            return (1.0 - btts_rate) * 0.5 + \
                   (home.get('clean_sheet_rate', 0.3) + away.get('clean_sheet_rate', 0.3)) / 2.0 * 0.5
        return btts_rate * 0.5 + scored_rate * 0.5

    if lab == 'draw':
        return 0.40  # Draws are inherently less stable/predictable

    if 'under 2.5' in lab or 'under 1.5' in lab:
        # Tight under markets need strong clean sheet + low scoring support
        clean = (home.get('clean_sheet_rate', 0.3) + away.get('clean_sheet_rate', 0.3)) / 2.0
        low_scoring = 1.0 - min(1.0, (home['avg_goals_scored'] + away['avg_goals_scored']) / 3.0)
        return clean * 0.55 + low_scoring * 0.45

    if 'under' in lab and 'goal' in lab:
        clean = (home.get('clean_sheet_rate', 0.3) + away.get('clean_sheet_rate', 0.3)) / 2.0
        low_scoring = 1.0 - min(1.0, (home['avg_goals_scored'] + away['avg_goals_scored']) / 4.0)
        return clean * 0.5 + low_scoring * 0.5

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

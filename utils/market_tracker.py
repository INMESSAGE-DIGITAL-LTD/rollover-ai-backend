"""
Market Performance Tracker — pseudo-learning from recent results.

Reads the last N days of daily_predictions from Firestore, fetches actual
match scores from SportMonks, determines win/loss for each market prediction,
and returns composite-score penalty multipliers.

Markets that are underperforming get reduced composite scores so the slip
builder naturally avoids repeating the same losing patterns day after day.

This is called once per generate cycle in services/generator.py.
"""
from datetime import datetime, timedelta, timezone


# ─── Result determination ────────────────────────────────────────────────────

def _check_result(home_score, away_score, market):
    """Return True (win), False (loss), or None (undeterminable)."""
    if home_score is None or away_score is None:
        return None

    total = home_score + away_score
    m = market.lower().strip()

    # Double Chance
    if 'double chance (12)' in m or m == 'home or away':
        return home_score != away_score       # Loses only on draw
    if 'double chance (1x)' in m or m == 'home or draw':
        return home_score >= away_score       # Loses only on away win
    if 'double chance (x2)' in m or m == 'draw or away':
        return away_score >= home_score       # Loses only on home win

    # 1X2
    if m == 'home win':
        return home_score > away_score
    if m == 'away win':
        return away_score > home_score
    if m == 'draw':
        return home_score == away_score

    # Total goals — Over
    if m == 'over 0.5 goals':
        return total >= 1
    if m == 'over 1.5 goals':
        return total >= 2
    if m == 'over 2.5 goals':
        return total >= 3
    if m == 'over 3.5 goals':
        return total >= 4

    # Total goals — Under
    if m == 'under 1.5 goals':
        return total <= 1
    if m == 'under 2.5 goals':
        return total <= 2
    if m == 'under 3.5 goals':
        return total <= 3
    if m == 'under 4.5 goals':
        return total <= 4

    # BTTS
    if m == 'both teams to score':
        return home_score >= 1 and away_score >= 1
    if m == 'btts no':
        return home_score == 0 or away_score == 0

    # Team goals — Over
    if m == 'home over 0.5 goals' or m == 'home to score':
        return home_score >= 1
    if m == 'home over 1.5 goals':
        return home_score >= 2
    if m == 'home over 2.5 goals':
        return home_score >= 3
    if m == 'away over 0.5 goals' or m == 'away to score':
        return away_score >= 1
    if m == 'away over 1.5 goals':
        return away_score >= 2
    if m == 'away over 2.5 goals':
        return away_score >= 3

    # Half-time markets can't be determined from FT score alone
    return None


def _find_fixture_score(fixtures_data, home_team, away_team):
    """Match a prediction to a finished fixture by team name and return score."""
    if not fixtures_data:
        return None, None

    home_lower = home_team.lower().strip()
    away_lower = away_team.lower().strip()

    for fix in fixtures_data.get('fixtures', []):
        fix_home = fix.get('home_team', '').lower().strip()
        fix_away = fix.get('away_team', '').lower().strip()

        if fix_home == home_lower and fix_away == away_lower:
            status = fix.get('match_status', '')
            h = fix.get('home_score')
            a = fix.get('away_score')
            if status in ('FT', 'AET', 'PEN') and h is not None and a is not None:
                return int(h), int(a)

    return None, None


# ─── Main entry point ────────────────────────────────────────────────────────

def get_market_penalties(proxy, lookback_days=7, min_picks=3):
    """
    Compute market penalty multipliers based on recent win rates.

    Args:
        proxy:         SportMonksProxy instance (for fetching past fixture scores).
        lookback_days: Days of history to analyse (default 7).
        min_picks:     Minimum picks needed before applying a penalty. Markets
                       seen fewer than this many times are left unpenalised.

    Returns:
        dict  {market_label: composite_score_multiplier}
        - 1.0   = no penalty (good performance or insufficient data)
        - 0.85  = slight under-performance (<60% win rate)
        - 0.65  = poor performance (<50% win rate)
        - 0.40  = very poor performance (<30% win rate)
        - >1.0  = bonus for consistently winning markets (up to 1.15)
    """
    try:
        from firebase_config import get_firestore_client
        db = get_firestore_client()
    except Exception as e:
        print(f"⚠️ MarketTracker: Firestore unavailable — skipping: {e}")
        return {}

    market_stats = {}  # {market_label: {'wins': N, 'losses': N}}

    print(f"📊 MarketTracker: Analysing last {lookback_days} days of results…")

    for i in range(1, lookback_days + 1):
        target_date = datetime.now(timezone.utc) - timedelta(days=i)
        date_str = target_date.strftime('%Y-%m-%d')

        try:
            doc = db.collection('daily_predictions').document(date_str).get()
            if not doc.exists:
                continue

            data = doc.to_dict()
            matches = data.get('matches', [])
            if not matches:
                continue

            # Fetch actual scores for this date via SportMonks proxy (cached 10 min)
            fixtures_result = proxy.get_fixtures(date_str)

            resolved = 0
            for m in matches:
                market = m.get('market', '')
                home_team = m.get('home_team', '')
                away_team = m.get('away_team', '')

                if not market or not home_team or not away_team:
                    continue

                home_score, away_score = _find_fixture_score(
                    fixtures_result, home_team, away_team
                )

                won = _check_result(home_score, away_score, market)
                if won is None:
                    continue  # Score not available or market undeterminable

                if market not in market_stats:
                    market_stats[market] = {'wins': 0, 'losses': 0}

                if won:
                    market_stats[market]['wins'] += 1
                else:
                    market_stats[market]['losses'] += 1
                resolved += 1

            if resolved:
                print(f"  📅 {date_str}: resolved {resolved}/{len(matches)} picks")

        except Exception as e:
            print(f"  ⚠️ MarketTracker: error for {date_str}: {e}")
            continue

    # ── Calculate penalty/boost multipliers ─────────────────────────────────
    # STRATEGY: Aggressively penalize losing markets AND aggressively boost
    # winning markets. The goal is to FOCUS on what's working, not just
    # avoid what's failing.
    penalties = {}
    for market, stats in market_stats.items():
        total = stats['wins'] + stats['losses']
        if total < min_picks:
            continue  # Not enough data — don't adjust

        win_rate = stats['wins'] / total

        if win_rate < 0.30:
            # Very poor (< 30%): block this market almost entirely
            penalties[market] = 0.20
            print(f"  🔴 {market}: {win_rate:.0%} win rate ({total} picks) → penalty ×0.20")
        elif win_rate < 0.45:
            # Poor (30–45%): strong penalty
            penalties[market] = 0.50
            print(f"  🟠 {market}: {win_rate:.0%} win rate ({total} picks) → penalty ×0.50")
        elif win_rate < 0.55:
            # Below average (45–55%): moderate penalty
            penalties[market] = 0.75
            print(f"  🟡 {market}: {win_rate:.0%} win rate ({total} picks) → penalty ×0.75")
        elif win_rate >= 0.80:
            # Excellent (80%+): strong boost — FOCUS on this market
            bonus = min(1.35, 1.0 + (win_rate - 0.80) * 1.75)
            penalties[market] = bonus
            print(f"  🟢 {market}: {win_rate:.0%} win rate ({total} picks) → BOOST ×{bonus:.2f}")
        elif win_rate >= 0.70:
            # Good (70-80%): significant boost
            bonus = min(1.25, 1.0 + (win_rate - 0.70) * 1.50)
            penalties[market] = bonus
            print(f"  🟢 {market}: {win_rate:.0%} win rate ({total} picks) → boost ×{bonus:.2f}")
        elif win_rate >= 0.60:
            # Decent (60-70%): small boost — reward consistency
            bonus = min(1.12, 1.0 + (win_rate - 0.60) * 1.20)
            penalties[market] = bonus
            print(f"  🟢 {market}: {win_rate:.0%} win rate ({total} picks) → boost ×{bonus:.2f}")
        # 55–60%: no modifier (neutral zone)

    if not penalties:
        print("  ℹ️ MarketTracker: insufficient historical data — no adjustments applied")

    return penalties

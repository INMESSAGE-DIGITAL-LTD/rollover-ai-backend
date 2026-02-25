"""
Result Auto-Updater.

Fetches actual FT scores from SportMonks for past predictions stored in
Firestore and marks each pick as 'won', 'lost', or 'void' (inconclusive).

Called from cron_generate.py before each new generation run so that:
  - The app can display win/loss history to users.
  - The market_tracker has accurate result data to penalise markets.

Only updates picks that are still 'pending'. Already-resolved picks are
left untouched so results are never overwritten.
"""
from datetime import datetime, timedelta, timezone


def _determine_result(home_score, away_score, market):
    """Return 'won', 'lost', or None (undeterminable from FT score)."""
    if home_score is None or away_score is None:
        return None

    total = home_score + away_score
    m = market.lower().strip()

    # Double Chance
    if 'double chance (12)' in m or m == 'home or away':
        return 'won' if home_score != away_score else 'lost'
    if 'double chance (1x)' in m or m == 'home or draw':
        return 'won' if home_score >= away_score else 'lost'
    if 'double chance (x2)' in m or m == 'draw or away':
        return 'won' if away_score >= home_score else 'lost'

    # 1X2
    if m == 'home win':
        return 'won' if home_score > away_score else 'lost'
    if m == 'away win':
        return 'won' if away_score > home_score else 'lost'
    if m == 'draw':
        return 'won' if home_score == away_score else 'lost'

    # Total goals — Over
    if m == 'over 0.5 goals':
        return 'won' if total >= 1 else 'lost'
    if m == 'over 1.5 goals':
        return 'won' if total >= 2 else 'lost'
    if m == 'over 2.5 goals':
        return 'won' if total >= 3 else 'lost'
    if m == 'over 3.5 goals':
        return 'won' if total >= 4 else 'lost'

    # Total goals — Under
    if m == 'under 1.5 goals':
        return 'won' if total <= 1 else 'lost'
    if m == 'under 2.5 goals':
        return 'won' if total <= 2 else 'lost'
    if m == 'under 3.5 goals':
        return 'won' if total <= 3 else 'lost'
    if m == 'under 4.5 goals':
        return 'won' if total <= 4 else 'lost'

    # BTTS
    if m == 'both teams to score':
        return 'won' if (home_score >= 1 and away_score >= 1) else 'lost'
    if m == 'btts no':
        return 'won' if (home_score == 0 or away_score == 0) else 'lost'

    # Team goals — Over
    if m in ('home over 0.5 goals', 'home to score'):
        return 'won' if home_score >= 1 else 'lost'
    if m == 'home over 1.5 goals':
        return 'won' if home_score >= 2 else 'lost'
    if m == 'home over 2.5 goals':
        return 'won' if home_score >= 3 else 'lost'
    if m in ('away over 0.5 goals', 'away to score'):
        return 'won' if away_score >= 1 else 'lost'
    if m == 'away over 1.5 goals':
        return 'won' if away_score >= 2 else 'lost'
    if m == 'away over 2.5 goals':
        return 'won' if away_score >= 3 else 'lost'

    # Half-time markets can't be determined from FT score
    return None


def _find_score(fixtures_data, home_team, away_team):
    """Match a prediction to a finished fixture by team name, return (h, a)."""
    if not fixtures_data:
        return None, None

    home_lower = home_team.lower().strip()
    away_lower = away_team.lower().strip()

    for fix in fixtures_data.get('fixtures', []):
        if (fix.get('home_team', '').lower().strip() == home_lower and
                fix.get('away_team', '').lower().strip() == away_lower):
            status = fix.get('match_status', '')
            h = fix.get('home_score')
            a = fix.get('away_score')
            if status in ('FT', 'AET', 'PEN') and h is not None and a is not None:
                return int(h), int(a)

    return None, None


def update_past_results(proxy, days_back=3):
    """
    Read the last `days_back` days of Firestore daily_predictions, fetch
    actual scores from SportMonks, and update each match's `result` field.

    Args:
        proxy:     SportMonksProxy instance.
        days_back: How many past days to process (default 3).

    Returns:
        dict with total updated counts.
    """
    try:
        from firebase_config import get_firestore_client
        db = get_firestore_client()
    except Exception as e:
        print(f"⚠️ ResultUpdater: Firestore unavailable: {e}")
        return {'updated': 0, 'errors': 0}

    total_updated = 0
    total_errors = 0

    print(f"🔄 ResultUpdater: Checking last {days_back} days of picks…")

    for i in range(1, days_back + 1):
        target = datetime.now(timezone.utc) - timedelta(days=i)
        date_str = target.strftime('%Y-%m-%d')

        try:
            ref = db.collection('daily_predictions').document(date_str)
            doc = ref.get()
            if not doc.exists:
                continue

            data = doc.to_dict()
            matches = data.get('matches', [])
            if not matches:
                continue

            # Check if all picks are already resolved — skip early
            pending = [m for m in matches if m.get('result', 'pending') == 'pending']
            if not pending:
                print(f"  ✅ {date_str}: all picks already resolved")
                continue

            # Fetch actual scores for this date
            fixtures_result = proxy.get_fixtures(date_str)

            updated_matches = []
            day_updated = 0
            day_errors = 0

            for match in matches:
                # Already resolved — leave it alone
                if match.get('result', 'pending') != 'pending':
                    updated_matches.append(match)
                    continue

                home = match.get('home_team', '')
                away = match.get('away_team', '')
                market = match.get('market', '')

                home_score, away_score = _find_score(fixtures_result, home, away)
                result = _determine_result(home_score, away_score, market)

                updated = dict(match)
                if result is not None:
                    updated['result'] = result
                    if home_score is not None:
                        updated['actual_home_score'] = home_score
                        updated['actual_away_score'] = away_score
                    day_updated += 1
                else:
                    # Score not found or market undeterminable (half-time etc.)
                    # Mark void only if the game should be finished by now
                    # (kickoff was > 2.5 hours ago)
                    kickoff_str = match.get('kickoff', '')
                    if kickoff_str:
                        try:
                            from datetime import datetime as dt
                            kickoff = dt.fromisoformat(kickoff_str.replace('Z', '+00:00'))
                            age_hours = (datetime.now(timezone.utc) - kickoff).total_seconds() / 3600
                            if age_hours > 2.5 and home_score is None:
                                # Game should be over but score not found — void
                                updated['result'] = 'void'
                                day_errors += 1
                        except Exception:
                            pass

                updated_matches.append(updated)

            # Only write back if something changed
            if day_updated > 0 or day_errors > 0:
                # Recalculate slip-level win/loss summary
                resolved = [m for m in updated_matches if m.get('result', 'pending') != 'pending']
                wins = sum(1 for m in resolved if m.get('result') == 'won')
                losses = sum(1 for m in resolved if m.get('result') == 'lost')

                ref.update({
                    'matches': updated_matches,
                    'results_summary': {
                        'wins': wins,
                        'losses': losses,
                        'pending': len([m for m in updated_matches if m.get('result', 'pending') == 'pending']),
                        'void': len([m for m in updated_matches if m.get('result') == 'void']),
                        'slip_result': 'won' if losses == 0 and wins > 0 else ('lost' if losses > 0 else 'pending'),
                    },
                    'results_updated_at': __import__('datetime').datetime.utcnow().isoformat(),
                })
                print(f"  📅 {date_str}: resolved {day_updated} picks "
                      f"({wins}W / {losses}L) | {day_errors} void")
                total_updated += day_updated
                total_errors += day_errors
            else:
                print(f"  ⏳ {date_str}: {len(pending)} picks still pending "
                      f"(scores not available yet)")

        except Exception as e:
            print(f"  ❌ ResultUpdater error for {date_str}: {e}")

    print(f"✅ ResultUpdater: done — {total_updated} picks resolved")
    return {'updated': total_updated, 'errors': total_errors}

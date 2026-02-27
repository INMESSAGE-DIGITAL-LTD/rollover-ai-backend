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


def _extract_goal_line(market):
    """Extract the numeric goal line from a market string, e.g. '1st Half Over 0.5' → 0.5.
    Always looks for the number AFTER 'over'/'under' so '2nd Half Over 0.5'
    returns 0.5, not 2.0 (which would be extracted from '2nd')."""
    import re
    # Prefer the number directly after over/under
    ov_match = re.search(r'(?:over|under)\s*(\d+\.?\d*)', market, re.IGNORECASE)
    if ov_match:
        return float(ov_match.group(1))
    # Fallback to first number in string
    match = re.search(r'(\d+\.?\d*)', market)
    return float(match.group(1)) if match else 0.5


def _determine_result(home_score, away_score, market, ht_home_score=None, ht_away_score=None):
    """Return 'won', 'lost', or None (undeterminable)."""
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

    # Half-time markets — need HT scores
    if '1st half' in m:
        if ht_home_score is None or ht_away_score is None:
            return None  # HT score data not available yet
        ht_total = ht_home_score + ht_away_score
        if 'over' in m:
            return 'won' if ht_total > _extract_goal_line(m) else 'lost'
        if 'under' in m:
            return 'won' if ht_total < _extract_goal_line(m) else 'lost'
        return None

    if '2nd half' in m:
        if ht_home_score is None or ht_away_score is None:
            return None  # HT score data not available yet
        h2_total = (home_score - ht_home_score) + (away_score - ht_away_score)
        if 'over' in m:
            return 'won' if h2_total > _extract_goal_line(m) else 'lost'
        if 'under' in m:
            return 'won' if h2_total < _extract_goal_line(m) else 'lost'
        return None

    return None


def _normalize_name(name):
    """Normalise a team name for fuzzy matching."""
    import unicodedata
    # Lowercase, strip, replace hyphens/underscores with space
    n = name.lower().strip().replace('-', ' ').replace('_', ' ')
    # Remove accents (e.g. é → e)
    n = ''.join(
        c for c in unicodedata.normalize('NFD', n)
        if unicodedata.category(c) != 'Mn'
    )
    # Collapse multiple spaces
    n = ' '.join(n.split())
    return n


def _names_match(a, b):
    """True if two team names are the same after normalisation, or one
    contains the other, or they share ≥2 significant tokens.

    Handles:
      'Paris Saint German' vs 'Paris Saint-Germain'  → token overlap
      'PSG' vs 'Paris Saint-Germain'                 → substring (psg in …)
      'AS Monaco' vs 'Monaco'                        → substring
    """
    na, nb = _normalize_name(a), _normalize_name(b)
    if na == nb:
        return True
    # Substring check (min 4 chars each to avoid false positives)
    if len(na) >= 4 and len(nb) >= 4:
        if na in nb or nb in na:
            return True
    # Token overlap: if ≥2 words of length ≥4 are shared → same club.
    # Catches "paris saint german" vs "paris saint germain" where the
    # final token differs by one character ("german" ≠ "germain") but
    # "paris" and "saint" both match.
    tokens_a = {w for w in na.split() if len(w) >= 4}
    tokens_b = {w for w in nb.split() if len(w) >= 4}
    if tokens_a and tokens_b and len(tokens_a & tokens_b) >= 2:
        return True
    return False


def _find_score(fixtures_data, home_team, away_team):
    """Match a prediction to a finished fixture by team name.
    Returns (home_score, away_score, ht_home_score, ht_away_score).
    Uses normalised fuzzy matching so hyphen/accent/abbreviation differences
    between stored names and SportMonks names don't cause misses."""
    if not fixtures_data:
        return None, None, None, None

    for fix in fixtures_data.get('fixtures', []):
        if (_names_match(fix.get('home_team', ''), home_team) and
                _names_match(fix.get('away_team', ''), away_team)):
            status = fix.get('match_status', '')
            h = fix.get('home_score')
            a = fix.get('away_score')
            ht_h = fix.get('ht_home_score')
            ht_a = fix.get('ht_away_score')
            if status in ('FT', 'AET', 'PEN') and h is not None and a is not None:
                return (
                    int(h), int(a),
                    int(ht_h) if ht_h is not None else None,
                    int(ht_a) if ht_a is not None else None,
                )

    return None, None, None, None


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

            # Check if all picks are already resolved — skip early.
            # Also re-evaluate 'void' picks so previously-voided half-time
            # markets get a real result now that we have HT score data.
            def _needs_evaluation(m):
                r = m.get('result')
                return r is None or r in ('pending', 'void')

            needs_eval = [m for m in matches if _needs_evaluation(m)]
            if not needs_eval:
                print(f"  ✅ {date_str}: all picks already resolved")
                continue

            # Fetch actual scores for this date
            fixtures_result = proxy.get_fixtures(date_str)

            updated_matches = []
            day_updated = 0
            day_errors = 0

            for match in matches:
                # Already firmly resolved — leave it alone
                if not _needs_evaluation(match):
                    updated_matches.append(match)
                    continue

                home = match.get('home_team', '')
                away = match.get('away_team', '')
                market = match.get('market', '')

                home_score, away_score, ht_home_score, ht_away_score = \
                    _find_score(fixtures_result, home, away)
                result = _determine_result(
                    home_score, away_score, market,
                    ht_home_score=ht_home_score,
                    ht_away_score=ht_away_score,
                )

                updated = dict(match)
                if result is not None:
                    updated['result'] = result
                    # Write scores into the match so the Flutter app can
                    # read home_score / away_score directly from Firestore.
                    if home_score is not None:
                        updated['home_score'] = home_score
                        updated['away_score'] = away_score
                        updated['match_status'] = 'FT'
                        updated['actual_home_score'] = home_score
                        updated['actual_away_score'] = away_score
                    if ht_home_score is not None:
                        updated['ht_home_score'] = ht_home_score
                        updated['ht_away_score'] = ht_away_score
                    day_updated += 1
                else:
                    # Score not found OR market undeterminable (no HT data yet).
                    # Void only when the game is well and truly finished (> 2.5h).
                    kickoff_str = match.get('kickoff', '')
                    if kickoff_str:
                        try:
                            from datetime import datetime as dt
                            kickoff = dt.fromisoformat(kickoff_str.replace('Z', '+00:00'))
                            if kickoff.tzinfo is None:
                                kickoff = kickoff.replace(tzinfo=timezone.utc)
                            age_hours = (datetime.now(timezone.utc) - kickoff).total_seconds() / 3600
                            if age_hours > 2.5:
                                updated['result'] = 'void'
                                if home_score is not None:
                                    updated['home_score'] = home_score
                                    updated['away_score'] = away_score
                                    updated['match_status'] = 'FT'
                                    updated['actual_home_score'] = home_score
                                    updated['actual_away_score'] = away_score
                                if ht_home_score is not None:
                                    updated['ht_home_score'] = ht_home_score
                                    updated['ht_away_score'] = ht_away_score
                                day_errors += 1
                        except Exception:
                            pass

                updated_matches.append(updated)

            # Always recalculate summary so the app can show win/loss badges
            resolved = [m for m in updated_matches if not _is_pending(m)]
            wins = sum(1 for m in resolved if m.get('result') == 'won')
            losses = sum(1 for m in resolved if m.get('result') == 'lost')
            still_pending = [m for m in updated_matches if _is_pending(m)]

            if day_updated > 0 or day_errors > 0:
                # New results resolved this run — write full match list + summary
                ref.update({
                    'matches': updated_matches,
                    'results_summary': {
                        'wins': wins,
                        'losses': losses,
                        'pending': len(still_pending),
                        'void': len([m for m in updated_matches if m.get('result') == 'void']),
                        'slip_result': 'won' if losses == 0 and wins > 0 else ('lost' if losses > 0 else 'pending'),
                    },
                    'results_updated_at': __import__('datetime').datetime.utcnow().isoformat(),
                })
                print(f"  📅 {date_str}: resolved {day_updated} picks "
                      f"({wins}W / {losses}L) | {day_errors} void")
                total_updated += day_updated
                total_errors += day_errors
            elif resolved:
                # Nothing new this run but some picks already resolved —
                # ensure results_summary is written (may have been missing)
                ref.update({
                    'results_summary': {
                        'wins': wins,
                        'losses': losses,
                        'pending': len(still_pending),
                        'void': len([m for m in updated_matches if m.get('result') == 'void']),
                        'slip_result': 'won' if losses == 0 and wins > 0 else ('lost' if losses > 0 else 'pending'),
                    },
                    'results_updated_at': __import__('datetime').datetime.utcnow().isoformat(),
                })
                print(f"  📅 {date_str}: summary synced ({wins}W / {losses}L / {len(still_pending)} pending)")
            else:
                print(f"  ⏳ {date_str}: {len(pending)} picks still pending "
                      f"(scores not available yet)")

        except Exception as e:
            print(f"  ❌ ResultUpdater error for {date_str}: {e}")

    print(f"✅ ResultUpdater: done — {total_updated} picks resolved")
    return {'updated': total_updated, 'errors': total_errors}

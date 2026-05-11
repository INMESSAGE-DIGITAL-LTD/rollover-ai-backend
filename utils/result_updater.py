"""Result Auto-Updater.

Fetches actual FT scores from SportMonks for past predictions stored in
Firestore and marks each pick as 'won', 'lost', or 'void' (inconclusive).

Called from cron_generate.py before each new generation run so that:
  - The app can display win/loss history to users.
  - The market_tracker has accurate result data to penalise markets.

Only updates picks that are still 'pending'. Already-resolved picks are
left untouched so results are never overwritten.
"""
from datetime import datetime, timedelta, timezone
import json
import os
import urllib.request
import urllib.error

SPORTMONKS_TOKEN = os.environ.get(
    'SPORTMONKS_TOKEN',
    'b7EFSY6Bmrxisf6OswWjYArQUHMakSEDRMTJVoFiH56sbHsxaJxFRpVrOuoL',
)
SPORTMONKS_BASE = 'https://api.sportmonks.com/v3/football'


def _extract_goal_line(market):
    """Extract the numeric goal line from a market string, e.g. '1st Half Over 0.5' → 0.5.
    Always looks for the number AFTER 'over'/'under' so '2nd Half Over 0.5'
    returns 0.5, not 2.0 (which would be extracted from '2nd')."""
    import re
    ov_match = re.search(r'(?:over|under)\s*(\d+\.?\d*)', market, re.IGNORECASE)
    if ov_match:
        return float(ov_match.group(1))
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
            return None
        ht_total = ht_home_score + ht_away_score
        if 'over' in m:
            return 'won' if ht_total > _extract_goal_line(m) else 'lost'
        if 'under' in m:
            return 'won' if ht_total < _extract_goal_line(m) else 'lost'
        return None

    if '2nd half' in m:
        if ht_home_score is None or ht_away_score is None:
            return None
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
    n = name.lower().strip().replace('-', ' ').replace('_', ' ')
    n = ''.join(
        c for c in unicodedata.normalize('NFD', n)
        if unicodedata.category(c) != 'Mn'
    )
    n = ' '.join(n.split())
    return n


def _names_match(a, b):
    """True if two team names are the same after normalisation, or one
    contains the other, or they share >=1 significant token."""
    na, nb = _normalize_name(a), _normalize_name(b)
    if na == nb:
        return True
    if len(na) >= 3 and len(nb) >= 3:
        if na in nb or nb in na:
            return True
    # Token overlap: if >=1 word of length >=4 is shared -> same club
    tokens_a = {w for w in na.split() if len(w) >= 4}
    tokens_b = {w for w in nb.split() if len(w) >= 4}
    if tokens_a and tokens_b and len(tokens_a & tokens_b) >= 1:
        return True
    # Short 3-char tokens (e.g. "aek", "ael", "psv", "cfr")
    tokens_a3 = {w for w in na.split() if len(w) == 3}
    tokens_b3 = {w for w in nb.split() if len(w) == 3}
    if tokens_a3 and tokens_b3 and len(tokens_a3 & tokens_b3) >= 1:
        return True
    return False


# ── API-Football direct call for scores ──

APIFOOTBALL_KEY = os.environ.get('APIFOOTBALL_KEY', 'da7a6fc2f03e7fb7994995143d29358f')
APIFOOTBALL_BASE = 'https://v3.football.api-sports.io'


def _fetch_fixtures_direct(date_str):
    """Fetch finished fixtures with scores from API-Football (all pages).
    On per-page errors, logs a warning and continues so partial results
    are never lost because of a single transient failure."""
    fixtures = []
    page = 1
    while True:
        url = f"{APIFOOTBALL_BASE}/fixtures?date={date_str}&timezone=UTC&page={page}"
        try:
            req = urllib.request.Request(url, headers={'x-apisports-key': APIFOOTBALL_KEY})
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = json.loads(resp.read().decode())
        except Exception as e:
            print(f"  ⚠️ API-Football error fetching scores for {date_str} p{page}: {e}")
            # Don't break — if we already have page 1 data, keep it.
            # Only break if this was the very first page (nothing collected yet).
            if page == 1:
                break
            # For later pages, stop paging but keep whatever we already collected.
            print(f"  ⚠️ Keeping {len(fixtures)} fixtures collected before error")
            break

        for event in body.get('response', []):
            status = (event.get('fixture') or {}).get('status', {})
            short = status.get('short', '')
            if short not in ('FT', 'AET', 'PEN'):
                continue

            teams = event.get('teams', {})
            home_name = (teams.get('home') or {}).get('name', '')
            away_name = (teams.get('away') or {}).get('name', '')
            if not home_name or not away_name:
                continue

            goals = event.get('goals', {})
            score = event.get('score', {})
            home_score = goals.get('home')
            away_score = goals.get('away')
            ht = score.get('halftime', {})
            ht_home = ht.get('home')
            ht_away = ht.get('away')

            if home_score is None or away_score is None:
                continue

            fixtures.append({
                'home_team': home_name,
                'away_team': away_name,
                'home_score': int(home_score),
                'away_score': int(away_score),
                'ht_home_score': int(ht_home) if ht_home is not None else None,
                'ht_away_score': int(ht_away) if ht_away is not None else None,
                'match_status': 'FT',
            })

        # Check if there are more pages
        paging = body.get('paging', {})
        current = paging.get('current', 1)
        total_pages = paging.get('total', 1)
        if current >= total_pages:
            break
        page += 1

    print(f"  📡 API-Football: {len(fixtures)} finished fixtures for {date_str} ({page} page(s))")
    return {'fixtures': fixtures}


def _find_score(fixtures_data, home_team, away_team):
    """Match a prediction to a finished fixture by team name."""
    if not fixtures_data:
        return None, None, None, None

    fixtures = fixtures_data.get('fixtures', [])
    for fix in fixtures:
        if (_names_match(fix.get('home_team', ''), home_team) and
                _names_match(fix.get('away_team', ''), away_team)):
            h = fix.get('home_score')
            a = fix.get('away_score')
            ht_h = fix.get('ht_home_score')
            ht_a = fix.get('ht_away_score')
            if h is not None and a is not None:
                return int(h), int(a), \
                    int(ht_h) if ht_h is not None else None, \
                    int(ht_a) if ht_a is not None else None

    # Debug: log first 5 available names to help diagnose mismatches
    avail = [(f.get('home_team', ''), f.get('away_team', '')) for f in fixtures[:5]]
    print(f"    🔎 No match for '{home_team}' vs '{away_team}'. "
          f"Available (first 5): {avail}")
    return None, None, None, None


def _is_pending(m):
    r = m.get('result')
    return r is None or r in ('pending', 'void')


def update_past_results(proxy, days_back=3):
    """
    Read the last `days_back` days of Firestore daily_predictions, fetch
    actual scores from SportMonks, and update each match's `result` field.

    Uses direct SportMonks API calls (not the proxy cache) to ensure
    fresh score data is always available.
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

    # Process both daily_predictions and daily_ai_pro collections
    collections_to_check = ['daily_predictions', 'daily_ai_pro', 'daily_rollover', 'daily_big_odds']

    for collection_name in collections_to_check:
        for i in range(1, days_back + 1):
            target = datetime.now(timezone.utc) - timedelta(days=i)
            date_str = target.strftime('%Y-%m-%d')

            try:
                ref = db.collection(collection_name).document(date_str)
                doc = ref.get()
                if not doc.exists:
                    continue

                data = doc.to_dict()

                # daily_predictions uses 'matches', daily_ai_pro uses 'tips'
                matches_key = 'matches'
                if collection_name == 'daily_ai_pro':
                    matches_key = 'tips'

                matches = data.get(matches_key, [])
                if not matches:
                    continue

                # Check if all picks are already resolved
                needs_eval = [m for m in matches if _is_pending(m)]
                if not needs_eval:
                    print(f"  ✅ {collection_name}/{date_str}: all resolved")
                    continue

                print(f"  🔍 {collection_name}/{date_str}: {len(needs_eval)}/{len(matches)} need evaluation")

                # Fetch actual scores directly from SportMonks (no proxy cache)
                fixtures_result = _fetch_fixtures_direct(date_str)

                updated_matches = []
                day_updated = 0
                day_errors = 0

                for match in matches:
                    if not _is_pending(match):
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
                        print(f"    ✅ {home} vs {away} | {market} → {result} ({home_score}-{away_score})")
                    else:
                        # Score not found — check if game should be old enough to void
                        kickoff_str = match.get('kickoff', '')
                        if kickoff_str:
                            try:
                                from datetime import datetime as dt
                                kickoff = dt.fromisoformat(kickoff_str.replace('Z', '+00:00'))
                                if kickoff.tzinfo is None:
                                    kickoff = kickoff.replace(tzinfo=timezone.utc)
                                age_hours = (datetime.now(timezone.utc) - kickoff).total_seconds() / 3600
                                # 10-hour window: gives late-night matches (22:30 kickoff) time
                                # to finish AND for the API to report the score before we void.
                                if age_hours > 10:
                                    updated['result'] = 'void'
                                    updated['match_status'] = 'FT'  # game is over even if result unknown
                                    day_errors += 1
                                    print(f"    ⚠️ {home} vs {away} | {market} → void (no score after {age_hours:.0f}h)")
                            except Exception:
                                pass
                        else:
                            # No kickoff time saved — if it's > 24h old, void it
                            age_hours = (datetime.now(timezone.utc) - target).total_seconds() / 3600
                            if age_hours > 24:
                                updated['result'] = 'void'
                                updated['match_status'] = 'FT'
                                day_errors += 1
                                print(f"    ⚠️ {home} vs {away} | {market} → void (no kickoff, {age_hours:.0f}h old)")
                            else:
                                print(f"    ❓ {home} vs {away} | {market} → no score found yet")

                    updated_matches.append(updated)

                # Calculate summary
                resolved = [m for m in updated_matches if not _is_pending(m)]
                wins = sum(1 for m in resolved if m.get('result') == 'won')
                losses = sum(1 for m in resolved if m.get('result') == 'lost')
                still_pending = [m for m in updated_matches if _is_pending(m)]

                if day_updated > 0 or day_errors > 0:
                    update_data = {
                        matches_key: updated_matches,
                        'results_summary': {
                            'wins': wins,
                            'losses': losses,
                            'pending': len(still_pending),
                            'void': len([m for m in updated_matches if m.get('result') == 'void']),
                            'slip_result': 'won' if losses == 0 and wins > 0 else ('lost' if losses > 0 else 'pending'),
                        },
                        'results_updated_at': datetime.utcnow().isoformat(),
                    }
                    ref.update(update_data)
                    print(f"  📅 {collection_name}/{date_str}: resolved {day_updated} picks "
                          f"({wins}W / {losses}L) | {day_errors} void")
                    total_updated += day_updated
                    total_errors += day_errors
                else:
                    print(f"  ⏳ {collection_name}/{date_str}: {len(still_pending)} picks still pending")

            except Exception as e:
                print(f"  ❌ ResultUpdater error for {collection_name}/{date_str}: {e}")
                import traceback
                traceback.print_exc()

    print(f"✅ ResultUpdater: done — {total_updated} picks resolved, {total_errors} void")
    return {'updated': total_updated, 'errors': total_errors}

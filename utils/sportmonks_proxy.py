"""
SportMonks API proxy with in-memory caching and background polling.
All SportMonks calls go through here — the API token never leaves the server.
"""
import os
import json
import time
import threading
import urllib.request
import urllib.error

SPORTMONKS_TOKEN = os.environ.get(
    'SPORTMONKS_TOKEN',
    'b7EFSY6Bmrxisf6OswWjYArQUHMakSEDRMTJVoFiH56sbHsxaJxFRpVrOuoL',
)
SPORTMONKS_BASE = 'https://api.sportmonks.com/v3/football'

# Import league ID → name mapping from fixture_fetcher
from utils.fixture_fetcher import LEAGUE_IDS, LEAGUE_FILTER

# State ID classification
LIVE_STATE_IDS = {2, 3, 4, 6, 9, 21, 22, 23, 25}
FINISHED_STATE_IDS = {5, 7, 8, 14, 15, 17}


def _state_to_status(state_id):
    if state_id in (1, 13, 16, 26):
        return 'NS'
    if state_id == 3:
        return 'HT'
    if state_id in LIVE_STATE_IDS:
        return 'Live'
    if state_id in FINISHED_STATE_IDS:
        return 'FT'
    if state_id in (10, 11, 12, 18):
        return 'FT'
    return 'NS'


class SportMonksProxy:
    """Cached proxy for SportMonks API. One instance shared across all requests."""

    def __init__(self):
        self._cache = {}  # key -> {'data': ..., 'ts': time.time()}
        self._lock = threading.Lock()
        self._polling = False
        self._poll_thread = None

    # ── Generic cache helpers ──

    def get_cache(self, key, ttl=120):
        with self._lock:
            entry = self._cache.get(key)
            if entry and (time.time() - entry['ts']) < ttl:
                return entry['data']
        return None

    def set_cache(self, key, data):
        with self._lock:
            self._cache[key] = {'data': data, 'ts': time.time()}

    # ── Live scores (background-polled every 2 min) ──

    def get_livescores(self):
        # Lazily start background polling on first call
        if not self._polling:
            self._start_polling()
        cached = self.get_cache('livescores', ttl=150)  # 2.5 min grace
        if cached is not None:
            return cached
        # If cache miss (first call or stale), fetch now
        return self._fetch_livescores()

    def _fetch_livescores(self):
        """Fetch live scores from SportMonks and cache."""
        try:
            url = (
                f"{SPORTMONKS_BASE}/livescores/inplay"
                f"?api_token={SPORTMONKS_TOKEN}"
                f"&include=participants;scores;league"
            )
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode())

            fixtures = []
            for event in body.get('data', []):
                f = self._parse_live_fixture(event)
                if f:
                    fixtures.append(f)

            result = {
                'fixtures': fixtures,
                'count': len(fixtures),
                'cached_at': time.time(),
            }
            self.set_cache('livescores', result)
            print(f"✅ Live scores cached: {len(fixtures)} matches in play")
            return result

        except Exception as e:
            print(f"⚠️ Livescores fetch error: {e}")
            # Return stale cache if available
            with self._lock:
                entry = self._cache.get('livescores')
                if entry:
                    return entry['data']
            return {'fixtures': [], 'count': 0, 'error': str(e)}

    def _parse_live_fixture(self, event):
        """Parse a SportMonks fixture into a lightweight dict for the app."""
        participants = event.get('participants', [])
        home_name = away_name = ''
        home_logo = away_logo = ''
        home_short = away_short = ''

        for p in participants:
            loc = (p.get('meta') or {}).get('location', '')
            if loc == 'home':
                home_name = p.get('name', '')
                home_logo = p.get('image_path', '')
                home_short = p.get('short_code', '')
            elif loc == 'away':
                away_name = p.get('name', '')
                away_logo = p.get('image_path', '')
                away_short = p.get('short_code', '')

        if not home_name or not away_name:
            return None

        state_id = event.get('state_id', 1)
        status = _state_to_status(state_id)

        # Extract league info
        league_data = event.get('league') or {}
        league_id = league_data.get('id') or event.get('league_id') or 0
        league_name = LEAGUE_IDS.get(league_id, league_data.get('name', ''))
        league_logo = league_data.get('image_path', '')
        league_country = (league_data.get('country') or {}).get('name', '')

        # Parse scores
        home_score = None
        away_score = None
        scores = event.get('scores', [])
        for s in scores:
            desc = s.get('description', '')
            score_data = s.get('score', {})
            participant = score_data.get('participant', '')
            goals = score_data.get('goals')
            if desc == 'CURRENT' and goals is not None:
                g = int(goals) if isinstance(goals, int) else int(goals)
                if participant == 'home':
                    home_score = g
                elif participant == 'away':
                    away_score = g

        return {
            'id': event.get('id'),
            'home_team': home_name,
            'away_team': away_name,
            'home_logo': home_logo,
            'away_logo': away_logo,
            'home_short_code': home_short,
            'away_short_code': away_short,
            'home_score': home_score,
            'away_score': away_score,
            'match_status': status,
            'state_id': state_id,
            'starting_at': event.get('starting_at', ''),
            'league_id': league_id,
            'league_name': league_name,
            'league_logo': league_logo,
            'league_country': league_country,
        }

    # ── Fixtures by date (cached 10 min) ──

    def get_fixtures(self, date_str):
        cache_key = f"fixtures_{date_str}"
        cached = self.get_cache(cache_key, ttl=600)  # 10 min
        if cached is not None:
            return cached
        return self._fetch_fixtures(date_str)

    def _fetch_fixtures(self, date_str):
        """Fetch all fixtures for a date from SportMonks."""
        try:
            url = (
                f"{SPORTMONKS_BASE}/fixtures/date/{date_str}"
                f"?api_token={SPORTMONKS_TOKEN}"
                f"&include=participants;scores;league"
                f"&filters=fixtureLeagues:{LEAGUE_FILTER}"
                f"&per_page=50"
            )
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = json.loads(resp.read().decode())

            fixtures = []
            for event in body.get('data', []):
                f = self._parse_live_fixture(event)
                if f:
                    fixtures.append(f)

            # Handle pagination
            pagination = body.get('pagination', {})
            if pagination.get('has_more'):
                url2 = url + '&page=2'
                req2 = urllib.request.Request(url2)
                with urllib.request.urlopen(req2, timeout=20) as resp2:
                    body2 = json.loads(resp2.read().decode())
                for event in body2.get('data', []):
                    f = self._parse_live_fixture(event)
                    if f:
                        fixtures.append(f)

            result = {
                'fixtures': fixtures,
                'count': len(fixtures),
                'date': date_str,
                'cached_at': time.time(),
            }
            cache_key = f"fixtures_{date_str}"
            self.set_cache(cache_key, result)
            print(f"✅ Fixtures cached for {date_str}: {len(fixtures)} matches")
            return result

        except Exception as e:
            print(f"⚠️ Fixtures fetch error for {date_str}: {e}")
            return {'fixtures': [], 'count': 0, 'date': date_str, 'error': str(e)}

    # ── Leagues (cached 24 hours) ──

    def get_leagues(self):
        cached = self.get_cache('leagues', ttl=86400)  # 24 hours
        if cached is not None:
            return cached
        return self._fetch_leagues()

    def _fetch_leagues(self):
        """Fetch all leagues from SportMonks with country info."""
        try:
            url = (
                f"{SPORTMONKS_BASE}/leagues"
                f"?api_token={SPORTMONKS_TOKEN}"
                f"&include=country"
                f"&per_page=50"
            )
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = json.loads(resp.read().decode())

            leagues = []
            for lg in body.get('data', []):
                leagues.append({
                    'id': lg.get('id'),
                    'name': lg.get('name', ''),
                    'logo': lg.get('image_path', ''),
                    'country': (lg.get('country') or {}).get('name', ''),
                    'country_logo': (lg.get('country') or {}).get('image_path', ''),
                    'active': lg.get('active', True),
                })

            # Page 2 if needed
            pagination = body.get('pagination', {})
            if pagination.get('has_more'):
                url2 = url + '&page=2'
                req2 = urllib.request.Request(url2)
                with urllib.request.urlopen(req2, timeout=20) as resp2:
                    body2 = json.loads(resp2.read().decode())
                for lg in body2.get('data', []):
                    leagues.append({
                        'id': lg.get('id'),
                        'name': lg.get('name', ''),
                        'logo': lg.get('image_path', ''),
                        'country': (lg.get('country') or {}).get('name', ''),
                        'country_logo': (lg.get('country') or {}).get('image_path', ''),
                        'active': lg.get('active', True),
                    })

            result = {
                'leagues': leagues,
                'count': len(leagues),
                'cached_at': time.time(),
            }
            self.set_cache('leagues', result)
            print(f"✅ Leagues cached: {len(leagues)}")
            return result

        except Exception as e:
            print(f"⚠️ Leagues fetch error: {e}")
            return {'leagues': [], 'count': 0, 'error': str(e)}

    # ── Background polling thread ──

    def _start_polling(self):
        if self._polling:
            return
        self._polling = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()
        print("🔄 Started background livescore polling (every 2 min)")

    def _poll_loop(self):
        """Background thread: poll live scores every 2 minutes."""
        while self._polling:
            try:
                self._fetch_livescores()
            except Exception as e:
                print(f"⚠️ Poll error: {e}")
            # Sleep 2 minutes
            time.sleep(120)

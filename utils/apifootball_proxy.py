"""
API-Football (api-sports.io) proxy with in-memory caching and background polling.
Replaces SportMonks. All API calls go through here — key never leaves the server.
Base URL: https://v3.football.api-sports.io
Auth:     x-apisports-key header
"""
import os
import json
import time
import threading
import urllib.request
import urllib.error
from datetime import datetime

APIFOOTBALL_KEY = os.environ.get('APIFOOTBALL_KEY', 'da7a6fc2f03e7fb7994995143d29358f')
APIFOOTBALL_BASE = 'https://v3.football.api-sports.io'

from utils.fixture_fetcher import LEAGUE_IDS


def _make_request(path, params=None):
    """Make a GET request to API-Football. Returns parsed JSON body or raises."""
    qs = ''
    if params:
        qs = '?' + '&'.join(f"{k}={v}" for k, v in params.items())
    url = f"{APIFOOTBALL_BASE}/{path}{qs}"
    req = urllib.request.Request(url, headers={'x-apisports-key': APIFOOTBALL_KEY})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


def _status_short_to_status(short):
    if short in ('NS', 'TBD', 'SUSP', 'PST', 'CANC', 'ABD', 'AWD', 'WO'):
        return 'NS'
    if short == 'HT':
        return 'HT'
    if short in ('1H', '2H', 'ET', 'BT', 'P', 'INT', 'LIVE'):
        return 'Live'
    if short in ('FT', 'AET', 'PEN'):
        return 'FT'
    return 'NS'


def _parse_fixture(item):
    """Parse one API-Football fixture object into a lightweight dict."""
    fix = item.get('fixture', {})
    league = item.get('league', {})
    teams = item.get('teams', {})
    goals = item.get('goals', {})
    score = item.get('score', {})

    home = teams.get('home', {})
    away = teams.get('away', {})

    if not home.get('name') or not away.get('name'):
        return None

    league_id = league.get('id', 0)
    league_name = LEAGUE_IDS.get(league_id, league.get('name', ''))
    status = _status_short_to_status(fix.get('status', {}).get('short', 'NS'))

    ht = score.get('halftime', {})
    ft = score.get('fulltime', {})

    return {
        'id': fix.get('id'),
        'home_team': home.get('name', ''),
        'away_team': away.get('name', ''),
        'home_logo': home.get('logo', ''),
        'away_logo': away.get('logo', ''),
        'home_short_code': '',
        'away_short_code': '',
        'home_team_id': home.get('id'),
        'away_team_id': away.get('id'),
        'home_score': goals.get('home'),
        'away_score': goals.get('away'),
        'ht_home_score': ht.get('home'),
        'ht_away_score': ht.get('away'),
        'match_status': status,
        'starting_at': fix.get('date', ''),
        'league_id': league_id,
        'league_name': league_name,
        'league_logo': league.get('logo', ''),
        'league_country': league.get('country', ''),
        'season': league.get('season'),
    }


class ApiFootballProxy:
    """Cached proxy for API-Football. One instance shared across all requests."""

    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()
        self._polling = False
        self._poll_thread = None

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
        if not self._polling:
            self._start_polling()
        cached = self.get_cache('livescores', ttl=150)
        if cached is not None:
            return cached
        return self._fetch_livescores()

    def _fetch_livescores(self):
        try:
            body = _make_request('fixtures', {'live': 'all'})
            fixtures = []
            for item in body.get('response', []):
                f = _parse_fixture(item)
                if f:
                    fixtures.append(f)

            result = {'fixtures': fixtures, 'count': len(fixtures), 'cached_at': time.time()}
            self.set_cache('livescores', result)
            print(f"✅ Live scores cached: {len(fixtures)} matches in play")
            return result
        except Exception as e:
            print(f"⚠️ Livescores fetch error: {e}")
            with self._lock:
                entry = self._cache.get('livescores')
                if entry:
                    return entry['data']
            return {'fixtures': [], 'count': 0, 'error': str(e)}

    # ── Fixtures by date (cached 10 min) ──

    def get_fixtures(self, date_str):
        cache_key = f"fixtures_{date_str}"
        cached = self.get_cache(cache_key, ttl=600)
        if cached is not None:
            return cached
        return self._fetch_fixtures(date_str)

    def _fetch_fixtures(self, date_str):
        try:
            body = _make_request('fixtures', {'date': date_str, 'timezone': 'UTC'})
            fixtures = []
            for item in body.get('response', []):
                f = _parse_fixture(item)
                if f:
                    fixtures.append(f)

            result = {'fixtures': fixtures, 'count': len(fixtures), 'date': date_str, 'cached_at': time.time()}
            self.set_cache(f"fixtures_{date_str}", result)
            print(f"✅ Fixtures cached for {date_str}: {len(fixtures)} matches")
            return result
        except Exception as e:
            print(f"⚠️ Fixtures fetch error for {date_str}: {e}")
            return {'fixtures': [], 'count': 0, 'date': date_str, 'error': str(e)}

    # ── Leagues (cached 24 hours) ──

    def get_leagues(self):
        cached = self.get_cache('leagues', ttl=86400)
        if cached is not None:
            return cached
        return self._fetch_leagues()

    def _fetch_leagues(self):
        try:
            season = datetime.now().year if datetime.now().month >= 8 else datetime.now().year - 1
            body = _make_request('leagues', {'current': 'true', 'season': season})
            leagues = []
            for item in body.get('response', []):
                lg = item.get('league', {})
                country = item.get('country', {})
                leagues.append({
                    'id': lg.get('id'),
                    'name': lg.get('name', ''),
                    'logo': lg.get('logo', ''),
                    'country': country.get('name', ''),
                    'country_logo': country.get('flag', ''),
                    'active': True,
                })

            result = {'leagues': leagues, 'count': len(leagues), 'cached_at': time.time()}
            self.set_cache('leagues', result)
            print(f"✅ Leagues cached: {len(leagues)}")
            return result
        except Exception as e:
            print(f"⚠️ Leagues fetch error: {e}")
            return {'leagues': [], 'count': 0, 'error': str(e)}

    # ── Background polling ──

    def _start_polling(self):
        if self._polling:
            return
        self._polling = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()
        print("🔄 Started background livescore polling (every 2 min)")

    def _poll_loop(self):
        while self._polling:
            try:
                self._fetch_livescores()
            except Exception as e:
                print(f"⚠️ Poll error: {e}")
            time.sleep(120)

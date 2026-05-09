"""
Fetch today's fixtures from API-Football (api-sports.io) and generate AI predictions + slip.
Supports mixed markets: Over/Under, 1X2, BTTS, Double Chance, Team Goals, Half Goals.
"""
import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

APIFOOTBALL_KEY = os.environ.get('APIFOOTBALL_KEY', 'da7a6fc2f03e7fb7994995143d29358f')
APIFOOTBALL_BASE = 'https://v3.football.api-sports.io'


def _get(path, params):
    qs = '&'.join(f"{k}={v}" for k, v in params.items())
    url = f"{APIFOOTBALL_BASE}/{path}?{qs}"
    req = urllib.request.Request(url, headers={'x-apisports-key': APIFOOTBALL_KEY})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


def get_current_season():
    now = datetime.now()
    return now.year if now.month >= 8 else now.year - 1


# League IDs — API-Football IDs (entirely different from SportMonks numbering)
LEAGUE_IDS = {
    # UEFA Competitions
    2: 'Champions League',
    3: 'Europa League',
    848: 'Conference League',
    # England
    39: 'Premier League',
    40: 'Championship',
    45: 'FA Cup',
    48: 'Carabao Cup',
    # Netherlands
    88: 'Eredivisie',
    # Germany
    78: 'Bundesliga',
    79: 'Bundesliga 2',
    # Austria
    218: 'Austrian Bundesliga',
    # Belgium
    144: 'Pro League',
    # Croatia
    210: '1. HNL',
    # Denmark
    119: 'Superliga',
    # France
    61: 'Ligue 1',
    62: 'Ligue 2',
    # Italy
    135: 'Serie A',
    136: 'Serie B',
    137: 'Coppa Italia',
    # Norway
    103: 'Eliteserien',
    # Poland
    106: 'Ekstraklasa',
    # Portugal
    94: 'Liga Portugal',
    95: 'Liga Portugal 2',
    # Scotland
    179: 'Premiership',
    # Spain
    140: 'La Liga',
    141: 'La Liga 2',
    143: 'Copa Del Rey',
    # Sweden
    113: 'Allsvenskan',
    # Greece
    197: 'Super League',
    # Turkey
    203: 'Super Lig',
    # Ukraine
    333: 'Premier League (Ukraine)',
}

# Cup competition IDs — require stronger stats evidence for team goal markets
CUP_LEAGUE_IDS = {45, 48, 137, 143}  # FA Cup, Carabao Cup, Coppa Italia, Copa Del Rey

LEAGUE_FILTER = set(LEAGUE_IDS.keys())

# Map bookmaker lines to our AI markets
LINE_TO_AI_MARKET = {
    0.5: 'fh_over_05',
    1.5: 'ft_over_15',
    2.5: 'ft_over_25',
    3.5: 'ft_over_25',
}

LINE_LABELS = {
    0.5: 'Over 0.5 Goals',
    1.5: 'Over 1.5 Goals',
    2.5: 'Over 2.5 Goals',
    3.5: 'Over 3.5 Goals',
}

AI_MARKET_MAP = {
    'home_to_score_yes': 'home_over_05',
    'away_to_score_yes': 'away_over_05',
    'fh_over_05': 'fh_over_05',
    'sh_over_05': 'sh_over_05',
    'home_over_05': 'home_over_05',
    'away_over_05': 'away_over_05',
    'btts_yes': 'btts_yes',
    'home_win': 'home_win',
    'away_win': 'away_win',
    'double_chance_home_draw': 'dc_home_draw',
    'double_chance_away_draw': 'dc_away_draw',
    'double_chance_home_away': 'dc_home_away',
    'draw': 'draw',
    'btts_no': 'btts_no',
    'home_over_15': 'home_over_15',
    'away_over_15': 'away_over_15',
    'fh_under_05': 'fh_under_05',
    'sh_under_05': 'sh_under_05',
}

AI_MARKET_FALLBACK = {
    'btts_yes': 'ft_over_15',
    'home_win': 'home_over_15',
    'away_win': 'away_over_15',
    'dc_home_draw': 'home_over_05',
    'dc_away_draw': 'away_over_05',
    'dc_home_away': 'ft_over_15',
    'ft_over_25': 'ft_over_15',
    'draw': 'ft_over_15',
    'btts_no': 'ft_over_15',
    'home_over_15': 'ft_over_15',
    'away_over_15': 'ft_over_15',
    'fh_under_05': 'fh_over_05',
    'sh_under_05': 'sh_over_05',
    'ft_under_25': 'ft_under_35',
    'ft_under_35': 'ft_under_15',
    'ft_under_15': 'ft_under_15',
}


def fetch_todays_fixtures():
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    return fetch_fixtures_by_date(today, no_league_filter=True)


def fetch_fixtures_for_rollover(date_str):
    """Fetch fixtures from ALL leagues for Rollover picks."""
    return fetch_fixtures_by_date(date_str, no_league_filter=True)


def fetch_fixtures_by_date(date_str, no_league_filter=False):
    fixtures = _fetch_fixtures_for_date(date_str, no_league_filter=no_league_filter)

    if not fixtures:
        try:
            from utils.football_data_fallback import fetch_fallback_fixtures
            fixtures = fetch_fallback_fixtures(date_str)
        except Exception as e:
            print(f"⚠️ Fallback import/fetch error: {e}")

    fixtures.sort(key=lambda f: f.get('commence_time', ''))
    print(f"✅ Fetched {len(fixtures)} fixtures for {date_str}")
    return fixtures


def _fetch_fixtures_for_date(date_str, no_league_filter=False):
    """Fetch fixtures + odds + predictions + injuries for a date from API-Football."""
    # Step 1: fetch fixtures
    raw_fixtures = _fetch_raw_fixtures(date_str)
    if not raw_fixtures:
        return []

    # Step 2: fetch odds and build fixture_id → markets map
    odds_map = _fetch_odds_map(date_str)

    # Step 3: identify fixtures without bookmaker odds — they need predictions to qualify.
    no_odds_ids = []
    for item in raw_fixtures:
        league_id = (item.get('league') or {}).get('id', 0)
        if not no_league_filter and league_id not in LEAGUE_FILTER:
            continue
        fid = (item.get('fixture') or {}).get('id')
        if fid and not odds_map.get(fid):
            no_odds_ids.append(fid)

    predictions_map = {}
    injuries_map    = {}
    try:
        from utils.apifootball_predictions import (
            fetch_predictions_for_fixtures,
            fetch_injuries_for_fixtures,
        )
        # Only fetch predictions for fixtures that LACK bookmaker odds.
        # Fixtures with bookmaker odds use XGBoost + real odds (no extra API call needed).
        # Fixtures without odds NEED predictions to derive lines and qualify at all.
        # Cap at 50 to avoid timing out the web request handler.
        predictions_map = fetch_predictions_for_fixtures(no_odds_ids[:50])

        # Injuries: only for fixtures we fetched predictions for (already limited)
        injuries_map = fetch_injuries_for_fixtures(list(predictions_map.keys())[:30])
    except Exception as e:
        print(f"⚠️ Predictions/injuries fetch skipped: {e}")

    # Step 4: parse and merge
    fixtures = []
    for item in raw_fixtures:
        league_id = (item.get('league') or {}).get('id', 0)
        if not no_league_filter and league_id not in LEAGUE_FILTER:
            continue
        fid        = (item.get('fixture') or {}).get('id')
        bookmakers = odds_map.get(fid, [])
        prediction = predictions_map.get(fid)
        injuries   = injuries_map.get(fid)
        fixture    = _parse_fixture(item, bookmakers, prediction=prediction,
                                    injuries=injuries, fixture_id=fid)
        if fixture:
            fixtures.append(fixture)

    print(f"  📅 {date_str}: {len(fixtures)} fixtures "
          f"({len(predictions_map)} with predictions, "
          f"{len(injuries_map)} with injuries)")
    return fixtures


def _fetch_raw_fixtures(date_str):
    """GET /fixtures?date={date}&timezone=UTC, handles pagination."""
    items = []
    try:
        body = _get('fixtures', {'date': date_str, 'timezone': 'UTC'})
        items.extend(body.get('response', []))
        # API-Football paginates at 20 results — check for more pages
        paging = body.get('paging', {})
        total_pages = paging.get('total', 1)
        for page in range(2, total_pages + 1):
            body2 = _get('fixtures', {'date': date_str, 'timezone': 'UTC', 'page': page})
            items.extend(body2.get('response', []))
    except Exception as e:
        print(f"⚠️ Fixtures fetch error for {date_str}: {e}")
    return items


def _fetch_odds_map(date_str):
    """GET /odds?date={date} → {fixture_id: bookmakers_list}"""
    odds_map = {}
    try:
        body = _get('odds', {'date': date_str})
        for entry in body.get('response', []):
            fix_id = (entry.get('fixture') or {}).get('id')
            if fix_id:
                odds_map[fix_id] = entry.get('bookmakers', [])
        # Handle pagination for odds
        paging = body.get('paging', {})
        total_pages = paging.get('total', 1)
        for page in range(2, min(total_pages + 1, 6)):  # cap at 5 pages
            body2 = _get('odds', {'date': date_str, 'page': page})
            for entry in body2.get('response', []):
                fix_id = (entry.get('fixture') or {}).get('id')
                if fix_id and fix_id not in odds_map:
                    odds_map[fix_id] = entry.get('bookmakers', [])
    except Exception as e:
        print(f"⚠️ Odds fetch error for {date_str}: {e}")
    return odds_map


def _parse_fixture(item, bookmakers=None, prediction=None, injuries=None, fixture_id=None):
    """Parse one API-Football fixture item + its bookmakers into our fixture dict."""
    try:
        fix    = item.get('fixture', {})
        league = item.get('league', {})
        teams  = item.get('teams', {})

        home = teams.get('home', {})
        away = teams.get('away', {})
        if not home.get('name') or not away.get('name'):
            return None

        league_id   = league.get('id', 0)
        season      = league.get('season', get_current_season())
        league_name = LEAGUE_IDS.get(league_id, league.get('name', f'League {league_id}'))

        # Parse odds markets from bookmakers
        lines, markets = _parse_bookmakers(bookmakers or [])

        # Record opening odds for movement tracking (no-op if already recorded)
        fid = fixture_id or fix.get('id')
        if fid and lines:
            try:
                from utils.apifootball_predictions import record_opening_odds
                for point, line_data in lines.items():
                    record_opening_odds(fid, f'over_{point}',  line_data.get('over', 0))
                    record_opening_odds(fid, f'under_{point}', line_data.get('under', 0))
            except Exception:
                pass

        # No bookmaker odds — try to derive from API-Football prediction
        odds_source = 'bookmaker'
        if not lines and not markets:
            if prediction:
                from utils.apifootball_predictions import derive_market_odds
                lines, markets = derive_market_odds(prediction)
                odds_source = 'prediction'
            else:
                # No bookmaker odds and no prediction (e.g. odds API quota exhausted).
                # Use conservative default odds so XGBoost can still evaluate the fixture.
                lines = {
                    1.5: {'over_odds': 1.44, 'under_odds': 2.60},
                    2.5: {'over_odds': 1.90, 'under_odds': 1.95},
                }
                markets = {
                    'fulltime_result': {'home': 2.20, 'draw': 3.30, 'away': 3.20},
                    'double_chance': {'home_draw': 1.35, 'away_draw': 1.50, 'home_away': 1.40},
                    'btts': {'yes': 1.80, 'no': 2.00},
                }
                odds_source = 'default'

        return {
            'home_team':     home.get('name', ''),
            'away_team':     away.get('name', ''),
            'home_team_id':  home.get('id'),
            'away_team_id':  away.get('id'),
            'season':        season,
            'commence_time': fix.get('date', ''),
            'league':        league_id,
            'league_name':   league_name,
            'league_logo':   league.get('logo', ''),
            'home_logo':     home.get('logo', ''),
            'away_logo':     away.get('logo', ''),
            'home_short_code': '',
            'away_short_code': '',
            'lines':         lines,
            'markets':       markets,
            'odds_source':   odds_source,
            'fixture_id':    fid,
            'af_prediction': prediction,   # for blending in _generate_match_options
            'af_injuries':   injuries,     # for injury adjustment
        }
    except Exception:
        return None


def _parse_bookmakers(bookmakers):
    """
    Parse API-Football bookmakers list into (lines, markets).
    Uses best (lowest) odds across all bookmakers per market/value.
    """
    lines = {}          # {total_float: {'over': best, 'under': best}}
    fulltime_result = {}
    double_chance = {}
    btts = {}
    home_to_score = {}
    away_to_score = {}
    first_half_goals = {}
    second_half_goals = {}
    home_goals = {}
    away_goals = {}

    for bk in bookmakers:
        for bet in bk.get('bets', []):
            bet_id = bet.get('id')
            bet_name = (bet.get('name') or '').lower()
            values = bet.get('values', [])

            # Match Winner (1X2)
            if bet_id == 1 or 'match winner' in bet_name:
                for v in values:
                    lbl = str(v.get('value') or '').strip()
                    odd = _safe_float(v.get('odd'))
                    if odd is None:
                        continue
                    key = _normalize_1x2_label(lbl)
                    _update_best_low(fulltime_result, key, odd)

            # Goals Over/Under (full time)
            elif bet_id == 5 or ('goals over/under' in bet_name and 'half' not in bet_name and 'home' not in bet_name and 'away' not in bet_name):
                for v in values:
                    lbl = str(v.get('value') or '').strip()  # e.g. "Over 2.5"
                    odd = _safe_float(v.get('odd'))
                    if odd is None:
                        continue
                    parts = lbl.split()
                    if len(parts) != 2:
                        continue
                    direction = parts[0].lower()
                    total = _safe_float(parts[1])
                    if total is None:
                        continue
                    if total not in lines:
                        lines[total] = {}
                    if direction == 'over':
                        if 'over' not in lines[total] or odd < lines[total]['over']:
                            lines[total]['over'] = odd
                    elif direction == 'under':
                        if 'under' not in lines[total] or odd < lines[total]['under']:
                            lines[total]['under'] = odd

            # Both Teams Score
            elif bet_id == 7 or 'both teams score' in bet_name or 'both teams to score' in bet_name:
                for v in values:
                    lbl = str(v.get('value') or '').strip().lower()
                    odd = _safe_float(v.get('odd'))
                    if odd:
                        _update_best_low(btts, lbl, odd)

            # Double Chance
            elif bet_id == 8 or 'double chance' in bet_name:
                for v in values:
                    lbl = str(v.get('value') or '').strip()
                    odd = _safe_float(v.get('odd'))
                    if odd is None:
                        continue
                    key = _normalize_dc_label(lbl)
                    if key:
                        _update_best_low(double_chance, key, odd)

            # Home Team Score a Goal
            elif bet_id == 6 or 'home team score' in bet_name:
                for v in values:
                    lbl = str(v.get('value') or '').strip().lower()
                    odd = _safe_float(v.get('odd'))
                    if odd:
                        _update_best_low(home_to_score, lbl, odd)

            # Away Team Score a Goal
            elif bet_id == 35 or 'away team score' in bet_name:
                for v in values:
                    lbl = str(v.get('value') or '').strip().lower()
                    odd = _safe_float(v.get('odd'))
                    if odd:
                        _update_best_low(away_to_score, lbl, odd)

            # 1st Half Goals Over/Under
            elif bet_id == 10 or ('first half' in bet_name and 'goal' in bet_name):
                _parse_ou_bet(first_half_goals, values)

            # 2nd Half Goals Over/Under
            elif bet_id == 33 or ('second half' in bet_name and 'goal' in bet_name):
                _parse_ou_bet(second_half_goals, values)

            # Home Team Goals Over/Under
            elif bet_id == 13 or ('home' in bet_name and 'goals over' in bet_name):
                _parse_ou_bet(home_goals, values)

            # Away Team Goals Over/Under
            elif bet_id == 14 or ('away' in bet_name and 'goals over' in bet_name):
                _parse_ou_bet(away_goals, values)

    # Filter lines to useful range with reasonable odds
    available_lines = {}
    for point in [0.5, 1.5, 2.5, 3.5]:
        if point in lines and 'over' in lines[point]:
            odd = lines[point]['over']
            if 1.01 <= odd <= 5.0:
                available_lines[point] = {
                    'over_odds': odd,
                    'under_odds': lines[point].get('under', 3.0),
                }

    markets = {}
    if fulltime_result:
        markets['fulltime_result'] = fulltime_result
    if double_chance:
        markets['double_chance'] = double_chance
    if btts:
        markets['btts'] = btts
    if home_to_score:
        markets['home_to_score'] = home_to_score
    if away_to_score:
        markets['away_to_score'] = away_to_score
    if first_half_goals:
        markets['first_half_goals'] = first_half_goals
    if second_half_goals:
        markets['second_half_goals'] = second_half_goals
    if home_goals:
        markets['home_goals'] = home_goals
    if away_goals:
        markets['away_goals'] = away_goals

    return available_lines, markets


def _parse_ou_bet(target, values):
    """Parse Over/Under bet values (e.g. 'Over 0.5', 'Under 0.5') into target dict."""
    for v in values:
        lbl = str(v.get('value') or '').strip()
        odd = _safe_float(v.get('odd'))
        if odd is None:
            continue
        parts = lbl.split()
        if len(parts) != 2:
            continue
        direction = parts[0].lower()
        total = _safe_float(parts[1])
        if total is None:
            continue
        if total not in target:
            target[total] = {}
        if direction == 'over':
            if 'over' not in target[total] or odd < target[total]['over']:
                target[total]['over'] = odd
        elif direction == 'under':
            if 'under' not in target[total] or odd < target[total]['under']:
                target[total]['under'] = odd


def _safe_float(v):
    if v is None:
        return None
    try:
        f = float(v)
        return f if f > 0 else None
    except (ValueError, TypeError):
        return None


def _update_best_low(d, key, value):
    if key and value and value > 1.0:
        if key not in d or value < d[key]:
            d[key] = value


def _normalize_1x2_label(label):
    l = label.lower().strip()
    if l in ('home', '1'):
        return 'home'
    if l in ('draw', 'x'):
        return 'draw'
    if l in ('away', '2'):
        return 'away'
    return ''


def _normalize_dc_label(label):
    l = label.lower().strip()
    if ('home' in l and 'draw' in l) or l in ('1x', 'x1', 'home/draw', 'draw/home'):
        return 'home_draw'
    if ('away' in l and 'draw' in l) or l in ('x2', '2x', 'draw/away', 'away/draw'):
        return 'away_draw'
    if ('home' in l and 'away' in l) or l in ('12', '1 or 2', 'home/away', 'away/home'):
        return 'home_away'
    return ''


def _generate_match_options(fixtures, predictor, stats_calculator, sm_stats=None, af_stats=None, free_mode=False):
    """
    Generate all match options from all markets for a list of fixtures.
    Integrates API-Football live stats + standings + statistical qualification + edge calculation.
    af_stats takes priority over sm_stats for backward compatibility.
    """
    from utils.stat_qualifier import passes_odds_safety, qualify_and_score, confidence_label
    from utils.apifootball_stats import get_team_standing

    live_stats = af_stats or sm_stats
    match_options = []

    for fix in fixtures:
        home = fix['home_team']
        away = fix['away_team']
        markets = fix.get('markets', {})

        home_id = fix.get('home_team_id')
        away_id = fix.get('away_team_id')
        league_id = fix.get('league')
        season = fix.get('season', get_current_season())
        is_cup = league_id in CUP_LEAGUE_IDS

        home_live = None
        away_live = None
        h2h_data = None
        standings_ctx = None

        if live_stats and home_id and away_id:
            try:
                home_live = live_stats.fetch_team_stats(home_id, league_id, season)
                away_live = live_stats.fetch_team_stats(away_id, league_id, season)
                h2h_data = live_stats.fetch_h2h(home_id, away_id)
            except Exception as e:
                print(f"⚠️ Live stats error for {home} vs {away}: {e}")

        if live_stats and league_id and home_id and away_id:
            try:
                home_standing = get_team_standing(league_id, home_id, season)
                away_standing = get_team_standing(league_id, away_id, season)
                if home_standing or away_standing:
                    standings_ctx = {'home': home_standing, 'away': away_standing}
                    if home_standing and away_standing:
                        print(f"  📊 {home} #{home_standing['position']} ({home_standing['zone']}) vs {away} #{away_standing['position']} ({away_standing['zone']})")
            except Exception as e:
                print(f"⚠️ Standings error for {home} vs {away}: {e}")

        league_tendency = None  # placeholder for future league-specific adjustments
        primary_line = next(iter(fix['lines'].values()), {})

        af_pred = fix.get('af_prediction')

        # ── Primary path: API-Football predictions ────────────────────────────
        # When available, use API-Football's data as the sole probability source.
        # Their global database (millions of matches, every league) is far more
        # reliable than our XGBoost model (24k matches, mostly top European leagues).
        # XGBoost only runs as a fallback when API-Football has no prediction.
        if af_pred:
            try:
                from utils.apifootball_predictions import af_prediction_to_ai_pred
                ai_pred = af_prediction_to_ai_pred(af_pred)
            except Exception as e:
                print(f"⚠️ af_prediction_to_ai_pred failed for {home} vs {away}: {e}")
                af_pred = None   # fall through to XGBoost

        # ── Fallback path: XGBoost model ──────────────────────────────────────
        if not af_pred:
            if home_live and away_live:
                features = _build_features_from_live(
                    home_live, away_live,
                    over15_odds=primary_line.get('over_odds', 1.5),
                    under15_odds=primary_line.get('under_odds', 2.5),
                )
            else:
                features = stats_calculator.build_match_features(
                    home, away,
                    over15_odds=primary_line.get('over_odds', 1.5),
                    under15_odds=primary_line.get('under_odds', 2.5),
                )
            ai_pred = predictor.predict_match(features)

        # ── Apply injury adjustments ──────────────────────────────────────────
        injuries = fix.get('af_injuries')
        if injuries:
            try:
                from utils.apifootball_predictions import apply_injury_adjustment
                ai_pred = apply_injury_adjustment(ai_pred, injuries)
            except Exception:
                pass

        base_info = {
            'home_team': home,
            'away_team': away,
            'commence_time': fix['commence_time'],
            'league': fix['league'],
            'league_name': fix.get('league_name', ''),
            'league_logo': fix.get('league_logo', ''),
            'home_logo': fix.get('home_logo', ''),
            'away_logo': fix.get('away_logo', ''),
            'home_short_code': fix.get('home_short_code', ''),
            'away_short_code': fix.get('away_short_code', ''),
            'all_predictions': {k: round(float(v), 3) for k, v in ai_pred.items()},
            'home_form': _build_form_summary(home_live, 'home') if home_live else None,
            'away_form': _build_form_summary(away_live, 'away') if away_live else None,
            'h2h': h2h_data,
            'standings': standings_ctx,
        }

        def _try_add(market_label, odds, ai_market_key, line=None, source='api'):
            if not passes_odds_safety(market_label, odds, free_mode=free_mode):
                return
            actual_key = ai_market_key
            if actual_key not in ai_pred:
                return  # No trained model for this market — don't guess
            raw_ai_prob = float(ai_pred.get(actual_key, 0.5))

            # Apply league-specific tendency adjustments
            lab = market_label.lower()
            if league_tendency:
                if 'over' in lab and 'goal' in lab:
                    raw_ai_prob *= league_tendency.get('over_boost', 1.0)
                    raw_ai_prob *= league_tendency.get('over_dampen', 1.0)
                if 'under' in lab and 'goal' in lab:
                    raw_ai_prob *= league_tendency.get('under_boost', 1.0)
                    raw_ai_prob *= league_tendency.get('under_dampen', 1.0)
                if lab in ('home win', 'away win', 'draw'):
                    raw_ai_prob *= league_tendency.get('result_dampen', 1.0)
                if lab == 'home win':
                    raw_ai_prob *= league_tendency.get('home_boost', 1.0)
                raw_ai_prob = min(0.97, raw_ai_prob)

            qual = qualify_and_score(
                market_label, odds, raw_ai_prob,
                home_live, away_live, h2h_data,
                standings=standings_ctx,
            )
            if qual is None:
                return

            # Apply odds movement multiplier to composite_score.
            # Sharp money shortening odds = stronger signal → boost score.
            movement_mult = 1.0
            fid = fix.get('fixture_id')
            if fid:
                try:
                    from utils.apifootball_predictions import get_odds_movement
                    movement_mult = get_odds_movement(
                        fid,
                        f'over_{line}' if line else market_label,
                        odds,
                    )
                except Exception:
                    pass

            opt = dict(base_info)
            opt.update({
                'line': line,
                'market': market_label,
                'odds': odds,
                'ai_prob': qual['ai_prob'],
                'confidence': confidence_label(qual['edge']),
                'edge': qual['edge'],
                'stability': qual['stability'],
                'composite_score': qual['composite_score'] * movement_mult,
                'source': source,
            })
            match_options.append(opt)

        # === Over/Under lines ===
        for point, line_data in fix['lines'].items():
            odds = line_data['over_odds']
            ai_market = LINE_TO_AI_MARKET.get(point, 'ft_over_15')
            label = LINE_LABELS.get(point, f'Over {point} Goals')
            _try_add(label, odds, ai_market, line=point)

            under_odds = line_data.get('under_odds', 0)
            if under_odds > 0 and point >= 2.5:
                under_label = f'Under {point} Goals'
                if point == 2.5:
                    under_ai_market = 'ft_under_25'
                elif point == 3.5:
                    under_ai_market = 'ft_under_35'
                else:
                    under_ai_market = 'ft_under_15'
                _try_add(under_label, under_odds, under_ai_market, line=point)

        # === BTTS Yes ===
        btts_m = markets.get('btts', {})
        if 'yes' in btts_m:
            _try_add('Both Teams to Score', btts_m['yes'], AI_MARKET_MAP['btts_yes'])

        # === Fulltime Result ===
        ftr = markets.get('fulltime_result', {})
        if 'home' in ftr:
            _try_add('Home Win', ftr['home'], AI_MARKET_MAP['home_win'])
        if 'away' in ftr:
            _try_add('Away Win', ftr['away'], AI_MARKET_MAP['away_win'])

        # === Double Chance ===
        dc = markets.get('double_chance', {})
        if 'home_draw' in dc:
            _try_add('Double Chance (1X)', dc['home_draw'], AI_MARKET_MAP['double_chance_home_draw'])
        if 'away_draw' in dc:
            _try_add('Double Chance (X2)', dc['away_draw'], AI_MARKET_MAP['double_chance_away_draw'])
        if 'home_away' in dc:
            _try_add('Double Chance (12)', dc['home_away'], AI_MARKET_MAP['double_chance_home_away'])

        # === Team Goals ===
        hts = markets.get('home_to_score', {})
        if 'yes' in hts:
            _try_add('Home to Score', hts['yes'], AI_MARKET_MAP['home_to_score_yes'])
        ats = markets.get('away_to_score', {})
        if 'yes' in ats:
            _try_add('Away to Score', ats['yes'], AI_MARKET_MAP['away_to_score_yes'])

        # === Half Goals ===
        fhg = markets.get('first_half_goals', {})
        if 0.5 in fhg and 'over' in fhg[0.5]:
            _try_add('1st Half Over 0.5', fhg[0.5]['over'], AI_MARKET_MAP['fh_over_05'])
        shg = markets.get('second_half_goals', {})
        if 0.5 in shg and 'over' in shg[0.5]:
            _try_add('2nd Half Over 0.5', shg[0.5]['over'], AI_MARKET_MAP['sh_over_05'])

        # === Home/Away Goals Over 0.5 ===
        hg = markets.get('home_goals', {})
        if 0.5 in hg and 'over' in hg[0.5]:
            home_venue_avg = (home_live or {}).get('home_avg_scored', 1.5)
            if not is_cup or home_venue_avg >= 1.2:
                _try_add('Home Over 0.5 Goals', hg[0.5]['over'], AI_MARKET_MAP['home_over_05'])
        ag = markets.get('away_goals', {})
        if 0.5 in ag and 'over' in ag[0.5]:
            away_venue_avg = (away_live or {}).get('away_avg_scored', 1.0)
            if not is_cup or away_venue_avg >= 1.0:
                _try_add('Away Over 0.5 Goals', ag[0.5]['over'], AI_MARKET_MAP['away_over_05'])

        # === Draw ===
        if 'draw' in ftr:
            _try_add('Draw', ftr['draw'], AI_MARKET_MAP['draw'])

        # === BTTS No ===
        if 'no' in btts_m:
            _try_add('BTTS No', btts_m['no'], AI_MARKET_MAP['btts_no'])

        # === 1st/2nd Half Under 0.5 ===
        if 0.5 in fhg and 'under' in fhg[0.5]:
            _try_add('1st Half Under 0.5', fhg[0.5]['under'], AI_MARKET_MAP['fh_under_05'])
        if 0.5 in shg and 'under' in shg[0.5]:
            _try_add('2nd Half Under 0.5', shg[0.5]['under'], AI_MARKET_MAP['sh_under_05'])

        # === Home/Away Over 1.5 & 2.5 Goals ===
        if 1.5 in hg and 'over' in hg[1.5]:
            _try_add('Home Over 1.5 Goals', hg[1.5]['over'], AI_MARKET_MAP['home_over_15'])
        if 2.5 in hg and 'over' in hg[2.5]:
            _try_add('Home Over 2.5 Goals', hg[2.5]['over'], 'ft_over_25')
        if 1.5 in ag and 'over' in ag[1.5]:
            _try_add('Away Over 1.5 Goals', ag[1.5]['over'], AI_MARKET_MAP['away_over_15'])
        if 2.5 in ag and 'over' in ag[2.5]:
            _try_add('Away Over 2.5 Goals', ag[2.5]['over'], 'ft_over_25')

    return match_options


def _build_features_from_live(home_stats, away_stats, over15_odds=1.5, under15_odds=2.5):
    """Build feature dict for XGBoost models using API-Football team stats."""
    home_attack = home_stats['avg_goals_scored'] / max(away_stats['avg_goals_conceded'], 0.3)
    away_attack = away_stats['avg_goals_scored'] / max(home_stats['avg_goals_conceded'], 0.3)

    # Use actual minute-bucket data from API-Football; fall back to approximation
    home_fh = home_stats.get('avg_first_half_goals', home_stats['avg_goals_scored'] * 0.45)
    away_fh = away_stats.get('avg_first_half_goals', away_stats['avg_goals_scored'] * 0.42)

    return {
        'home_goals_per_game': home_stats['avg_goals_scored'],
        'home_goals_conceded_per_game': home_stats['avg_goals_conceded'],
        'home_over15_rate': home_stats['over15_rate'],
        'home_over05_rate': home_stats.get('scored_in_rate', 0.78),
        'home_first_half_goals': home_fh,
        'away_goals_per_game': away_stats['avg_goals_scored'],
        'away_goals_conceded_per_game': away_stats['avg_goals_conceded'],
        'away_over15_rate': away_stats['over15_rate'],
        'away_over05_rate': away_stats.get('scored_in_rate', 0.70),
        'away_first_half_goals': away_fh,
        'home_home_goals': home_stats['home_avg_scored'],
        'home_home_conceded': home_stats['home_avg_conceded'],
        'away_away_goals': away_stats['away_avg_scored'],
        'away_away_conceded': away_stats['away_avg_conceded'],
        'total_expected_goals': home_stats['home_avg_scored'] + away_stats['away_avg_scored'],
        'defensive_strength': home_stats['home_avg_conceded'] + away_stats['away_avg_conceded'],
        'over15_odds': over15_odds,
        'under15_odds': under15_odds,
        # Extended features
        'home_btts_rate': home_stats.get('btts_rate', 0.55),
        'away_btts_rate': away_stats.get('btts_rate', 0.55),
        'home_clean_sheet_rate': home_stats.get('clean_sheet_rate', 0.30),
        'away_clean_sheet_rate': away_stats.get('clean_sheet_rate', 0.25),
        'home_attack_strength': home_attack,
        'away_attack_strength': away_attack,
        'attack_vs_defense_ratio': home_attack / max(away_attack, 0.3),
        'home_momentum': 0.0,
        'away_momentum': 0.0,
        'home_goals_std': 0.5,
        'away_goals_std': 0.5,
        'home_over25_rate': home_stats.get('over25_rate', 0.45),
        'away_over25_rate': away_stats.get('over25_rate', 0.40),
        'home_scored_in_rate': home_stats.get('scored_in_rate', 0.78),
        'away_scored_in_rate': away_stats.get('scored_in_rate', 0.70),
    }


def build_daily_slip(fixtures, predictor, stats_calculator, max_matches=4, max_odds=2.60, sm_stats=None, af_stats=None, free_mode=False):
    from itertools import product

    live_stats = af_stats or sm_stats
    match_options = _generate_match_options(fixtures, predictor, stats_calculator, af_stats=live_stats, free_mode=free_mode)

    if not match_options:
        return _empty_result(fixtures)

    match_options.sort(key=lambda x: x.get('composite_score', 0), reverse=True)

    fixture_options = {}
    for opt in match_options:
        key = f"{opt['home_team']}_{opt['away_team']}"
        if key not in fixture_options:
            fixture_options[key] = []
        if len(fixture_options[key]) < 3:
            fixture_options[key].append(opt)

    fixture_keys = list(fixture_options.keys())
    num_fixtures = len(fixture_keys)

    if num_fixtures == 0:
        return _empty_result(fixtures)

    best_slip = None
    best_score = -1
    best_count = 0

    for target_count in [4, 3, 2]:
        if num_fixtures < target_count:
            continue
        if best_slip and best_count > target_count:
            break

        from itertools import combinations as combs
        for fixture_combo in combs(range(num_fixtures), target_count):
            option_lists = [fixture_options[fixture_keys[i]] for i in fixture_combo]
            for market_combo in product(*option_lists):
                combined = 1.0
                for pick in market_combo:
                    combined *= pick['odds']

                if combined < 1.50 or combined > max_odds:
                    continue

                avg_composite = sum(p.get('composite_score', 0) for p in market_combo) / len(market_combo)
                ideal_bonus = 1.0
                if 2.00 <= combined <= 2.30:
                    ideal_bonus = 1.25
                elif 1.90 <= combined <= 2.40:
                    ideal_bonus = 1.15
                elif 1.80 <= combined < 1.90:
                    ideal_bonus = 1.05
                elif 1.50 <= combined < 1.80:
                    ideal_bonus = 0.90

                score = avg_composite * ideal_bonus

                if score > best_score:
                    best_score = score
                    best_slip = list(market_combo)
                    best_count = target_count

    if not best_slip:
        for i, a in enumerate(match_options[:10]):
            for j, b in enumerate(match_options[:10]):
                if i >= j:
                    continue
                combined = a['odds'] * b['odds']
                if 1.50 <= combined <= max_odds:
                    best_slip = [a, b]
                    break
            if best_slip:
                break
        if not best_slip and match_options:
            best_slip = [match_options[0]]

    if not best_slip:
        return _empty_result(fixtures)

    combined_odds = 1.0
    for p in best_slip:
        combined_odds *= p['odds']

    return {
        'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'total_fixtures_analyzed': len(fixtures),
        'slip': {
            'matches': _format_slip_matches(best_slip),
            'match_count': len(best_slip),
            'combined_odds': round(combined_odds, 2),
            'slip_confidence': _slip_confidence(best_slip),
        },
        'all_predictions': _format_all_predictions(match_options),
    }


def _empty_result(fixtures):
    return {
        'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'total_fixtures_analyzed': len(fixtures) if fixtures else 0,
        'slip': {
            'matches': [],
            'match_count': 0,
            'combined_odds': 0,
            'slip_confidence': 'NONE',
        },
        'all_predictions': [],
        'message': 'No safe rollover picks today.',
    }


def build_parlay_slip(fixtures, predictor, stats_calculator, num_matches=5, min_odds=1.30, max_odds=3.00, sm_stats=None, af_stats=None, free_mode=False, exclude_matches=None, exclude_match_markets=None, market_penalties=None):
    live_stats = af_stats or sm_stats
    match_options = _generate_match_options(fixtures, predictor, stats_calculator, af_stats=live_stats, free_mode=free_mode)

    filtered = [o for o in match_options if min_odds <= o['odds'] <= max_odds]

    if exclude_matches:
        filtered = [o for o in filtered if f"{o['home_team']}_{o['away_team']}" not in exclude_matches]
        print(f"   After excluding {len(exclude_matches)} matches: {len(filtered)} options remain")

    if exclude_match_markets:
        filtered = [o for o in filtered if f"{o['home_team']}_{o['away_team']}_{o['market']}" not in exclude_match_markets]
        print(f"   After excluding {len(exclude_match_markets)} match+market combos: {len(filtered)} options remain")

    if market_penalties:
        for opt in filtered:
            penalty = market_penalties.get(opt['market'], 1.0)
            if penalty != 1.0:
                opt['composite_score'] = opt.get('composite_score', 0) * penalty

    filtered.sort(key=lambda x: x.get('composite_score', 0), reverse=True)

    slip_matches = []
    combined_odds = 1.0
    used_matches = set()
    market_type_count = {}
    MAX_SAME_MARKET = 2

    for opt in filtered:
        match_key = f"{opt['home_team']}_{opt['away_team']}"
        if match_key in used_matches:
            continue
        market_label = opt['market']
        if market_type_count.get(market_label, 0) >= MAX_SAME_MARKET:
            continue
        slip_matches.append(opt)
        combined_odds *= opt['odds']
        used_matches.add(match_key)
        market_type_count[market_label] = market_type_count.get(market_label, 0) + 1
        if len(slip_matches) >= num_matches:
            break

    if len(slip_matches) < num_matches:
        RELAXED_MAX = 3
        for opt in filtered:
            if len(slip_matches) >= num_matches:
                break
            match_key = f"{opt['home_team']}_{opt['away_team']}"
            if match_key in used_matches:
                continue
            market_label = opt['market']
            if market_type_count.get(market_label, 0) >= RELAXED_MAX:
                continue
            slip_matches.append(opt)
            combined_odds *= opt['odds']
            used_matches.add(match_key)
            market_type_count[market_label] = market_type_count.get(market_label, 0) + 1

    return {
        'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'total_fixtures_analyzed': len(fixtures),
        'slip': {
            'matches': _format_slip_matches(slip_matches),
            'match_count': len(slip_matches),
            'combined_odds': round(combined_odds, 2),
            'slip_confidence': _slip_confidence(slip_matches),
        },
        'all_predictions': _format_all_predictions(match_options),
    }


def _format_slip_matches(matches):
    result = []
    for m in matches:
        entry = {
            'home_team': m['home_team'],
            'away_team': m['away_team'],
            'match': f"{m['home_team']} vs {m['away_team']}",
            'league': _league_name(m['league']),
            'league_logo': m.get('league_logo', ''),
            'home_logo': m.get('home_logo', ''),
            'away_logo': m.get('away_logo', ''),
            'home_short_code': m.get('home_short_code', ''),
            'away_short_code': m.get('away_short_code', ''),
            'kickoff': m['commence_time'],
            'market': m['market'],
            'odds': m['odds'],
            'ai_probability': round(m['ai_prob'] * 100, 1),
            'confidence': m['confidence'],
            'edge': round(m['edge'] * 100, 1),
            'source': m.get('source', 'api'),
            'all_markets': {
                k: {
                    'probability': round(v * 100, 1),
                    'confidence': 'HIGH' if v >= 0.75 else 'MEDIUM' if v >= 0.65 else 'LOW',
                }
                for k, v in m['all_predictions'].items()
            },
        }

        if m.get('home_form'):
            entry['home_form'] = m['home_form']
        if m.get('away_form'):
            entry['away_form'] = m['away_form']

        h2h = m.get('h2h')
        if h2h:
            entry['h2h'] = {
                'played': h2h.get('total_matches', 0),
                'avg_goals': round(h2h.get('avg_goals', 0), 1),
                'btts_pct': round((h2h.get('btts_count', 0) / max(h2h.get('total_matches', 1), 1)) * 100),
                'over25_pct': round((h2h.get('over25_count', 0) / max(h2h.get('total_matches', 1), 1)) * 100),
            }

        standings = m.get('standings')
        if standings:
            s = {}
            if standings.get('home'):
                s['home_pos'] = standings['home'].get('position')
                s['home_pts'] = standings['home'].get('points')
                s['home_zone'] = standings['home'].get('zone')
            if standings.get('away'):
                s['away_pos'] = standings['away'].get('position')
                s['away_pts'] = standings['away'].get('points')
                s['away_zone'] = standings['away'].get('zone')
            if s:
                entry['standings'] = s

        result.append(entry)
    return result


def _format_all_predictions(predictions):
    result = []
    for p in predictions[:20]:
        result.append({
            'home_team': p['home_team'],
            'away_team': p['away_team'],
            'match': f"{p['home_team']} vs {p['away_team']}",
            'league': _league_name(p['league']),
            'league_logo': p.get('league_logo', ''),
            'home_logo': p.get('home_logo', ''),
            'away_logo': p.get('away_logo', ''),
            'home_short_code': p.get('home_short_code', ''),
            'away_short_code': p.get('away_short_code', ''),
            'kickoff': p['commence_time'],
            'market': p['market'],
            'odds': p['odds'],
            'ai_probability': round(p['ai_prob'] * 100, 1),
            'confidence': p['confidence'],
            'edge': round(p['edge'] * 100, 1),
            'composite_score': round(p.get('composite_score', 0), 3),
        })
    return result


def _slip_confidence(matches):
    if not matches:
        return 'NONE'
    high_count = sum(1 for m in matches if m['confidence'] == 'HIGH')
    if high_count == len(matches):
        return 'HIGH'
    if high_count > 0:
        return 'MEDIUM'
    return 'LOW'


def _league_name(league_id):
    if league_id in LEAGUE_IDS:
        return LEAGUE_IDS[league_id]
    return f'League {league_id}'


def _build_form_summary(stats, side):
    if not stats:
        return None
    return {
        'avg_scored': round(stats.get('avg_goals_scored', 0), 1),
        'avg_conceded': round(stats.get('avg_goals_conceded', 0), 1),
        'scored_in_pct': round(stats.get('scored_in_rate', 0) * 100),
        'clean_sheet_pct': round(stats.get('clean_sheet_rate', 0) * 100),
        'over15_pct': round(stats.get('over15_rate', 0) * 100),
        'btts_pct': round(stats.get('btts_rate', 0) * 100),
        'matches': stats.get('matches_played', 0),
    }


# ── Public exports ───────────────────────────────────────────────────────────
generate_match_options = _generate_match_options
format_slip_matches = _format_slip_matches
slip_confidence = _slip_confidence

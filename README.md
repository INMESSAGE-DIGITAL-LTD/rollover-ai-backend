# Rollover AI — Football Prediction Backend

> **Code repository:** GitHub (`vikcy112/rollover-ai-backend`)
> **Live backend:** Render (`https://rollover-ai-backend.onrender.com`)
> **Auto-deploy:** Every push to `main` is automatically deployed to Render.

---

## Architecture

```
SportMonks API  →  XGBoost Models (24 markets)  →  Statistical Qualification
                                                  →  H2H + Standings Context
                                                  →  Market Performance Tracker
                                                  →  Slip Builder (diversity cap)
                                                  →  Firestore Storage
                                                  →  Flutter App
```

### Four-Tab Model

| Tab | Backend Endpoint | Source | Purpose |
|-----|-----------------|--------|---------|
| **Rollover** | `GET /api/today` or rollover slip | Firestore / live | Safest 4-match accumulator |
| **AI Pro** | `GET /api/picks/<date>` | Firestore (cron-generated nightly) | Up to 10 AI-curated picks, strict safety |
| **Free** | `GET /api/free-picks/<date>` | Live on-demand | 6 riskier teaser picks, higher odds |
| **Explore** | `GET /api/fixtures/<date>` | SportMonks (all leagues, no filter) | Full match browser — every game available |

> The **Explore tab is intentionally separate** from the curated picks tabs. It shows the full universe of available fixtures so users can browse any match — not just the 10 the AI selected. Matches already shown in AI Pro or Free tabs are excluded from Explore to avoid duplication.

---

## Prediction Engine

### Markets Available (24+)

**Goals markets:**
- Over 0.5 / 1.5 / 2.5 / 3.5 Goals
- **Under 2.5 Goals** *(newly added — catches defensive, low-scoring fixtures)*
- Under 3.5 / 4.5 Goals
- Both Teams to Score (BTTS Yes / No)

**Team goals:**
- Home Over 0.5 / 1.5 / 2.5 Goals
- Away Over 0.5 / 1.5 / 2.5 Goals
- Home to Score / Away to Score

**Half-time goals:**
- 1st Half Over 0.5 / Under 0.5
- 2nd Half Over 0.5 / Under 0.5

**Match result:**
- Home Win / Away Win / Draw
- Double Chance (1X) / Double Chance (X2) / Double Chance (12)

### How the Score is Calculated

Each candidate pick receives a **composite score**:

```
composite = edge × 0.40 + adjusted_probability × 0.35 + stability × 0.25

where:
  edge              = adjusted_prob − implied_prob (from bookmaker odds)
  adjusted_prob     = XGBoost prediction blended with live team stats + H2H
  stability         = how consistent both teams' recent form supports this market
```

Picks are ranked by composite score. The slip builder takes the top-scoring picks within the requested odds range, subject to the diversity cap.

### Data Sources

| Source | Used For |
|--------|----------|
| **SportMonks API v3** | Live fixture odds, team stats (last 10 games), H2H (last 5 games), league standings, live scores |
| **XGBoost models** (24) | Base AI probability per market, trained on historical CSV data |
| **Google Firestore** | Storing daily AI Pro predictions, reading past results for market tracker |
| **Football-Data.org** | Fallback fixtures when SportMonks returns nothing |

---

## Smart Features

### Market Diversity Cap
The slip builder enforces a maximum of **3 picks of the same market type** per slip. This prevents the old behaviour of generating 8× Double Chance (12) picks.

### H2H-Aware DC(12) Qualification
Double Chance (12) predictions now check H2H draw history:
- ≥ 40% H2H draw rate → prediction is **rejected** (too risky)
- 25–40% H2H draw rate → probability boost is **reduced**

This catches Kudrivka-type fixtures where both teams frequently draw.

### Conservative Home/Away Over 0.5 Scoring
The scored-in rate now uses the **average** of both teams, not the maximum. This prevents Brondby-type errors where the opponent's high away-scoring rate inflated confidence in the home team scoring.

### Market Performance Tracker (Pseudo-Learning)
Before each generation run, the system:
1. Reads the last 7 days of Firestore predictions
2. Fetches actual finished scores from SportMonks
3. Calculates win rate per market type
4. Applies composite score multipliers:

| Win Rate | Multiplier | Effect |
|----------|-----------|--------|
| < 30% | × 0.40 | Strong penalty — market nearly avoided |
| 30–50% | × 0.65 | Moderate penalty |
| 50–60% | × 0.85 | Mild penalty |
| 60–75% | × 1.00 | No change |
| > 75% | × 1.05–1.15 | Small bonus |

This means the model naturally avoids markets that have been losing recently and favours markets that have been winning — without full retraining.

### Under 2.5 Goals
Now evaluated as a real market. Qualification uses:
- Combined average goals from both teams (lower = stronger signal)
- Clean sheet rates
- H2H under-goal rate (weighted 40% when ≥ 3 H2H matches available)

---

## Project Structure

```
rollover-ai-backend/
├── app.py                          # Flask API (all endpoints)
├── cron_generate.py                # Render cron worker (runs daily at 23:00 UTC)
├── firebase_config.py              # Firestore client initialisation
├── history.py                      # SQLite pick history routes
├── requirements.txt
│
├── models/
│   ├── multi_market_predictor.py   # 24 XGBoost models wrapper
│   └── trained/                    # Saved .pkl model files
│
├── services/
│   └── generator.py                # Shared generation logic (used by app + cron)
│
├── utils/
│   ├── fixture_fetcher.py          # SportMonks fixture fetch + slip builder
│   ├── sportmonks_proxy.py         # Cached SportMonks proxy (livescores, fixtures, leagues)
│   ├── sportmonks_stats.py         # Team stats + H2H + standings fetch
│   ├── stat_qualifier.py           # Statistical qualification + edge calculation + safety rules
│   ├── market_tracker.py           # Market performance tracker (pseudo-learning)
│   ├── team_stats.py               # CSV-based team stats fallback
│   └── football_data_fallback.py   # Football-Data.org fallback fetcher
│
└── data/
    └── raw/
        └── all_matches.csv         # Historical training data
```

---

## API Endpoints

### Public

| Endpoint | Description |
|----------|-------------|
| `GET /` | Service info + model count |
| `GET /health` | Health check |
| `GET /api/picks/<date>` | AI Pro picks for a date (reads Firestore, generates on-demand if missing) |
| `GET /api/free-picks/<date>` | Free tab picks (live generation, higher odds range) |
| `GET /api/today` | Quick summary of today's picks |
| `GET /api/livescores` | Live in-play scores (polled every 2 min) |
| `GET /api/fixtures/<date>` | **Explore tab** — all available fixtures (no league filter, paginated) |
| `GET /api/leagues` | All available leagues |
| `GET /api/parlay` | Custom parlay builder |
| `GET /api/history` | Past pick history |
| `POST /api/predict` | Single-match prediction (all markets) |

### Protected (CRON_SECRET required)

| Endpoint | Description |
|----------|-------------|
| `POST /api/generate-daily` | Manual trigger: run AI + save to Firestore |

---

## Cron Schedule

The Render cron job runs `cron_generate.py` daily:

```
Schedule: 0 23 * * *   (23:00 UTC = midnight WAT)
```

Each run:
1. Fetches today's fixtures from SportMonks (filtered to 29 leagues)
2. Runs `get_market_penalties()` — reads last 7 days of Firestore results
3. Runs XGBoost + statistical qualification on all fixtures
4. Writes top 10 picks to `Firestore → daily_predictions/{date}`
5. Backs up to SQLite history
6. Deletes Firestore docs older than 7 days

---

## Safety Rules (SAFETY_RULES)

Per-market odds bounds used by the qualification engine. Picks outside these bounds are discarded regardless of AI probability.

| Market | Min Odds | Sweet Max | Abs Max |
|--------|----------|-----------|---------|
| Double Chance (12) | 1.01 | 1.30 | 1.40 |
| Home/Away Over 0.5 Goals | 1.05 | 1.40 | 1.50 |
| Over 1.5 Goals | 1.10 | 1.45 | 1.57 |
| Under 2.5 Goals | 1.30 | 1.60 | 1.70 |
| Over 2.5 Goals | 1.20 | 1.50 | 1.60 |
| Under 3.5 Goals | 1.20 | 1.55 | 1.60 |
| Both Teams to Score | 1.25 | 1.50 | 1.57 |
| Home Win / Away Win | 1.15 | 1.50 | 1.60 |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SPORTMONKS_TOKEN` | SportMonks API v3 token |
| `CRON_SECRET` | Bearer token for `/api/generate-daily` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to Firebase service account JSON |

---

## Deploying

Push to `main` → Render auto-deploys in ~60 seconds.

```bash
git add .
git commit -m "your change"
git push origin main
```

Render free tier cold-starts after 15 min of inactivity. The first request may take 30–60 seconds. The Flutter app handles this with a loading state.

---

## Explore Tab — Full Match Browser

The Explore tab is the fourth tab in the Flutter app. Unlike the other tabs which show only the AI-curated picks, Explore gives users a **full match browser** — every fixture SportMonks returns for the selected date, minus the games already shown in AI Pro / Free tabs.

### How it works (end-to-end)

```
Flutter ExploreController
  └─ RolloverBackendService.fetchFixtures(dateStr)
       └─ GET /api/fixtures/<date>                 ← Render (app.py)
            └─ SportMonksProxy.get_fixtures()       ← sportmonks_proxy.py
                 └─ SportMonks /fixtures/date/<date>
                      ├─ No league filter (all leagues returned)
                      ├─ 100 results per page
                      └─ Up to 5 pages (500 fixtures max)
```

### Key difference from AI Pro / Free picks

| | AI Pro & Free | Explore |
|-|--------------|---------|
| **Endpoint** | `/api/picks` / `/api/free-picks` | `/api/fixtures/<date>` |
| **League filter** | Yes — 29 specific leagues (`LEAGUE_FILTER`) | **None** — all leagues the SportMonks plan covers |
| **Odds required** | Yes — picks need bookmaker odds to pass qualification | No — raw fixture data, no odds needed |
| **AI analysis** | Full XGBoost + statistical qualification | None — raw match listing only |
| **Pagination** | Single page (≤ 50) | Up to 5 pages (up to 500 fixtures) |
| **Caching** | 10 min in-memory | 10 min in-memory (same proxy cache) |
| **Flutter cache** | None | `GetStorage('explore_cache')` by date |

### What the Flutter app does with it

The `ExploreController` in the Flutter app:
1. Fetches all fixtures from `/api/fixtures/<date>`
2. Calls `FixtureToExplore.convertAll()` to parse them into `ExploreMatch` objects
3. Runs `_excludeCuratedPicks()` — removes any match already shown in AI Pro or Free tabs (matched by home team + away team name)
4. Displays the remaining matches grouped by league, top leagues first
5. Supports: date navigation (today + 7 days back), market filter (All / Over 1.5 / BTTS / Live / etc.), team/league search, league grouping

### Why Explore was empty (fixed)

Previously, `/api/fixtures/<date>` had the same `&filters=fixtureLeagues:{LEAGUE_FILTER}` restriction as the picks endpoint. On quiet days (e.g. mid-week), this returned exactly the same 10 fixtures as the AI picks — so `_excludeCuratedPicks()` removed all of them, leaving Explore blank.

**Fix applied:** `sportmonks_proxy.py → _fetch_fixtures()` now has no league filter and fetches up to 500 fixtures across all available leagues. Weekend days typically return 80–150 fixtures; after excluding 10 AI picks, Explore shows 70–140 matches.

---

## What's Next (Roadmap)

- [ ] Weekly model retraining script using recent SportMonks results
- [ ] `Under 2.5 Goals` appearing in production picks (needs fixtures with combined avg goals < 2.0)
- [ ] Result auto-updater: fetch FT scores and mark Firestore picks as won/lost
- [ ] Push notifications when daily picks are generated

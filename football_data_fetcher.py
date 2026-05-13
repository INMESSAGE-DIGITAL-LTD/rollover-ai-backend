"""
football_data_fetcher.py
========================
Downloads FREE historical match data from football-data.co.uk and uses it to:
  1. Compute real Over/Under/BTTS rates per league per season
  2. Update league_dna.py profiles dynamically
  3. Build a training CSV for XGBoost retraining

WHY football-data.co.uk?
  - 100% FREE, no API key, no rate limits
  - 25+ years of historical data
  - Covers 35+ leagues
  - Each CSV row = one match with: home/away team, goals, full-time result,
    and BOOKMAKER ODDS from 8 providers (Bet365, Pinnacle, Betfair ...)
  - Perfect for training XGBoost on real closing-line odds + outcomes

USAGE
  python football_data_fetcher.py --update          # download + update DNA
  python football_data_fetcher.py --build-training  # build training CSV
  python football_data_fetcher.py --stats           # print league summary table

SCHEDULE (GitHub Actions)
  Run `--update` every Monday via GitHub Actions (free with GitHub Pro).
  Commit updated league_stats.json -- Render redeploys automatically.
"""

import io
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

import requests
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# football-data.co.uk URL template
# Format: https://www.football-data.co.uk/mmz4281/{season}/{division}.csv
# Season: "2425" = 2024/25, "2324" = 2023/24 etc.
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{div}.csv"

# Seasons to download (last 3 seasons + current)
SEASONS = ["2223", "2324", "2425"]

# Map: friendly name -> (division code on football-data.co.uk, API-Football league name)
LEAGUE_MAP: dict[str, tuple[str, str]] = {
    # England
    "E0":  ("E0",  "Premier League"),
    "E1":  ("E1",  "Championship"),
    "E2":  ("E2",  "League One"),
    # Germany
    "D1":  ("D1",  "Bundesliga"),
    "D2":  ("D2",  "2. Bundesliga"),
    # Italy
    "I1":  ("I1",  "Serie A"),
    "I2":  ("I2",  "Serie B"),
    # Spain
    "SP1": ("SP1", "La Liga"),
    "SP2": ("SP2", "La Liga 2"),
    # France
    "F1":  ("F1",  "Ligue 1"),
    "F2":  ("F2",  "Ligue 2"),
    # Netherlands
    "N1":  ("N1",  "Eredivisie"),
    # Belgium
    "B1":  ("B1",  "Pro League"),
    # Portugal
    "P1":  ("P1",  "Primeira Liga"),
    # Scotland
    "SC0": ("SC0", "Scottish Premiership"),
    # Turkey
    "T1":  ("T1",  "Super Lig"),
    # Greece
    "G1":  ("G1",  "Super League"),
}

ALT_BASE_URL = "https://www.football-data.co.uk/new/{country}/{season}.csv"
ALT_LEAGUE_MAP: dict[str, tuple[str, str]] = {}

OUTPUT_DIR = Path(__file__).parent / "data"
STATS_FILE = OUTPUT_DIR / "league_stats.json"
TRAINING_FILE = OUTPUT_DIR / "training_data.csv"


# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD
# ─────────────────────────────────────────────────────────────────────────────

def _download_csv(div: str, season: str) -> pd.DataFrame | None:
    url = BASE_URL.format(season=season, div=div)
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text), on_bad_lines="skip", dtype=str)
        df = df.dropna(how="all")
        return df
    except Exception as e:
        log.warning("Failed to download %s %s: %s", div, season, e)
        return None


def download_all_seasons(div: str) -> pd.DataFrame:
    frames = []
    for season in SEASONS:
        df = _download_csv(div, season)
        if df is not None and not df.empty:
            df["_season"] = season
            df["_div"] = div
            frames.append(df)
            log.info("  + %s %s -- %d rows", div, season, len(df))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# STATS COMPUTATION
# ─────────────────────────────────────────────────────────────────────────────

def _to_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def compute_league_stats(df: pd.DataFrame) -> dict:
    """Compute Over/Under/BTTS rates from a raw football-data.co.uk DataFrame."""
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    if "FTHG" not in df.columns or "FTAG" not in df.columns:
        log.warning("  No FTHG/FTAG columns -- skipping")
        return {}

    df["home_goals"] = _to_float(df["FTHG"])
    df["away_goals"] = _to_float(df["FTAG"])
    df = df.dropna(subset=["home_goals", "away_goals"])

    if len(df) < 20:
        return {}

    df["total_goals"] = df["home_goals"] + df["away_goals"]
    df["btts"] = (df["home_goals"] > 0) & (df["away_goals"] > 0)
    df["ftr"] = df.get("FTR", pd.Series(dtype=str))

    n = len(df)
    stats = {
        "matches": n,
        "avg_goals_pg": round(df["total_goals"].mean(), 3),
        "over15_rate":  round((df["total_goals"] > 1.5).mean(), 3),
        "over25_rate":  round((df["total_goals"] > 2.5).mean(), 3),
        "over35_rate":  round((df["total_goals"] > 3.5).mean(), 3),
        "under15_rate": round((df["total_goals"] < 1.5).mean(), 3),
        "under25_rate": round((df["total_goals"] < 2.5).mean(), 3),
        "under35_rate": round((df["total_goals"] < 3.5).mean(), 3),
        "btts_rate":    round(df["btts"].mean(), 3),
        "home_win_rate": round((df["ftr"] == "H").mean(), 3) if "FTR" in df.columns else 0.0,
        "draw_rate":     round((df["ftr"] == "D").mean(), 3) if "FTR" in df.columns else 0.0,
        "away_win_rate": round((df["ftr"] == "A").mean(), 3) if "FTR" in df.columns else 0.0,
        "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    if stats["over25_rate"] >= 0.57:
        stats["profile"] = "high_scoring"
    elif stats["over25_rate"] <= 0.48:
        stats["profile"] = "low_scoring"
    else:
        stats["profile"] = "balanced"

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# TRAINING DATA BUILDER
# ─────────────────────────────────────────────────────────────────────────────

WANTED_COLS = [
    "FTHG", "FTAG", "FTR",
    "B365H", "B365D", "B365A",
    "B365>2.5", "B365<2.5",
    "BbAv>2.5", "BbAv<2.5",
    "PSH", "PSD", "PSA",
    "HomeTeam", "AwayTeam", "Date",
]


def build_training_df(div: str, df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Build a clean training row per match with:
      - Features: bookmaker implied probabilities, home/away advantage
      - Labels: over15, over25, over35, btts, result (H/D/A)
    """
    if df_raw.empty:
        return pd.DataFrame()

    available = [c for c in WANTED_COLS if c in df_raw.columns]
    df = df_raw[available + ["_season"]].copy()
    df["div"] = div

    df["home_goals"] = _to_float(df.get("FTHG", pd.Series(dtype=str)))
    df["away_goals"] = _to_float(df.get("FTAG", pd.Series(dtype=str)))
    df = df.dropna(subset=["home_goals", "away_goals"])
    df["total_goals"] = df["home_goals"] + df["away_goals"]

    df["label_over15"]  = (df["total_goals"] > 1.5).astype(int)
    df["label_over25"]  = (df["total_goals"] > 2.5).astype(int)
    df["label_over35"]  = (df["total_goals"] > 3.5).astype(int)
    df["label_under25"] = (df["total_goals"] < 2.5).astype(int)
    df["label_under35"] = (df["total_goals"] < 3.5).astype(int)
    df["label_btts"]    = ((df["home_goals"] > 0) & (df["away_goals"] > 0)).astype(int)
    df["label_home_win"]= (df.get("FTR", "") == "H").astype(int)
    df["label_draw"]    = (df.get("FTR", "") == "D").astype(int)
    df["label_away_win"]= (df.get("FTR", "") == "A").astype(int)

    for col in ["B365H", "B365D", "B365A", "B365>2.5", "B365<2.5",
                "PSH", "PSD", "PSA"]:
        num = _to_float(df[col]) if col in df.columns else pd.Series([None] * len(df))
        df[f"prob_{col}"] = 1.0 / num

    if all(c in df.columns for c in ["prob_B365H", "prob_B365D", "prob_B365A"]):
        total = df["prob_B365H"] + df["prob_B365D"] + df["prob_B365A"]
        df["implied_home"]   = df["prob_B365H"] / total
        df["implied_draw"]   = df["prob_B365D"] / total
        df["implied_away"]   = df["prob_B365A"] / total
        df["implied_over25"] = _to_float(df.get("prob_B365>2.5", pd.Series(dtype=float)))
        df["implied_under25"] = _to_float(df.get("prob_B365<2.5", pd.Series(dtype=float)))

    return df


# ─────────────────────────────────────────────────────────────────────────────
# MAIN COMMANDS
# ─────────────────────────────────────────────────────────────────────────────

def cmd_update():
    """Download all leagues, compute stats, save to league_stats.json, update DNA."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_stats: dict[str, dict] = {}

    for div, (_, api_name) in LEAGUE_MAP.items():
        log.info("Downloading %s (%s) ...", api_name, div)
        df = download_all_seasons(div)
        if df.empty:
            log.warning("  -> No data for %s", div)
            continue
        stats = compute_league_stats(df)
        if stats:
            all_stats[api_name] = stats
            log.info(
                "  -> %s: avg %.2f goals, over25=%.1f%%, profile=%s",
                api_name, stats["avg_goals_pg"],
                stats["over25_rate"] * 100, stats["profile"]
            )

    STATS_FILE.write_text(json.dumps(all_stats, indent=2))
    log.info("Saved stats to %s", STATS_FILE)
    _apply_stats_to_dna(all_stats)


def cmd_build_training():
    """Download all leagues, build combined training CSV."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frames = []

    for div, (_, api_name) in LEAGUE_MAP.items():
        log.info("Building training data for %s ...", api_name)
        df_raw = download_all_seasons(div)
        df_train = build_training_df(div, df_raw)
        if not df_train.empty:
            df_train["league_name"] = api_name
            frames.append(df_train)

    if not frames:
        log.error("No training data built.")
        return

    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(TRAINING_FILE, index=False)
    log.info("Saved %d rows to %s", len(combined), TRAINING_FILE)
    log.info("Columns: %s", list(combined.columns))


def cmd_stats():
    """Print a league stats summary table."""
    if not STATS_FILE.exists():
        log.error("Run --update first to generate %s", STATS_FILE)
        return
    stats = json.loads(STATS_FILE.read_text())
    rows = sorted(stats.items(), key=lambda x: x[1].get("over25_rate", 0), reverse=True)
    print(f"\n{'League':<30} {'Profile':<15} {'AvgGoals':>9} {'Over15%':>8} {'Over25%':>8} {'Over35%':>8} {'BTTS%':>7} {'Matches':>8}")
    print("-" * 100)
    for name, s in rows:
        print(
            f"{name:<30} {s.get('profile','?'):<15} "
            f"{s.get('avg_goals_pg',0):>9.2f} "
            f"{s.get('over15_rate',0)*100:>7.1f}% "
            f"{s.get('over25_rate',0)*100:>7.1f}% "
            f"{s.get('over35_rate',0)*100:>7.1f}% "
            f"{s.get('btts_rate',0)*100:>6.1f}% "
            f"{s.get('matches',0):>8}"
        )
    print()


def _apply_stats_to_dna(all_stats: dict[str, dict]) -> None:
    """Push fresh stats into league_dna module (runtime update)."""
    try:
        from utils.league_dna import update_dna_from_stats
        for api_name, s in all_stats.items():
            update_dna_from_stats(
                league_name=api_name,
                avg_goals_pg=s["avg_goals_pg"],
                over25_rate=s["over25_rate"],
                over15_rate=s["over15_rate"],
                btts_rate=s["btts_rate"],
                home_win_rate=s.get("home_win_rate", 0.44),
                draw_rate=s.get("draw_rate", 0.25),
            )
        log.info("League DNA updated in memory.")
    except ImportError:
        log.warning("league_dna not importable -- skipping DNA update")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="football-data.co.uk fetcher")
    parser.add_argument("--update",         action="store_true", help="Download + update league DNA")
    parser.add_argument("--build-training", action="store_true", help="Build training CSV for XGBoost")
    parser.add_argument("--stats",          action="store_true", help="Print league stats table")
    args = parser.parse_args()

    if args.update:
        cmd_update()
    if args.build_training:
        cmd_build_training()
    if args.stats:
        cmd_stats()
    if not any(vars(args).values()):
        parser.print_help()

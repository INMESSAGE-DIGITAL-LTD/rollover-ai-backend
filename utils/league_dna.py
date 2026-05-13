"""
league_dna.py
=============
League DNA profiles — every league has a scoring personality.

HIGH_SCORING leagues (Australia A-League, Eredivisie, Belgian Pro League …)
    → Over 2.5/3.5 at short odds 1.20-1.50 hit very often
    → We LOWER our confidence threshold to pick those markets more aggressively

LOW_SCORING leagues (Serie A, Ligue 1, African CHAN-style cups …)
    → Under 2.5/Under 3.5 at short odds 1.20-1.50 hit very often
    → We LOWER our confidence threshold for under markets

BALANCED leagues (Premier League, La Liga, Bundesliga …)
    → No strong bias — normal thresholds apply

HOW THIS PLUGS INTO YOUR EXISTING PIPELINE
-------------------------------------------
1. get_league_dna(league_name) → returns a LeagueDNA object
2. LeagueDNA.adjust_score(market, base_score) → boosts/penalises a composite score
3. LeagueDNA.preferred_markets → pre-filter before XGBoost scoring (saves API calls)
4. LeagueDNA.avoid_markets   → hard-block markets even if XGBoost says 70%

DATA SOURCE for updating these numbers automatically:
    football-data.co.uk (100% FREE, 25+ years, CSV download)
    → run `python football_data_fetcher.py --update` weekly via GitHub Actions
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import difflib
import re

# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class LeagueDNA:
    """Scoring personality of a league, derived from historical match data."""

    name: str

    # --- Historical averages (updated monthly from football-data.co.uk) ---
    avg_goals_pg: float = 2.6
    over15_rate: float = 0.76
    over25_rate: float = 0.52
    over35_rate: float = 0.28
    btts_rate: float = 0.50
    home_win_rate: float = 0.45
    draw_rate: float = 0.24

    # --- Profile (computed from rates above) ---
    profile: str = "balanced"

    # --- Market guidance ---
    preferred_markets: list = field(default_factory=list)
    avoid_markets: list = field(default_factory=list)

    # --- Threshold adjustments ---
    over_adjustment: float = 0.0
    under_adjustment: float = 0.0
    btts_adjustment: float = 0.0
    result_adjustment: float = 0.0

    def adjust_score(self, market: str, base_score: float) -> float:
        m = market.lower()
        delta = 0.0
        if "over" in m:
            delta = self.over_adjustment
        elif "under" in m:
            delta = self.under_adjustment
        elif "btts" in m or "both teams" in m:
            delta = self.btts_adjustment
        elif any(x in m for x in ["home win", "away win", "draw", "double chance", "1x", "x2", "12"]):
            delta = self.result_adjustment
        return max(0.0, min(1.0, base_score + delta))

    def is_preferred(self, market: str) -> bool:
        m = market.lower()
        return any(p.lower() in m for p in self.preferred_markets)

    def is_avoided(self, market: str) -> bool:
        m = market.lower()
        return any(a.lower() in m for a in self.avoid_markets)

    @property
    def is_high_scoring(self) -> bool:
        return self.profile == "high_scoring"

    @property
    def is_low_scoring(self) -> bool:
        return self.profile == "low_scoring"


# ──────────────────────────────────────────────────────────────────────────────
# LEAGUE DNA DATABASE
# ──────────────────────────────────────────────────────────────────────────────

_DNA: dict = {}

def _add(**kwargs) -> None:
    dna = LeagueDNA(**kwargs)
    _DNA[dna.name.lower()] = dna


# =============================================================================
# HIGH-SCORING LEAGUES
# =============================================================================

_add(
    name="A-League Men",
    avg_goals_pg=3.08,
    over15_rate=0.83,
    over25_rate=0.64,
    over35_rate=0.38,
    btts_rate=0.56,
    home_win_rate=0.43,
    draw_rate=0.24,
    profile="high_scoring",
    preferred_markets=["Over 1.5 Goals", "Over 2.5 Goals", "Over 3.5 Goals", "BTTS Yes"],
    avoid_markets=["Under 2.5 Goals", "Under 1.5 Goals"],
    over_adjustment=0.07,
    btts_adjustment=0.05,
    under_adjustment=-0.10,
)

_add(
    name="A-League Women",
    avg_goals_pg=3.40,
    over15_rate=0.86,
    over25_rate=0.70,
    over35_rate=0.44,
    btts_rate=0.58,
    home_win_rate=0.42,
    draw_rate=0.20,
    profile="high_scoring",
    preferred_markets=["Over 2.5 Goals", "Over 3.5 Goals", "Over 1.5 Goals"],
    avoid_markets=["Under 2.5 Goals"],
    over_adjustment=0.09,
    btts_adjustment=0.06,
    under_adjustment=-0.12,
)

_add(
    name="Eredivisie",
    avg_goals_pg=3.10,
    over15_rate=0.84,
    over25_rate=0.63,
    over35_rate=0.37,
    btts_rate=0.57,
    home_win_rate=0.46,
    draw_rate=0.23,
    profile="high_scoring",
    preferred_markets=["Over 2.5 Goals", "Over 1.5 Goals", "BTTS Yes"],
    avoid_markets=["Under 2.5 Goals"],
    over_adjustment=0.06,
    btts_adjustment=0.05,
    under_adjustment=-0.08,
)

_add(
    name="Pro League",
    avg_goals_pg=2.92,
    over15_rate=0.81,
    over25_rate=0.59,
    over35_rate=0.33,
    btts_rate=0.54,
    home_win_rate=0.46,
    draw_rate=0.24,
    profile="high_scoring",
    preferred_markets=["Over 2.5 Goals", "Over 1.5 Goals", "BTTS Yes"],
    avoid_markets=["Under 2.5 Goals"],
    over_adjustment=0.05,
    btts_adjustment=0.04,
    under_adjustment=-0.07,
)

_add(
    name="Scottish Premiership",
    avg_goals_pg=2.85,
    over15_rate=0.79,
    over25_rate=0.57,
    over35_rate=0.31,
    btts_rate=0.52,
    home_win_rate=0.44,
    draw_rate=0.25,
    profile="high_scoring",
    preferred_markets=["Over 2.5 Goals", "Over 1.5 Goals"],
    avoid_markets=[],
    over_adjustment=0.04,
    btts_adjustment=0.03,
    under_adjustment=-0.05,
)

_add(
    name="Bundesliga",
    avg_goals_pg=2.91,
    over15_rate=0.80,
    over25_rate=0.59,
    over35_rate=0.33,
    btts_rate=0.54,
    home_win_rate=0.43,
    draw_rate=0.25,
    profile="high_scoring",
    preferred_markets=["Over 2.5 Goals", "BTTS Yes"],
    avoid_markets=["Under 2.5 Goals"],
    over_adjustment=0.04,
    btts_adjustment=0.04,
    under_adjustment=-0.06,
)

_add(
    name="2. Bundesliga",
    avg_goals_pg=2.95,
    over15_rate=0.81,
    over25_rate=0.60,
    over35_rate=0.34,
    btts_rate=0.55,
    home_win_rate=0.44,
    draw_rate=0.24,
    profile="high_scoring",
    preferred_markets=["Over 2.5 Goals", "Over 1.5 Goals", "BTTS Yes"],
    avoid_markets=["Under 2.5 Goals"],
    over_adjustment=0.05,
    btts_adjustment=0.04,
    under_adjustment=-0.07,
)

_add(
    name="Jupiler Pro League",
    avg_goals_pg=2.92,
    over15_rate=0.81,
    over25_rate=0.59,
    over35_rate=0.33,
    btts_rate=0.54,
    home_win_rate=0.46,
    draw_rate=0.24,
    profile="high_scoring",
    preferred_markets=["Over 2.5 Goals", "Over 1.5 Goals"],
    avoid_markets=["Under 2.5 Goals"],
    over_adjustment=0.05,
    btts_adjustment=0.04,
    under_adjustment=-0.07,
)

_add(
    name="Eliteserien",
    avg_goals_pg=2.88,
    over15_rate=0.79,
    over25_rate=0.57,
    over35_rate=0.30,
    btts_rate=0.52,
    home_win_rate=0.44,
    draw_rate=0.24,
    profile="high_scoring",
    preferred_markets=["Over 2.5 Goals", "Over 1.5 Goals"],
    avoid_markets=[],
    over_adjustment=0.04,
    btts_adjustment=0.03,
    under_adjustment=-0.05,
)

_add(
    name="Allsvenskan",
    avg_goals_pg=2.80,
    over15_rate=0.78,
    over25_rate=0.56,
    over35_rate=0.29,
    btts_rate=0.51,
    home_win_rate=0.44,
    draw_rate=0.26,
    profile="high_scoring",
    preferred_markets=["Over 2.5 Goals", "Over 1.5 Goals"],
    avoid_markets=[],
    over_adjustment=0.04,
    btts_adjustment=0.02,
    under_adjustment=-0.04,
)

_add(
    name="Süper Lig",
    avg_goals_pg=2.83,
    over15_rate=0.79,
    over25_rate=0.56,
    over35_rate=0.28,
    btts_rate=0.52,
    home_win_rate=0.48,
    draw_rate=0.24,
    profile="high_scoring",
    preferred_markets=["Over 2.5 Goals", "Over 1.5 Goals", "Home Win"],
    avoid_markets=["Under 2.5 Goals"],
    over_adjustment=0.04,
    result_adjustment=0.04,
    under_adjustment=-0.05,
)

_add(
    name="Super Lig",
    avg_goals_pg=2.83,
    over15_rate=0.79,
    over25_rate=0.56,
    over35_rate=0.28,
    btts_rate=0.52,
    home_win_rate=0.48,
    draw_rate=0.24,
    profile="high_scoring",
    preferred_markets=["Over 2.5 Goals", "Over 1.5 Goals", "Home Win"],
    avoid_markets=["Under 2.5 Goals"],
    over_adjustment=0.04,
    result_adjustment=0.04,
    under_adjustment=-0.05,
)

_add(
    name="CAF Champions League",
    avg_goals_pg=2.70,
    over15_rate=0.77,
    over25_rate=0.53,
    over35_rate=0.27,
    btts_rate=0.50,
    home_win_rate=0.47,
    draw_rate=0.26,
    profile="high_scoring",
    preferred_markets=["Over 2.5 Goals", "Over 1.5 Goals"],
    avoid_markets=[],
    over_adjustment=0.03,
    btts_adjustment=0.02,
)

_add(
    name="NPFL",
    avg_goals_pg=2.65,
    over15_rate=0.76,
    over25_rate=0.52,
    over35_rate=0.25,
    btts_rate=0.48,
    home_win_rate=0.50,
    draw_rate=0.25,
    profile="high_scoring",
    preferred_markets=["Over 1.5 Goals", "Over 2.5 Goals", "Home Win"],
    avoid_markets=[],
    over_adjustment=0.03,
    result_adjustment=0.05,
)

_add(
    name="Ghana Premier League",
    avg_goals_pg=2.55,
    over15_rate=0.74,
    over25_rate=0.49,
    over35_rate=0.22,
    btts_rate=0.46,
    home_win_rate=0.49,
    draw_rate=0.26,
    profile="high_scoring",
    preferred_markets=["Over 1.5 Goals", "Home Win"],
    avoid_markets=["BTTS Yes"],
    over_adjustment=0.02,
    result_adjustment=0.04,
)

_add(
    name="Primeira Liga",
    avg_goals_pg=2.75,
    over15_rate=0.78,
    over25_rate=0.54,
    over35_rate=0.28,
    btts_rate=0.51,
    home_win_rate=0.46,
    draw_rate=0.25,
    profile="high_scoring",
    preferred_markets=["Over 2.5 Goals", "Over 1.5 Goals"],
    avoid_markets=[],
    over_adjustment=0.03,
    btts_adjustment=0.02,
    under_adjustment=-0.04,
)

_add(
    name="Major League Soccer",
    avg_goals_pg=2.85,
    over15_rate=0.80,
    over25_rate=0.57,
    over35_rate=0.30,
    btts_rate=0.52,
    home_win_rate=0.46,
    draw_rate=0.22,
    profile="high_scoring",
    preferred_markets=["Over 2.5 Goals", "Over 1.5 Goals"],
    avoid_markets=["Under 2.5 Goals"],
    over_adjustment=0.05,
    under_adjustment=-0.06,
)

_add(
    name="MLS",
    avg_goals_pg=2.85,
    over15_rate=0.80,
    over25_rate=0.57,
    over35_rate=0.30,
    btts_rate=0.52,
    home_win_rate=0.46,
    draw_rate=0.22,
    profile="high_scoring",
    preferred_markets=["Over 2.5 Goals", "Over 1.5 Goals"],
    avoid_markets=["Under 2.5 Goals"],
    over_adjustment=0.05,
    under_adjustment=-0.06,
)

# =============================================================================
# LOW-SCORING LEAGUES
# =============================================================================

_add(
    name="Serie A",
    avg_goals_pg=2.48,
    over15_rate=0.73,
    over25_rate=0.46,
    over35_rate=0.20,
    btts_rate=0.43,
    home_win_rate=0.42,
    draw_rate=0.28,
    profile="low_scoring",
    preferred_markets=["Under 2.5 Goals", "Under 3.5 Goals", "1X Double Chance"],
    avoid_markets=["Over 2.5 Goals", "BTTS Yes"],
    under_adjustment=0.08,
    over_adjustment=-0.10,
    btts_adjustment=-0.08,
    result_adjustment=0.03,
)

_add(
    name="Ligue 1",
    avg_goals_pg=2.50,
    over15_rate=0.74,
    over25_rate=0.47,
    over35_rate=0.21,
    btts_rate=0.44,
    home_win_rate=0.43,
    draw_rate=0.27,
    profile="low_scoring",
    preferred_markets=["Under 2.5 Goals", "Under 3.5 Goals", "1X Double Chance"],
    avoid_markets=["Over 2.5 Goals", "BTTS Yes"],
    under_adjustment=0.07,
    over_adjustment=-0.09,
    btts_adjustment=-0.07,
)

_add(
    name="Ligue 2",
    avg_goals_pg=2.45,
    over15_rate=0.72,
    over25_rate=0.44,
    over35_rate=0.18,
    btts_rate=0.42,
    home_win_rate=0.43,
    draw_rate=0.28,
    profile="low_scoring",
    preferred_markets=["Under 2.5 Goals", "Under 3.5 Goals"],
    avoid_markets=["Over 2.5 Goals", "BTTS Yes"],
    under_adjustment=0.09,
    over_adjustment=-0.11,
    btts_adjustment=-0.09,
)

_add(
    name="La Liga",
    avg_goals_pg=2.58,
    over15_rate=0.75,
    over25_rate=0.49,
    over35_rate=0.23,
    btts_rate=0.47,
    home_win_rate=0.43,
    draw_rate=0.27,
    profile="low_scoring",
    preferred_markets=["Under 2.5 Goals", "Under 3.5 Goals"],
    avoid_markets=["Over 2.5 Goals"],
    under_adjustment=0.05,
    over_adjustment=-0.07,
    btts_adjustment=-0.04,
)

_add(
    name="Primera Division",
    avg_goals_pg=2.58,
    over15_rate=0.75,
    over25_rate=0.49,
    over35_rate=0.23,
    btts_rate=0.47,
    home_win_rate=0.43,
    draw_rate=0.27,
    profile="low_scoring",
    preferred_markets=["Under 2.5 Goals", "Under 3.5 Goals"],
    avoid_markets=["Over 2.5 Goals"],
    under_adjustment=0.05,
    over_adjustment=-0.07,
    btts_adjustment=-0.04,
)

_add(
    name="Greek Super League",
    avg_goals_pg=2.42,
    over15_rate=0.71,
    over25_rate=0.43,
    over35_rate=0.17,
    btts_rate=0.41,
    home_win_rate=0.47,
    draw_rate=0.27,
    profile="low_scoring",
    preferred_markets=["Under 2.5 Goals", "Under 3.5 Goals", "Home Win"],
    avoid_markets=["Over 2.5 Goals", "BTTS Yes"],
    under_adjustment=0.10,
    over_adjustment=-0.12,
    btts_adjustment=-0.10,
    result_adjustment=0.05,
)

_add(
    name="Super League",
    avg_goals_pg=2.42,
    over15_rate=0.71,
    over25_rate=0.43,
    over35_rate=0.17,
    btts_rate=0.41,
    home_win_rate=0.47,
    draw_rate=0.27,
    profile="low_scoring",
    preferred_markets=["Under 2.5 Goals", "Under 3.5 Goals", "Home Win"],
    avoid_markets=["Over 2.5 Goals", "BTTS Yes"],
    under_adjustment=0.10,
    over_adjustment=-0.12,
    btts_adjustment=-0.10,
    result_adjustment=0.05,
)

_add(
    name="CAF Confederation Cup",
    avg_goals_pg=2.40,
    over15_rate=0.70,
    over25_rate=0.42,
    over35_rate=0.16,
    btts_rate=0.40,
    home_win_rate=0.48,
    draw_rate=0.28,
    profile="low_scoring",
    preferred_markets=["Under 2.5 Goals", "Home Win"],
    avoid_markets=["Over 2.5 Goals", "BTTS Yes"],
    under_adjustment=0.08,
    over_adjustment=-0.10,
    result_adjustment=0.04,
)

_add(
    name="Egypt Premier League",
    avg_goals_pg=2.38,
    over15_rate=0.70,
    over25_rate=0.41,
    over35_rate=0.16,
    btts_rate=0.39,
    home_win_rate=0.49,
    draw_rate=0.27,
    profile="low_scoring",
    preferred_markets=["Under 2.5 Goals", "Home Win", "1X Double Chance"],
    avoid_markets=["Over 2.5 Goals", "BTTS Yes"],
    under_adjustment=0.09,
    over_adjustment=-0.11,
    result_adjustment=0.05,
)

# =============================================================================
# BALANCED LEAGUES
# =============================================================================

_add(
    name="Premier League",
    avg_goals_pg=2.66,
    over15_rate=0.77,
    over25_rate=0.52,
    over35_rate=0.25,
    btts_rate=0.50,
    home_win_rate=0.44,
    draw_rate=0.25,
    profile="balanced",
    preferred_markets=["Over 1.5 Goals"],
    avoid_markets=[],
)

_add(
    name="Championship",
    avg_goals_pg=2.62,
    over15_rate=0.76,
    over25_rate=0.50,
    over35_rate=0.23,
    btts_rate=0.48,
    home_win_rate=0.43,
    draw_rate=0.27,
    profile="balanced",
    preferred_markets=["Over 1.5 Goals"],
    avoid_markets=[],
)

_add(
    name="Liga MX",
    avg_goals_pg=2.60,
    over15_rate=0.76,
    over25_rate=0.50,
    over35_rate=0.24,
    btts_rate=0.49,
    home_win_rate=0.44,
    draw_rate=0.26,
    profile="balanced",
    preferred_markets=["Over 1.5 Goals", "Over 2.5 Goals"],
    avoid_markets=[],
    over_adjustment=0.02,
)

_add(
    name="J1 League",
    avg_goals_pg=2.74,
    over15_rate=0.78,
    over25_rate=0.53,
    over35_rate=0.26,
    btts_rate=0.50,
    home_win_rate=0.46,
    draw_rate=0.24,
    profile="balanced",
    preferred_markets=["Over 1.5 Goals", "Over 2.5 Goals"],
    avoid_markets=[],
    over_adjustment=0.02,
)

_add(
    name="K League 1",
    avg_goals_pg=2.70,
    over15_rate=0.78,
    over25_rate=0.53,
    over35_rate=0.26,
    btts_rate=0.51,
    home_win_rate=0.46,
    draw_rate=0.24,
    profile="balanced",
    preferred_markets=["Over 1.5 Goals"],
    avoid_markets=[],
    over_adjustment=0.02,
)

_add(
    name="Saudi Professional League",
    avg_goals_pg=2.78,
    over15_rate=0.79,
    over25_rate=0.55,
    over35_rate=0.29,
    btts_rate=0.51,
    home_win_rate=0.46,
    draw_rate=0.24,
    profile="balanced",
    preferred_markets=["Over 2.5 Goals", "Over 1.5 Goals"],
    avoid_markets=[],
    over_adjustment=0.03,
)

_add(
    name="Saudi Premier League",
    avg_goals_pg=2.78,
    over15_rate=0.79,
    over25_rate=0.55,
    over35_rate=0.29,
    btts_rate=0.51,
    home_win_rate=0.46,
    draw_rate=0.24,
    profile="balanced",
    preferred_markets=["Over 2.5 Goals", "Over 1.5 Goals"],
    avoid_markets=[],
    over_adjustment=0.03,
)

# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────────────────

_FALLBACK = LeagueDNA(
    name="Unknown",
    profile="balanced",
    preferred_markets=["Over 1.5 Goals"],
    avoid_markets=[],
)


def _normalise(name: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", name.lower()).strip()


def get_league_dna(league_name: str) -> LeagueDNA:
    """
    Return the LeagueDNA for the given league name.
    Tries exact match, fuzzy substring, difflib close-match, then fallback.
    """
    key = league_name.lower().strip()

    if key in _DNA:
        return _DNA[key]

    norm_key = _normalise(key)
    for canon_key, dna in _DNA.items():
        if _normalise(canon_key) == norm_key:
            return dna

    candidates = list(_DNA.keys())
    close = difflib.get_close_matches(key, candidates, n=1, cutoff=0.75)
    if close:
        return _DNA[close[0]]

    for canon_key, dna in _DNA.items():
        if norm_key in _normalise(canon_key) or _normalise(canon_key) in norm_key:
            return dna

    return _FALLBACK


def list_high_scoring_leagues() -> list:
    return [d.name for d in _DNA.values() if d.profile == "high_scoring"]


def list_low_scoring_leagues() -> list:
    return [d.name for d in _DNA.values() if d.profile == "low_scoring"]


def get_best_market_for_league(league_name: str) -> Optional[str]:
    dna = get_league_dna(league_name)
    if dna.preferred_markets:
        return dna.preferred_markets[0]
    return None


# ──────────────────────────────────────────────────────────────────────────────
# DYNAMIC UPDATES FROM football-data.co.uk
# ──────────────────────────────────────────────────────────────────────────────

def update_dna_from_stats(
    league_name: str,
    avg_goals_pg: float,
    over25_rate: float,
    over15_rate: float,
    btts_rate: float,
    home_win_rate: float,
    draw_rate: float,
) -> None:
    dna = get_league_dna(league_name)

    dna.avg_goals_pg = round(avg_goals_pg, 2)
    dna.over25_rate = round(over25_rate, 3)
    dna.over15_rate = round(over15_rate, 3)
    dna.btts_rate = round(btts_rate, 3)
    dna.home_win_rate = round(home_win_rate, 3)
    dna.draw_rate = round(draw_rate, 3)

    if over25_rate >= 0.57:
        dna.profile = "high_scoring"
        dna.over_adjustment = round(min(0.10, (over25_rate - 0.52) * 0.7), 3)
        dna.under_adjustment = round(-dna.over_adjustment * 1.2, 3)
        dna.preferred_markets = ["Over 2.5 Goals", "Over 1.5 Goals"]
        dna.avoid_markets = ["Under 2.5 Goals"]
    elif over25_rate <= 0.48:
        dna.profile = "low_scoring"
        dna.under_adjustment = round(min(0.10, (0.52 - over25_rate) * 0.7), 3)
        dna.over_adjustment = round(-dna.under_adjustment * 1.2, 3)
        dna.preferred_markets = ["Under 2.5 Goals", "Under 3.5 Goals"]
        dna.avoid_markets = ["Over 2.5 Goals"]
    else:
        dna.profile = "balanced"
        dna.over_adjustment = 0.0
        dna.under_adjustment = 0.0

    _DNA[league_name.lower()] = dna

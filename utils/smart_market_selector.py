"""
smart_market_selector.py
========================
The DNA-aware brain of the pick pipeline.

HOW IT WORKS
------------
1. Fetch fixture's league name -> look up LeagueDNA
2. Check preferred_markets and avoid_markets BEFORE running XGBoost
3. Run XGBoost composite scoring for remaining candidate markets
4. Apply DNA adjustment: dna.adjust_score(market, base_score)
5. Apply dynamic threshold: threshold = BASE_THRESHOLD - dna.{market}_adjustment
6. Return best pick OR None if nothing clears threshold
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Optional

from .league_dna import LeagueDNA, get_league_dna

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

BASE_THRESHOLDS: dict[str, float] = {
    "over 1.5 goals":   0.68,
    "over 2.5 goals":   0.70,
    "over 3.5 goals":   0.72,
    "under 1.5 goals":  0.72,
    "under 2.5 goals":  0.70,
    "under 3.5 goals":  0.68,
    "btts yes":         0.68,
    "btts no":          0.70,
    "home win":         0.65,
    "away win":         0.67,
    "draw":             0.72,
    "1x double chance": 0.65,
    "x2 double chance": 0.67,
    "12 double chance": 0.67,
}

MIN_ODDS: dict[str, float] = {
    "over 1.5 goals":   1.10,
    "over 2.5 goals":   1.18,
    "over 3.5 goals":   1.25,
    "under 1.5 goals":  1.20,
    "under 2.5 goals":  1.18,
    "under 3.5 goals":  1.10,
    "btts yes":         1.20,
    "btts no":          1.15,
    "home win":         1.18,
    "away win":         1.30,
    "draw":             1.40,
    "1x double chance": 1.10,
    "x2 double chance": 1.15,
    "12 double chance": 1.20,
}

ROLLOVER_MAX_ODDS: dict[str, float] = {
    "over 1.5 goals":   1.70,
    "over 2.5 goals":   1.85,
    "over 3.5 goals":   2.10,
    "under 1.5 goals":  1.80,
    "under 2.5 goals":  1.85,
    "under 3.5 goals":  1.70,
    "btts yes":         1.80,
    "btts no":          1.75,
    "home win":         1.90,
    "away win":         2.50,
    "draw":             3.20,
    "1x double chance": 1.65,
    "x2 double chance": 1.75,
    "12 double chance": 1.75,
}


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MarketCandidate:
    market: str
    odds: float
    base_score: float
    adjusted_score: float
    threshold: float
    clears_threshold: bool
    dna_profile: str
    is_preferred: bool
    is_avoided: bool
    reject_reason: Optional[str] = None


@dataclass
class SmartPick:
    fixture_id: int
    home_team: str
    away_team: str
    league: str
    match_date: str
    market: str
    odds: float
    adjusted_score: float
    threshold: float
    confidence_pct: float
    dna_profile: str
    all_candidates: list[MarketCandidate] = field(default_factory=list)

    @property
    def is_high_value(self) -> bool:
        return self.adjusted_score >= self.threshold + 0.05

    def to_dict(self) -> dict:
        return {
            "fixture_id":      self.fixture_id,
            "home_team":       self.home_team,
            "away_team":       self.away_team,
            "league":          self.league,
            "match_date":      self.match_date,
            "market":          self.market,
            "odds":            self.odds,
            "adjusted_score":  round(self.adjusted_score, 4),
            "threshold":       round(self.threshold, 4),
            "confidence_pct":  round(self.confidence_pct, 1),
            "dna_profile":     self.dna_profile,
            "is_high_value":   self.is_high_value,
        }


# ─────────────────────────────────────────────────────────────────────────────
# CORE SELECTOR
# ─────────────────────────────────────────────────────────────────────────────

class SmartMarketSelector:
    """
    DNA-aware market selector.

        selector = SmartMarketSelector(mode="rollover")  # or "ai_pro", "big_odds"
        pick = selector.select_best_market(fixture_dict, xgb_scores, odds_dict)
    """

    def __init__(
        self,
        mode: str = "rollover",
        custom_thresholds: Optional[dict[str, float]] = None,
    ):
        self.mode = mode
        self._thresholds = dict(BASE_THRESHOLDS)
        if custom_thresholds:
            self._thresholds.update({k.lower(): v for k, v in custom_thresholds.items()})

    def select_best_market(
        self,
        fixture: dict,
        xgb_scores: dict[str, float],
        odds: dict[str, float],
    ) -> Optional[SmartPick]:
        league_name = fixture.get("league", "Unknown")
        dna = get_league_dna(league_name)

        candidates = self._build_candidates(xgb_scores, odds, dna)
        qualifying = [c for c in candidates if c.clears_threshold]

        if not qualifying:
            return None

        qualifying.sort(
            key=lambda c: (
                not c.is_preferred,
                -(c.adjusted_score - c.threshold),
            )
        )

        best = qualifying[0]
        confidence_pct = (best.adjusted_score / best.threshold) * 100

        log.info(
            "PICK %s vs %s -> %s @ %.2f  (score=%.3f, threshold=%.3f, dna=%s)",
            fixture.get("home_team"), fixture.get("away_team"),
            best.market, best.odds,
            best.adjusted_score, best.threshold, dna.profile,
        )

        return SmartPick(
            fixture_id=fixture.get("fixture_id", 0),
            home_team=fixture.get("home_team", ""),
            away_team=fixture.get("away_team", ""),
            league=league_name,
            match_date=fixture.get("match_date", ""),
            market=best.market,
            odds=best.odds,
            adjusted_score=best.adjusted_score,
            threshold=best.threshold,
            confidence_pct=confidence_pct,
            dna_profile=dna.profile,
            all_candidates=candidates,
        )

    def score_all_markets(
        self,
        fixture: dict,
        xgb_scores: dict[str, float],
        odds: dict[str, float],
    ) -> list[MarketCandidate]:
        dna = get_league_dna(fixture.get("league", "Unknown"))
        candidates = self._build_candidates(xgb_scores, odds, dna)
        return sorted(candidates, key=lambda c: c.adjusted_score, reverse=True)

    def _get_threshold(self, market: str, dna: LeagueDNA) -> float:
        key = market.lower()
        base = self._thresholds.get(key, 0.70)
        adj = dna.adjust_score(market, 0.0)
        adjusted = base - adj
        return max(0.50, min(0.90, adjusted))

    def _odds_ok(self, market: str, odds: float) -> tuple[bool, Optional[str]]:
        key = market.lower()
        min_o = MIN_ODDS.get(key, 1.10)
        max_o = None

        if self.mode == "rollover":
            max_o = ROLLOVER_MAX_ODDS.get(key, 2.00)
        elif self.mode == "ai_pro":
            max_o = 3.50
        elif self.mode == "big_odds":
            max_o = 8.00

        if odds < min_o:
            return False, f"odds {odds:.2f} below min {min_o:.2f}"
        if max_o and odds > max_o:
            return False, f"odds {odds:.2f} above max {max_o:.2f}"
        return True, None

    def _build_candidates(
        self,
        xgb_scores: dict[str, float],
        odds: dict[str, float],
        dna: LeagueDNA,
    ) -> list[MarketCandidate]:
        candidates = []

        for market, base_score in xgb_scores.items():
            market_odds = odds.get(market)

            if dna.is_avoided(market):
                candidates.append(MarketCandidate(
                    market=market, odds=market_odds or 0.0,
                    base_score=base_score, adjusted_score=0.0,
                    threshold=1.0, clears_threshold=False,
                    dna_profile=dna.profile, is_preferred=False, is_avoided=True,
                    reject_reason="DNA avoid",
                ))
                continue

            if market_odds is None or market_odds <= 1.0:
                candidates.append(MarketCandidate(
                    market=market, odds=0.0,
                    base_score=base_score, adjusted_score=base_score,
                    threshold=1.0, clears_threshold=False,
                    dna_profile=dna.profile, is_preferred=dna.is_preferred(market),
                    is_avoided=False, reject_reason="no odds",
                ))
                continue

            odds_ok, odds_reason = self._odds_ok(market, market_odds)
            if not odds_ok:
                adj_score = dna.adjust_score(market, base_score)
                candidates.append(MarketCandidate(
                    market=market, odds=market_odds,
                    base_score=base_score, adjusted_score=adj_score,
                    threshold=1.0, clears_threshold=False,
                    dna_profile=dna.profile, is_preferred=dna.is_preferred(market),
                    is_avoided=False, reject_reason=odds_reason,
                ))
                continue

            adj_score = dna.adjust_score(market, base_score)
            threshold = self._get_threshold(market, dna)
            clears = adj_score >= threshold

            candidates.append(MarketCandidate(
                market=market, odds=market_odds,
                base_score=base_score, adjusted_score=adj_score,
                threshold=threshold, clears_threshold=clears,
                dna_profile=dna.profile, is_preferred=dna.is_preferred(market),
                is_avoided=False,
            ))

        return candidates


def pick_best_n(
    fixtures: list[dict],
    xgb_scores_per_fixture: list[dict[str, float]],
    odds_per_fixture: list[dict[str, float]],
    n: int = 4,
    mode: str = "rollover",
    min_odds_for_accumulator: float = 1.30,
) -> list[SmartPick]:
    selector = SmartMarketSelector(mode=mode)
    picks: list[SmartPick] = []

    for fixture, scores, odds in zip(fixtures, xgb_scores_per_fixture, odds_per_fixture):
        pick = selector.select_best_market(fixture, scores, odds)
        if pick and pick.odds >= min_odds_for_accumulator:
            picks.append(pick)

    picks.sort(key=lambda p: p.adjusted_score - p.threshold, reverse=True)
    return picks[:n]


def compute_accumulator_odds(picks: list[SmartPick]) -> float:
    result = 1.0
    for p in picks:
        result *= p.odds
    return round(result, 2)

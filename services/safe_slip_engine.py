"""
Safe Slip Engine — probability-first daily slip builder.

Philosophy: users must WIN daily. Every other generator in this repo ranks
picks by edge/value (beat the bookmaker long-term); this engine ranks by
raw win probability and restricts legs to the four statistically safest
markets. Value is secondary — a slip that lands at 2.05 beats a "+EV" slip
that loses.

Markets allowed (labels match result_updater grading + Flutter rendering):
  - Over 1.5 Goals
  - Double Chance (1X)   (home or draw)
  - Double Chance (X2)   (draw or away)
  - Double Chance (12)   (home or away)

Slip construction:
  - Only real bookmaker odds (odds_source == 'bookmaker'), never derived
    or default odds — the combined 2.00-2.20 target is meaningless with
    fabricated leg prices.
  - One leg per fixture, 2-3 legs, combined odds in [2.00, 2.20].
  - Score = product of leg probabilities (the slip's actual win chance),
    with a small bonus for mixing markets so free users can't infer the
    hidden pick from the visible teams alone.
"""
import math
from itertools import combinations


# market label → (min leg odds, max leg odds, min blended probability)
SAFE_MARKETS = {
    'Over 1.5 Goals':     (1.15, 1.50, 0.78),
    'Double Chance (1X)': (1.10, 1.50, 0.78),
    'Double Chance (X2)': (1.10, 1.50, 0.78),
    'Double Chance (12)': (1.08, 1.45, 0.80),
}

# Widening ladder used when the strict window can't be filled.
FALLBACK_WINDOWS = [(2.00, 2.20), (1.95, 2.30), (1.85, 2.45)]

MAX_CANDIDATES = 20   # top-probability legs considered for combination search

# Reserve/youth/women teams have unreliable data and inflated model
# confidence — never ship them, even on thin off-season days.
JUNK_KEYWORDS = ('II', ' B ', 'U18', 'U19', 'U20', 'U21', 'U23',
                 'Women', 'Reserves', 'Youth')


def _is_junk(opt):
    fields = (opt.get('home_team', ''), opt.get('away_team', ''),
              opt.get('league_name', ''))
    return any(k in f for k in JUNK_KEYWORDS for f in fields)


def filter_safe_options(match_options, *, market_penalties=None,
                        exclude_match_markets=None, allowed_markets=None,
                        allow_derived_odds=False):
    """Reduce raw match options to safe-market, high-probability candidates.

    Returns at most one option per fixture (the highest-probability one).
    """
    markets = allowed_markets or SAFE_MARKETS
    exclude = exclude_match_markets or set()
    penalties = market_penalties or {}

    by_fixture = {}
    for opt in match_options:
        market = opt.get('market', '')
        rule = markets.get(market)
        if rule is None:
            continue
        if _is_junk(opt):
            continue
        min_odds, max_odds, min_prob = rule

        odds = float(opt.get('odds', 0))
        if not (min_odds <= odds <= max_odds):
            continue

        # Real bookmaker prices only — derived/default odds make the
        # combined-odds target fiction.
        if not allow_derived_odds and opt.get('odds_source') != 'bookmaker':
            continue

        key = f"{opt.get('home_team','')}_{opt.get('away_team','')}"
        if f"{key}_{market}" in exclude:
            continue

        # Markets that lost recently must clear a higher probability bar
        # instead of being score-penalised: this engine never knowingly
        # ships a below-threshold leg.
        required = min_prob
        if penalties.get(market, 1.0) < 1.0:
            required = min(0.90, min_prob + 0.03)

        prob = float(opt.get('ai_prob', 0))
        if prob < required:
            continue

        best = by_fixture.get(key)
        if best is None or (prob, opt.get('stability', 0)) > (
                float(best.get('ai_prob', 0)), best.get('stability', 0)):
            by_fixture[key] = opt

    candidates = sorted(
        by_fixture.values(),
        key=lambda o: (float(o.get('ai_prob', 0)), o.get('stability', 0)),
        reverse=True,
    )
    return candidates[:MAX_CANDIDATES]


def _slip_score(combo):
    """Win probability of the whole slip, with a mix bonus."""
    prob = 1.0
    for leg in combo:
        prob *= float(leg.get('ai_prob', 0))
    distinct = len({leg.get('market') for leg in combo})
    if distinct >= 2:
        prob *= 1.05  # prefer mixed-market slips (harder to reverse-engineer)
    return prob


def select_safe_slip(candidates, *, min_combined=2.00, max_combined=2.20,
                     max_legs=3):
    """Pick the highest-win-probability combo whose combined odds land in
    the target window. Returns (legs, combined_odds); ([], 0) if empty pool.
    """
    if not candidates:
        return [], 0.0

    windows = [(min_combined, max_combined)]
    windows += [w for w in FALLBACK_WINDOWS if w != (min_combined, max_combined)]

    for lo, hi in windows:
        best, best_score = None, -1.0
        for size in range(2, max_legs + 1):
            if len(candidates) < size:
                continue
            for combo in combinations(candidates, size):
                combined = 1.0
                for leg in combo:
                    combined *= float(leg.get('odds', 1.0))
                if not (lo <= combined <= hi):
                    continue
                score = _slip_score(combo)
                if score > best_score:
                    best, best_score = combo, score
        if best:
            combined = 1.0
            for leg in best:
                combined *= float(leg.get('odds', 1.0))
            return list(best), round(combined, 2)

    # Nothing lands in any window (thin off-season days: only tiny-odds legs
    # available). Greedily stack the highest-probability legs toward the 2x
    # floor — six 1.11 legs ≈ 1.87 beats a 1.23 pair, and every extra leg is
    # still a ≥78% pick.
    THIN_DAY_MAX_LEGS = 6
    legs = []
    combined = 1.0
    for opt in candidates:
        if len(legs) >= THIN_DAY_MAX_LEGS or combined >= min_combined:
            break
        nxt = combined * float(opt.get('odds', 1.0))
        if nxt > max_combined:
            continue
        legs.append(opt)
        combined = nxt
    return legs, round(combined, 2)


def build_safe_slip(match_options, *, min_combined=2.00, max_combined=2.20,
                    max_legs=3, market_penalties=None,
                    exclude_match_markets=None):
    """match_options (from generate_match_options) → (legs, combined_odds)."""
    candidates = filter_safe_options(
        match_options,
        market_penalties=market_penalties,
        exclude_match_markets=exclude_match_markets,
    )
    legs, combined = select_safe_slip(
        candidates,
        min_combined=min_combined,
        max_combined=max_combined,
        max_legs=max_legs,
    )
    if legs:
        probs = ', '.join(
            f"{l.get('market','?')}@{l.get('odds')}({float(l.get('ai_prob',0)):.0%})"
            for l in legs
        )
        est = 1.0
        for l in legs:
            est *= float(l.get('ai_prob', 0))
        print(f"🛡️ SafeSlip: {len(legs)} legs, combined {combined}, "
              f"est. win prob {est:.0%} → {probs}")
    else:
        print("🛡️ SafeSlip: no qualifying safe legs today")
    return legs, combined

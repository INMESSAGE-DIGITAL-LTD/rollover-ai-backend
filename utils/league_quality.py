"""
League quality: which competitions our picks may come from.

Audit 2026-10-03..09: recent losses clustered in leagues the model has no
data for (Nicaragua, Barbados-Bermuda, Mexican 3rd tier, Uzbekistan...) and
in women's / reserve sides that slipped through the old keyword filter
("Djurgården W", "Aldosivi Res.").
"""
import re

# API-Football league ids with deep data and liquid betting markets.
WHITELIST = {
    # UEFA club + national team competitive
    2, 3, 848, 5, 32, 4, 1, 34, 9, 6, 29, 30,
    # England / Spain / Italy / Germany / France (top two tiers)
    39, 40, 140, 141, 135, 136, 78, 79, 61, 62,
    # Rest of Europe, top tiers
    88, 94, 144, 203, 179, 197, 218, 207, 119, 103, 113, 106, 345, 283,
    210, 235, 333,
    # Americas
    71, 128, 253, 262, 239, 265, 13, 11,
    # Asia / Oceania / Middle East
    98, 292, 307, 188,
}

_JUNK_TEAM = re.compile(
    r"(\b(W|U\s?\d{2}|II|III|B|Res\.?|Reserves?|Women|Youth|Academy)\b)\s*$",
    re.IGNORECASE,
)
_JUNK_LEAGUE = re.compile(
    r"women|friendl|u\s?\d{2}|youth|reserve|junior|amateur|regional",
    re.IGNORECASE,
)


def is_junk(opt):
    """Women's, reserve, youth sides and friendlies."""
    for team in (opt.get('home_team', ''), opt.get('away_team', '')):
        if _JUNK_TEAM.search(team or ''):
            return True
    return bool(_JUNK_LEAGUE.search(opt.get('league_name', '') or ''))


def is_whitelisted(opt):
    try:
        return int(opt.get('league')) in WHITELIST
    except (TypeError, ValueError):
        return False

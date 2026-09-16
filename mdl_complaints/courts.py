"""Expand the JPML's court abbreviations into readable names.

Attachment descriptions identify the originating court with a compact code.
Two conventions show up in practice, sometimes within the same docket:

* JPML style -- state code then division letter: ``CAN``, ``MOW``, ``INS``.
* Reporter style -- division letter, ``D``, then state code: ``NDCA``, ``SDIN``.

Both are regular, so the codes are decoded rather than stored in a
hand-maintained table of ~94 districts.
"""

from __future__ import annotations

import re

STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

DIVISIONS = {
    "N": "Northern", "S": "Southern", "E": "Eastern",
    "W": "Western", "C": "Central", "M": "Middle",
}

# Districts that are not states and so do not follow the pattern.
TERRITORIES = {
    "DC": "District of Columbia",
    "PR": "Puerto Rico",
    "GU": "Guam",
    "VI": "Virgin Islands",
    "NMI": "Northern Mariana Islands",
}


_REPORTER_RE = re.compile(r"^(?P<div>[NSEWCM])D(?P<state>[A-Z]{2})$")
_DISTRICT_RE = re.compile(r"^D(?P<state>[A-Z]{2})$")


# Districts whose CourtListener id does not follow the state+division+"d" rule.
_TERRITORY_IDS = {
    "DC": "dcd", "PR": "prd", "GU": "gud", "VI": "vid", "NMI": "nmid",
}


def parse_court_code(code: str) -> tuple[str, str]:
    """Split a court code into ``(state_code, division_letter)``.

    Returns ``("", "")`` when the code is not recognised.

    >>> parse_court_code("CAN")
    ('CA', 'N')
    >>> parse_court_code("NDCA")
    ('CA', 'N')
    >>> parse_court_code("MA")
    ('MA', '')
    """
    if not code:
        return "", ""
    key = code.strip().upper()
    if key in STATES:
        return key, ""
    if len(key) == 3 and key[:2] in STATES and key[2] in DIVISIONS:
        return key[:2], key[2]
    match = _REPORTER_RE.match(key)
    if match and match.group("state") in STATES:
        return match.group("state"), match.group("div")
    match = _DISTRICT_RE.match(key)
    if match and match.group("state") in STATES:
        return match.group("state"), ""
    return "", ""


def courtlistener_id(code: str) -> str:
    """Map a JPML court code to a CourtListener ``court_id``.

    CourtListener ids are the lowercased state code, the division letter and a
    trailing ``d`` -- ``CAN`` and ``NDCA`` both become ``cand``.

    >>> courtlistener_id("CAN")
    'cand'
    >>> courtlistener_id("NDCA")
    'cand'
    >>> courtlistener_id("NV")
    'nvd'
    >>> courtlistener_id("DC")
    'dcd'
    >>> courtlistener_id("ZZQ")
    ''
    """
    key = (code or "").strip().upper()
    if key in _TERRITORY_IDS:
        return _TERRITORY_IDS[key]
    state, division = parse_court_code(key)
    if not state:
        return ""
    return f"{state}{division}d".lower()


def _build_name_index() -> dict[str, str]:
    """``{"california northern": "cand", ...}`` for parsing entry descriptions."""
    index: dict[str, str] = {}
    for state_code, state_name in STATES.items():
        index[state_name.lower()] = f"{state_code.lower()}d"
        for division_letter, division_name in DIVISIONS.items():
            key = f"{state_name} {division_name}".lower()
            index[key] = f"{state_code.lower()}{division_letter.lower()}d"
    for code, name in TERRITORIES.items():
        index[name.lower()] = _TERRITORY_IDS[code]
    return index


_NAME_TO_ID = _build_name_index()


def court_id_from_name(name: str) -> str:
    """Map a spelled-out district to a CourtListener ``court_id``.

    JPML entry descriptions name courts in full ("Florida Northern District
    Court"), unlike attachment descriptions which use codes.

    >>> court_id_from_name("Florida Northern")
    'flnd'
    >>> court_id_from_name("District of Columbia")
    'dcd'
    >>> court_id_from_name("Atlantis Eastern")
    ''
    """
    return _NAME_TO_ID.get((name or "").strip().lower(), "")


def expand_court_code(code: str) -> str:
    """Return a human-readable district name for a JPML court code.

    Unrecognised codes are returned unchanged rather than guessed at, so bad
    input is visible in the output instead of silently mislabelled.

    >>> expand_court_code("CAN")
    'California Northern'
    >>> expand_court_code("NDCA")
    'California Northern'
    >>> expand_court_code("SDIN")
    'Indiana Southern'
    >>> expand_court_code("MA")
    'Massachusetts'
    >>> expand_court_code("ZZQ")
    'ZZQ'
    """
    if not code:
        return ""
    key = code.strip().upper()
    if key in TERRITORIES:
        return TERRITORIES[key]
    if key in STATES:
        return STATES[key]
    # JPML style: state code + division letter, e.g. CAN.
    if len(key) == 3 and key[:2] in STATES and key[2] in DIVISIONS:
        return f"{STATES[key[:2]]} {DIVISIONS[key[2]]}"
    # Reporter style: division letter + D + state code, e.g. NDCA.
    match = _REPORTER_RE.match(key)
    if match and match.group("state") in STATES:
        return f"{STATES[match.group('state')]} {DIVISIONS[match.group('div')]}"
    # Single-district states written as DMN, DNV, ...
    match = _DISTRICT_RE.match(key)
    if match and match.group("state") in STATES:
        return STATES[match.group("state")]
    return code

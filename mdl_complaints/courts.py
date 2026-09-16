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

"""Canonical Indian state list (code + name) shared by the rules engine, the
fuel-band lookup, and the fuel expense dropdown.

This is the single source of truth for the ``state_code`` values stored on
`trips` / `expenses` and referenced by `fuel_benchmarks`. Keeping it here
(Server Authoritative) let the API hand the exact list to the client dropdown, so
the driver can pick the fueling state and the engine can look up its band.
"""

from __future__ import annotations

# Ordered, stable list used for the fueling-state dropdown. Matches the 2-letter
# RTO codes used across the app (plate prefix, fuel_benchmarks.state_code).
INDIAN_STATES: list[tuple[str, str]] = [
    ("AN", "Andaman & Nicobar"),
    ("AP", "Andhra Pradesh"),
    ("AR", "Arunachal Pradesh"),
    ("AS", "Assam"),
    ("BR", "Bihar"),
    ("CH", "Chandigarh"),
    ("CG", "Chhattisgarh"),
    ("DD", "Dadra & Nagar Haveli"),
    ("DL", "Delhi"),
    ("GA", "Goa"),
    ("GJ", "Gujarat"),
    ("HR", "Haryana"),
    ("HP", "Himachal Pradesh"),
    ("JK", "Jammu & Kashmir"),
    ("JH", "Jharkhand"),
    ("KA", "Karnataka"),
    ("KL", "Kerala"),
    ("LD", "Lakshadweep"),
    ("MP", "Madhya Pradesh"),
    ("MH", "Maharashtra"),
    ("MN", "Manipur"),
    ("ML", "Meghalaya"),
    ("MZ", "Mizoram"),
    ("NL", "Nagaland"),
    ("OR", "Odisha"),
    ("PY", "Puducherry"),
    ("PB", "Punjab"),
    ("RJ", "Rajasthan"),
    ("SK", "Sikkim"),
    ("TN", "Tamil Nadu"),
    ("TS", "Telangana"),
    ("TR", "Tripura"),
    ("UP", "Uttar Pradesh"),
    ("UK", "Uttarakhand"),
    ("WB", "West Bengal"),
]

STATE_NAME_BY_CODE: dict[str, str] = {code: name for code, name in INDIAN_STATES}

STATE_CODES: list[str] = [code for code, _ in INDIAN_STATES]

# Aliases from the goodreturns "state name" -> canonical code, used by the
# live-rates scraper (services/fuel_live.py) to map scraped names to codes.
NAME_ALIASES: dict[str, str] = {

    "uttarpradesh": "UP",
    "delhi": "DL",
    "haryana": "HR",
    "madhyapradesh": "MP",
    "uttarakhand": "UK",
    "punjab": "PB",
    "rajasthan": "RJ",
    "bihar": "BR",
    "chandigarh": "CH",

    # "andaman&nicobar": "AN",
    # "andhrapradesh": "AP",
    # "arunachalpradesh": "AR",
    # "assam": "AS",
    # "chhatisgarh": "CG",
    # "chhattisgarh": "CG",
    # "goa": "GA",
    # "gujarat": "GJ",
    # "himachalpradesh": "HP",
    # "jammukashmir": "JK",
    # "jharkhand": "JH",
    # "karnataka": "KA",
    # "kerala": "KL",
    # "lakshadweep": "LD",
    # "maharashtra": "MH",
    # "manipur": "MN",
    # "meghalaya": "ML",
    # "mizoram": "MZ",
    # "nagaland": "NL",
    # "odisha": "OR",
    # "pondicherry": "PY",
    # "sikkim": "SK",
    # "tamilnadu": "TN",
    # "telangana": "TS",
    # "tripura": "TR",
    # "westbengal": "WB",
}


def normalise_state_name(name: str) -> str:
    """Lowercase, strip non-alphanumeric chars so names match NAME_ALIASES."""
    return "".join(ch for ch in (name or "").lower() if ch.isalnum())


def code_from_name(name: str) -> str | None:
    """Return a canonical state code from a human state name, or None."""
    return NAME_ALIASES.get(normalise_state_name(name))

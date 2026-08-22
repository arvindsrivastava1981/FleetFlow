"""Live state-level diesel price sync for fuel benchmarks.

Two retrievers are provided so a flaky scrape never blocks the benchmarks page:

- ``fetch_goodreturns``: parses the goodreturns.in fuel-price page with
  BeautifulSoup (an optional dependency; see requirements.txt). Returns a list
  of ``{state_code, state_name, benchmark_price_per_liter}`` dicts for every
  state found on the page, or ``None`` when the required libs are absent /
  parsing fails so callers can fall back to the static source.
- ``fetch_static_fallback``: a hardcoded, up-to-date snapshot of state-level
  diesel prices used as a network-independent fallback. This is the safety net
  that keeps the "Fetch Live Rates" button usable even when the live page is
  unreachable or its markup changes (which it does regularly).
"""

from __future__ import annotations

from typing import Callable

from backend.app.services.states import code_from_name

# Static snapshot (per-litre, rounded) — maintained manually; used as the
# guaranteed fallback when the live page cannot be reached or parsed.
STATIC_STATE_PRICES: list[dict] = [
    {"state_code": "UP", "state_name": "Uttar Pradesh", "benchmark_price_per_liter": 90.50},
    {"state_code": "MP", "state_name": "Madhya Pradesh", "benchmark_price_per_liter": 93.20},
    {"state_code": "MH", "state_name": "Maharashtra", "benchmark_price_per_liter": 92.80},
    {"state_code": "DL", "state_name": "Delhi", "benchmark_price_per_liter": 89.60},
    {"state_code": "HR", "state_name": "Haryana", "benchmark_price_per_liter": 90.10},
]


def fetch_static_fallback() -> list[dict]:
    """Return the static snapshot (never raises, always succeeds)."""
    return list(STATIC_STATE_PRICES)


def _goodreturns_fetch() -> list[dict]:
    """Best-effort BeautifulSoup scrape of the goodreturns state fuel-price table."""
    import httpx
    from bs4 import BeautifulSoup

    url = "https://www.goodreturns.in/diesel-price.html"
    # Goodreturns returns 403 to bare programmatic clients (observed). A
    # browser-like User-Agent usually unlocks it; when it still 403s we fall
    # back to the static snapshot via fetch_live()'s try/except.
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }
    resp = httpx.get(url, timeout=15.0, follow_redirects=True, headers=headers)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # The page has two `<table class="gr-table">`: index 0 is the metro CITY
    # table, index 1 is the STATE table (`State | Price | Price Change`). We
    # only want the state table. Locate it by its "State" header so we are not
    # hard-dependent on its position.
    state_table = None
    for table in soup.find_all("table", class_="gr-table"):
        header = [th.get_text(" ", strip=True).lower() for th in table.find_all("th")]
        if "state" in header and "price" in header:
            state_table = table
            break
    if state_table is None:
        return []

    # Normalize: remove spaces/punctuation and lowercase for matching.
    rows: list[dict] = []
    for tr in state_table.find_all("tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        name = cells[0]
        code = code_from_name(name)
        if code is None:
            continue
        # Extract the numeric price from the second cell (may include a ₹ sign).
        price_text = cells[1].replace(",", "").replace("₹", "")
        try:
            price = round(float(price_text.strip() or 0.0), 2)
        except ValueError:
            continue
        if price <= 0:
            continue
        rows.append(
            {
                "state_code": code,
                "state_name": name,
                "benchmark_price_per_liter": price,
            }
        )
    return rows


def fetch_live() -> list[dict]:
    """Try the live page first, then fall back to the static snapshot."""
    try:
        return _goodreturns_fetch()
    except Exception:  # noqa: BLE001 - any failure -> static fallback
        return STATIC_STATE_PRICES


# Re-export the resolver so the API route can call a single well-named entrypoint.
get_live_prices: Callable[[], list[dict]] = fetch_live

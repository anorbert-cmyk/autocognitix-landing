#!/usr/bin/env python3
"""
autobazar.eu search-based price scraper (Slovak market, EUR prices).

Fetches search result pages for a given brand/model, extracts price/year/
mileage/fuel data from listing cards, and returns aggregated price statistics
converted to HUF via exchange-rate.json.

Uses only Python stdlib — no pip dependencies required.

Site structure (as of 2026-03):
  Search:  /en/vysledky/osobne-vozidla/{brand}/{model}/?page=N
  Detail:  /en/detail/{seo-slug}/{listing-id}/
  Prices are in EUR with space-separated thousands: "12 750 €"
  robots.txt allows crawling /en/vysledky/ pages (pages 2-50 explicitly allowed).

Usage:
    python autobazar_parser.py --brand Volkswagen --model Golf
    python autobazar_parser.py --brand Skoda --model Octavia --max 50
    python autobazar_parser.py --brand Volkswagen --model Golf --output results.json
    python autobazar_parser.py --list-brands
"""

import argparse
import json
import logging
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("autobazar")

BASE_URL = "https://www.autobazar.eu"
SEARCH_PATH = "/en/vysledky/osobne-vozidla"

# ---------------------------------------------------------------------------
# Config import (local)
# ---------------------------------------------------------------------------

try:
    from config import (
        BRANDS,
        REQUEST_DELAY,
        REQUEST_TIMEOUT,
        USER_AGENT,
    )
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import (
        BRANDS,
        REQUEST_DELAY,
        REQUEST_TIMEOUT,
        USER_AGENT,
    )

# ---------------------------------------------------------------------------
# AutoBazar.eu slug overrides
#
# hasznaltauto.hu uses Hungarian slugs; AutoBazar.eu uses lowercase English /
# brand-standard slugs.  We map from the canonical brand/model names in
# config.BRANDS to AutoBazar URL slugs.
# ---------------------------------------------------------------------------

_AUTOBAZAR_BRAND_SLUGS: Dict[str, str] = {
    "Suzuki": "suzuki",
    "Opel": "opel",
    "Volkswagen": "volkswagen",
    "Toyota": "toyota",
    "Ford": "ford",
    "Skoda": "skoda",
    "BMW": "bmw",
    "Mercedes-Benz": "mercedes-benz",
    "Audi": "audi",
    "Renault": "renault",
    "Peugeot": "peugeot",
    "Citroen": "citroen",
    "Hyundai": "hyundai",
    "Kia": "kia",
    "Fiat": "fiat",
    "Dacia": "dacia",
    "Honda": "honda",
    "Mazda": "mazda",
    "Nissan": "nissan",
    "Seat": "seat",
    "Volvo": "volvo",
    "Mitsubishi": "mitsubishi",
    "Jeep": "jeep",
    "Alfa Romeo": "alfa-romeo",
    "Mini": "mini",
}

_AUTOBAZAR_MODEL_SLUGS: Dict[str, Dict[str, str]] = {
    "BMW": {
        "3-series": "rad-3",
        "5-series": "rad-5",
        "1-series": "rad-1",
    },
    "Mercedes-Benz": {
        "A-class": "a",
        "C-class": "c",
        "E-class": "e",
    },
    "Citroen": {
        "C5 Aircross": "c5-aircross",
        "C3 Aircross": "c3-aircross",
    },
    "Mitsubishi": {
        "Eclipse Cross": "eclipse-cross",
        "Space Star": "space-star",
    },
    "Jeep": {
        "Grand Cherokee": "grand-cherokee",
    },
    "Volkswagen": {
        "T-Roc": "t-roc",
    },
    "Hyundai": {
        "ix35": "ix35",
    },
    "Mazda": {
        "CX-5": "cx-5",
        "CX-3": "cx-3",
        "CX-30": "cx-30",
    },
    "Nissan": {
        "X-Trail": "x-trail",
    },
    "Honda": {
        "CR-V": "cr-v",
        "HR-V": "hr-v",
    },
    "Fiat": {
        "500X": "500x",
    },
}


def _resolve_slugs(brand_name: str, model_name: str) -> Optional[Tuple[str, str]]:
    """Resolve brand/model names to AutoBazar.eu URL slugs."""
    brand_info = BRANDS.get(brand_name)
    if not brand_info:
        return None

    # Check model exists in config
    if model_name not in brand_info["models"]:
        return None

    # Brand slug: use override or lowercase the name
    brand_slug = _AUTOBAZAR_BRAND_SLUGS.get(brand_name, brand_name.lower())

    # Model slug: use override, or fall back to lowercase with spaces → hyphens
    model_overrides = _AUTOBAZAR_MODEL_SLUGS.get(brand_name, {})
    if model_name in model_overrides:
        model_slug = model_overrides[model_name]
    else:
        model_slug = model_name.lower().replace(" ", "-")

    return brand_slug, model_slug


# ---------------------------------------------------------------------------
# Exchange rate
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "shared" / "data"
_EXCHANGE_RATE_FILE = _DATA_DIR / "exchange-rate.json"

# Fallback rate if exchange-rate.json is missing
_DEFAULT_EUR_HUF = 400.0


def _load_eur_huf_rate() -> float:
    """Load EUR→HUF rate from shared/data/exchange-rate.json."""
    if _EXCHANGE_RATE_FILE.exists():
        try:
            with open(_EXCHANGE_RATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Canonical key is `rate` (Wave 1 schema, see shared/data/README.md);
            # legacy `EUR_HUF`/`eur_huf` kept as backwards-compat for stale local
            # checkouts. Without `rate` here the loader silently fell through to
            # the hardcoded 400.0 fallback after Wave 1 — Wave 4 fix.
            rate = data.get("rate") or data.get("EUR_HUF") or data.get("eur_huf")
            if rate and float(rate) > 0:
                log.info("EUR/HUF rate from %s: %.2f", _EXCHANGE_RATE_FILE.name, float(rate))
                return float(rate)
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            log.warning("Could not read exchange rate file: %s", exc)

    log.warning("Using default EUR/HUF rate: %.2f", _DEFAULT_EUR_HUF)
    return _DEFAULT_EUR_HUF


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------


def fetch_url(url: str, retries: int = 2) -> Optional[str]:
    """Fetch a URL and return the response body as a string, or None on failure."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,sk;q=0.8,hu;q=0.7",
    }
    req = urllib.request.Request(url, headers=headers)

    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                charset = resp.headers.get_content_charset() or "utf-8"
                return resp.read().decode(charset, errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                log.debug("404 Not Found: %s", url)
                return None
            if exc.code == 429:
                wait = REQUEST_DELAY * attempt * 3
                log.warning("Rate-limited (429) on %s — waiting %.1fs", url, wait)
                time.sleep(wait)
                continue
            log.warning("HTTP %d on %s (attempt %d/%d)", exc.code, url, attempt, retries)
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            log.warning("Network error on %s: %s (attempt %d/%d)", url, exc, attempt, retries)
        if attempt < retries:
            time.sleep(REQUEST_DELAY)

    log.error("Failed to fetch %s after %d attempts", url, retries)
    return None


# ---------------------------------------------------------------------------
# Search-page HTML parsing
# ---------------------------------------------------------------------------


class _SearchPageParser(HTMLParser):
    """
    Parse an AutoBazar.eu search result page.

    Extracts listing card data from the HTML.  The site renders listings
    as <a> links to detail pages, with price shown as "12 750 €" and
    metadata (year, mileage, fuel, power) near SVG feature icons.

    We collect text content and reconstruct listings from positional
    patterns in the text stream.
    """

    def __init__(self) -> None:
        super().__init__()
        self._detail_links: List[str] = []
        self._all_text: List[str] = []
        self._in_a = False
        self._current_href = ""
        self._script_buf: List[str] = []
        self._in_script = False
        self._script_type = ""
        self._json_data: List[dict] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr_dict = dict(attrs)
        if tag == "a":
            href = attr_dict.get("href", "")
            if href and ("/detail/" in href or "/detail-" in href):
                full = href if href.startswith("http") else BASE_URL + href
                if full not in self._detail_links:
                    self._detail_links.append(full)
            self._in_a = True
            self._current_href = href
        if tag == "script":
            self._script_type = attr_dict.get("type", "")
            if self._script_type == "application/ld+json":
                self._in_script = True
                self._script_buf = []
            # Also look for __NEXT_DATA__ or embedded props
            script_id = attr_dict.get("id", "")
            if script_id == "__NEXT_DATA__":
                self._in_script = True
                self._script_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._in_a = False
        if tag == "script" and self._in_script:
            self._in_script = False
            raw = "".join(self._script_buf)
            try:
                data = json.loads(raw)
                self._json_data.append(data)
            except (json.JSONDecodeError, TypeError):
                pass

    def handle_data(self, data: str) -> None:
        if self._in_script:
            self._script_buf.append(data)
        text = data.strip()
        if text:
            self._all_text.append(text)


def _parse_number(text: str) -> Optional[int]:
    """Extract an integer from text, stripping spaces/separators."""
    cleaned = re.sub(r"[^\d]", "", text)
    if cleaned:
        try:
            return int(cleaned)
        except ValueError:
            pass
    return None


def _extract_listings_from_text(
    text_chunks: List[str],
    detail_links: List[str],
    json_data: List[dict],
) -> List[Dict[str, Any]]:
    """
    Extract listing data from the collected text stream and detail links.

    Strategy:
    1. First try to extract from embedded JSON (__NEXT_DATA__ / props).
    2. Fall back to regex on the text stream: find price patterns ("N €"),
       year (4-digit near date icon context), mileage ("N km"), fuel keywords.
    """
    listings: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Strategy 1: Embedded JSON (Next.js pageProps / trpcState)
    # ------------------------------------------------------------------
    for jd in json_data:
        items = _dig_json_listings(jd)
        if items:
            for item in items:
                listing = _normalize_json_listing(item)
                if listing and listing.get("price_eur"):
                    listings.append(listing)

    if listings:
        log.info("  Extracted %d listings from embedded JSON", len(listings))
        return listings

    # ------------------------------------------------------------------
    # Strategy 2: Regex on text stream
    # ------------------------------------------------------------------
    full_text = "\n".join(text_chunks)

    # Find all price occurrences: "12 750 €" or "12750 €" or "12,750 €"
    price_pattern = re.compile(r"([\d\s\.,]+)\s*€")
    year_pattern = re.compile(r"\b(\d{1,2}/)?(\d{4})\b")
    km_pattern = re.compile(r"([\d\s\.,]+)\s*km\b", re.IGNORECASE)
    fuel_keywords = {
        "diesel", "benzin", "petrol", "gasoline", "benzín",
        "lpg", "cng", "hybrid", "electric", "elektro", "phev",
        "plug-in", "nafta",
    }

    # Split text into segments roughly corresponding to listing cards.
    # Each listing card typically starts with a price or a detail link title.
    # We look for price occurrences and gather context around them.
    prices_found: List[Dict[str, Any]] = []
    for m in price_pattern.finditer(full_text):
        price_val = _parse_number(m.group(1))
        if not price_val or price_val < 100 or price_val > 500000:
            # Skip implausible EUR prices (monthly payments, etc.)
            continue

        # Look at surrounding context (300 chars before and after)
        start = max(0, m.start() - 300)
        end = min(len(full_text), m.end() + 300)
        context = full_text[start:end]

        entry: Dict[str, Any] = {"price_eur": price_val}

        # Year
        for ym in year_pattern.finditer(context):
            y = int(ym.group(2))
            if 1990 <= y <= 2030:
                entry["year"] = y
                break

        # Mileage
        km_m = km_pattern.search(context)
        if km_m:
            entry["mileage_km"] = _parse_number(km_m.group(1))

        # Fuel type
        context_lower = context.lower()
        for kw in fuel_keywords:
            if kw in context_lower:
                entry["fuel_type"] = kw.capitalize()
                break

        prices_found.append(entry)

    # Deduplicate by price+year combo (same card can match multiple times)
    seen = set()
    for entry in prices_found:
        key = (entry.get("price_eur"), entry.get("year"), entry.get("mileage_km"))
        if key not in seen:
            seen.add(key)
            listings.append(entry)

    log.info("  Extracted %d listings from text patterns", len(listings))
    return listings


def _dig_json_listings(data: Any, depth: int = 0) -> List[dict]:
    """Recursively search JSON for arrays of listing-like objects."""
    if depth > 10:
        return []

    results: List[dict] = []

    if isinstance(data, dict):
        # Check if this dict looks like a listing
        if _is_listing_dict(data):
            results.append(data)

        for v in data.values():
            results.extend(_dig_json_listings(v, depth + 1))

    elif isinstance(data, list):
        # Check if this is an array of listing dicts
        listing_count = sum(1 for item in data if isinstance(item, dict) and _is_listing_dict(item))
        if listing_count >= 2:
            for item in data:
                if isinstance(item, dict) and _is_listing_dict(item):
                    results.append(item)
        else:
            for item in data:
                results.extend(_dig_json_listings(item, depth + 1))

    return results


def _is_listing_dict(d: dict) -> bool:
    """Check if a dict looks like a car listing (has price-like and year-like keys)."""
    keys_lower = {k.lower() for k in d.keys()}
    has_price = any(
        kw in keys_lower
        for kw in ("price", "pricecurrent", "price_eur", "pricewithvat", "cena")
    )
    has_vehicle = any(
        kw in keys_lower
        for kw in ("year", "yearvalue", "mileage", "fuelvalue", "fuel", "brand", "make", "model")
    )
    return has_price and has_vehicle


def _normalize_json_listing(item: dict) -> Optional[Dict[str, Any]]:
    """Normalize a raw JSON listing dict to our standard format."""
    result: Dict[str, Any] = {}

    # Price (EUR)
    for key in ("priceCurrent", "price", "priceWithVat", "price_eur", "cena"):
        val = item.get(key)
        if val is not None:
            try:
                p = int(float(str(val).replace(" ", "").replace(",", "")))
                if 100 < p < 500000:
                    result["price_eur"] = p
                    break
            except (ValueError, TypeError):
                pass

    # Year
    for key in ("yearValue", "year", "rok"):
        val = item.get(key)
        if val is not None:
            y = _parse_number(str(val))
            if y and 1990 <= y <= 2030:
                result["year"] = y
                break

    # Mileage
    for key in ("mileage", "mileageValue", "km", "kilometre"):
        val = item.get(key)
        if val is not None:
            m = _parse_number(str(val))
            if m is not None:
                result["mileage_km"] = m
                break

    # Fuel
    for key in ("fuelValue", "fuel", "fuelType", "palivo"):
        val = item.get(key)
        if val:
            result["fuel_type"] = str(val).strip()
            break

    return result if result.get("price_eur") else None


# ---------------------------------------------------------------------------
# Pagination & scraping flow
# ---------------------------------------------------------------------------


def _build_search_url(brand_slug: str, model_slug: str, page: int = 1) -> str:
    """Build a search result page URL."""
    url = f"{BASE_URL}{SEARCH_PATH}/{brand_slug}/{model_slug}/"
    if page > 1:
        url += f"?page={page}"
    return url


def _scrape_search_page(url: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Fetch and parse a single search result page.

    Returns (listings, detail_links).
    """
    html = fetch_url(url)
    if not html:
        return [], []

    parser = _SearchPageParser()
    try:
        parser.feed(html)
    except Exception as exc:
        log.warning("HTML parse error on %s: %s", url, exc)
        return [], []

    listings = _extract_listings_from_text(
        parser._all_text,
        parser._detail_links,
        parser._json_data,
    )

    return listings, parser._detail_links


def _detect_max_page(html: str) -> int:
    """Detect the maximum page number from pagination links."""
    # Pattern: ?page=N in href attributes
    pages = re.findall(r"\?page=(\d+)", html)
    if pages:
        return max(int(p) for p in pages)
    return 1


def _scrape_detail_page(url: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a detail page and extract structured listing data.

    Detail pages often have richer embedded JSON (priceCurrent, yearValue, etc.).
    """
    html = fetch_url(url)
    if not html:
        return None

    result: Dict[str, Any] = {"source_url": url}

    # Try to extract from embedded JSON in the page
    # Look for patterns like "priceCurrent":12750
    price_m = re.search(r'"priceCurrent"\s*:\s*(\d+)', html)
    if price_m:
        result["price_eur"] = int(price_m.group(1))

    year_m = re.search(r'"yearValue"\s*:\s*"?(\d{4})"?', html)
    if year_m:
        result["year"] = int(year_m.group(1))

    mileage_m = re.search(r'"mileage"\s*:\s*(\d+)', html)
    if mileage_m:
        result["mileage_km"] = int(mileage_m.group(1))

    fuel_m = re.search(r'"fuelValue"\s*:\s*"([^"]+)"', html)
    if fuel_m:
        result["fuel_type"] = fuel_m.group(1)

    # Fallback: parse from visible text
    if "price_eur" not in result:
        price_text = re.search(r"([\d\s\.,]+)\s*€", html)
        if price_text:
            p = _parse_number(price_text.group(1))
            if p and 100 < p < 500000:
                result["price_eur"] = p

    if "year" not in result:
        # Look for year in specs section: "2/2020" or standalone "2020"
        year_text = re.search(
            r"(?:date\.svg|Year|Rok)[^0-9]{0,50}(\d{1,2}/)?(\d{4})", html
        )
        if year_text:
            y = int(year_text.group(2))
            if 1990 <= y <= 2030:
                result["year"] = y

    if "mileage_km" not in result:
        km_text = re.search(r"([\d\s\.,]{2,12})\s*km\b", html, re.IGNORECASE)
        if km_text:
            result["mileage_km"] = _parse_number(km_text.group(1))

    return result if result.get("price_eur") else None


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate_by_year(
    listings: List[Dict[str, Any]],
    eur_huf_rate: float,
) -> Dict[str, Dict[str, Any]]:
    """Group listings by year and compute min/median/max price stats in both EUR and HUF."""
    by_year: Dict[int, List[int]] = defaultdict(list)
    no_year: List[int] = []

    for item in listings:
        price = item.get("price_eur")
        if not price or price <= 0:
            continue
        year = item.get("year")
        if year and 1990 <= year <= 2030:
            by_year[year].append(price)
        else:
            no_year.append(price)

    result = {}
    for year in sorted(by_year.keys()):
        prices_eur = sorted(by_year[year])
        result[str(year)] = _compute_stats(prices_eur, eur_huf_rate)

    if no_year:
        no_year.sort()
        stats = _compute_stats(no_year, eur_huf_rate)
        result["unknown_year"] = stats

    return result


def _compute_stats(prices_eur: List[int], eur_huf_rate: float) -> Dict[str, Any]:
    """Compute price statistics for a list of EUR prices."""
    min_eur = prices_eur[0]
    max_eur = prices_eur[-1]
    median_eur = int(statistics.median(prices_eur))
    avg_eur = int(statistics.mean(prices_eur))

    return {
        "count": len(prices_eur),
        "min_eur": min_eur,
        "median_eur": median_eur,
        "avg_eur": avg_eur,
        "max_eur": max_eur,
        # HUF conversions (rounded to nearest 10,000)
        "min": _eur_to_huf(min_eur, eur_huf_rate),
        "avg": _eur_to_huf(avg_eur, eur_huf_rate),
        "max": _eur_to_huf(max_eur, eur_huf_rate),
    }


def _eur_to_huf(eur: int, rate: float) -> int:
    """Convert EUR to HUF, rounded to nearest 10,000."""
    return int(round(eur * rate / 10000) * 10000)


def _fuel_distribution(listings: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count listings by fuel type."""
    dist: Dict[str, int] = defaultdict(int)
    for item in listings:
        ft = item.get("fuel_type", "unknown")
        dist[str(ft)] += 1
    return dict(sorted(dist.items(), key=lambda x: -x[1]))


# ---------------------------------------------------------------------------
# Main scraping flow
# ---------------------------------------------------------------------------


def scrape_brand_model(
    brand_name: str,
    model_name: str,
    max_listings: Optional[int] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Full pipeline: search pages -> extract -> detail fallback -> aggregate.

    Returns a dict with metadata and aggregated price stats.
    """
    if verbose:
        log.setLevel(logging.DEBUG)

    # Resolve slugs
    slugs = _resolve_slugs(brand_name, model_name)
    if not slugs:
        brand_info = BRANDS.get(brand_name)
        if not brand_info:
            log.error("Unknown brand: %s. Available: %s", brand_name, ", ".join(BRANDS.keys()))
            return {"error": f"Unknown brand: {brand_name}"}
        log.error(
            "Unknown model: %s for %s. Available: %s",
            model_name, brand_name, ", ".join(brand_info["models"].keys()),
        )
        return {"error": f"Unknown model: {model_name} for {brand_name}"}

    brand_slug, model_slug = slugs
    limit = max_listings or 30

    log.info("=== Scraping %s %s from autobazar.eu ===", brand_name, model_name)
    log.info("Search URL: %s", _build_search_url(brand_slug, model_slug))

    # Load exchange rate
    eur_huf_rate = _load_eur_huf_rate()

    # Step 1: Fetch first search page to detect pagination
    log.info("Step 1/3: Fetching search results...")
    first_url = _build_search_url(brand_slug, model_slug, page=1)
    first_html = fetch_url(first_url)
    if not first_html:
        return {
            "brand": brand_name,
            "model": model_name,
            "error": "Could not fetch search page",
        }

    max_page = _detect_max_page(first_html)
    log.info("  Detected %d pages of results", max_page)

    # Parse first page
    parser = _SearchPageParser()
    try:
        parser.feed(first_html)
    except Exception as exc:
        log.warning("HTML parse error on page 1: %s", exc)

    all_listings = _extract_listings_from_text(
        parser._all_text, parser._detail_links, parser._json_data,
    )
    all_detail_links = list(parser._detail_links)

    # Step 2: Fetch additional search pages if needed
    pages_to_fetch = min(max_page, max(1, (limit + 19) // 20))  # ~20 listings per page
    if pages_to_fetch > 1:
        log.info("Step 2/3: Fetching pages 2–%d...", pages_to_fetch)
        for page in range(2, pages_to_fetch + 1):
            if len(all_listings) >= limit:
                break
            time.sleep(REQUEST_DELAY)
            url = _build_search_url(brand_slug, model_slug, page=page)
            log.info("  Page %d/%d: %s", page, pages_to_fetch, url)
            page_listings, page_links = _scrape_search_page(url)
            all_listings.extend(page_listings)
            all_detail_links.extend(page_links)
    else:
        log.info("Step 2/3: Single page of results — skipping pagination")

    log.info("  Collected %d listings from search pages", len(all_listings))

    # Step 3: If search-page extraction yielded few results, fall back to
    # scraping individual detail pages (more reliable but slower).
    if len(all_listings) < min(limit, 5) and all_detail_links:
        log.info(
            "Step 3/3: Search extraction sparse — scraping %d detail pages...",
            min(len(all_detail_links), limit),
        )
        detail_listings: List[Dict[str, Any]] = []
        for i, link in enumerate(all_detail_links[:limit], 1):
            time.sleep(REQUEST_DELAY)
            log.info("  [%d/%d] %s", i, min(len(all_detail_links), limit), link)
            data = _scrape_detail_page(link)
            if data:
                detail_listings.append(data)
                log.info(
                    "    -> %d EUR, year=%s, km=%s",
                    data.get("price_eur", 0),
                    data.get("year", "?"),
                    data.get("mileage_km", "?"),
                )
        # Merge: prefer detail data, then search data
        all_listings = detail_listings if detail_listings else all_listings
    else:
        log.info("Step 3/3: Sufficient data from search pages — skipping detail scrape")

    # Trim to limit
    all_listings = all_listings[:limit]

    if not all_listings:
        log.warning("No listings found for %s %s", brand_name, model_name)
        return {
            "brand": brand_name,
            "model": model_name,
            "source": "autobazar.eu",
            "listings_found": 0,
            "error": "No listings found",
        }

    # Aggregate
    log.info("Aggregating %d listings...", len(all_listings))
    aggregated = aggregate_by_year(all_listings, eur_huf_rate)

    # Overall stats
    all_prices_eur = sorted(
        item["price_eur"] for item in all_listings if item.get("price_eur")
    )
    overall_eur: Dict[str, Any] = {}
    overall_huf: Dict[str, Any] = {}
    if all_prices_eur:
        overall_eur = {
            "count": len(all_prices_eur),
            "min": all_prices_eur[0],
            "median": int(statistics.median(all_prices_eur)),
            "avg": int(statistics.mean(all_prices_eur)),
            "max": all_prices_eur[-1],
        }
        overall_huf = {
            "count": len(all_prices_eur),
            "min": _eur_to_huf(all_prices_eur[0], eur_huf_rate),
            "avg": _eur_to_huf(int(statistics.mean(all_prices_eur)), eur_huf_rate),
            "max": _eur_to_huf(all_prices_eur[-1], eur_huf_rate),
        }

    result = {
        "brand": brand_name,
        "model": model_name,
        "source": "autobazar.eu",
        "currency_original": "EUR",
        "eur_huf_rate": eur_huf_rate,
        "scrape_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "listings_scraped": len(all_listings),
        "overall_stats_eur": overall_eur,
        "overall_stats_huf": overall_huf,
        "by_year": aggregated,
        "fuel_type_distribution": _fuel_distribution(all_listings),
        "sample_listings": all_listings[:10],
    }

    log.info(
        "=== Done: %d listings, EUR range %s – %s (HUF %s – %s) ===",
        len(all_listings),
        f"{overall_eur.get('min', 0):,}",
        f"{overall_eur.get('max', 0):,}",
        f"{overall_huf.get('min', 0):,}",
        f"{overall_huf.get('max', 0):,}",
    )

    return result


# ---------------------------------------------------------------------------
# Output compatibility with hungarian-market-prices.json
# ---------------------------------------------------------------------------


def to_market_prices_format(result: Dict[str, Any]) -> Dict[str, Dict[str, Dict[str, int]]]:
    """
    Convert scraper output to the format used in hungarian-market-prices.json:

        { "BrandName": { "ModelName": { "2024": { "min": N, "avg": N, "max": N } } } }

    Prices are in HUF.
    """
    brand = result.get("brand", "Unknown")
    model = result.get("model", "Unknown")
    by_year = result.get("by_year", {})

    years_data: Dict[str, Dict[str, int]] = {}
    for year_str, stats in by_year.items():
        if year_str == "unknown_year":
            continue
        years_data[year_str] = {
            "min": stats["min"],
            "avg": stats["avg"],
            "max": stats["max"],
        }

    return {brand: {model: years_data}}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def print_summary(result: Dict[str, Any]) -> None:
    """Print a human-readable summary to stdout."""
    if "error" in result and result.get("listings_scraped", 0) == 0:
        print(f"\nError: {result['error']}")
        return

    eur_huf = result.get("eur_huf_rate", _DEFAULT_EUR_HUF)

    print(f"\n{'=' * 65}")
    print(f"  {result['brand']} {result['model']} — autobazar.eu (Slovak market)")
    print(f"{'=' * 65}")
    print(f"  Scraped at:   {result.get('scrape_timestamp', 'N/A')}")
    print(f"  Listings:     {result.get('listings_scraped', 0)}")
    print(f"  EUR/HUF rate: {eur_huf:.2f}")

    overall_eur = result.get("overall_stats_eur", {})
    overall_huf = result.get("overall_stats_huf", {})
    if overall_eur:
        print(f"\n  Overall Price Stats:")
        print(f"  {'':8} {'EUR':>12}  {'HUF':>14}")
        print(f"  {'Min':<8} {overall_eur.get('min', 0):>12,}  {overall_huf.get('min', 0):>14,}")
        print(f"  {'Median':<8} {overall_eur.get('median', 0):>12,}  {'—':>14}")
        print(f"  {'Avg':<8} {overall_eur.get('avg', 0):>12,}  {overall_huf.get('avg', 0):>14,}")
        print(f"  {'Max':<8} {overall_eur.get('max', 0):>12,}  {overall_huf.get('max', 0):>14,}")

    by_year = result.get("by_year", {})
    if by_year:
        print(f"\n  Price by Year:")
        print(f"  {'Year':<8} {'#':>4} {'Min EUR':>10} {'Med EUR':>10} {'Max EUR':>10}  {'Avg HUF':>12}")
        print(f"  {'-' * 60}")
        for year, stats in by_year.items():
            label = "N/A" if year == "unknown_year" else year
            print(
                f"  {label:<8} {stats['count']:>4} "
                f"{stats['min_eur']:>10,} {stats['median_eur']:>10,} {stats['max_eur']:>10,}"
                f"  {stats['avg']:>12,}"
            )

    fuel = result.get("fuel_type_distribution", {})
    if fuel:
        print(f"\n  Fuel Type Distribution:")
        for ft, count in fuel.items():
            print(f"    {ft}: {count}")

    print(f"\n{'=' * 65}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="autobazar.eu price scraper (Slovak market, EUR → HUF)",
    )
    parser.add_argument(
        "--brand", required=False, default=None,
        help="Brand name (e.g. Volkswagen, Skoda, BMW)",
    )
    parser.add_argument(
        "--model", required=False, default=None,
        help="Model name (e.g. Golf, Octavia, 3-series)",
    )
    parser.add_argument(
        "--max", type=int, default=30,
        help="Max listings to scrape (default: 30)",
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Output JSON file path",
    )
    parser.add_argument(
        "--market-format", action="store_true",
        help="Also output in hungarian-market-prices.json compatible format",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--list-brands", action="store_true",
        help="List available brands and models",
    )

    args = parser.parse_args()

    if args.list_brands:
        print("\nAvailable brands and models:\n")
        for brand_name, info in sorted(BRANDS.items()):
            models = ", ".join(sorted(info["models"].keys()))
            brand_slug = _AUTOBAZAR_BRAND_SLUGS.get(brand_name, brand_name.lower())
            print(f"  {brand_name} ({brand_slug}): {models}")
        print()
        return

    if not args.brand or not args.model:
        parser.error("--brand and --model are required (unless using --list-brands)")

    result = scrape_brand_model(
        brand_name=args.brand,
        model_name=args.model,
        max_listings=args.max,
        verbose=args.verbose,
    )

    # Print human-readable summary
    print_summary(result)

    # Optionally write JSON
    if args.output:
        output_data = result
        if args.market_format:
            output_data = {
                "autobazar_raw": result,
                "market_prices": to_market_prices_format(result),
            }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        log.info("Results written to %s", args.output)
    elif args.market_format:
        # Print market-format JSON to stdout
        market = to_market_prices_format(result)
        print(json.dumps(market, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

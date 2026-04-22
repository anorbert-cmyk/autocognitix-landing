#!/usr/bin/env python3
"""
bazos.sk (auto.bazos.sk) search-based price scraper.

Bazos.sk is a Slovak classified ads site with native EUR prices.
Uses search pages (not sitemaps) for efficient brand/model lookup,
then optionally fetches detail pages for year/mileage extraction.

Uses only Python stdlib — no pip dependencies required.

Usage:
    python bazos_parser.py --brand Volkswagen --model Golf
    python bazos_parser.py --brand Skoda --model Octavia --max 30
    python bazos_parser.py --brand Skoda --model Octavia --output results.json
    python bazos_parser.py --list-brands
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
import urllib.parse
import urllib.request
from collections import defaultdict
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bazos")

BASE_URL = "https://auto.bazos.sk"
ITEMS_PER_PAGE = 20

# Sanity bounds — reject junk listings (1 EUR teaser, 999k EUR supercars, etc.)
EUR_PRICE_MIN = 500
EUR_PRICE_MAX = 300_000
HUF_PRICE_MIN = 300_000
HUF_PRICE_MAX = 200_000_000

# ---------------------------------------------------------------------------
# Config import (local)
# ---------------------------------------------------------------------------

try:
    from config import (
        BRANDS,
        MAX_LISTINGS_PER_QUERY,
        REQUEST_DELAY,
        REQUEST_TIMEOUT,
        USER_AGENT,
    )
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import (
        BRANDS,
        MAX_LISTINGS_PER_QUERY,
        REQUEST_DELAY,
        REQUEST_TIMEOUT,
        USER_AGENT,
    )

# ---------------------------------------------------------------------------
# Bazos.sk brand slug mapping
# ---------------------------------------------------------------------------
# Bazos uses its own slug convention (lowercase, no diacritics, some
# abbreviations).  This maps config brand names -> bazos URL slugs.

BAZOS_BRAND_SLUGS: Dict[str, str] = {
    "Alfa Romeo": "alfa",
    "Audi": "audi",
    "BMW": "bmw",
    "Citroen": "citroen",
    "Dacia": "dacia",
    "Fiat": "fiat",
    "Ford": "ford",
    "Honda": "honda",
    "Hyundai": "hyundai",
    "Jeep": "jeep",
    "Kia": "kia",
    "Mazda": "mazda",
    "Mercedes-Benz": "mercedes",
    "Mini": "mini",
    "Mitsubishi": "mitsubishi",
    "Nissan": "nissan",
    "Opel": "opel",
    "Peugeot": "peugeot",
    "Renault": "renault",
    "Seat": "seat",
    "Skoda": "skoda",
    "Suzuki": "suzuki",
    "Toyota": "toyota",
    "Volkswagen": "volkswagen",
    "Volvo": "volvo",
}

# Bazos uses simple lowercase model names in search queries.
# Most models map 1:1 (just lowercase), but some need adjustment.
BAZOS_MODEL_SEARCH: Dict[str, Dict[str, str]] = {
    "BMW": {
        "3-series": "3",
        "5-series": "5",
        "1-series": "1",
    },
    "Mercedes-Benz": {
        "A-class": "A",
        "C-class": "C",
        "E-class": "E",
    },
    "Citroen": {
        "C5 Aircross": "C5 Aircross",
        "C3 Aircross": "C3 Aircross",
    },
    "Jeep": {
        "Grand Cherokee": "Grand Cherokee",
    },
    "Mitsubishi": {
        "Eclipse Cross": "Eclipse Cross",
        "Space Star": "Space Star",
    },
}

# ---------------------------------------------------------------------------
# Exchange rate loading
# ---------------------------------------------------------------------------

EXCHANGE_RATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "shared", "data", "exchange-rate.json",
)


def load_eur_huf_rate() -> float:
    """Load EUR/HUF exchange rate from shared data file."""
    try:
        with open(EXCHANGE_RATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Canonical key is `rate` (Wave 1 schema, see shared/data/README.md);
        # legacy `EUR_HUF`/`eur_huf` kept as backwards-compat for stale local
        # checkouts. Without `rate` here the loader silently fell through to
        # the hardcoded 390.0 fallback after Wave 1 — Wave 4 fix.
        rate = data.get("rate") or data.get("EUR_HUF") or data.get("eur_huf")
        if rate:
            log.info("EUR/HUF rate: %.2f (from %s)", rate, data.get("date", "?"))
            return float(rate)
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
        log.warning("Could not load exchange rate: %s — using fallback", exc)

    # Fallback rate
    fallback = 390.0
    log.info("Using fallback EUR/HUF rate: %.2f", fallback)
    return fallback


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------


def fetch_url(url: str, retries: int = 2) -> Optional[str]:
    """Fetch a URL and return the response body as a string, or None on failure."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "sk-SK,sk;q=0.9,en;q=0.5",
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
# Search page HTML parser
# ---------------------------------------------------------------------------


class BazosSearchParser(HTMLParser):
    """
    Parse a Bazos.sk search results page.

    Actual HTML structure (verified March 2026):

      <div class="inzeraty inzeratyflex">
        <div class="inzeratynadpis">
          <a href="/inzerat/{id}/{slug}.php"><img ...></a>
          <h2 class=nadpis><a href="/inzerat/{id}/{slug}.php">Title</a></h2>
          <div class=popis>Description text...</div>
        </div>
        <div class="inzeratycena"><b><span translate="no">  6 999 €</span></b></div>
        <div class="inzeratylok">City<br>ZIP</div>
      </div>
    """

    def __init__(self):
        super().__init__()
        self.listings: List[Dict[str, Any]] = []
        self._current_listing: Optional[Dict[str, Any]] = None

        # Track which div we're inside
        self._in_nadpis = False   # <h2 class=nadpis>
        self._in_popis = False    # <div class=popis>
        self._in_cena = False     # <div class="inzeratycena">
        self._in_lok = False      # <div class="inzeratylok">

        self._nadpis_href = ""
        self._nadpis_text = ""
        self._popis_text = ""
        self._cena_text = ""
        self._lok_text = ""

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        attr_dict = dict(attrs)
        cls = attr_dict.get("class", "")

        # New listing container
        if tag == "div" and "inzeraty" in cls and "inzeratyflex" in cls:
            # Flush previous listing
            self._flush_listing()
            self._current_listing = {}

        # Title heading: <h2 class=nadpis>
        if tag == "h2" and "nadpis" in cls:
            self._in_nadpis = True
            self._nadpis_text = ""
            self._nadpis_href = ""

        # Link inside title heading
        if tag == "a" and self._in_nadpis:
            href = attr_dict.get("href", "")
            if "/inzerat/" in href:
                self._nadpis_href = href

        # Description: <div class=popis>
        if tag == "div" and "popis" in cls:
            self._in_popis = True
            self._popis_text = ""

        # Price: <div class="inzeratycena">
        if tag == "div" and "inzeratycena" in cls:
            self._in_cena = True
            self._cena_text = ""

        # Location: <div class="inzeratylok">
        if tag == "div" and "inzeratylok" in cls:
            self._in_lok = True
            self._lok_text = ""

    def handle_endtag(self, tag: str):
        if tag == "h2" and self._in_nadpis:
            self._in_nadpis = False
            if self._current_listing is not None and self._nadpis_href:
                self._current_listing["url"] = self._nadpis_href
                self._current_listing["title"] = self._nadpis_text.strip()

        if tag == "div" and self._in_popis:
            self._in_popis = False
            if self._current_listing is not None:
                self._current_listing["description"] = self._popis_text.strip()

        if tag == "div" and self._in_cena:
            self._in_cena = False
            if self._current_listing is not None:
                price = _parse_eur_price(self._cena_text)
                if price:
                    self._current_listing["price_eur"] = price

        if tag == "div" and self._in_lok:
            self._in_lok = False
            if self._current_listing is not None:
                self._current_listing["location"] = self._lok_text.strip()

    def handle_data(self, data: str):
        if self._in_nadpis:
            self._nadpis_text += data
        if self._in_popis:
            self._popis_text += data
        if self._in_cena:
            self._cena_text += data
        if self._in_lok:
            self._lok_text += " " + data

    def _flush_listing(self):
        """Save current listing if it has the minimum required data."""
        if self._current_listing and self._current_listing.get("url"):
            self.listings.append(self._current_listing)
        self._current_listing = None

    def finalize(self):
        """Flush the last pending listing."""
        self._flush_listing()


class BazosDetailParser(HTMLParser):
    """
    Parse a Bazos.sk detail page for year, mileage, and precise price.

    Detail pages contain lines like:
      "Rok výroby: 09/2021"
      "Najazdené: 119 700 km"
      "Cena: 47999 €"
    """

    def __init__(self):
        super().__init__()
        self._all_text: List[str] = []

    def handle_data(self, data: str):
        self._all_text.append(data)

    def get_text(self) -> str:
        return " ".join(self._all_text)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_eur_price(text: str) -> Optional[int]:
    """Extract EUR price from text like '6 999 €' or '14499€'."""
    # Remove everything except digits and whitespace before €
    match = re.search(r"([\d\s\.\,]+)\s*€", text)
    if match:
        cleaned = re.sub(r"[^\d]", "", match.group(1))
        if cleaned:
            try:
                return int(cleaned)
            except ValueError:
                pass
    return None


def _parse_number(text: str) -> Optional[int]:
    """Extract an integer from text, stripping spaces/separators."""
    cleaned = re.sub(r"[^\d]", "", text)
    if cleaned:
        try:
            return int(cleaned)
        except ValueError:
            pass
    return None


def _extract_year_from_text(text: str) -> Optional[int]:
    """Extract production year from detail page text."""
    # "Rok výroby: 09/2021" or "Rok výroby: 2021"
    match = re.search(
        r"[Rr]ok\s+v[ýy]roby[:\s]+(?:\d{1,2}/)?((?:19|20)\d{2})",
        text,
    )
    if match:
        return int(match.group(1))

    # Fallback: look for year in title patterns like "6/2015" or "2018"
    match = re.search(r"(?:\d{1,2}/)?((?:19|20)\d{2})", text)
    if match:
        year = int(match.group(1))
        if 1990 <= year <= 2030:
            return year

    return None


def _extract_year_from_title(title: str) -> Optional[int]:
    """Try to extract year from listing title like 'Golf 2.0TDI 6/2015'."""
    # Pattern: MM/YYYY or just YYYY in title
    match = re.search(r"(?:\d{1,2}/)?((?:19|20)\d{2})", title)
    if match:
        year = int(match.group(1))
        if 1990 <= year <= 2030:
            return year
    return None


def _extract_mileage_from_text(text: str) -> Optional[int]:
    """Extract mileage from detail page text."""
    # "Najazdené: 119 700 km" or "119700 km"
    match = re.search(r"[Nn]ajazden[eé][:\s]+([\d\s]+)\s*km", text)
    if match:
        return _parse_number(match.group(1))

    # Fallback: any number followed by km
    match = re.search(r"([\d\s]{3,10})\s*km\b", text)
    if match:
        return _parse_number(match.group(1))

    return None


# ---------------------------------------------------------------------------
# URL construction
# ---------------------------------------------------------------------------


def get_bazos_brand_slug(brand_name: str) -> Optional[str]:
    """Resolve brand name to bazos.sk URL slug."""
    return BAZOS_BRAND_SLUGS.get(brand_name)


def get_bazos_model_search_term(brand_name: str, model_name: str) -> str:
    """Get the search term for a model on bazos.sk."""
    overrides = BAZOS_MODEL_SEARCH.get(brand_name, {})
    return overrides.get(model_name, model_name)


def build_search_url(brand_slug: str, model_search: str, offset: int = 0) -> str:
    """
    Build a bazos.sk search URL.

    Pattern: https://auto.bazos.sk/{brand}/{offset}/?hledat={model}
    """
    if offset > 0:
        path = f"/{brand_slug}/{offset}/"
    else:
        path = f"/{brand_slug}/"

    params = urllib.parse.urlencode({"hledat": model_search})
    return f"{BASE_URL}{path}?{params}"


# ---------------------------------------------------------------------------
# Search page scraping
# ---------------------------------------------------------------------------


def scrape_search_page(url: str) -> List[Dict[str, Any]]:
    """Fetch and parse a single search results page, returning listing dicts."""
    html = fetch_url(url)
    if not html:
        return []

    parser = BazosSearchParser()
    try:
        parser.feed(html)
        parser.finalize()
    except Exception as exc:
        log.warning("HTML parse error on %s: %s", url, exc)
        return []

    # Normalize URLs to absolute
    for listing in parser.listings:
        href = listing.get("url", "")
        if href and not href.startswith("http"):
            listing["url"] = BASE_URL + href

    return parser.listings


def scrape_detail_page(url: str) -> Dict[str, Any]:
    """Fetch a detail page and extract year/mileage."""
    html = fetch_url(url)
    if not html:
        return {}

    parser = BazosDetailParser()
    try:
        parser.feed(html)
    except Exception as exc:
        log.warning("HTML parse error on detail %s: %s", url, exc)
        return {}

    text = parser.get_text()
    result: Dict[str, Any] = {}

    year = _extract_year_from_text(text)
    if year:
        result["year"] = year

    mileage = _extract_mileage_from_text(text)
    if mileage:
        result["mileage"] = mileage

    # Also try to get a more precise price from detail page
    price = _parse_eur_price(text)
    if price:
        result["price_eur"] = price

    return result


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate_by_year(
    listings: List[Dict[str, Any]],
    eur_huf_rate: float,
) -> Dict[str, Dict[str, Any]]:
    """
    Group listings by year and compute min/median/max price stats in HUF.

    URL-dedup (bazos pagination can re-surface listings) + EUR/HUF sanity bounds.
    """
    by_year: Dict[int, List[int]] = defaultdict(list)
    no_year: List[int] = []
    seen_urls: set[str] = set()
    rejected_bounds = 0
    rejected_dup = 0

    for item in listings:
        url = item.get("url")
        if url:
            if url in seen_urls:
                rejected_dup += 1
                continue
            seen_urls.add(url)

        price_eur = item.get("price_eur")
        if not price_eur or price_eur <= 0:
            continue
        if price_eur < EUR_PRICE_MIN or price_eur > EUR_PRICE_MAX:
            rejected_bounds += 1
            continue

        price_huf = int(round(price_eur * eur_huf_rate))
        if price_huf < HUF_PRICE_MIN or price_huf > HUF_PRICE_MAX:
            rejected_bounds += 1
            continue

        year = item.get("year")
        if year and 1990 <= year <= 2030:
            by_year[year].append(price_huf)
        else:
            no_year.append(price_huf)

    if rejected_bounds or rejected_dup:
        log.info(
            "aggregate_by_year: rejected %d out-of-bounds, %d duplicate URLs",
            rejected_bounds, rejected_dup,
        )

    result = {}
    for year in sorted(by_year.keys()):
        prices = sorted(by_year[year])
        result[str(year)] = {
            "count": len(prices),
            "min": prices[0],
            "median": int(statistics.median(prices)),
            "avg": int(statistics.mean(prices)),
            "max": prices[-1],
            "prices": prices,
        }

    if no_year:
        no_year.sort()
        result["unknown_year"] = {
            "count": len(no_year),
            "min": no_year[0],
            "median": int(statistics.median(no_year)),
            "avg": int(statistics.mean(no_year)),
            "max": no_year[-1],
        }

    return result


def _fuel_distribution(listings: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count listings by fuel type."""
    dist: Dict[str, int] = defaultdict(int)
    for item in listings:
        ft = item.get("fuel_type", "unknown")
        dist[str(ft)] += 1
    return dict(sorted(dist.items(), key=lambda x: -x[1]))


# ---------------------------------------------------------------------------
# Output format compatible with hungarian-market-prices.json
# ---------------------------------------------------------------------------


def to_market_prices_format(
    brand_name: str,
    model_name: str,
    by_year: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Convert aggregated data to the format used in hungarian-market-prices.json.

    Output: { "brands": { "Brand": { "Model": { "YYYY": { min, avg, max } } } } }
    """
    model_data = {}
    for year_str, stats in by_year.items():
        if year_str == "unknown_year":
            continue
        model_data[year_str] = {
            "min": stats["min"],
            "avg": stats["avg"],
            "max": stats["max"],
        }

    return {
        "_meta": {
            "source": "bazos.sk (Slovak market, EUR converted to HUF)",
            "updated": time.strftime("%Y-%m-%d"),
            "currency": "HUF",
        },
        "brands": {
            brand_name: {
                model_name: model_data,
            },
        },
    }


# ---------------------------------------------------------------------------
# Main scraping flow
# ---------------------------------------------------------------------------


def scrape_brand_model(
    brand_name: str,
    model_name: str,
    max_listings: Optional[int] = None,
    fetch_details: bool = True,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Full pipeline: search pages -> (optional) detail pages -> aggregate.

    Returns a dict with metadata and aggregated price stats.
    """
    if verbose:
        log.setLevel(logging.DEBUG)

    # Resolve brand
    brand_info = BRANDS.get(brand_name)
    if not brand_info:
        log.error("Unknown brand: %s. Available: %s", brand_name, ", ".join(BRANDS.keys()))
        return {"error": f"Unknown brand: {brand_name}"}

    if model_name not in brand_info["models"]:
        log.error(
            "Unknown model: %s for %s. Available: %s",
            model_name, brand_name, ", ".join(brand_info["models"].keys()),
        )
        return {"error": f"Unknown model: {model_name} for {brand_name}"}

    bazos_slug = get_bazos_brand_slug(brand_name)
    if not bazos_slug:
        log.error("No bazos.sk slug mapping for brand: %s", brand_name)
        return {"error": f"No bazos.sk mapping for brand: {brand_name}"}

    model_search = get_bazos_model_search_term(brand_name, model_name)
    limit = max_listings or MAX_LISTINGS_PER_QUERY

    log.info(
        "=== Scraping bazos.sk: %s %s (/%s/?hledat=%s) ===",
        brand_name, model_name, bazos_slug, model_search,
    )

    # Load exchange rate
    eur_huf_rate = load_eur_huf_rate()

    # Step 1: Fetch search result pages
    log.info("Step 1/3: Fetching search result pages...")
    all_listings: List[Dict[str, Any]] = []
    offset = 0
    pages_fetched = 0
    max_pages = (limit // ITEMS_PER_PAGE) + 2  # safety margin

    while len(all_listings) < limit and pages_fetched < max_pages:
        url = build_search_url(bazos_slug, model_search, offset)
        log.info("  Page %d (offset %d): %s", pages_fetched + 1, offset, url)

        page_listings = scrape_search_page(url)
        if not page_listings:
            log.info("  No more listings found — stopping pagination")
            break

        all_listings.extend(page_listings)
        pages_fetched += 1
        offset += ITEMS_PER_PAGE

        log.info("  -> %d listings on this page (total: %d)", len(page_listings), len(all_listings))

        if len(page_listings) < ITEMS_PER_PAGE:
            log.info("  Last page reached (fewer than %d items)", ITEMS_PER_PAGE)
            break

        time.sleep(REQUEST_DELAY)

    # Trim to limit
    all_listings = all_listings[:limit]

    if not all_listings:
        log.warning("No listings found for %s %s on bazos.sk", brand_name, model_name)
        return {
            "brand": brand_name,
            "model": model_name,
            "source": "bazos.sk",
            "listings_found": 0,
            "error": "No listings found",
        }

    # Filter: only keep listings with a price
    priced = [l for l in all_listings if l.get("price_eur")]
    log.info("Listings with price: %d / %d", len(priced), len(all_listings))

    # Step 2: Try to extract year from title; optionally fetch detail pages
    log.info("Step 2/3: Extracting year/mileage data...")
    detail_fetches = 0
    max_detail_fetches = min(len(priced), limit)

    for listing in priced:
        # First try year from title (free — no extra request)
        title = listing.get("title", "")
        year_from_title = _extract_year_from_title(title)
        if year_from_title:
            listing["year"] = year_from_title

        # Fetch detail page if we still need year and detail fetching is on
        if fetch_details and "year" not in listing and detail_fetches < max_detail_fetches:
            detail_url = listing.get("url")
            if detail_url:
                log.info("  Fetching detail: %s", detail_url)
                detail_data = scrape_detail_page(detail_url)
                listing.update({k: v for k, v in detail_data.items() if k not in listing})
                detail_fetches += 1
                time.sleep(REQUEST_DELAY)

    log.info("Detail pages fetched: %d", detail_fetches)

    # Step 3: Aggregate
    log.info("Step 3/3: Aggregating %d listings...", len(priced))
    aggregated = aggregate_by_year(priced, eur_huf_rate)

    # Overall stats (in EUR)
    all_eur_prices = sorted([l["price_eur"] for l in priced if l.get("price_eur")])
    overall_eur = {}
    overall_huf = {}
    if all_eur_prices:
        overall_eur = {
            "count": len(all_eur_prices),
            "min": all_eur_prices[0],
            "median": int(statistics.median(all_eur_prices)),
            "avg": int(statistics.mean(all_eur_prices)),
            "max": all_eur_prices[-1],
        }
        overall_huf = {
            "count": len(all_eur_prices),
            "min": int(round(all_eur_prices[0] * eur_huf_rate)),
            "median": int(round(statistics.median(all_eur_prices) * eur_huf_rate)),
            "avg": int(round(statistics.mean(all_eur_prices) * eur_huf_rate)),
            "max": int(round(all_eur_prices[-1] * eur_huf_rate)),
        }

    # Market-prices compatible format
    market_format = to_market_prices_format(brand_name, model_name, aggregated)

    result = {
        "brand": brand_name,
        "model": model_name,
        "source": "bazos.sk",
        "bazos_brand_slug": bazos_slug,
        "bazos_model_search": model_search,
        "scrape_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "eur_huf_rate": eur_huf_rate,
        "pages_fetched": pages_fetched,
        "listings_found": len(all_listings),
        "listings_with_price": len(priced),
        "detail_pages_fetched": detail_fetches,
        "overall_stats_eur": overall_eur,
        "overall_stats_huf": overall_huf,
        "by_year": aggregated,
        "fuel_type_distribution": _fuel_distribution(priced),
        "market_prices_format": market_format,
        "sample_listings": [
            {
                "title": l.get("title"),
                "price_eur": l.get("price_eur"),
                "price_huf": int(round(l["price_eur"] * eur_huf_rate)) if l.get("price_eur") else None,
                "year": l.get("year"),
                "mileage": l.get("mileage"),
                "url": l.get("url"),
            }
            for l in priced[:10]
        ],
    }

    log.info(
        "=== Done: %d listings, EUR range %s – %s (HUF %s – %s) ===",
        len(priced),
        f"{overall_eur.get('min', 0):,}",
        f"{overall_eur.get('max', 0):,}",
        f"{overall_huf.get('min', 0):,}",
        f"{overall_huf.get('max', 0):,}",
    )

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def print_summary(result: Dict[str, Any]) -> None:
    """Print a human-readable summary to stdout."""
    if "error" in result and result.get("listings_with_price", 0) == 0:
        print(f"\nError: {result['error']}")
        return

    rate = result.get("eur_huf_rate", 390.0)

    print(f"\n{'=' * 65}")
    print(f"  {result['brand']} {result['model']} — bazos.sk Price Report")
    print(f"{'=' * 65}")
    print(f"  Source: bazos.sk (Slovak market, EUR prices)")
    print(f"  Scraped at: {result.get('scrape_timestamp', 'N/A')}")
    print(f"  EUR/HUF rate: {rate:.2f}")
    print(f"  Pages fetched: {result.get('pages_fetched', 0)}")
    print(f"  Listings found: {result.get('listings_found', 0)}")
    print(f"  With valid price: {result.get('listings_with_price', 0)}")
    print(f"  Detail pages fetched: {result.get('detail_pages_fetched', 0)}")

    overall_eur = result.get("overall_stats_eur", {})
    overall_huf = result.get("overall_stats_huf", {})
    if overall_eur:
        print(f"\n  Overall Price Stats:")
        print(f"  {'':>8} {'EUR':>12}  {'HUF':>14}")
        print(f"  {'Min:':<8} {overall_eur.get('min', 0):>12,}  {overall_huf.get('min', 0):>14,}")
        print(f"  {'Median:':<8} {overall_eur.get('median', 0):>12,}  {overall_huf.get('median', 0):>14,}")
        print(f"  {'Avg:':<8} {overall_eur.get('avg', 0):>12,}  {overall_huf.get('avg', 0):>14,}")
        print(f"  {'Max:':<8} {overall_eur.get('max', 0):>12,}  {overall_huf.get('max', 0):>14,}")

    by_year = result.get("by_year", {})
    if by_year:
        print(f"\n  Price by Year (HUF):")
        print(f"  {'Year':<8} {'Count':>6} {'Min':>14} {'Median':>14} {'Max':>14}")
        print(f"  {'-' * 58}")
        for year, stats in by_year.items():
            label = "N/A" if year == "unknown_year" else year
            print(
                f"  {label:<8} {stats['count']:>6} "
                f"{stats['min']:>14,} {stats['median']:>14,} {stats['max']:>14,}"
            )

    samples = result.get("sample_listings", [])
    if samples:
        print(f"\n  Sample Listings (first {len(samples)}):")
        for s in samples:
            yr = s.get("year", "?")
            price_eur = s.get("price_eur", 0)
            price_huf = s.get("price_huf", 0)
            title = (s.get("title") or "?")[:50]
            print(f"    {yr}  {price_eur:>8,} EUR  ({price_huf:>12,} HUF)  {title}")

    print(f"\n{'=' * 65}\n")


def main():
    parser = argparse.ArgumentParser(
        description="bazos.sk (Slovak market) price scraper with EUR->HUF conversion"
    )
    parser.add_argument(
        "--brand", required=False, default=None,
        help="Brand name (e.g. Volkswagen, Skoda, Toyota)",
    )
    parser.add_argument(
        "--model", required=False, default=None,
        help="Model name (e.g. Golf, Octavia, Corolla)",
    )
    parser.add_argument(
        "--max", type=int, default=None,
        help="Max listings to scrape (default: from config)",
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Output JSON file path",
    )
    parser.add_argument(
        "--no-details", action="store_true",
        help="Skip fetching detail pages (faster, but less year/mileage data)",
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
            bazos_slug = BAZOS_BRAND_SLUGS.get(brand_name, "?")
            models = ", ".join(sorted(info["models"].keys()))
            print(f"  {brand_name} (/{bazos_slug}/): {models}")
        print()
        return

    if not args.brand or not args.model:
        parser.error("--brand and --model are required (unless using --list-brands)")

    result = scrape_brand_model(
        brand_name=args.brand,
        model_name=args.model,
        max_listings=args.max,
        fetch_details=not args.no_details,
        verbose=args.verbose,
    )

    # Print human-readable summary
    print_summary(result)

    # Optionally write JSON
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        log.info("Results written to %s", args.output)


if __name__ == "__main__":
    main()

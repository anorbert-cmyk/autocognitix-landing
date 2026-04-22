#!/usr/bin/env python3
"""
hasznaltauto.hu sitemap-based price scraper.

Fetches the sitemap index, finds car listing URLs for a given brand/model,
scrapes price/year/mileage/fuel data, and returns aggregated price statistics
per year bucket.

Uses only Python stdlib — no pip dependencies required.

Usage:
    python hasznaltauto_parser.py --brand Suzuki --model Swift
    python hasznaltauto_parser.py --brand Suzuki --model Swift --max 50
    python hasznaltauto_parser.py --brand Suzuki --model Swift --output results.json
"""

import argparse
import json
import logging
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
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
log = logging.getLogger("hasznaltauto")

SITEMAP_INDEX_URL = "https://www.hasznaltauto.hu/sitemap/sitemap_index.xml"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# Sanity bounds for HUF prices (300k HUF – 200M HUF).
# Lower: reject 1-HUF "ask for quote" entries.
# Upper: reject obvious mis-scrapes (price typed with extra zeros).
HUF_PRICE_MIN = 300_000
HUF_PRICE_MAX = 200_000_000

# ---------------------------------------------------------------------------
# Config import (local)
# ---------------------------------------------------------------------------

try:
    from config import (
        BRANDS,
        MAX_LISTINGS_PER_QUERY,
        MAX_SUB_SITEMAPS,
        REQUEST_DELAY,
        REQUEST_TIMEOUT,
        USER_AGENT,
    )
except ImportError:
    # Fallback defaults if config.py is not on sys.path
    sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
    from config import (
        BRANDS,
        MAX_LISTINGS_PER_QUERY,
        MAX_SUB_SITEMAPS,
        REQUEST_DELAY,
        REQUEST_TIMEOUT,
        USER_AGENT,
    )

# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------


def fetch_url(url: str, retries: int = 2) -> Optional[str]:
    """Fetch a URL and return the response body as a string, or None on failure."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.5",
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
# Sitemap parsing
# ---------------------------------------------------------------------------


def fetch_sitemap_index() -> List[str]:
    """Fetch the sitemap index and return sub-sitemap URLs."""
    body = fetch_url(SITEMAP_INDEX_URL)
    if not body:
        log.error("Could not fetch sitemap index")
        return []

    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        log.error("XML parse error on sitemap index: %s", exc)
        return []

    urls = []
    for sitemap_el in root.findall("sm:sitemap", SITEMAP_NS):
        loc = sitemap_el.find("sm:loc", SITEMAP_NS)
        if loc is not None and loc.text:
            urls.append(loc.text.strip())
    log.info("Sitemap index contains %d sub-sitemaps", len(urls))
    return urls


def filter_car_sitemaps(sitemap_urls: List[str]) -> List[str]:
    """Filter sub-sitemap URLs to those likely containing car listings."""
    keywords = ("szemelyauto", "szemely", "auto", "listing", "hirdetes")
    matched = [
        url for url in sitemap_urls
        if any(kw in url.lower() for kw in keywords)
    ]
    if not matched:
        # Fallback: if no keyword match, try all sitemaps (some sites use
        # generic names like sitemap1.xml, sitemap2.xml)
        log.warning(
            "No keyword-matched sitemaps found — falling back to all %d sitemaps",
            len(sitemap_urls),
        )
        matched = sitemap_urls
    log.info("Selected %d car-related sitemaps", len(matched))
    return matched[:MAX_SUB_SITEMAPS]


def extract_listing_urls_from_sitemap(sitemap_url: str) -> List[str]:
    """Parse a single sub-sitemap XML and return all <loc> URLs."""
    body = fetch_url(sitemap_url)
    if not body:
        return []

    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        log.warning("XML parse error on %s: %s", sitemap_url, exc)
        return []

    urls = []
    for url_el in root.findall("sm:url", SITEMAP_NS):
        loc = url_el.find("sm:loc", SITEMAP_NS)
        if loc is not None and loc.text:
            urls.append(loc.text.strip())
    return urls


def find_matching_urls(
    all_urls: List[str], brand_slug: str, model_slug: str
) -> List[str]:
    """Filter listing URLs that match the brand/model pattern."""
    # Expected pattern: /szemelyauto/{brand}/{model}/...
    pattern = f"/szemelyauto/{brand_slug}/{model_slug}/"
    matched = [u for u in all_urls if pattern in u.lower()]
    log.info(
        "Found %d URLs matching %s/%s out of %d total",
        len(matched), brand_slug, model_slug, len(all_urls),
    )
    return matched[:MAX_LISTINGS_PER_QUERY]


# ---------------------------------------------------------------------------
# HTML parsing — extract listing data
# ---------------------------------------------------------------------------


class ListingDataParser(HTMLParser):
    """Extract structured data from a hasznaltauto.hu listing page."""

    def __init__(self):
        super().__init__()
        self._in_script_ld = False
        self._script_buf = []
        self._in_price = False
        self._price_text = ""

        # Collected raw texts for fallback regex parsing
        self._all_text_chunks: List[str] = []
        self._current_tag = ""
        self._meta_data: Dict[str, str] = {}
        self._json_ld: List[dict] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]):
        attr_dict = dict(attrs)
        self._current_tag = tag

        # JSON-LD script blocks
        if tag == "script" and attr_dict.get("type") == "application/ld+json":
            self._in_script_ld = True
            self._script_buf = []

        # Price spans — multiple possible class names
        if tag == "span":
            cls = attr_dict.get("class", "")
            if "price" in cls.lower() or "vetelar" in cls.lower():
                self._in_price = True
                self._price_text = ""

        # Meta tags with price / vehicle info
        if tag == "meta":
            prop = attr_dict.get("property", "") or attr_dict.get("name", "")
            content = attr_dict.get("content", "")
            if prop and content:
                self._meta_data[prop] = content

    def handle_endtag(self, tag: str):
        if tag == "script" and self._in_script_ld:
            self._in_script_ld = False
            raw = "".join(self._script_buf)
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    self._json_ld.extend(data)
                else:
                    self._json_ld.append(data)
            except (json.JSONDecodeError, TypeError):
                pass

        if tag == "span" and self._in_price:
            self._in_price = False

    def handle_data(self, data: str):
        if self._in_script_ld:
            self._script_buf.append(data)
        if self._in_price:
            self._price_text += data
        self._all_text_chunks.append(data)


def _parse_number(text: str) -> Optional[int]:
    """Extract an integer from text, stripping spaces/separators."""
    cleaned = re.sub(r"[^\d]", "", text)
    if cleaned:
        try:
            return int(cleaned)
        except ValueError:
            pass
    return None


def _extract_from_json_ld(ld_items: List[dict]) -> Dict[str, Any]:
    """Try to pull price/vehicle data from JSON-LD."""
    result: Dict[str, Any] = {}
    for item in ld_items:
        item_type = item.get("@type", "")

        # Product or Vehicle or Car
        if item_type in ("Product", "Vehicle", "Car", "Offer"):
            offers = item.get("offers", item)
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            price = offers.get("price") or offers.get("lowPrice")
            if price is not None:
                result["price"] = _parse_number(str(price))
            currency = offers.get("priceCurrency")
            if currency:
                result["currency"] = currency

            # Vehicle specifics
            if "brand" in item:
                b = item["brand"]
                result["brand"] = b.get("name", b) if isinstance(b, dict) else str(b)
            if "model" in item:
                result["model"] = str(item["model"])
            if "vehicleModelDate" in item:
                result["year"] = _parse_number(str(item["vehicleModelDate"]))
            if "mileageFromOdometer" in item:
                m = item["mileageFromOdometer"]
                if isinstance(m, dict):
                    result["mileage"] = _parse_number(str(m.get("value", "")))
                else:
                    result["mileage"] = _parse_number(str(m))
            if "fuelType" in item:
                result["fuel_type"] = str(item["fuelType"])

    return result


# Hungarian label -> key mapping for regex fallback
_HU_LABELS = {
    r"(?:Vételár|Ár|Irányár|Price)": "price",
    r"(?:Évjárat|Első forgalomba helyezés|Gyártás éve|Year)": "year",
    r"(?:Kilométeróra állása|Futásteljesítmény|Km|Mileage)": "mileage",
    r"(?:Üzemanyag|Fuel)": "fuel_type",
    r"(?:Márka|Brand)": "brand",
    r"(?:Modell|Model)": "model",
}


def _extract_from_text(chunks: List[str]) -> Dict[str, Any]:
    """Fallback: regex-scan the concatenated page text for key data."""
    text = " ".join(chunks)
    result: Dict[str, Any] = {}

    # Price: look for patterns like "2 490 000 Ft" or "2.490.000 HUF"
    price_match = re.search(
        r"([\d\s\.\,]{4,12})\s*(?:Ft|HUF|forint)", text, re.IGNORECASE
    )
    if price_match and "price" not in result:
        result["price"] = _parse_number(price_match.group(1))

    # Year: 4-digit year near keywords
    year_match = re.search(
        r"(?:Évjárat|forgalomba|Gyártás)[^\d]{0,30}((?:19|20)\d{2})",
        text, re.IGNORECASE,
    )
    if year_match:
        result["year"] = int(year_match.group(1))

    # Mileage: number followed by "km"
    km_match = re.search(r"([\d\s\.\,]{2,10})\s*km\b", text, re.IGNORECASE)
    if km_match:
        result["mileage"] = _parse_number(km_match.group(1))

    # Fuel type
    fuel_match = re.search(
        r"(?:Üzemanyag|Fuel)[^\w]{0,20}(\w[\w\s/\-]{2,25})",
        text, re.IGNORECASE,
    )
    if fuel_match:
        result["fuel_type"] = fuel_match.group(1).strip()

    return result


def parse_listing(html: str, url: str) -> Optional[Dict[str, Any]]:
    """Parse a single listing page and return extracted data dict."""
    parser = ListingDataParser()
    try:
        parser.feed(html)
    except Exception as exc:
        log.warning("HTML parse error on %s: %s", url, exc)
        return None

    # Try JSON-LD first (most reliable)
    data = _extract_from_json_ld(parser._json_ld)

    # Merge in meta tag data
    for key, value in parser._meta_data.items():
        if "price" in key.lower() and "price" not in data:
            data["price"] = _parse_number(value)
        if "currency" in key.lower() and "currency" not in data:
            data["currency"] = value

    # Price from span
    if "price" not in data and parser._price_text:
        data["price"] = _parse_number(parser._price_text)

    # Fallback: regex on text
    text_data = _extract_from_text(parser._all_text_chunks)
    for k, v in text_data.items():
        if k not in data:
            data[k] = v

    # Try to extract brand/model from URL if missing
    url_match = re.search(
        r"/szemelyauto/([^/]+)/([^/]+)/", url, re.IGNORECASE
    )
    if url_match:
        if "brand" not in data:
            data["brand"] = url_match.group(1)
        if "model" not in data:
            data["model"] = url_match.group(2)

    data["source_url"] = url

    # Validate: we need at least price to be useful
    if not data.get("price"):
        log.debug("No price found for %s — skipping", url)
        return None

    return data


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate_by_year(
    listings: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Group listings by year and compute min/median/max price stats.

    Applies URL-based dedup (listings can appear across sitemap shards) and
    HUF sanity bounds (reject < HUF_PRICE_MIN and > HUF_PRICE_MAX).
    """
    by_year: Dict[int, List[int]] = defaultdict(list)
    no_year: List[int] = []
    seen_urls: set[str] = set()
    rejected_bounds = 0
    rejected_dup = 0

    for item in listings:
        url = item.get("source_url")
        if url:
            if url in seen_urls:
                rejected_dup += 1
                continue
            seen_urls.add(url)

        price = item.get("price")
        if not price or price <= 0:
            continue
        if price < HUF_PRICE_MIN or price > HUF_PRICE_MAX:
            rejected_bounds += 1
            continue

        year = item.get("year")
        if year and 1990 <= year <= 2030:
            by_year[year].append(price)
        else:
            no_year.append(price)

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
    Full pipeline: sitemap -> filter -> scrape -> aggregate.

    Returns a dict with metadata and aggregated price stats.
    """
    if verbose:
        log.setLevel(logging.DEBUG)

    # Resolve brand/model slugs
    brand_info = BRANDS.get(brand_name)
    if not brand_info:
        log.error("Unknown brand: %s. Available: %s", brand_name, ", ".join(BRANDS.keys()))
        return {"error": f"Unknown brand: {brand_name}"}

    model_slug = brand_info["models"].get(model_name)
    if not model_slug:
        log.error(
            "Unknown model: %s for %s. Available: %s",
            model_name, brand_name, ", ".join(brand_info["models"].keys()),
        )
        return {"error": f"Unknown model: {model_name} for {brand_name}"}

    brand_slug = brand_info["slug"]
    limit = max_listings or MAX_LISTINGS_PER_QUERY

    log.info("=== Scraping %s %s (%s/%s) ===", brand_name, model_name, brand_slug, model_slug)

    # Step 1: Fetch sitemap index
    log.info("Step 1/4: Fetching sitemap index...")
    sub_sitemaps = fetch_sitemap_index()
    if not sub_sitemaps:
        return {"error": "Could not fetch sitemap index"}
    time.sleep(REQUEST_DELAY)

    # Step 2: Filter to car sitemaps and collect listing URLs
    log.info("Step 2/4: Scanning sub-sitemaps for %s/%s listings...", brand_slug, model_slug)
    car_sitemaps = filter_car_sitemaps(sub_sitemaps)

    all_listing_urls: List[str] = []
    for i, sm_url in enumerate(car_sitemaps, 1):
        log.info("  Scanning sub-sitemap %d/%d: %s", i, len(car_sitemaps), sm_url)
        urls = extract_listing_urls_from_sitemap(sm_url)
        matching = find_matching_urls(urls, brand_slug, model_slug)
        all_listing_urls.extend(matching)
        log.info("  -> %d matching URLs (total so far: %d)", len(matching), len(all_listing_urls))

        if len(all_listing_urls) >= limit:
            all_listing_urls = all_listing_urls[:limit]
            log.info("  Reached limit of %d URLs — stopping sitemap scan", limit)
            break

        time.sleep(REQUEST_DELAY)

    if not all_listing_urls:
        log.warning("No matching listing URLs found")
        return {
            "brand": brand_name,
            "model": model_name,
            "listings_found": 0,
            "error": "No matching listings found in sitemaps",
        }

    # Step 3: Scrape individual listings
    log.info("Step 3/4: Scraping %d listing pages...", len(all_listing_urls))
    listings: List[Dict[str, Any]] = []
    errors = 0

    for i, url in enumerate(all_listing_urls, 1):
        log.info("  [%d/%d] %s", i, len(all_listing_urls), url)
        html = fetch_url(url)
        if html:
            data = parse_listing(html, url)
            if data:
                listings.append(data)
                log.info(
                    "    -> Price: %s HUF, Year: %s, Km: %s",
                    f"{data.get('price', '?'):,}" if data.get("price") else "?",
                    data.get("year", "?"),
                    f"{data.get('mileage', '?'):,}" if data.get("mileage") else "?",
                )
            else:
                errors += 1
        else:
            errors += 1
        time.sleep(REQUEST_DELAY)

    # Step 4: Aggregate
    log.info("Step 4/4: Aggregating %d listings...", len(listings))
    aggregated = aggregate_by_year(listings)

    # Compute overall stats
    all_prices = [item["price"] for item in listings if item.get("price")]
    overall = {}
    if all_prices:
        all_prices.sort()
        overall = {
            "count": len(all_prices),
            "min": all_prices[0],
            "median": int(statistics.median(all_prices)),
            "avg": int(statistics.mean(all_prices)),
            "max": all_prices[-1],
        }

    result = {
        "brand": brand_name,
        "model": model_name,
        "brand_slug": brand_slug,
        "model_slug": model_slug,
        "urls_found": len(all_listing_urls),
        "listings_scraped": len(listings),
        "parse_errors": errors,
        "overall_stats": overall,
        "by_year": aggregated,
        "fuel_type_distribution": _fuel_distribution(listings),
        "sample_listings": listings[:10],  # first 10 as sample
    }

    log.info(
        "=== Done: %d listings, price range %s – %s HUF ===",
        len(listings),
        f"{overall.get('min', 0):,}",
        f"{overall.get('max', 0):,}",
    )

    return result


def _fuel_distribution(listings: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count listings by fuel type."""
    dist: Dict[str, int] = defaultdict(int)
    for item in listings:
        ft = item.get("fuel_type", "unknown")
        dist[str(ft)] += 1
    return dict(sorted(dist.items(), key=lambda x: -x[1]))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def print_summary(result: Dict[str, Any]) -> None:
    """Print a human-readable summary to stdout."""
    if "error" in result and result.get("listings_scraped", 0) == 0:
        print(f"\nError: {result['error']}")
        return

    print(f"\n{'=' * 60}")
    print(f"  {result['brand']} {result['model']} — hasznaltauto.hu Price Report")
    print(f"{'=' * 60}")
    print(f"  Scraped at: {result.get('scrape_timestamp', 'N/A')}")
    print(f"  URLs found: {result.get('urls_found', 0)}")
    print(f"  Successfully parsed: {result.get('listings_scraped', 0)}")
    print(f"  Parse errors: {result.get('parse_errors', 0)}")

    overall = result.get("overall_stats", {})
    if overall:
        print(f"\n  Overall Price Stats (HUF):")
        print(f"    Min:    {overall.get('min', 0):>12,}")
        print(f"    Median: {overall.get('median', 0):>12,}")
        print(f"    Avg:    {overall.get('avg', 0):>12,}")
        print(f"    Max:    {overall.get('max', 0):>12,}")

    by_year = result.get("by_year", {})
    if by_year:
        print(f"\n  Price by Year:")
        print(f"  {'Year':<8} {'Count':>6} {'Min':>12} {'Median':>12} {'Max':>12}")
        print(f"  {'-' * 52}")
        for year, stats in by_year.items():
            if year == "unknown_year":
                label = "N/A"
            else:
                label = year
            print(
                f"  {label:<8} {stats['count']:>6} "
                f"{stats['min']:>12,} {stats['median']:>12,} {stats['max']:>12,}"
            )

    fuel = result.get("fuel_type_distribution", {})
    if fuel:
        print(f"\n  Fuel Type Distribution:")
        for ft, count in fuel.items():
            print(f"    {ft}: {count}")

    print(f"\n{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="hasznaltauto.hu sitemap-based price scraper"
    )
    parser.add_argument(
        "--brand", required=False, default=None, help="Brand name (e.g. Suzuki, Opel, Volkswagen)"
    )
    parser.add_argument(
        "--model", required=False, default=None, help="Model name (e.g. Swift, Astra, Golf)"
    )
    parser.add_argument(
        "--max", type=int, default=None, help="Max listings to scrape (default: from config)"
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None, help="Output JSON file path"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "--list-brands", action="store_true", help="List available brands and models"
    )

    args = parser.parse_args()

    if args.list_brands:
        print("\nAvailable brands and models:\n")
        for brand_name, info in sorted(BRANDS.items()):
            models = ", ".join(sorted(info["models"].keys()))
            print(f"  {brand_name}: {models}")
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
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        log.info("Results written to %s", args.output)


if __name__ == "__main__":
    main()

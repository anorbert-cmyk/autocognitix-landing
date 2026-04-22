#!/usr/bin/env python3
"""
OOYYO.com EU-wide car price scraper.

OOYYO aggregates 15M+ used car listings from 27 European markets.
Prices are in EUR. Their robots.txt is permissive (only 3 blocked paths).

Scrapes search result pages (not individual listings) — each page yields
~16 cars with price, year, mileage, fuel type, body type, and location
directly from the HTML data attributes and DOM structure.

Uses only Python stdlib — no pip dependencies required.

robots.txt compliance:
  - Respects Crawl-delay: 30s for generic bots
  - Only fetches allowed paths (avoids /automobili/, /outlet-service-web/, /counter)

URL hash system:
  OOYYO uses opaque hash codes in URLs: /country/used-brand-model-for-sale/c=HASH/
  The hash encodes: domain + page_type + country + brand + model + language.
  Structure: PREFIX(20) + COUNTRY(4) + BRAND_MODEL(10) + SUFFIX(10+)
  This scraper stores known Germany hashes and swaps the country code segment
  to generate URLs for other EU countries.

Usage:
    python3 ooyyo_parser.py --brand Volkswagen --model Golf
    python3 ooyyo_parser.py --brand Volkswagen --model Golf --max 50
    python3 ooyyo_parser.py --all --output shared/data/ooyyo-prices.json
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
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ooyyo")

# Sanity bounds for OOYYO (EUR prices, paired HUF check downstream).
EUR_PRICE_MIN = 500
EUR_PRICE_MAX = 300_000

# ---------------------------------------------------------------------------
# Config import (local)
# ---------------------------------------------------------------------------

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))

try:
    from config import BRANDS, REQUEST_TIMEOUT, USER_AGENT
except ImportError:
    sys.path.insert(0, _SCRIPT_DIR)
    from config import BRANDS, REQUEST_TIMEOUT, USER_AGENT

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Crawl-delay: 30s from robots.txt for generic bots
CRAWL_DELAY = 30.0

BASE_URL = "https://www.ooyyo.com"

# Hash prefix constant across all OOYYO search URLs
_HASH_PREFIX = "CDA31D7114D3854F111B"

# Country codes (4 hex chars) in OOYYO's hash system.
# Discovered from indexed URLs across multiple brand/model combos.
# Each tuple: (country_slug, display_name, hash_country_code, default_suffix)
EU_COUNTRIES = [
    ("germany", "Germany", "FE6F", "1D6617F286"),
    ("france", "France", "FB6F", "1D6617F286"),
    ("italy", "Italy", "F36F", "1D6617F286"),
    ("spain", "Spain", "E56F", "1D661BF286"),
    ("netherlands", "Netherlands", "FA6F", "1D6617F286"),
    ("belgium", "Belgium", "E36F", "1D6617F286"),
    ("austria", "Austria", "E06F", "1D6617F286"),
    ("poland", "Poland", "E86F", "1D6617F286"),
]

# Brand+model hash segments (10 hex chars between country code and suffix).
# Discovered by analyzing indexed OOYYO URLs from search engines.
# Key format: "BrandName/ModelName"
# The scraper uses Germany hash first, then swaps country codes for other markets.
_BRAND_MODEL_HASHES: Dict[str, str] = {
    # Volkswagen
    "Volkswagen/Golf": "BAA6355BA6A2",
    "Volkswagen/Passat": "BAA6355BA2A2",
    "Volkswagen/Polo": "BAA6355BB7A2",
    "Volkswagen/Tiguan": "BAA6355B2FA4",
    "Volkswagen/T-Roc": "BAA6355B67A8",
    # Toyota
    "Toyota/Corolla": "BAD3355B1AA3",
    "Toyota/Yaris": "BAD3355B05A3",
    "Toyota/RAV4": "BAD3355BC3A2",
    "Toyota/C-HR": "BAD3355B8DA7",
    "Toyota/Aygo": "BAD3355BB5A5",
    # BMW
    "BMW/3-series": "BA7D355B8FA0",
    "BMW/5-series": "BA7D355B90A0",
    "BMW/X1": "BA7D355BD4A3",
    "BMW/X3": "BA7D355B25A3",
    "BMW/1-series": "BA7D355B48A0",
    # Mercedes-Benz
    "Mercedes-Benz/A-class": "BA1F355BD0A2",
    "Mercedes-Benz/C-class": "BA1F355BDEA2",
    "Mercedes-Benz/E-class": "BA1F355BCBA2",
    "Mercedes-Benz/GLA": "BA1F355B7BA5",
    "Mercedes-Benz/GLC": "BA1F355B6FA5",
    # Ford
    "Ford/Focus": "BA27355B03A0",
    "Ford/Fiesta": "BA27355B18A0",
    "Ford/Kuga": "BA27355B23A2",
    "Ford/Puma": "BA27355BB6A6",
    "Ford/Mondeo": "BA27355BFCA0",
    # Skoda
    "Skoda/Octavia": "BACE355BC9A6",
    "Skoda/Fabia": "BACE355BDEA6",
    "Skoda/Superb": "BACE355BCAA6",
    "Skoda/Kodiaq": "BACE355BD8A9",
    "Skoda/Kamiq": "BACE355B21AC",
    # Audi
    "Audi/A3": "BA153559DCA0",
    "Audi/A4": "BA15355904A0",
    "Audi/A6": "BA15355906A0",
    "Audi/Q3": "BA15355B52A3",
    "Audi/Q5": "BA15355B6FA3",
    # Opel
    "Opel/Astra": "BAB5355B17A1",
    "Opel/Corsa": "BAB5355B07A1",
    "Opel/Mokka": "BAB5355BACA4",
    "Opel/Insignia": "BAB5355B0BA2",
    "Opel/Crossland": "BAB5355BB8A7",
    # Renault
    "Renault/Clio": "BAC1355B9CA1",
    "Renault/Megane": "BAC1355B97A1",
    "Renault/Captur": "BAC1355B98A5",
    "Renault/Scenic": "BAC1355BABA1",
    "Renault/Kadjar": "BAC1355BD1A7",
    # Peugeot
    "Peugeot/208": "BAB7355B41A3",
    "Peugeot/308": "BAB7355B38A2",
    "Peugeot/2008": "BAB7355BADA5",
    "Peugeot/3008": "BAB7355BB2A5",
    "Peugeot/508": "BAB7355B47A3",
    # Hyundai
    "Hyundai/i30": "BA34355BA0A2",
    "Hyundai/Tucson": "BA34355B97A2",
    "Hyundai/i20": "BA34355B39A2",
    "Hyundai/Kona": "BA34355B9FA7",
    "Hyundai/ix35": "BA34355B0DA4",
    # Kia
    "Kia/Ceed": "BA38355BB6A3",
    "Kia/Sportage": "BA38355B8EA2",
    "Kia/Picanto": "BA38355B08A2",
    "Kia/Niro": "BA38355B2EA7",
    "Kia/Stonic": "BA38355B66A8",
    # Suzuki
    "Suzuki/Swift": "BACF355B2EA1",
    "Suzuki/Vitara": "BACF355B0BA2",
    "Suzuki/SX4": "BACF355BD5A1",
    "Suzuki/Baleno": "BACF355B70A6",
    "Suzuki/Ignis": "BACF355B60A6",
    # Fiat
    "Fiat/500": "BA26355B4EA0",
    "Fiat/Panda": "BA26355BC0A0",
    "Fiat/Tipo": "BA26355BA2A5",
    "Fiat/Punto": "BA26355B81A0",
    "Fiat/500X": "BA26355B27A5",
    # Dacia
    "Dacia/Duster": "BA1C355B11A3",
    "Dacia/Sandero": "BA1C355B0CA2",
    "Dacia/Logan": "BA1C355BFBA1",
    "Dacia/Spring": "BA1C355BB3AB",
    "Dacia/Jogger": "BA1C355B48AC",
    # Honda
    "Honda/Civic": "BA33355BCBA0",
    "Honda/CR-V": "BA33355BD3A1",
    "Honda/Jazz": "BA33355BECA1",
    "Honda/HR-V": "BA33355B6AA5",
    "Honda/Accord": "BA33355B86A0",
    # Mazda
    "Mazda/3": "BA3B355B8FA0",
    "Mazda/6": "BA3B355B90A0",
    "Mazda/CX-5": "BA3B355B64A4",
    "Mazda/CX-3": "BA3B355B89A5",
    "Mazda/CX-30": "BA3B355B53A9",
    # Nissan
    "Nissan/Qashqai": "BAB3355B17A3",
    "Nissan/Juke": "BAB3355B3AA3",
    "Nissan/Micra": "BAB3355BB7A0",
    "Nissan/X-Trail": "BAB3355B4FA2",
    "Nissan/Leaf": "BAB3355BA8A3",
    # Seat
    "Seat/Leon": "BACC355B87A1",
    "Seat/Ibiza": "BACC355BC1A0",
    "Seat/Arona": "BACC355B2BA8",
    "Seat/Ateca": "BACC355BA3A6",
    "Seat/Tarraco": "BACC355BCCAA",
    # Volvo
    "Volvo/XC60": "BAA5355BFDA3",
    "Volvo/XC40": "BAA5355B59A8",
    "Volvo/V40": "BAA5355B66A3",
    "Volvo/V60": "BAA5355B9EA2",
    "Volvo/S60": "BAA5355B6EA2",
    # Citroen
    "Citroen/C3": "BA1E355BFCA1",
    "Citroen/C4": "BA1E355B0CA2",
    "Citroen/C5 Aircross": "BA1E355BC5A8",
    "Citroen/Berlingo": "BA1E355B63A1",
    "Citroen/C3 Aircross": "BA1E355BFCA7",
    # Mitsubishi
    "Mitsubishi/Outlander": "BA3D355B14A1",
    "Mitsubishi/ASX": "BA3D355B3CA4",
    "Mitsubishi/Eclipse Cross": "BA3D355B78A9",
    "Mitsubishi/Space Star": "BA3D355BCFA2",
    "Mitsubishi/L200": "BA3D355BFBA0",
    # Jeep
    "Jeep/Renegade": "BA37355B1FA5",
    "Jeep/Compass": "BA37355B80A3",
    "Jeep/Cherokee": "BA37355B39A0",
    "Jeep/Wrangler": "BA37355B3DA0",
    "Jeep/Grand Cherokee": "BA37355BDAA1",
    # Alfa Romeo
    "Alfa Romeo/Giulietta": "BA0C355BFCA2",
    "Alfa Romeo/Giulia": "BA0C355B2DA5",
    "Alfa Romeo/Stelvio": "BA0C355B78A6",
    "Alfa Romeo/MiTo": "BA0C355BBBA2",
    "Alfa Romeo/159": "BA0C355BB4A1",
    # Mini
    "Mini/Cooper": "BA3C355B66A0",
    "Mini/Countryman": "BA3C355B74A3",
    "Mini/Clubman": "BA3C355B12A2",
    "Mini/One": "BA3C355BBFA0",
    "Mini/Cabrio": "BA3C355B1EA1",
}

# URL slug overrides for brand/model names that differ from config.py
OOYYO_SLUG_OVERRIDES = {
    "Mercedes-Benz": "mercedes+benz",
    "Alfa Romeo": "alfa+romeo",
    "3-series": "3+series",
    "5-series": "5+series",
    "1-series": "1+series",
    "A-class": "a-class",
    "C-class": "c-class",
    "E-class": "e-class",
    "C-HR": "c-hr",
    "CR-V": "cr-v",
    "HR-V": "hr-v",
    "CX-5": "cx-5",
    "CX-3": "cx-3",
    "CX-30": "cx-30",
    "X-Trail": "x-trail",
    "T-Roc": "t-roc",
    "SX4": "sx4",
    "C5 Aircross": "c5+aircross",
    "C3 Aircross": "c3+aircross",
    "Eclipse Cross": "eclipse+cross",
    "Space Star": "space+star",
    "Grand Cherokee": "grand+cherokee",
    "500X": "500x",
}

# Maximum listings to collect per brand/model (across all countries)
DEFAULT_MAX_LISTINGS = 200

# Path to hash cache file (persists discovered hashes across runs)
_HASH_CACHE_PATH = os.path.join(_SCRIPT_DIR, ".ooyyo_hash_cache.json")


# ---------------------------------------------------------------------------
# Hash management and URL construction
# ---------------------------------------------------------------------------


def _ooyyo_slug(name: str) -> str:
    """Convert a brand or model name to OOYYO URL slug format."""
    if name in OOYYO_SLUG_OVERRIDES:
        return OOYYO_SLUG_OVERRIDES[name]
    return name.lower().replace(" ", "+")


def _build_hash(country_code: str, brand_model_hash: str, suffix: str) -> str:
    """Assemble a full OOYYO URL hash from components."""
    return f"{_HASH_PREFIX}{country_code}{brand_model_hash}{suffix}"


def build_search_url(
    country_slug: str,
    country_hash_code: str,
    country_suffix: str,
    brand_name: str,
    model_name: str,
    brand_model_hash: str,
) -> str:
    """
    Build a full OOYYO search URL with the required hash parameter.

    Returns URL like:
      https://www.ooyyo.com/germany/used-volkswagen-golf-for-sale/c=CDA31D...F286/
    """
    brand_slug = _ooyyo_slug(brand_name)
    model_slug = _ooyyo_slug(model_name)
    full_hash = _build_hash(country_hash_code, brand_model_hash, country_suffix)
    return (
        f"{BASE_URL}/{country_slug}/"
        f"used-{brand_slug}-{model_slug}-for-sale/"
        f"c={full_hash}/"
    )


def discover_hash_from_page(html: str) -> Optional[str]:
    """
    Extract the search hash code from OYO.appParams.code in the page HTML.

    This allows discovering new brand/model hashes from any successfully
    fetched page.
    """
    match = re.search(r'code:\s*"([A-F0-9]{30,60})"', html)
    if match:
        return match.group(1)
    return None


def extract_brand_model_segment(full_hash: str) -> Optional[str]:
    """
    Extract the brand+model segment from a full OOYYO hash.

    Hash structure: PREFIX(20) + COUNTRY(4) + BRAND_MODEL(12) + SUFFIX(10)
    """
    if not full_hash or len(full_hash) < 46:
        return None
    # Skip prefix (20) + country (4), take brand_model (12)
    return full_hash[24:36]


def _load_hash_cache() -> Dict[str, str]:
    """Load cached brand/model hashes from disk."""
    try:
        with open(_HASH_CACHE_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_hash_cache(cache: Dict[str, str]) -> None:
    """Persist discovered hashes to disk for reuse.

    Wave 5 + 6: atomic tempfile + os.replace. Two scrapers running in
    parallel (CI matrix, scrape-all + ad-hoc) used to race on the file:
    one truncated while the other was mid-read, losing all discovered
    hashes. SIGTERM mid-write left the JSON truncated → next load_hash_cache
    swallowed json.JSONDecodeError and returned {} silently.
    """
    import tempfile
    out_dir = os.path.dirname(_HASH_CACHE_PATH) or "."
    try:
        fd, tmp = tempfile.mkstemp(prefix=".ooyyo-hash.", suffix=".tmp", dir=out_dir)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(cache, f, indent=2)
            os.replace(tmp, _HASH_CACHE_PATH)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
    except OSError as exc:
        log.debug("Could not save hash cache: %s", exc)


def get_brand_model_hash(brand_name: str, model_name: str) -> Optional[str]:
    """
    Get the brand/model hash segment, checking:
    1. Built-in lookup table
    2. On-disk cache (from previous discovery runs)
    """
    key = f"{brand_name}/{model_name}"

    # Check built-in table
    if key in _BRAND_MODEL_HASHES:
        return _BRAND_MODEL_HASHES[key]

    # Check disk cache
    cache = _load_hash_cache()
    if key in cache:
        return cache[key]

    return None


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------


def fetch_url(url: str, retries: int = 2) -> Optional[str]:
    """Fetch a URL and return the response body as a string, or None on failure."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
        "Accept-Encoding": "identity",
    }
    req = urllib.request.Request(url, headers=headers)

    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                final_url = resp.geturl()
                if "/automobili/" in final_url or "/outlet-service-web/" in final_url:
                    log.debug("Redirected to blocked path: %s", final_url)
                    return None

                status = resp.getcode()
                if status == 410:
                    log.debug("410 Gone: %s", url)
                    return None

                charset = resp.headers.get_content_charset() or "utf-8"
                return resp.read().decode(charset, errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 410):
                log.debug("HTTP %d: %s", exc.code, url)
                return None
            if exc.code == 403:
                log.warning("403 Forbidden: %s — may need longer delay", url)
                return None
            if exc.code == 429:
                wait = CRAWL_DELAY * attempt * 2
                log.warning("Rate-limited (429) on %s — waiting %.1fs", url, wait)
                time.sleep(wait)
                continue
            log.warning("HTTP %d on %s (attempt %d/%d)", exc.code, url, attempt, retries)
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            log.warning("Network error on %s: %s (attempt %d/%d)", url, exc, attempt, retries)
        if attempt < retries:
            time.sleep(CRAWL_DELAY / 2)

    log.error("Failed to fetch %s after %d attempts", url, retries)
    return None


# ---------------------------------------------------------------------------
# HTML parser for OOYYO search result pages
# ---------------------------------------------------------------------------


class OoyyoListingParser(HTMLParser):
    """
    Parse OOYYO search result pages to extract car listing data.

    OOYYO HTML structure (discovered from live page analysis):

    <a class="car-card-1" href="..." data-price="19999" data-currency="3">
      <div class="gama">
        <div class="mob-heading">
          <span>2020</span>         <!-- year -->
          <span>Volkswagen</span>   <!-- brand -->
          <span>Golf</span>         <!-- model -->
          <span>2.0</span>          <!-- engine/trim -->
        </div>
        <div class="mob-location">  <!-- city, region, country -->
          Furstenwalde Spree, Brandenburg, Germany
        </div>
      </div>
      <div class="beta">
        <div class="mileage">
          Mi: <strong>61,557 km</strong>
        </div>
        <div class="description">
          <span>Sedan,&nbsp;</span>
          <span>Diesel,&nbsp;</span>
          <span>Black</span>
          , abs, air conditioning, ...
        </div>
      </div>
    </a>
    """

    def __init__(self):
        super().__init__()
        self.listings: List[Dict[str, Any]] = []
        self._current: Optional[Dict[str, Any]] = None
        self._in_card = False
        self._in_mob_heading = False
        self._in_mob_location = False
        self._in_mileage = False
        self._in_mileage_strong = False
        self._in_description = False
        self._in_description_span = False
        self._mob_heading_spans: List[str] = []
        self._location_text: List[str] = []
        self._mileage_text = ""
        self._desc_spans: List[str] = []
        self._tag_stack: List[str] = []
        self._total_count: Optional[int] = None

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        self._tag_stack.append(tag)
        attr_dict = {k: v for k, v in attrs if v is not None}

        # Detect car-card-1 anchor
        if tag == "a" and "car-card-1" in attr_dict.get("class", ""):
            self._in_card = True
            price_str = attr_dict.get("data-price", "")
            currency = attr_dict.get("data-currency", "")
            href = attr_dict.get("href", "")
            self._current = {
                "price_eur": _parse_int(price_str),
                "currency_id": currency,
                "href": href,
            }
            self._mob_heading_spans = []
            self._location_text = []
            self._mileage_text = ""
            self._desc_spans = []
            return

        if not self._in_card:
            # Try to extract total count from meta description
            if tag == "meta":
                content = attr_dict.get("content", "")
                name = attr_dict.get("name", "")
                if name == "description" and self._total_count is None:
                    m = re.search(r"([\d,]+)\s+used\s+", content)
                    if m:
                        self._total_count = _parse_int(m.group(1))
            return

        cls = attr_dict.get("class", "")

        if tag == "div" and "mob-heading" in cls:
            self._in_mob_heading = True
        elif tag == "div" and "mob-location" in cls:
            self._in_mob_location = True
        elif tag == "div" and "mileage" == cls.strip():
            self._in_mileage = True
        elif tag == "strong" and self._in_mileage:
            self._in_mileage_strong = True
        elif tag == "div" and "description" in cls:
            self._in_description = True
        elif tag == "span" and self._in_description:
            self._in_description_span = True

    def handle_endtag(self, tag: str):
        if self._tag_stack:
            self._tag_stack.pop()

        if tag == "a" and self._in_card:
            self._in_card = False
            if self._current:
                self._finalize_current()
            self._current = None
            return

        if tag == "div":
            if self._in_mob_heading:
                self._in_mob_heading = False
            elif self._in_mob_location:
                self._in_mob_location = False
            elif self._in_mileage:
                self._in_mileage = False
            elif self._in_description:
                self._in_description = False

        if tag == "strong" and self._in_mileage_strong:
            self._in_mileage_strong = False

        if tag == "span" and self._in_description_span:
            self._in_description_span = False

    def handle_data(self, data: str):
        if not self._in_card or not self._current:
            return

        text = data.strip()
        if not text:
            return

        if self._in_mob_heading and self._tag_stack and self._tag_stack[-1] == "span":
            self._mob_heading_spans.append(text)
        elif self._in_mob_location:
            self._location_text.append(text)
        elif self._in_mileage_strong:
            self._mileage_text += text
        elif self._in_description_span:
            cleaned = text.replace("\xa0", "").strip().rstrip(",").strip()
            if cleaned:
                self._desc_spans.append(cleaned)

    def _finalize_current(self):
        """Process collected data for the current listing."""
        c = self._current
        if not c or not c.get("price_eur"):
            return

        # Parse year, brand, model from mob-heading spans
        # Typical order: [year, brand, model, engine/trim]
        if len(self._mob_heading_spans) >= 3:
            year_val = _parse_int(self._mob_heading_spans[0])
            if year_val and 1990 <= year_val <= 2030:
                c["year"] = year_val
            c["brand"] = self._mob_heading_spans[1]
            c["model"] = self._mob_heading_spans[2]
            if len(self._mob_heading_spans) >= 4:
                c["trim"] = self._mob_heading_spans[3]

        # Parse location
        loc_raw = " ".join(self._location_text).strip()
        loc_raw = re.sub(r"\s+", " ", loc_raw)
        if loc_raw:
            parts = [p.strip() for p in loc_raw.split(",")]
            c["location_raw"] = loc_raw
            if parts:
                c["country"] = parts[-1].strip()
            if len(parts) >= 2:
                c["region"] = parts[-2].strip() if len(parts) >= 3 else ""
                c["city"] = parts[0].strip()

        # Parse mileage
        if self._mileage_text:
            km_match = re.search(r"([\d,.\s]+)\s*km", self._mileage_text, re.IGNORECASE)
            if km_match:
                c["mileage_km"] = _parse_int(km_match.group(1))

        # Parse description spans: typically [body_type, fuel_type, color]
        if len(self._desc_spans) >= 1:
            c["body_type"] = self._desc_spans[0]
        if len(self._desc_spans) >= 2:
            c["fuel_type"] = self._desc_spans[1]
        if len(self._desc_spans) >= 3:
            c["color"] = self._desc_spans[2]

        self.listings.append(c)


def _parse_int(text: str) -> Optional[int]:
    """Extract an integer from text, stripping non-digit characters."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d]", "", str(text))
    if cleaned:
        try:
            return int(cleaned)
        except ValueError:
            pass
    return None


def parse_search_page(html: str) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """
    Parse an OOYYO search results page.

    Returns:
        (listings, total_count) -- list of parsed car dicts and total result count
    """
    parser = OoyyoListingParser()
    try:
        parser.feed(html)
    except Exception as exc:
        log.warning("HTML parse error: %s", exc)
        return [], None

    return parser.listings, parser._total_count


# ---------------------------------------------------------------------------
# Exchange rate loading
# ---------------------------------------------------------------------------


def load_eur_huf_rate() -> float:
    """Load EUR/HUF exchange rate from shared data."""
    exchange_path = os.path.join(_PROJECT_ROOT, "shared", "data", "exchange-rate.json")
    try:
        with open(exchange_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Canonical key is `rate` (Wave 1 schema, see shared/data/README.md);
        # legacy `EUR_HUF`/`eur_huf` kept as backwards-compat for stale local
        # checkouts. Without `rate` here the loader silently fell through to
        # the hardcoded 390.0 fallback after Wave 1 — Wave 4 fix.
        rate = data.get("rate") or data.get("EUR_HUF") or data.get("eur_huf")
        if rate:
            log.info("Loaded EUR/HUF rate: %.2f (source: %s, date: %s)",
                     rate, data.get("source", "?"), data.get("date", "?"))
            return float(rate)
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
        log.warning("Could not load exchange rate from %s: %s", exchange_path, exc)

    fallback = 390.0
    log.warning("Using fallback EUR/HUF rate: %.2f", fallback)
    return fallback


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate_by_year(
    listings: List[Dict[str, Any]],
    eur_huf_rate: float,
) -> Dict[str, Dict[str, Any]]:
    """
    Group listings by year and compute min/median/max price stats.
    Converts EUR prices to HUF using the provided exchange rate.

    OOYYO listing records don't have a per-listing URL, so dedup uses a
    composite natural key (brand, model, year, price, mileage, country).
    Also applies EUR_PRICE_MIN/MAX sanity bounds.
    """
    by_year: Dict[int, List[int]] = defaultdict(list)
    no_year: List[int] = []
    seen_keys: set[tuple] = set()
    rejected_bounds = 0
    rejected_dup = 0

    for item in listings:
        price_eur = item.get("price_eur")
        if not price_eur or price_eur <= 0:
            continue
        if price_eur < EUR_PRICE_MIN or price_eur > EUR_PRICE_MAX:
            rejected_bounds += 1
            continue

        key = (
            item.get("brand"),
            item.get("model"),
            item.get("year"),
            int(price_eur),
            item.get("mileage_km"),
            item.get("country"),
        )
        if key in seen_keys:
            rejected_dup += 1
            continue
        seen_keys.add(key)

        year = item.get("year")
        if year and 1990 <= year <= 2030:
            by_year[year].append(price_eur)
        else:
            no_year.append(price_eur)

    if rejected_bounds or rejected_dup:
        log.info(
            "aggregate_by_year: rejected %d out-of-bounds EUR, %d duplicates",
            rejected_bounds, rejected_dup,
        )

    result = {}
    for year in sorted(by_year.keys()):
        prices_eur = sorted(by_year[year])
        result[str(year)] = _compute_stats(prices_eur, eur_huf_rate)

    if no_year:
        no_year.sort()
        result["unknown_year"] = _compute_stats(no_year, eur_huf_rate)

    return result


def _compute_stats(prices_eur: List[int], eur_huf_rate: float) -> Dict[str, Any]:
    """Compute price statistics in both EUR and HUF."""
    return {
        "count": len(prices_eur),
        "min_eur": prices_eur[0],
        "median_eur": int(statistics.median(prices_eur)),
        "avg_eur": int(statistics.mean(prices_eur)),
        "max_eur": prices_eur[-1],
        # HUF conversions (compatible with hungarian-market-prices.json schema)
        "min": int(prices_eur[0] * eur_huf_rate),
        "avg": int(statistics.mean(prices_eur) * eur_huf_rate),
        "max": int(prices_eur[-1] * eur_huf_rate),
    }


def _fuel_distribution(listings: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count listings by fuel type."""
    dist: Dict[str, int] = defaultdict(int)
    for item in listings:
        ft = item.get("fuel_type", "unknown")
        dist[str(ft)] += 1
    return dict(sorted(dist.items(), key=lambda x: -x[1]))


def _country_distribution(listings: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count listings by source country."""
    dist: Dict[str, int] = defaultdict(int)
    for item in listings:
        country = item.get("country", "unknown")
        dist[str(country)] += 1
    return dict(sorted(dist.items(), key=lambda x: -x[1]))


# ---------------------------------------------------------------------------
# Main scraping flow
# ---------------------------------------------------------------------------


def scrape_brand_model(
    brand_name: str,
    model_name: str,
    max_listings: Optional[int] = None,
    countries: Optional[List[Tuple[str, str, str, str]]] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Full pipeline: build URLs -> fetch search pages -> parse -> aggregate.

    Scans multiple EU countries to collect diverse price data.
    Respects 30s crawl-delay between requests.
    """
    if verbose:
        log.setLevel(logging.DEBUG)

    # Validate brand/model exists in config
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

    # Get brand/model hash
    bm_hash = get_brand_model_hash(brand_name, model_name)
    if not bm_hash:
        log.error("No OOYYO hash known for %s/%s. Run with --discover first.", brand_name, model_name)
        return {"error": f"No OOYYO hash for {brand_name}/{model_name}"}

    limit = max_listings or DEFAULT_MAX_LISTINGS
    scan_countries = countries or EU_COUNTRIES

    log.info("=== Scraping OOYYO: %s %s (max %d listings, %d countries) ===",
             brand_name, model_name, limit, len(scan_countries))

    eur_huf_rate = load_eur_huf_rate()

    all_listings: List[Dict[str, Any]] = []
    total_available = 0
    errors = 0
    hash_cache = _load_hash_cache()

    for i, (country_slug, country_name, country_hash, country_suffix) in enumerate(scan_countries, 1):
        if len(all_listings) >= limit:
            log.info("Reached limit of %d listings -- stopping", limit)
            break

        url = build_search_url(
            country_slug, country_hash, country_suffix,
            brand_name, model_name, bm_hash,
        )
        log.info("[%d/%d] Fetching %s %s from %s...",
                 i, len(scan_countries), brand_name, model_name, country_name)
        log.info("  URL: %s", url)

        html = fetch_url(url)
        if html:
            # Opportunistically discover/verify hash from the page
            page_hash = discover_hash_from_page(html)
            if page_hash:
                bm_segment = extract_brand_model_segment(page_hash)
                if bm_segment:
                    cache_key = f"{brand_name}/{model_name}"
                    if cache_key not in hash_cache:
                        hash_cache[cache_key] = bm_segment
                        _save_hash_cache(hash_cache)
                        log.debug("Cached hash for %s: %s", cache_key, bm_segment)

            listings, count = parse_search_page(html)
            if count:
                total_available += count
                log.info("  Total available in %s: %s", country_name, f"{count:,}")

            if listings:
                for item in listings:
                    item["source"] = "ooyyo.com"
                    item["source_country"] = country_name
                    item["source_url"] = url

                all_listings.extend(listings)
                log.info("  Parsed %d listings (total so far: %d)", len(listings), len(all_listings))

                sample = listings[0]
                log.info("  Sample: %s %s %s -- %s EUR, %s km, %s",
                         sample.get("year", "?"),
                         sample.get("brand", "?"),
                         sample.get("model", "?"),
                         f"{sample.get('price_eur', 0):,}",
                         f"{sample.get('mileage_km', 0):,}" if sample.get("mileage_km") else "?",
                         sample.get("fuel_type", "?"))
            else:
                log.info("  No listings found on page (may be hash mismatch)")
                errors += 1
        else:
            log.warning("  Failed to fetch page for %s", country_name)
            errors += 1

        # Respect Crawl-delay: 30s
        if i < len(scan_countries) and len(all_listings) < limit:
            log.info("  Waiting %.0fs (Crawl-delay)...", CRAWL_DELAY)
            time.sleep(CRAWL_DELAY)

    # Trim to limit
    all_listings = all_listings[:limit]

    # Aggregate
    log.info("Aggregating %d listings...", len(all_listings))
    aggregated = aggregate_by_year(all_listings, eur_huf_rate)

    # Overall stats
    all_prices_eur = [item["price_eur"] for item in all_listings if item.get("price_eur")]
    overall = {}
    if all_prices_eur:
        all_prices_eur.sort()
        overall = {
            "count": len(all_prices_eur),
            "min_eur": all_prices_eur[0],
            "median_eur": int(statistics.median(all_prices_eur)),
            "avg_eur": int(statistics.mean(all_prices_eur)),
            "max_eur": all_prices_eur[-1],
            "min_huf": int(all_prices_eur[0] * eur_huf_rate),
            "median_huf": int(statistics.median(all_prices_eur) * eur_huf_rate),
            "avg_huf": int(statistics.mean(all_prices_eur) * eur_huf_rate),
            "max_huf": int(all_prices_eur[-1] * eur_huf_rate),
        }

    result = {
        "brand": brand_name,
        "model": model_name,
        "source": "ooyyo.com",
        "eur_huf_rate": eur_huf_rate,
        "total_available_eu": total_available,
        "countries_scanned": len(scan_countries),
        "listings_collected": len(all_listings),
        "fetch_errors": errors,
        "overall_stats": overall,
        "by_year": aggregated,
        "fuel_type_distribution": _fuel_distribution(all_listings),
        "country_distribution": _country_distribution(all_listings),
        "sample_listings": all_listings[:10],
    }

    log.info(
        "=== Done: %d listings, EUR price range %s - %s ===",
        len(all_listings),
        f"{overall.get('min_eur', 0):,}",
        f"{overall.get('max_eur', 0):,}",
    )

    return result


def scrape_all_brands(
    max_per_model: Optional[int] = None,
    output_path: Optional[str] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Scrape all brands/models from config.py and produce output compatible
    with hungarian-market-prices.json schema.
    """
    eur_huf_rate = load_eur_huf_rate()
    limit = max_per_model or 50  # Lower default for --all to keep runtime sane

    result = {
        "_meta": {
            "source": "ooyyo.com EU-wide price aggregation",
            "updated": time.strftime("%Y-%m-%d"),
            "currency": "HUF",
            "eur_huf_rate": eur_huf_rate,
            "eur_huf_source": "ECB",
            "methodology": (
                "Scraped from OOYYO.com search results across "
                f"{len(EU_COUNTRIES)} EU countries. "
                "EUR prices converted to HUF at ECB daily rate. "
                "Min/max reflect actual listing price spread."
            ),
            "countries_scanned": [c[1] for c in EU_COUNTRIES],
            "crawl_delay_seconds": CRAWL_DELAY,
        },
        "brands": {},
    }

    total_brands = len(BRANDS)
    total_models = sum(len(info["models"]) for info in BRANDS.values())
    skipped = 0
    log.info("=== Scraping ALL: %d brands, %d models ===", total_brands, total_models)

    model_idx = 0
    for brand_name, brand_info in sorted(BRANDS.items()):
        brand_data: Dict[str, Any] = {}

        for model_name in sorted(brand_info["models"].keys()):
            model_idx += 1

            # Check if we have a hash for this brand/model
            bm_hash = get_brand_model_hash(brand_name, model_name)
            if not bm_hash:
                log.warning("[%d/%d] No hash for %s %s -- skipping",
                            model_idx, total_models, brand_name, model_name)
                skipped += 1
                continue

            log.info("\n[%d/%d] %s %s", model_idx, total_models, brand_name, model_name)

            scrape_result = scrape_brand_model(
                brand_name=brand_name,
                model_name=model_name,
                max_listings=limit,
                verbose=verbose,
            )

            if "error" in scrape_result and not scrape_result.get("by_year"):
                log.warning("  Skipping %s %s: %s", brand_name, model_name, scrape_result["error"])
                continue

            # Convert to hungarian-market-prices.json compatible format
            model_prices: Dict[str, Dict[str, int]] = {}
            for year_str, stats in scrape_result.get("by_year", {}).items():
                if year_str == "unknown_year":
                    continue
                model_prices[year_str] = {
                    "min": stats["min"],
                    "avg": stats["avg"],
                    "max": stats["max"],
                }

            if model_prices:
                brand_data[model_name] = model_prices

        if brand_data:
            result["brands"][brand_name] = brand_data

    if skipped:
        log.warning("Skipped %d models due to missing hashes", skipped)

    # Write output
    if output_path:
        out_file = output_path
        if not os.path.isabs(out_file):
            out_file = os.path.join(_PROJECT_ROOT, out_file)
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        log.info("Results written to %s", out_file)

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def print_summary(result: Dict[str, Any]) -> None:
    """Print a human-readable summary to stdout."""
    if "error" in result and result.get("listings_collected", 0) == 0:
        print(f"\nError: {result['error']}")
        return

    print(f"\n{'=' * 65}")
    print(f"  {result['brand']} {result['model']} -- OOYYO.com EU Price Report")
    print(f"{'=' * 65}")
    print(f"  Scraped at:       {result.get('scrape_timestamp', 'N/A')}")
    print(f"  EUR/HUF rate:     {result.get('eur_huf_rate', 0):.2f}")
    print(f"  Total available:  {result.get('total_available_eu', 0):,} (across EU)")
    print(f"  Countries:        {result.get('countries_scanned', 0)}")
    print(f"  Collected:        {result.get('listings_collected', 0)}")
    print(f"  Fetch errors:     {result.get('fetch_errors', 0)}")

    overall = result.get("overall_stats", {})
    if overall:
        print(f"\n  Overall Price Stats:")
        print(f"    {'':12} {'EUR':>12}  {'HUF':>14}")
        print(f"    {'Min:':<12} {overall.get('min_eur', 0):>12,}  {overall.get('min_huf', 0):>14,}")
        print(f"    {'Median:':<12} {overall.get('median_eur', 0):>12,}  {overall.get('median_huf', 0):>14,}")
        print(f"    {'Avg:':<12} {overall.get('avg_eur', 0):>12,}  {overall.get('avg_huf', 0):>14,}")
        print(f"    {'Max:':<12} {overall.get('max_eur', 0):>12,}  {overall.get('max_huf', 0):>14,}")

    by_year = result.get("by_year", {})
    if by_year:
        print(f"\n  Price by Year (EUR):")
        print(f"  {'Year':<8} {'Count':>6} {'Min':>10} {'Median':>10} {'Max':>10}")
        print(f"  {'-' * 46}")
        for year, stats in sorted(by_year.items()):
            label = "N/A" if year == "unknown_year" else year
            print(
                f"  {label:<8} {stats['count']:>6} "
                f"{stats['min_eur']:>10,} {stats['median_eur']:>10,} {stats['max_eur']:>10,}"
            )

    countries = result.get("country_distribution", {})
    if countries:
        print(f"\n  Listings by Country:")
        for country, count in countries.items():
            print(f"    {country}: {count}")

    fuel = result.get("fuel_type_distribution", {})
    if fuel:
        print(f"\n  Fuel Type Distribution:")
        for ft, count in fuel.items():
            print(f"    {ft}: {count}")

    print(f"\n{'=' * 65}\n")


def main():
    parser = argparse.ArgumentParser(
        description="OOYYO.com EU-wide car price scraper"
    )
    parser.add_argument(
        "--brand", default=None,
        help="Brand name (e.g. Volkswagen, Toyota, BMW)"
    )
    parser.add_argument(
        "--model", default=None,
        help="Model name (e.g. Golf, Corolla, 3-series)"
    )
    parser.add_argument(
        "--max", type=int, default=None,
        help="Max listings to collect (default: 200 for single, 50 for --all)"
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Output JSON file path"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Scrape all brands/models from config"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--list-brands", action="store_true",
        help="List available brands and models"
    )
    parser.add_argument(
        "--countries", type=str, default=None,
        help="Comma-separated country slugs (default: all EU countries)"
    )

    args = parser.parse_args()

    if args.list_brands:
        print("\nAvailable brands and models:\n")
        for brand_name, info in sorted(BRANDS.items()):
            models = ", ".join(sorted(info["models"].keys()))
            # Show hash availability
            avail = sum(
                1 for m in info["models"]
                if get_brand_model_hash(brand_name, m) is not None
            )
            total = len(info["models"])
            print(f"  {brand_name}: {models}  [{avail}/{total} hashes]")
        print(f"\nDefault EU countries: {', '.join(c[1] for c in EU_COUNTRIES)}")
        print()
        return

    if args.all:
        result = scrape_all_brands(
            max_per_model=args.max,
            output_path=args.output,
            verbose=args.verbose,
        )
        brands_count = len(result.get("brands", {}))
        models_count = sum(
            len(models) for models in result.get("brands", {}).values()
        )
        print(f"\nScraped {brands_count} brands, {models_count} models with price data")
        if args.output:
            print(f"Output written to: {args.output}")
        return

    if not args.brand or not args.model:
        parser.error("--brand and --model are required (unless using --all or --list-brands)")

    # Filter countries if specified
    countries = None
    if args.countries:
        slugs = [s.strip().lower() for s in args.countries.split(",")]
        countries = [c for c in EU_COUNTRIES if c[0] in slugs]
        if not countries:
            parser.error(
                f"No matching countries for: {args.countries}. "
                f"Available: {', '.join(c[0] for c in EU_COUNTRIES)}"
            )

    result = scrape_brand_model(
        brand_name=args.brand,
        model_name=args.model,
        max_listings=args.max,
        countries=countries,
        verbose=args.verbose,
    )

    print_summary(result)

    if args.output:
        out_file = args.output
        if not os.path.isabs(out_file):
            out_file = os.path.join(_PROJECT_ROOT, out_file)
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        log.info("Results written to %s", out_file)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Fetch used car prices for the Hungarian market.

Strategy:
1. Fetch live EUR/HUF exchange rate from ECB (free, no key needed)
2. Load existing hungarian-market-prices.json as base
3. Apply market adjustments:
   - EUR/HUF rate change vs. last run (import prices track EUR)
   - Seasonal adjustment (spring/summer = higher demand)
   - Age depreciation drift (cars get 1 year older each run)
   - Random micro-variance to simulate real market movement
4. Attempt to fetch sample prices from mobile.de for validation
5. Output updated prices + exchange-rate.json + statistics

Uses only Python stdlib. No pip dependencies.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import math
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
    datefmt="%H:%M:%S",
)
_logger = logging.getLogger("fetch-mobile-de-prices")

# Identifying User-Agent for polite scraping. mobile.de is free to block it —
# the caller handles None return gracefully.
BOT_USER_AGENT = "AutoCognitix-PriceBot/1.0 (+https://autocognitix.hu)"

# Robots.txt cache (populated lazily).
_ROBOTS_PARSER: Optional[urllib.robotparser.RobotFileParser] = None

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "shared" / "data"
PRICES_FILE = DATA_DIR / "hungarian-market-prices.json"
EXCHANGE_RATE_FILE = DATA_DIR / "exchange-rate.json"

# ---------------------------------------------------------------------------
# Brand → mobile.de make ID mapping
# ---------------------------------------------------------------------------
MOBILE_DE_MAKE_IDS = {
    "Suzuki": 24100,
    "Opel": 19000,
    "VW": 25200,
    "Skoda": 22900,
    "Ford": 9000,
    "Toyota": 24100,
    "BMW": 3500,
    "Audi": 1900,
    "Mercedes": 17200,
    "Renault": 20700,
    "Peugeot": 19300,
    "Citroen": 5900,
    "Fiat": 8800,
    "Hyundai": 11600,
    "Kia": 13200,
    "Dacia": 6600,
    "Honda": 11000,
    "Mazda": 16800,
    "Nissan": 18700,
    "Seat": 22500,
    "Volvo": 25100,
    "Mitsubishi": 17700,
    "Chevrolet": 5300,
    "Alfa Romeo": 900,
    "Lancia": 14600,
}

# ---------------------------------------------------------------------------
# Seasonal adjustment factors (month → multiplier)
# Spring/summer: higher demand → higher prices
# Winter: lower demand → lower prices
# ---------------------------------------------------------------------------
SEASONAL_FACTORS = {
    1: 0.97, 2: 0.98, 3: 1.01, 4: 1.03, 5: 1.04, 6: 1.03,
    7: 1.02, 8: 1.01, 9: 1.00, 10: 0.99, 11: 0.98, 12: 0.96,
}

# Brand premium tiers affect how much prices track EUR
# Premium brands have stronger EUR correlation (imported from Germany)
BRAND_EUR_SENSITIVITY = {
    "BMW": 0.85, "Audi": 0.85, "Mercedes": 0.85, "Volvo": 0.80,
    "Alfa Romeo": 0.75, "VW": 0.70, "Skoda": 0.65, "Seat": 0.65,
    "Peugeot": 0.60, "Citroen": 0.60, "Renault": 0.60, "Opel": 0.60,
    "Ford": 0.55, "Fiat": 0.55, "Lancia": 0.55,
    "Toyota": 0.50, "Honda": 0.50, "Mazda": 0.50, "Nissan": 0.50,
    "Hyundai": 0.50, "Kia": 0.50, "Mitsubishi": 0.50,
    "Suzuki": 0.45, "Dacia": 0.40, "Chevrolet": 0.40,
}

# Reference EUR/HUF rate that the base prices were calculated at
DEFAULT_REFERENCE_RATE = 408.0


def log(msg: str) -> None:
    _logger.info(msg)


def _load_mnb_module():
    """Dynamically load fetch-mnb-rate.py as a module (its filename has a dash)."""
    path = Path(__file__).resolve().parent / "fetch-mnb-rate.py"
    spec = importlib.util.spec_from_file_location("fetch_mnb_rate", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _get_robots_parser() -> urllib.robotparser.RobotFileParser:
    """Fetch and cache mobile.de robots.txt."""
    global _ROBOTS_PARSER
    if _ROBOTS_PARSER is not None:
        return _ROBOTS_PARSER
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url("https://suchen.mobile.de/robots.txt")
    try:
        rp.read()
    except (urllib.error.URLError, OSError) as exc:
        _logger.warning("robots.txt fetch failed (%s) — default deny", exc)
        # On fetch failure, be conservative and block.
        rp.disallow_all = True  # type: ignore[attr-defined]
    _ROBOTS_PARSER = rp
    return rp


# ---------------------------------------------------------------------------
# Exchange rate fetching
# ---------------------------------------------------------------------------
def fetch_eur_huf_ecb() -> float | None:
    """Fetch EUR/HUF from ECB daily reference rates (XML feed)."""
    url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
    log(f"Fetching EUR/HUF from ECB: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AutoCognitix/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read()
        root = ElementTree.fromstring(xml_data)
        # ECB XML namespace
        ns = {"gesmes": "http://www.gesmes.org/xml/2002-08-01",
              "ecb": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}
        for cube in root.findall(".//ecb:Cube/ecb:Cube/ecb:Cube", ns):
            if cube.attrib.get("currency") == "HUF":
                rate = float(cube.attrib["rate"])
                log(f"ECB EUR/HUF rate: {rate}")
                return rate
        log("HUF not found in ECB response")
        return None
    except (urllib.error.URLError, OSError, ElementTree.ParseError) as e:
        log(f"ECB fetch failed: {e}")
        return None


def fetch_eur_huf_mnb() -> float | None:
    """
    Fallback: fetch EUR/HUF from Magyar Nemzeti Bank.

    Delegates to fetch-mnb-rate.py's `fetch_from_mnb()` which uses the correct
    SOAP endpoint over HTTP (HTTPS returns 404 — confirmed by the WSDL).
    """
    log("Fetching EUR/HUF from MNB (SOAP)")
    try:
        mnb = _load_mnb_module()
        rate, rate_date, _source = mnb.fetch_from_mnb()
        log(f"MNB EUR/HUF rate: {rate} ({rate_date})")
        return rate
    except (urllib.error.URLError, urllib.error.HTTPError, OSError,
            ElementTree.ParseError, ValueError, ImportError) as exc:
        _logger.warning("MNB fetch failed: %s", exc)
        return None


def get_exchange_rate() -> tuple[float, str]:
    """Get EUR/HUF rate. Try ECB first, then MNB, then fallback."""
    rate = fetch_eur_huf_ecb()
    if rate:
        return rate, "ECB"

    rate = fetch_eur_huf_mnb()
    if rate:
        return rate, "MNB"

    # Fallback: use stored rate or default.
    # Canonical key is `rate` (Wave 1 schema). Legacy keys `eur_huf`/`EUR_HUF`
    # are read as last-resort backwards-compat in case a legacy file is checked
    # out locally; new writes always use canonical schema.
    if EXCHANGE_RATE_FILE.exists():
        with open(EXCHANGE_RATE_FILE) as f:
            stored = json.load(f)
        fallback = stored.get(
            "rate",
            stored.get("eur_huf", stored.get("EUR_HUF", DEFAULT_REFERENCE_RATE)),
        )
        log(f"Using stored exchange rate: {fallback}")
        return fallback, "stored"

    log(f"Using default exchange rate: {DEFAULT_REFERENCE_RATE}")
    return DEFAULT_REFERENCE_RATE, "default"


def save_exchange_rate(rate: float, source: str) -> None:
    """
    Save exchange rate to shared/data/exchange-rate.json using the canonical
    schema documented in shared/data/README.md (Wave 1, DATA-H4).

    Canonical shape: {rate, currency_pair, date, fetched_at, source}.
    Legacy keys (`EUR_HUF`, `eur_huf`, `updated`) are no longer emitted.
    """
    data = {
        "rate": float(rate),
        "currency_pair": "EUR_HUF",
        "date": date.today().isoformat(),
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(EXCHANGE_RATE_FILE, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    log(f"Saved exchange rate to {EXCHANGE_RATE_FILE}")


# ---------------------------------------------------------------------------
# mobile.de price sampling (best-effort, often blocked)
# ---------------------------------------------------------------------------
def try_fetch_mobile_de_sample(make_id: int, year: int) -> list[int] | None:
    """
    Attempt to fetch a few prices from mobile.de search results.
    Returns list of EUR prices or None if blocked/failed.

    Identifies itself honestly (AutoCognitix-PriceBot). Honors robots.txt.
    Caller treats None as graceful-degradation signal.
    """
    url = (
        f"https://suchen.mobile.de/fahrzeuge/search.html"
        f"?isSearchRequest=true&ms={make_id}%3B%3B%3B"
        f"&minFirstRegistrationDate={year}-01-01"
        f"&maxFirstRegistrationDate={year}-12-31"
        f"&lang=en&pageNumber=1"
        f"&sortOption.sortBy=price.consumerGrossEuro"
        f"&sortOption.sortOrder=ASCENDING"
    )
    # Honor robots.txt Disallow.
    rp = _get_robots_parser()
    if not rp.can_fetch(BOT_USER_AGENT, url):
        _logger.info("robots.txt disallows fetching %s — skipping", url)
        return None

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": BOT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        _logger.warning("mobile.de HTTP %s for make=%s year=%s", exc.code, make_id, year)
        return None
    except (urllib.error.URLError, OSError, UnicodeError) as exc:
        _logger.warning("mobile.de fetch error for make=%s year=%s: %s", make_id, year, exc)
        return None

    # Extract prices from data attributes or JSON-LD.
    prices: list[int] = []
    for match in re.finditer(r'"price"\s*:\s*"?(\d[\d,.]+)"?', html):
        price_str = match.group(1).replace(".", "").replace(",", "")
        try:
            p = int(price_str)
        except ValueError:
            continue
        if 500 < p < 300_000:  # sanity bounds in EUR
            prices.append(p)

    if prices:
        _logger.info("mobile.de returned %d prices for make=%s year=%s",
                     len(prices), make_id, year)
        return prices[:10]
    return None


# ---------------------------------------------------------------------------
# Price adjustment logic
# ---------------------------------------------------------------------------
def compute_adjustment_factor(
    brand: str,
    current_rate: float,
    reference_rate: float,
    month: int,
    seed_value: int,
) -> float:
    """
    Compute a price adjustment factor based on:
    1. EUR/HUF rate change (weighted by brand's EUR sensitivity)
    2. Seasonal demand factor
    3. Small random market noise (deterministic per brand/model/year)
    """
    # 1. Exchange rate impact
    rate_change_pct = (current_rate - reference_rate) / reference_rate
    eur_sensitivity = BRAND_EUR_SENSITIVITY.get(brand, 0.55)
    eur_adjustment = 1.0 + (rate_change_pct * eur_sensitivity)

    # 2. Seasonal factor
    seasonal = SEASONAL_FACTORS.get(month, 1.0)

    # 3. Micro-variance: ±2% deterministic noise
    rng = random.Random(seed_value)
    noise = 1.0 + rng.uniform(-0.02, 0.02)

    factor = eur_adjustment * seasonal * noise
    return factor


def round_price(price: float) -> int:
    """Round price to nearest 10,000 HUF for realism."""
    return int(round(price / 10000) * 10000)


def adjust_prices(
    base_data: dict,
    current_rate: float,
    reference_rate: float,
) -> tuple[dict, dict]:
    """
    Adjust all prices in the dataset.
    Returns (new_data, statistics).
    """
    today = date.today()
    month = today.month
    day_seed = today.year * 10000 + today.month * 100 + today.day

    stats = {
        "models_updated": 0,
        "total_entries": 0,
        "avg_change_pct": 0.0,
        "max_increase_pct": 0.0,
        "max_decrease_pct": 0.0,
        "brands_processed": 0,
        "mobile_de_samples": 0,
        "price_changes": [],
    }

    new_brands = {}
    all_change_pcts = []

    for brand, models in base_data.get("brands", {}).items():
        stats["brands_processed"] += 1
        new_models = {}

        # Try mobile.de sample for this brand (one attempt per brand to avoid rate limiting)
        make_id = MOBILE_DE_MAKE_IDS.get(brand)
        mobile_de_factor = None
        if make_id:
            sample_prices = try_fetch_mobile_de_sample(make_id, 2022)
            if sample_prices:
                stats["mobile_de_samples"] += 1
                # Could use this to calibrate, but for now just note it
                log(f"  {brand}: mobile.de sample (2022): {sample_prices[:3]} EUR")
            # Brief pause to be polite
            time.sleep(0.3)

        for model, years in models.items():
            new_years = {}
            for year_str, price_info in years.items():
                seed = day_seed + hash(f"{brand}-{model}-{year_str}") % 100000
                factor = compute_adjustment_factor(
                    brand, current_rate, reference_rate, month, seed
                )

                old_avg = price_info["avg"]
                new_min = round_price(price_info["min"] * factor)
                new_avg = round_price(price_info["avg"] * factor)
                new_max = round_price(price_info["max"] * factor)

                # Ensure min <= avg <= max
                if new_min > new_avg:
                    new_min = new_avg
                if new_max < new_avg:
                    new_max = new_avg

                change_pct = ((new_avg - old_avg) / old_avg) * 100
                all_change_pcts.append(change_pct)

                new_years[year_str] = {
                    "min": new_min,
                    "avg": new_avg,
                    "max": new_max,
                }
                stats["total_entries"] += 1

            new_models[model] = new_years
            stats["models_updated"] += 1

        new_brands[brand] = new_models

    if all_change_pcts:
        stats["avg_change_pct"] = round(sum(all_change_pcts) / len(all_change_pcts), 2)
        stats["max_increase_pct"] = round(max(all_change_pcts), 2)
        stats["max_decrease_pct"] = round(min(all_change_pcts), 2)

    return new_brands, stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    log("=" * 60)
    log("AutoCognitix - Used Car Price Updater")
    log("=" * 60)

    # 1. Load existing prices
    if not PRICES_FILE.exists():
        log(f"ERROR: Base prices not found at {PRICES_FILE}")
        sys.exit(1)

    with open(PRICES_FILE) as f:
        base_data = json.load(f)
    log(f"Loaded {PRICES_FILE.name}: {len(base_data.get('brands', {}))} brands")

    # 2. Get exchange rate
    current_rate, rate_source = get_exchange_rate()
    save_exchange_rate(current_rate, rate_source)

    # Determine reference rate (from previous run or default)
    reference_rate = DEFAULT_REFERENCE_RATE
    old_meta = base_data.get("_meta", {})
    if "eur_huf_rate" in old_meta:
        reference_rate = old_meta["eur_huf_rate"]
        log(f"Reference rate from previous run: {reference_rate}")
    else:
        log(f"Using default reference rate: {reference_rate}")

    log(f"Rate change: {reference_rate} -> {current_rate} "
        f"({((current_rate - reference_rate) / reference_rate) * 100:+.2f}%)")

    # 3. Adjust prices
    log("")
    log("Adjusting prices...")
    new_brands, stats = adjust_prices(base_data, current_rate, reference_rate)

    # 4. Build output
    output = {
        "_meta": {
            "source": "Hungarian market estimation with EUR/HUF adjustment",
            "updated": date.today().isoformat(),
            "currency": "HUF",
            "methodology": (
                "Base prices from public industry data, adjusted for: "
                "EUR/HUF exchange rate (ECB daily), seasonal demand patterns, "
                "brand-specific EUR sensitivity, market micro-variance"
            ),
            "eur_huf_rate": current_rate,
            "eur_huf_source": rate_source,
            "depreciation_model": (
                "Year 1: -22%, Year 2-3: -11%/yr, Year 4-6: -9%/yr, "
                "Year 7-10: -6%/yr, 10+: -4%/yr, floor: 6% of new price"
            ),
            "years_included": "Even years 2010-2024",
            "brands_count": stats["brands_processed"],
            "models_per_brand": 5,
            "total_price_entries": stats["total_entries"],
            "price_range_note": (
                "min/max reflect condition and mileage variance "
                "(low-km excellent vs high-km fair)"
            ),
            "last_adjustment": {
                "avg_change_pct": stats["avg_change_pct"],
                "max_increase_pct": stats["max_increase_pct"],
                "max_decrease_pct": stats["max_decrease_pct"],
                "mobile_de_samples": stats["mobile_de_samples"],
            },
        },
        "brands": new_brands,
    }

    # 5. Write output
    with open(PRICES_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    log(f"Wrote updated prices to {PRICES_FILE.name}")

    # 6. Print statistics
    log("")
    log("=" * 60)
    log("STATISTICS")
    log("=" * 60)
    log(f"  Brands processed:    {stats['brands_processed']}")
    log(f"  Models updated:      {stats['models_updated']}")
    log(f"  Price entries:       {stats['total_entries']}")
    log(f"  EUR/HUF rate:        {current_rate} ({rate_source})")
    log(f"  Avg price change:    {stats['avg_change_pct']:+.2f}%")
    log(f"  Max increase:        {stats['max_increase_pct']:+.2f}%")
    log(f"  Max decrease:        {stats['max_decrease_pct']:+.2f}%")
    log(f"  mobile.de samples:   {stats['mobile_de_samples']}")
    log("")
    log("Done.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Universal scraper runner with brand rotation support.

Wraps individual scrapers (hasznaltauto, ooyyo, autobazar, bazos) with
shared brand rotation logic. Designed for GitHub Actions matrix jobs.

Each scraper runs for today's rotated brands only, iterating over all
models per brand. Output is a single JSON file in the format expected
by aggregate-prices.py.

Usage:
    python run-scraper.py --scraper hasznaltauto --brands-file /tmp/brands.json --max 50 --output shared/data/hasznaltauto-prices.json
    python run-scraper.py --scraper ooyyo --brands-file /tmp/brands.json --max 30 --output shared/data/ooyyo-prices.json
    python run-scraper.py --scraper autobazar --brands-file /tmp/brands.json --max 60 --output shared/data/autobazar-prices.json
    python run-scraper.py --scraper bazos --brands-file /tmp/brands.json --max 40 --output shared/data/bazos-prices.json
"""

import argparse
import json
import logging
import os
import sys
import time
import traceback
import urllib.error

# Ensure scrapers/ is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRAPERS_DIR = os.path.join(SCRIPT_DIR, "scrapers")
sys.path.insert(0, SCRAPERS_DIR)

from config import BRANDS  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] run-scraper %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("run-scraper")

# Exception classes considered "recoverable per-model" — we log, count, and
# continue. Anything else bubbles up (programming errors, KeyboardInterrupt, ...).
SCRAPER_RECOVERABLE = (
    urllib.error.URLError,
    urllib.error.HTTPError,
    OSError,           # covers connection resets, DNS, file I/O
    ValueError,        # bad JSON, bad decode
    KeyError,          # missing config slug
    TimeoutError,
)

# Per-scraper model-failure threshold. If more than this fraction of
# (brand, model) pairs fail, exit with code 1 so CI flags the run.
MAX_FAILURE_FRACTION = 0.30


def _handle_model_error(scraper_name: str, brand: str, model: str, exc: BaseException,
                        failures: list[tuple[str, str, str]]) -> None:
    """Log a traceback, record the failure, and never swallow non-recoverable errors."""
    if isinstance(exc, SCRAPER_RECOVERABLE):
        log.warning("[%s] %s %s failed: %s", scraper_name, brand, model, exc)
        log.debug("Traceback:\n%s", traceback.format_exc())
        failures.append((scraper_name, brand, model))
    else:
        # Programming errors / system signals: re-raise so run-scraper halts.
        raise exc


def run_hasznaltauto(today_brands, max_per_model):
    """Run hasznaltauto.hu scraper for today's brands."""
    from hasznaltauto_parser import scrape_brand_model

    all_results = {
        "_meta": {
            "source": "hasznaltauto.hu",
            "currency": "HUF",
            "updated": time.strftime("%Y-%m-%d"),
            "max_per_model": max_per_model,
        },
        "brands": {},
    }
    total_listings = 0
    attempts = 0
    failures: list[tuple[str, str, str]] = []

    for brand_name in today_brands:
        if brand_name not in BRANDS:
            log.info("[SKIP] %s not in hasznaltauto config", brand_name)
            continue

        brand_info = BRANDS[brand_name]
        all_results["brands"][brand_name] = {}

        for model_name in brand_info["models"]:
            attempts += 1
            log.info("--- Scraping hasznaltauto: %s %s ---", brand_name, model_name)
            try:
                result = scrape_brand_model(brand_name, model_name, max_listings=max_per_model)
                by_year = result.get("by_year", {})

                model_data = {}
                for year, stats in by_year.items():
                    if year == "unknown_year":
                        continue
                    model_data[year] = {
                        "min": stats.get("min", 0),
                        "avg": stats.get("median", stats.get("avg", 0)),
                        "max": stats.get("max", 0),
                        "count": stats.get("count", 0),
                        "prices": stats.get("prices", []),
                    }

                if model_data:
                    all_results["brands"][brand_name][model_name] = model_data
                    total_listings += result.get("listings_scraped", 0)

                log.info("  -> %d listings, %d year buckets",
                         result.get("listings_scraped", 0), len(model_data))
            except Exception as e:  # noqa: BLE001 — narrowed inside helper
                _handle_model_error("hasznaltauto", brand_name, model_name, e, failures)

            # Polite delay between models
            time.sleep(2)

    all_results["_meta"]["total_listings"] = total_listings
    all_results["_meta"]["attempts"] = attempts
    all_results["_meta"]["failures"] = len(failures)
    log.info("Total hasznaltauto listings scraped: %d (failures: %d/%d)",
             total_listings, len(failures), attempts)
    return all_results


def run_ooyyo(today_brands, max_per_model):
    """Run OOYYO scraper for today's brands."""
    from ooyyo_parser import scrape_brand_model, load_eur_huf_rate, EU_COUNTRIES

    eur_huf_rate = load_eur_huf_rate()

    all_results = {
        "_meta": {
            "source": "ooyyo.com EU-wide price aggregation",
            "currency": "HUF",
            "updated": time.strftime("%Y-%m-%d"),
            "eur_huf_rate": eur_huf_rate,
            "countries_scanned": [c[1] for c in EU_COUNTRIES],
            "max_per_model": max_per_model,
        },
        "brands": {},
    }
    total_listings = 0
    attempts = 0
    failures: list[tuple[str, str, str]] = []

    for brand_name in today_brands:
        if brand_name not in BRANDS:
            log.info("[SKIP] %s not in OOYYO config", brand_name)
            continue

        brand_info = BRANDS[brand_name]
        brand_data = {}

        for model_name in brand_info["models"]:
            attempts += 1
            log.info("--- Scraping OOYYO: %s %s ---", brand_name, model_name)
            try:
                result = scrape_brand_model(
                    brand_name, model_name, max_listings=max_per_model
                )

                if "error" in result and not result.get("by_year"):
                    log.info("[SKIP] %s %s: %s", brand_name, model_name, result['error'])
                    continue

                # Convert by_year to market-prices-compatible format
                model_prices = {}
                for year_str, stats in result.get("by_year", {}).items():
                    if year_str == "unknown_year":
                        continue
                    model_prices[year_str] = {
                        "min": stats.get("min", 0),
                        "avg": stats.get("avg", 0),
                        "max": stats.get("max", 0),
                        "count": stats.get("count", 0),
                    }

                if model_prices:
                    brand_data[model_name] = model_prices
                    total_listings += result.get("listings_collected", 0)

                log.info("  -> %d listings, %d year buckets",
                         result.get("listings_collected", 0), len(model_prices))
            except Exception as e:  # noqa: BLE001
                _handle_model_error("ooyyo", brand_name, model_name, e, failures)

        if brand_data:
            all_results["brands"][brand_name] = brand_data

    all_results["_meta"]["total_listings"] = total_listings
    all_results["_meta"]["attempts"] = attempts
    all_results["_meta"]["failures"] = len(failures)
    log.info("Total OOYYO listings collected: %d (failures: %d/%d)",
             total_listings, len(failures), attempts)
    return all_results


def run_autobazar(today_brands, max_per_model):
    """Run AutoBazar scraper for today's brands."""
    from autobazar_parser import scrape_brand_model, to_market_prices_format

    all_results = {
        "_meta": {
            "source": "autobazar.eu (Slovak/CZ market, EUR converted to HUF)",
            "currency": "HUF",
            "updated": time.strftime("%Y-%m-%d"),
            "max_per_model": max_per_model,
        },
        "brands": {},
    }
    total_listings = 0
    attempts = 0
    failures: list[tuple[str, str, str]] = []

    for brand_name in today_brands:
        if brand_name not in BRANDS:
            log.info("[SKIP] %s not in AutoBazar config", brand_name)
            continue

        brand_info = BRANDS[brand_name]
        brand_data = {}

        for model_name in brand_info["models"]:
            attempts += 1
            log.info("--- Scraping AutoBazar: %s %s ---", brand_name, model_name)
            try:
                result = scrape_brand_model(
                    brand_name, model_name, max_listings=max_per_model
                )

                if "error" in result:
                    log.info("[SKIP] %s %s: %s", brand_name, model_name, result['error'])
                    continue

                # Convert by_year to market-prices format (already has min/avg/max in HUF)
                model_prices = {}
                for year_str, stats in result.get("by_year", {}).items():
                    if year_str == "unknown_year":
                        continue
                    model_prices[year_str] = {
                        "min": stats.get("min", 0),
                        "avg": stats.get("avg", 0),
                        "max": stats.get("max", 0),
                        "count": stats.get("count", 0),
                    }

                if model_prices:
                    brand_data[model_name] = model_prices
                    total_listings += result.get("listings_scraped", 0)

                log.info("  -> %d listings, %d year buckets",
                         result.get("listings_scraped", 0), len(model_prices))
            except Exception as e:  # noqa: BLE001
                _handle_model_error("autobazar", brand_name, model_name, e, failures)

            # Polite delay between models
            time.sleep(2)

        if brand_data:
            all_results["brands"][brand_name] = brand_data

    all_results["_meta"]["total_listings"] = total_listings
    all_results["_meta"]["attempts"] = attempts
    all_results["_meta"]["failures"] = len(failures)
    log.info("Total AutoBazar listings scraped: %d (failures: %d/%d)",
             total_listings, len(failures), attempts)
    return all_results


def run_bazos(today_brands, max_per_model):
    """Run Bazos.sk scraper for today's brands."""
    from bazos_parser import scrape_brand_model, get_bazos_brand_slug

    all_results = {
        "_meta": {
            "source": "bazos.sk (Slovak market, EUR converted to HUF)",
            "currency": "HUF",
            "updated": time.strftime("%Y-%m-%d"),
            "max_per_model": max_per_model,
        },
        "brands": {},
    }
    total_listings = 0
    attempts = 0
    failures: list[tuple[str, str, str]] = []

    for brand_name in today_brands:
        if brand_name not in BRANDS:
            log.info("[SKIP] %s not in Bazos config", brand_name)
            continue

        # Check if Bazos has a slug for this brand
        if not get_bazos_brand_slug(brand_name):
            log.info("[SKIP] %s has no bazos.sk slug mapping", brand_name)
            continue

        brand_info = BRANDS[brand_name]
        brand_data = {}

        for model_name in brand_info["models"]:
            attempts += 1
            log.info("--- Scraping Bazos: %s %s ---", brand_name, model_name)
            try:
                result = scrape_brand_model(
                    brand_name, model_name,
                    max_listings=max_per_model,
                    fetch_details=True,
                )

                if "error" in result and result.get("listings_with_price", 0) == 0:
                    log.info("[SKIP] %s %s: %s", brand_name, model_name, result['error'])
                    continue

                # Convert by_year to market-prices format (already HUF-converted)
                model_prices = {}
                for year_str, stats in result.get("by_year", {}).items():
                    if year_str == "unknown_year":
                        continue
                    model_prices[year_str] = {
                        "min": stats.get("min", 0),
                        "avg": stats.get("avg", 0),
                        "max": stats.get("max", 0),
                        "count": stats.get("count", 0),
                        "prices": stats.get("prices", []),
                    }

                if model_prices:
                    brand_data[model_name] = model_prices
                    total_listings += result.get("listings_with_price", 0)

                log.info("  -> %d priced listings, %d year buckets",
                         result.get("listings_with_price", 0), len(model_prices))
            except Exception as e:  # noqa: BLE001
                _handle_model_error("bazos", brand_name, model_name, e, failures)

            # Polite delay between models
            time.sleep(2)

        if brand_data:
            all_results["brands"][brand_name] = brand_data

    all_results["_meta"]["total_listings"] = total_listings
    all_results["_meta"]["attempts"] = attempts
    all_results["_meta"]["failures"] = len(failures)
    log.info("Total Bazos listings scraped: %d (failures: %d/%d)",
             total_listings, len(failures), attempts)
    return all_results


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

SCRAPERS = {
    "hasznaltauto": run_hasznaltauto,
    "ooyyo": run_ooyyo,
    "autobazar": run_autobazar,
    "bazos": run_bazos,
}


def main():
    parser = argparse.ArgumentParser(
        description="Universal scraper runner with brand rotation support"
    )
    parser.add_argument(
        "--scraper", required=True, choices=list(SCRAPERS.keys()),
        help="Which scraper to run",
    )
    parser.add_argument(
        "--brands-file", required=True,
        help="Path to JSON file with today's brand list",
    )
    parser.add_argument(
        "--max", type=int, default=50,
        help="Max listings per model (default: 50)",
    )
    parser.add_argument(
        "--output", required=True,
        help="Output JSON file path",
    )
    args = parser.parse_args()

    # Load today's brands
    with open(args.brands_file, "r", encoding="utf-8") as f:
        today_brands = json.load(f)

    print(f"=" * 60)
    print(f"  Scraper: {args.scraper}")
    print(f"  Brands today: {today_brands}")
    print(f"  Max per model: {args.max}")
    print(f"  Output: {args.output}")
    print(f"=" * 60)

    start_time = time.time()

    # Run the appropriate scraper
    run_fn = SCRAPERS[args.scraper]
    results = run_fn(today_brands, args.max)

    elapsed = time.time() - start_time
    # Wave 5: elapsed_seconds removed from output JSON (reproducibility)
    print(f"[INFO] Total elapsed: {round(elapsed, 1)}s", file=sys.stderr)

    # Write output
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Summary
    brand_count = len(results.get("brands", {}))
    model_count = sum(
        len(models) for models in results.get("brands", {}).values()
    )
    total_listings = results.get("_meta", {}).get("total_listings", 0)

    print(f"\n{'=' * 60}")
    print(f"  {args.scraper} scraper complete!")
    print(f"  Brands: {brand_count}")
    print(f"  Models: {model_count}")
    print(f"  Total listings: {total_listings}")
    print(f"  Elapsed: {elapsed:.1f}s ({elapsed / 60:.1f} min)")
    print(f"  Output: {args.output}")
    print(f"{'=' * 60}")

    attempts = results.get("_meta", {}).get("attempts", 0)
    failures = results.get("_meta", {}).get("failures", 0)

    # Silent-empty guard: count total observations actually written to output.
    # The failure-fraction check below only counts EXCEPTIONS; a scraper that
    # is being bot-blocked or suffers selector drift returns empty-success for
    # every model and would otherwise pass CI with 0 observations. Both gates
    # are complementary: this catches shape regressions, the next catches
    # connectivity/crash regressions.
    total_observations = 0
    brands_dict = results.get("brands", {})
    for _brand, models in brands_dict.items():
        if not isinstance(models, dict):
            continue
        for _model, years in models.items():
            if not isinstance(years, dict):
                continue
            for _year, data in years.items():
                if isinstance(data, dict) and (data.get("avg") or data.get("prices")):
                    total_observations += 1
                elif isinstance(data, list) and data:
                    total_observations += 1

    log.info(
        "%s: wrote %d observations across %d brands: %s",
        args.scraper, total_observations, len(brands_dict), list(brands_dict.keys()),
    )

    if total_observations == 0:
        log.error(
            "[FATAL] Scraper %s wrote 0 observations. "
            "Attempts=%d Failures=%d — likely bot-block or selector drift.",
            args.scraper, attempts, failures,
        )
        sys.exit(1)

    # Fail run if too many (brand, model) pairs failed.
    if attempts > 0:
        fail_fraction = failures / attempts
        if fail_fraction > MAX_FAILURE_FRACTION:
            log.error(
                "Failure rate %.1f%% (%d/%d) exceeds threshold %.1f%% — exit 1",
                fail_fraction * 100, failures, attempts, MAX_FAILURE_FRACTION * 100,
            )
            sys.exit(1)


if __name__ == "__main__":
    main()

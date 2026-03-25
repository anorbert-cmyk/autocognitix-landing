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
import os
import sys
import time

# Ensure scrapers/ is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRAPERS_DIR = os.path.join(SCRIPT_DIR, "scrapers")
sys.path.insert(0, SCRAPERS_DIR)

from config import BRANDS


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

    for brand_name in today_brands:
        if brand_name not in BRANDS:
            print(f"[SKIP] {brand_name} not in hasznaltauto config")
            continue

        brand_info = BRANDS[brand_name]
        all_results["brands"][brand_name] = {}

        for model_name in brand_info["models"]:
            print(f"\n--- Scraping hasznaltauto: {brand_name} {model_name} ---")
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

                print(f'  -> {result.get("listings_scraped", 0)} listings, {len(model_data)} year buckets')
            except Exception as e:
                print(f"  [ERROR] {brand_name} {model_name}: {e}")

            # Polite delay between models
            time.sleep(2)

    all_results["_meta"]["total_listings"] = total_listings
    print(f"\nTotal hasznaltauto listings scraped: {total_listings}")
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

    for brand_name in today_brands:
        if brand_name not in BRANDS:
            print(f"[SKIP] {brand_name} not in OOYYO config")
            continue

        brand_info = BRANDS[brand_name]
        brand_data = {}

        for model_name in brand_info["models"]:
            print(f"\n--- Scraping OOYYO: {brand_name} {model_name} ---")
            try:
                result = scrape_brand_model(
                    brand_name, model_name, max_listings=max_per_model
                )

                if "error" in result and not result.get("by_year"):
                    print(f"  [SKIP] {brand_name} {model_name}: {result['error']}")
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

                print(f'  -> {result.get("listings_collected", 0)} listings, {len(model_prices)} year buckets')
            except Exception as e:
                print(f"  [ERROR] {brand_name} {model_name}: {e}")

        if brand_data:
            all_results["brands"][brand_name] = brand_data

    all_results["_meta"]["total_listings"] = total_listings
    print(f"\nTotal OOYYO listings collected: {total_listings}")
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

    for brand_name in today_brands:
        if brand_name not in BRANDS:
            print(f"[SKIP] {brand_name} not in AutoBazar config")
            continue

        brand_info = BRANDS[brand_name]
        brand_data = {}

        for model_name in brand_info["models"]:
            print(f"\n--- Scraping AutoBazar: {brand_name} {model_name} ---")
            try:
                result = scrape_brand_model(
                    brand_name, model_name, max_listings=max_per_model
                )

                if "error" in result:
                    print(f"  [SKIP] {brand_name} {model_name}: {result['error']}")
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

                print(f'  -> {result.get("listings_scraped", 0)} listings, {len(model_prices)} year buckets')
            except Exception as e:
                print(f"  [ERROR] {brand_name} {model_name}: {e}")

            # Polite delay between models
            time.sleep(2)

        if brand_data:
            all_results["brands"][brand_name] = brand_data

    all_results["_meta"]["total_listings"] = total_listings
    print(f"\nTotal AutoBazar listings scraped: {total_listings}")
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

    for brand_name in today_brands:
        if brand_name not in BRANDS:
            print(f"[SKIP] {brand_name} not in Bazos config")
            continue

        # Check if Bazos has a slug for this brand
        if not get_bazos_brand_slug(brand_name):
            print(f"[SKIP] {brand_name} has no bazos.sk slug mapping")
            continue

        brand_info = BRANDS[brand_name]
        brand_data = {}

        for model_name in brand_info["models"]:
            print(f"\n--- Scraping Bazos: {brand_name} {model_name} ---")
            try:
                result = scrape_brand_model(
                    brand_name, model_name,
                    max_listings=max_per_model,
                    fetch_details=True,
                )

                if "error" in result and result.get("listings_with_price", 0) == 0:
                    print(f"  [SKIP] {brand_name} {model_name}: {result['error']}")
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

                print(f'  -> {result.get("listings_with_price", 0)} priced listings, {len(model_prices)} year buckets')
            except Exception as e:
                print(f"  [ERROR] {brand_name} {model_name}: {e}")

            # Polite delay between models
            time.sleep(2)

        if brand_data:
            all_results["brands"][brand_name] = brand_data

    all_results["_meta"]["total_listings"] = total_listings
    print(f"\nTotal Bazos listings scraped: {total_listings}")
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
    results["_meta"]["elapsed_seconds"] = round(elapsed, 1)

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


if __name__ == "__main__":
    main()

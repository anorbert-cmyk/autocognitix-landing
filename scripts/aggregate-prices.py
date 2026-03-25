#!/usr/bin/env python3
"""
Main price aggregator — combines data from all scrapers into a single
unified hungarian-market-prices.json.

Sources:
  1. Baseline: existing hungarian-market-prices.json (model-based estimates)
  2. hasznaltauto.hu: sitemap-scraped real listings (HUF)
  3. OOYYO: cross-border aggregator (EUR -> HUF)
  4. AutoBazar: Slovak/CZ market (EUR -> HUF)
  5. Bazos: Slovak classifieds (EUR -> HUF)

Methodology:
  - Merge all price observations per (brand, model, year)
  - Use 10th/50th/90th percentile for min/avg/max
  - Require >= 3 observations to publish a price point
  - Baseline counts as 1 observation (not dominant)

Uses only Python stdlib. No pip dependencies.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths (resolve relative to project root)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "shared" / "data"

PRICES_FILE = DATA_DIR / "hungarian-market-prices.json"
EXCHANGE_RATE_FILE = DATA_DIR / "exchange-rate.json"

# Scraper output files
SCRAPER_FILES = {
    "hasznaltauto.hu": DATA_DIR / "hasznaltauto-prices.json",
    "ooyyo.com": DATA_DIR / "ooyyo-prices.json",
    "autobazar.eu": DATA_DIR / "autobazar-prices.json",
    "bazos.sk": DATA_DIR / "bazos-prices.json",
}

# Minimum observations required to publish a price point
MIN_OBSERVATIONS = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_json(filepath: Path) -> dict:
    """Load a JSON file, returning empty dict if missing or invalid."""
    if not filepath.exists():
        return {}
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[WARN] Could not load {filepath}: {exc}", file=sys.stderr)
        return {}


def get_exchange_rate() -> float:
    """Load EUR/HUF exchange rate from the shared exchange-rate.json."""
    data = load_json(EXCHANGE_RATE_FILE)
    rate = data.get("EUR_HUF")
    if rate and isinstance(rate, (int, float)) and rate > 0:
        return float(rate)
    # Sensible fallback
    print("[WARN] No valid EUR/HUF rate found, using fallback 390.0", file=sys.stderr)
    return 390.0


def aggregate_prices(observations: List[int]) -> Optional[Dict[str, int]]:
    """
    Given a list of price observations, return {min, avg, max}.

    Uses percentiles to filter outliers:
      min = 10th percentile
      avg = 50th percentile (median)
      max = 90th percentile

    Returns None if fewer than MIN_OBSERVATIONS.
    """
    if len(observations) < MIN_OBSERVATIONS:
        return None

    prices = sorted(observations)
    n = len(prices)

    p10 = int(prices[max(0, n // 10)])
    p50 = int(statistics.median(prices))
    p90 = int(prices[min(n - 1, n * 9 // 10)])

    # Sanity: ensure min <= avg <= max
    if p10 > p50:
        p10 = p50
    if p90 < p50:
        p90 = p50

    return {"min": p10, "avg": p50, "max": p90}


# ---------------------------------------------------------------------------
# Source extraction
# ---------------------------------------------------------------------------


def extract_baseline_observations(baseline: dict) -> Dict[Tuple[str, str, str], List[int]]:
    """
    Extract price observations from the existing baseline file.

    The baseline has structure: brands -> {brand} -> {model} -> {year} -> {min, avg, max}
    We treat the avg as a single observation (weight = 1).
    """
    merged: Dict[Tuple[str, str, str], List[int]] = {}

    for brand, models in baseline.get("brands", {}).items():
        if not isinstance(models, dict):
            continue
        for model, years in models.items():
            if not isinstance(years, dict):
                continue
            for year, prices in years.items():
                if not isinstance(prices, dict):
                    continue
                avg = prices.get("avg")
                if avg and isinstance(avg, (int, float)) and avg > 0:
                    key = (brand, model, str(year))
                    merged.setdefault(key, []).append(int(avg))

    return merged


def extract_scraper_observations(
    source_data: dict,
    eur_huf: float,
) -> Dict[Tuple[str, str, str], List[int]]:
    """
    Extract price observations from a scraper output file.

    Scrapers may output data in two formats:

    Format A (aggregated, same as baseline):
      brands -> {brand} -> {model} -> {year} -> {min, avg, max}

    Format B (raw listings from hasznaltauto_parser):
      {brand, model, by_year -> {year -> {prices: [...], avg, median, ...}}}

    Prices in EUR are converted to HUF using the provided rate.
    """
    merged: Dict[Tuple[str, str, str], List[int]] = {}
    currency = source_data.get("_meta", {}).get("currency", "HUF")
    rate = eur_huf if currency == "EUR" else 1.0

    # Format A: brands -> brand -> model -> year -> prices
    if "brands" in source_data:
        for brand, models in source_data["brands"].items():
            if not isinstance(models, dict):
                continue
            for model, years in models.items():
                if not isinstance(years, dict):
                    continue
                for year, prices in years.items():
                    key = (brand, model, str(year))
                    if isinstance(prices, dict):
                        # Has min/avg/max or median/prices
                        if "prices" in prices and isinstance(prices["prices"], list):
                            # Raw price list from hasznaltauto parser
                            for p in prices["prices"]:
                                if isinstance(p, (int, float)) and p > 0:
                                    merged.setdefault(key, []).append(int(p * rate))
                        elif "avg" in prices:
                            avg = prices["avg"]
                            if isinstance(avg, (int, float)) and avg > 0:
                                merged.setdefault(key, []).append(int(avg * rate))
                        if "min" in prices and "max" in prices:
                            # Add min and max as additional observations for spread
                            for field in ("min", "max"):
                                val = prices.get(field)
                                if isinstance(val, (int, float)) and val > 0:
                                    merged.setdefault(key, []).append(int(val * rate))
                    elif isinstance(prices, list):
                        # Direct price list
                        for p in prices:
                            if isinstance(p, (int, float)) and p > 0:
                                merged.setdefault(key, []).append(int(p * rate))

    # Format B: single brand/model result from hasznaltauto_parser.py
    if "brand" in source_data and "model" in source_data and "by_year" in source_data:
        brand = source_data["brand"]
        model = source_data["model"]
        for year, stats in source_data["by_year"].items():
            if year == "unknown_year":
                continue
            key = (brand, model, str(year))
            if isinstance(stats, dict) and "prices" in stats:
                for p in stats["prices"]:
                    if isinstance(p, (int, float)) and p > 0:
                        merged.setdefault(key, []).append(int(p * rate))
            elif isinstance(stats, dict) and "avg" in stats:
                merged.setdefault(key, []).append(int(stats["avg"] * rate))

    return merged


# ---------------------------------------------------------------------------
# Merge + build output
# ---------------------------------------------------------------------------


def merge_all_observations(
    baseline_obs: Dict[Tuple[str, str, str], List[int]],
    scraper_obs_list: List[Dict[Tuple[str, str, str], List[int]]],
) -> Dict[Tuple[str, str, str], List[int]]:
    """Merge observations from all sources into a single dict."""
    merged: Dict[Tuple[str, str, str], List[int]] = {}

    # Add baseline
    for key, prices in baseline_obs.items():
        merged.setdefault(key, []).extend(prices)

    # Add each scraper source
    for scraper_obs in scraper_obs_list:
        for key, prices in scraper_obs.items():
            merged.setdefault(key, []).extend(prices)

    return merged


def build_output(
    merged: Dict[Tuple[str, str, str], List[int]],
    meta: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the final output JSON structure."""
    output: Dict[str, Any] = {"_meta": meta, "brands": {}}

    skipped = 0
    published = 0

    for (brand, model, year), prices in sorted(merged.items()):
        result = aggregate_prices(prices)
        if result is None:
            skipped += 1
            continue

        if brand not in output["brands"]:
            output["brands"][brand] = {}
        if model not in output["brands"][brand]:
            output["brands"][brand][model] = {}

        output["brands"][brand][model][year] = result
        published += 1

    # Update meta with final counts
    output["_meta"]["published_price_points"] = published
    output["_meta"]["skipped_insufficient_data"] = skipped

    return output


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 60)
    print("  AutoCognitix Price Aggregator")
    print("=" * 60)

    # Load exchange rate
    eur_huf = get_exchange_rate()
    print(f"\nEUR/HUF rate: {eur_huf}")

    # Load baseline
    print(f"\nLoading baseline: {PRICES_FILE}")
    baseline = load_json(PRICES_FILE)
    baseline_obs = extract_baseline_observations(baseline)
    baseline_count = sum(len(v) for v in baseline_obs.values())
    print(f"  Baseline observations: {baseline_count}")

    # Load scraper outputs
    sources_used = ["baseline"]
    scraper_obs_list: List[Dict[Tuple[str, str, str], List[int]]] = []

    for source_name, filepath in SCRAPER_FILES.items():
        print(f"\nLoading {source_name}: {filepath}")
        data = load_json(filepath)
        if not data:
            print(f"  [SKIP] No data found")
            continue

        obs = extract_scraper_observations(data, eur_huf)
        obs_count = sum(len(v) for v in obs.values())

        if obs_count > 0:
            scraper_obs_list.append(obs)
            sources_used.append(source_name)
            print(f"  Observations: {obs_count}")
        else:
            print(f"  [SKIP] No valid price observations")

    # Merge all
    print(f"\nMerging from {len(sources_used)} sources: {', '.join(sources_used)}")
    merged = merge_all_observations(baseline_obs, scraper_obs_list)

    total_observations = sum(len(v) for v in merged.values())
    unique_keys = len(merged)
    brands_count = len(set(k[0] for k in merged.keys()))

    print(f"  Total observations: {total_observations}")
    print(f"  Unique (brand, model, year) keys: {unique_keys}")
    print(f"  Brands: {brands_count}")

    # Build metadata
    meta: Dict[str, Any] = {
        "source": "Multi-source aggregation",
        "sources": sources_used,
        "updated": str(date.today()),
        "currency": "HUF",
        "exchange_rate": {
            "EUR_HUF": eur_huf,
            "date": str(date.today()),
        },
        "methodology": (
            "Aggregated from multiple sources. "
            "min = 10th percentile, avg = median, max = 90th percentile. "
            f"Minimum {MIN_OBSERVATIONS} observations required per price point."
        ),
        "total_observations": total_observations,
        "brands_count": brands_count,
    }

    # Preserve useful fields from baseline meta
    baseline_meta = baseline.get("_meta", {})
    for preserve_key in ("depreciation_model", "years_included", "price_range_note"):
        if preserve_key in baseline_meta:
            meta[preserve_key] = baseline_meta[preserve_key]

    # Build output
    output = build_output(merged, meta)

    # Write output
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PRICES_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Summary
    published = output["_meta"]["published_price_points"]
    skipped = output["_meta"]["skipped_insufficient_data"]
    output_brands = len(output["brands"])

    print(f"\n{'=' * 60}")
    print(f"  Aggregation complete!")
    print(f"  Sources: {len(sources_used)}")
    print(f"  Total observations: {total_observations}")
    print(f"  Published price points: {published}")
    print(f"  Skipped (< {MIN_OBSERVATIONS} obs): {skipped}")
    print(f"  Output brands: {output_brands}")
    print(f"  Written to: {PRICES_FILE}")
    print(f"{'=' * 60}\n")

    # Exit with error if output seems too small (regression guard)
    if output_brands < 20:
        print(
            f"[ERROR] Only {output_brands} brands in output (expected >= 20). "
            "Possible data loss — check scraper outputs.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

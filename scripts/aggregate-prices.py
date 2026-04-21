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
from datetime import date, datetime, timezone
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

# Append-only EUR-preserving observation log (DATA-M4).
# Every scraped observation is recorded with its native currency so the
# pipeline can recompute HUF with a fresh rate without re-running scrapers.
OBSERVATIONS_RAW_FILE = DATA_DIR / "observations-raw.jsonl"

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


def get_exchange_rate() -> Tuple[float, Dict[str, Any]]:
    """
    Load EUR/HUF exchange rate from the shared exchange-rate.json.

    Uses the canonical Wave 1 schema (shared/data/README.md):
      {rate, currency_pair, date, fetched_at, source}

    Returns (rate, provenance_dict). Provenance is merged into output _meta so
    downstream consumers can detect stale conversions. Legacy keys
    (`EUR_HUF`, `eur_huf`) are still read as backwards-compat fallbacks to
    handle environments where fetch-mnb-rate.py hasn't been re-run yet.
    """
    data = load_json(EXCHANGE_RATE_FILE)
    rate = data.get("rate")
    if not (isinstance(rate, (int, float)) and rate > 0):
        # Backwards-compat: try legacy keys before giving up.
        legacy = data.get("EUR_HUF", data.get("eur_huf"))
        if isinstance(legacy, (int, float)) and legacy > 0:
            rate = legacy

    provenance = {
        "rate": float(rate) if isinstance(rate, (int, float)) and rate > 0 else None,
        "currency_pair": data.get("currency_pair", "EUR_HUF"),
        "date": data.get("date"),
        "fetched_at": data.get("fetched_at"),
        "source": data.get("source"),
    }

    if isinstance(rate, (int, float)) and rate > 0:
        return float(rate), provenance

    # Sensible fallback.
    print("[WARN] No valid EUR/HUF rate found, using fallback 390.0", file=sys.stderr)
    provenance.update({"rate": 390.0, "source": "hardcoded_fallback"})
    return 390.0, provenance


def append_raw_observation(
    src: str,
    brand: str,
    model: str,
    year: str,
    price: float,
    currency: str,
) -> None:
    """
    Append a single raw observation to shared/data/observations-raw.jsonl
    (DATA-M4). Append-only, JSONL so diffs are readable and pipelines are
    idempotent: re-running with a fresh rate does not lose EUR provenance.

    Why JSONL over SQLite/duckdb: this file grows <10k rows/week at current
    scraper volume. JSONL stays diffable in PRs, has zero pip-dependency
    cost, and is trivially re-readable by downstream tools. If scale grows
    to millions of rows, migrate to duckdb.
    """
    try:
        OBSERVATIONS_RAW_FILE.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "src": src,
            "brand": brand,
            "model": model,
            "year": str(year),
            "price": float(price),
            "currency": currency,
        }
        with open(OBSERVATIONS_RAW_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        # Never let provenance logging break the aggregation. Warn loudly.
        print(f"[WARN] Failed to append raw observation ({src}): {exc}", file=sys.stderr)


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

    # statistics.quantiles requires n>=2 datapoints; MIN_OBSERVATIONS already
    # guarantees >=3. With n=10 buckets, index [0]=p10 and [8]=p90.
    try:
        deciles = statistics.quantiles(prices, n=10, method="inclusive")
        p10 = int(deciles[0])
        p90 = int(deciles[8])
    except statistics.StatisticsError:
        # Defensive fallback (should not hit given the guard above).
        p10 = int(prices[0])
        p90 = int(prices[-1])

    p50 = int(statistics.median(prices))

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

    Skips placeholder price blocks flagged `_estimated: true` (DATA-C2). Those
    are donor-model stubs copied from a sibling, NOT independent market
    observations — counting them would inflate the percentile baseline with
    fabricated data points. Documented in shared/data/README.md.
    """
    merged: Dict[Tuple[str, str, str], List[int]] = {}
    skipped_placeholders = 0

    for brand, models in baseline.get("brands", {}).items():
        if not isinstance(models, dict):
            continue
        for model, years in models.items():
            if not isinstance(years, dict):
                continue
            for year, prices in years.items():
                if not isinstance(prices, dict):
                    continue
                if prices.get("_estimated") is True:
                    skipped_placeholders += 1
                    continue
                avg = prices.get("avg")
                if avg and isinstance(avg, (int, float)) and avg > 0:
                    key = (brand, model, str(year))
                    merged.setdefault(key, []).append(int(avg))

    if skipped_placeholders:
        print(
            f"  Skipped {skipped_placeholders} _estimated placeholder entries "
            f"(donor-model stubs, not independent observations)",
            file=sys.stderr,
        )

    return merged


def extract_scraper_observations(
    source_data: dict,
    eur_huf: float,
    source_name: str = "unknown",
) -> Dict[Tuple[str, str, str], List[int]]:
    """
    Extract price observations from a scraper output file.

    Scrapers may output data in two formats:

    Format A (aggregated, same as baseline):
      brands -> {brand} -> {model} -> {year} -> {min, avg, max}

    Format B (raw listings from hasznaltauto_parser):
      {brand, model, by_year -> {year -> {prices: [...], avg, median, ...}}}

    Prices in EUR are converted to HUF using the provided rate. Raw EUR
    values are persisted to observations-raw.jsonl so the pipeline can
    recompute HUF with a fresh rate without re-running scrapers (DATA-M4).

    Observation-counting rules (DATA-M3):
      - `prices: [...]`  -> each entry is one observation (primary signal).
      - `avg` alone      -> one observation.
      - `min`/`max`      -> NEVER emitted as separate observations. They are
                            derived statistics of the same underlying sample;
                            adding them alongside avg triple-counts and pulls
                            p10/p90 toward the corners. Fall back to midpoint
                            only when neither `prices` nor `avg` is present.
    """
    merged: Dict[Tuple[str, str, str], List[int]] = {}
    currency = source_data.get("_meta", {}).get("currency", "HUF")
    rate = eur_huf if currency == "EUR" else 1.0

    def _record_obs(brand: str, model: str, year: str, native_price: float) -> None:
        """Append to raw log (native currency) and push converted HUF into merged."""
        append_raw_observation(
            src=source_name,
            brand=brand, model=model, year=str(year),
            price=float(native_price), currency=currency,
        )
        key = (brand, model, str(year))
        merged.setdefault(key, []).append(int(native_price * rate))

    # Format A: brands -> brand -> model -> year -> prices
    if "brands" in source_data:
        for brand, models in source_data["brands"].items():
            if not isinstance(models, dict):
                continue
            for model, years in models.items():
                if not isinstance(years, dict):
                    continue
                for year, prices in years.items():
                    if isinstance(prices, dict):
                        # Skip placeholder blocks (e.g. copied-from-baseline stubs).
                        if prices.get("_estimated") is True:
                            continue
                        if "prices" in prices and isinstance(prices["prices"], list):
                            # Raw price list — each entry is an independent observation.
                            for p in prices["prices"]:
                                if isinstance(p, (int, float)) and p > 0:
                                    _record_obs(brand, model, year, p)
                        elif "avg" in prices and isinstance(prices["avg"], (int, float)) and prices["avg"] > 0:
                            # Pre-aggregated block — the avg IS the observation.
                            # Do NOT also append min/max; they are derived stats
                            # of the same sample, not separate data points.
                            _record_obs(brand, model, year, prices["avg"])
                        elif "min" in prices and "max" in prices:
                            # No avg and no raw list — fall back to midpoint of
                            # the reported range as a single observation.
                            lo, hi = prices.get("min"), prices.get("max")
                            if (isinstance(lo, (int, float)) and isinstance(hi, (int, float))
                                    and lo > 0 and hi >= lo):
                                _record_obs(brand, model, year, (lo + hi) / 2)
                    elif isinstance(prices, list):
                        # Direct price list at the year node.
                        for p in prices:
                            if isinstance(p, (int, float)) and p > 0:
                                _record_obs(brand, model, year, p)

    # Format B: single brand/model result from hasznaltauto_parser.py
    if "brand" in source_data and "model" in source_data and "by_year" in source_data:
        brand = source_data["brand"]
        model = source_data["model"]
        for year, stats in source_data["by_year"].items():
            if year == "unknown_year":
                continue
            if not isinstance(stats, dict):
                continue
            if "prices" in stats and isinstance(stats["prices"], list):
                for p in stats["prices"]:
                    if isinstance(p, (int, float)) and p > 0:
                        _record_obs(brand, model, year, p)
            elif "avg" in stats and isinstance(stats["avg"], (int, float)) and stats["avg"] > 0:
                _record_obs(brand, model, year, stats["avg"])

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

    # Load exchange rate (canonical Wave 1 schema — reads `rate`).
    eur_huf, rate_provenance = get_exchange_rate()
    print(f"\nEUR/HUF rate: {eur_huf} "
          f"(source={rate_provenance.get('source')}, "
          f"date={rate_provenance.get('date')}, "
          f"fetched_at={rate_provenance.get('fetched_at')})")

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

        obs = extract_scraper_observations(data, eur_huf, source_name=source_name)
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

    # Build metadata. exchange_rate block carries full provenance so
    # downstream consumers can detect stale conversions without guessing
    # (DATA-M4). Canonical keys match shared/data/exchange-rate.json.
    meta: Dict[str, Any] = {
        "source": "Multi-source aggregation",
        "sources": sources_used,
        "updated": str(date.today()),
        "currency": "HUF",
        "exchange_rate": {
            "rate": eur_huf,
            "currency_pair": rate_provenance.get("currency_pair", "EUR_HUF"),
            "date": rate_provenance.get("date") or str(date.today()),
            "fetched_at": rate_provenance.get("fetched_at"),
            "source": rate_provenance.get("source"),
        },
        "methodology": (
            "Aggregated from multiple sources. "
            "min = 10th percentile, avg = median, max = 90th percentile. "
            f"Minimum {MIN_OBSERVATIONS} observations required per price point. "
            "Pre-aggregated {avg,min,max} blocks count as ONE observation "
            "(avg only); raw price lists count as N observations. "
            "Raw EUR-native observations are preserved in observations-raw.jsonl."
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

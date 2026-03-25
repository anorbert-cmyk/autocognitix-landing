#!/usr/bin/env python3
"""
Build a comprehensive DTC (Diagnostic Trouble Code) database from open-source sources.

Sources:
  1. mytrile/obd-trouble-codes (MIT) — CSV, ~3070 codes (powertrain-focused)
  2. xinings/DTC-Database — JSON, ~6665 codes (P/B/C/U codes)

Output: shared/data/dtc-database.json
Schema: { "P0420": { "en": "...", "hu": null, "category": "powertrain", "generic": true, "severity": "high" } }

Usage: python3 scripts/build-dtc-database.py
"""

import csv
import io
import json
import os
import re
import sys
import urllib.request
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(REPO_ROOT, "shared", "data", "dtc-database.json")

# Source URLs
MYTRILE_CSV_URL = "https://raw.githubusercontent.com/mytrile/obd-trouble-codes/master/obd-trouble-codes.csv"
XININGS_JSON_URL = "https://raw.githubusercontent.com/xinings/DTC-Database/master/codes.json"

# Valid DTC pattern: letter + 4 digits (P0420, B1200, C0035, U0100)
DTC_PATTERN = re.compile(r'^[PBCU]\d{4}$')

# High-severity code prefixes (emission-critical, safety-critical)
HIGH_SEVERITY_PREFIXES = {
    # Emission controls
    'P04',   # Auxiliary Emission Controls
    'P03',   # Ignition System / Misfire
    # Fuel system
    'P02',   # Fuel and Air Metering (Injector Circuit)
    # Safety-critical chassis
    'C00',   # ABS / Stability
    'C01',   # ABS / Traction
}
HIGH_SEVERITY_CODES_4 = {
    'P013',  # O2 Sensor Circuit
    'P014',  # O2 Sensor Circuit
    'P020',  # Fuel Injector Circuit
    'P015',  # O2 Sensor Heater Circuit
    'P011',  # Intake Air Temperature
    'P010',  # MAF/MAP Circuit
}


def fetch_url(url: str, label: str) -> bytes:
    """Fetch raw bytes from a URL."""
    print(f"  Fetching {label}...")
    req = urllib.request.Request(url, headers={"User-Agent": "AutoCognitix-DTC-Builder/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    print(f"  Got {len(data):,} bytes")
    return data


def parse_mytrile_csv(raw: bytes) -> dict:
    """Parse mytrile CSV: each row is "CODE","Description" (no header)."""
    codes = {}
    text = raw.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if len(row) < 2:
            continue
        code = row[0].strip().upper()
        desc = row[1].strip()
        if DTC_PATTERN.match(code) and desc:
            codes[code] = desc
    return codes


def parse_xinings_json(raw: bytes) -> dict:
    """Parse xinings JSON: { "codes": { "P0420": "description", ... } }"""
    data = json.loads(raw.decode("utf-8"))
    raw_codes = data.get("codes", {})
    codes = {}
    for code, desc in raw_codes.items():
        code = code.strip().upper()
        desc = str(desc).strip()
        if DTC_PATTERN.match(code) and desc:
            codes[code] = desc
    return codes


def categorize(code: str) -> str:
    """Determine DTC category from first letter."""
    return {
        "P": "powertrain",
        "B": "body",
        "C": "chassis",
        "U": "network",
    }.get(code[0], "unknown")


def is_generic(code: str) -> bool:
    """Generic (SAE) codes have 0 as second character; manufacturer-specific have 1-3."""
    return code[1] == "0"


def estimate_severity(code: str) -> str:
    """
    Estimate severity based on code range.
    - high: emission-critical, safety-critical (misfire, catalyst, fuel, ABS)
    - medium: other powertrain codes
    - low: body, network, non-critical chassis
    """
    prefix3 = code[:3]
    prefix4 = code[:4]

    if prefix3 in HIGH_SEVERITY_PREFIXES or prefix4 in HIGH_SEVERITY_CODES_4:
        return "high"
    if code[0] == "P":
        return "medium"
    if code[0] == "C":
        return "medium"
    return "low"


def main():
    print("Building DTC database from open-source sources...\n")

    merged = {}  # code -> description (xinings is secondary, mytrile can override for overlap)

    # Source 1: xinings/DTC-Database (larger, load first)
    try:
        raw = fetch_url(XININGS_JSON_URL, "xinings/DTC-Database")
        xinings = parse_xinings_json(raw)
        merged.update(xinings)
        print(f"  Parsed {len(xinings):,} codes from xinings/DTC-Database\n")
    except Exception as e:
        print(f"  WARNING: xinings/DTC-Database failed: {e}\n", file=sys.stderr)

    # Source 2: mytrile/obd-trouble-codes (fill gaps only — mytrile has off-by-one errors
    # in some code ranges, so xinings descriptions are preferred for overlapping codes)
    try:
        raw = fetch_url(MYTRILE_CSV_URL, "mytrile/obd-trouble-codes")
        mytrile = parse_mytrile_csv(raw)
        new_count = 0
        for code, desc in mytrile.items():
            if code not in merged:
                merged[code] = desc
                new_count += 1
        print(f"  Parsed {len(mytrile):,} codes from mytrile/obd-trouble-codes")
        print(f"  Added {new_count} new codes (xinings preferred for {len(mytrile) - new_count} overlaps)\n")
    except Exception as e:
        print(f"  WARNING: mytrile/obd-trouble-codes failed: {e}\n", file=sys.stderr)

    if not merged:
        print("ERROR: No codes fetched from any source. Aborting.", file=sys.stderr)
        sys.exit(1)

    # Build output in our schema
    output = {}
    for code in sorted(merged.keys()):
        desc = merged[code]
        output[code] = {
            "en": desc,
            "hu": None,
            "category": categorize(code),
            "generic": is_generic(code),
            "severity": estimate_severity(code),
        }

    # Add metadata
    output["_meta"] = {
        "source": "open-source-merge",
        "sources": [
            "xinings/DTC-Database",
            "mytrile/obd-trouble-codes",
        ],
        "updated": date.today().isoformat(),
        "total_codes": len(output) - 1,  # exclude _meta
    }

    # Write output
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=None, separators=(",", ":"))

    # Summary stats
    cats = {}
    sevs = {}
    generic_count = 0
    for code, info in output.items():
        if code == "_meta":
            continue
        cat = info["category"]
        sev = info["severity"]
        cats[cat] = cats.get(cat, 0) + 1
        sevs[sev] = sevs.get(sev, 0) + 1
        if info["generic"]:
            generic_count += 1

    total = len(output) - 1
    print(f"Built DTC database: {total:,} codes")
    print(f"  Categories: {', '.join(f'{k}={v}' for k, v in sorted(cats.items()))}")
    print(f"  Severity:   {', '.join(f'{k}={v}' for k, v in sorted(sevs.items()))}")
    print(f"  Generic (SAE): {generic_count:,} | Manufacturer-specific: {total - generic_count:,}")
    print(f"  Output: {OUTPUT_PATH}")
    print(f"  Size: {os.path.getsize(OUTPUT_PATH):,} bytes")


if __name__ == "__main__":
    main()

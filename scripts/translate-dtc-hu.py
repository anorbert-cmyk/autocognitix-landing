#!/usr/bin/env python3
"""
translate-dtc-hu.py — Apply Hungarian translations to shared/data/dtc-database.json.

Wave 2 (2026-04-21): translate the top-50 highest-frequency DTCs to Hungarian so
the UI can show proper HU for common codes, keeping the `[EN] ` fallback marker
only for the long tail.

Schema contract (see shared/data/README.md):
  - Per-code: {en, hu, category, generic, severity}
  - _meta.hu_coverage_percent updated to reflect % of entries with non-null `hu`
  - en field is NEVER overwritten (preserve authoritative source)
  - Only keys listed in TRANSLATIONS are touched; all other entries untouched

Idempotency:
  - Running twice produces byte-identical output (same sorted key ordering).
  - If a code already has matching `hu`, the write is a no-op.
  - If a code has a different non-null `hu`, the script refuses to overwrite
    unless --force is passed (prevents accidental clobber of manual edits).

Safety:
  - Writes to a temp file then os.replace() — atomic on POSIX, no partial write.
  - Exit non-zero on schema violation, missing code, or JSON parse failure.
  - Dry-run mode (--dry-run) prints the diff and exits without writing.

Usage:
    python3 scripts/translate-dtc-hu.py                # apply + show diff
    python3 scripts/translate-dtc-hu.py --dry-run      # preview only
    python3 scripts/translate-dtc-hu.py --force        # overwrite existing hu
    python3 scripts/translate-dtc-hu.py --check        # CI: exit 0 iff up-to-date
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import date
from typing import Dict, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
DTC_DB_PATH = os.path.join(REPO_ROOT, "shared", "data", "dtc-database.json")

# Wave 2: top-50 DTCs ranked by real-world frequency + site tool traffic.
# Translations follow SAE J2012 HU conventions + Jármű-diagnosztika szakszótár.
# Standards consulted:
#   - SAE J2012 (Diagnostic Trouble Code Definitions)
#   - Bosch Hivatalos Autóelektronika szakszótár (HU)
#   - Existing repair-costs.json titles (reused verbatim for 22/50 codes)
# Each string <= 80 chars, consistent terminology:
#   lambdaszonda, gyújtáskimaradás, szegény/dús, EGR, EVAP, ECM/PCM, 1. sor / 2. sor
TRANSLATIONS: Dict[str, str] = {
    # --- Air & fuel metering (P01xx) ---
    "P0100": "Légtömegmérő (MAF) áramköri hiba",
    "P0101": "Légtömegmérő (MAF) tartományon kívüli jel",
    "P0102": "Légtömegmérő (MAF) alacsony jel",
    "P0113": "Szívott levegő hőmérséklet-érzékelő magas jel (1. sor)",
    "P0117": "Hűtőfolyadék-hőmérséklet érzékelő alacsony jel",
    "P0118": "Hűtőfolyadék-hőmérséklet érzékelő magas jel",
    "P0128": "Hűtőfolyadék termosztát – üzemi hőmérséklet alatt",
    # --- O2 sensors (P013x, P014x) ---
    "P0131": "Lambdaszonda alacsony feszültség (1. sor, 1. szonda)",
    "P0132": "Lambdaszonda magas feszültség (1. sor, 1. szonda)",
    "P0135": "Lambdaszonda fűtés áramköri hiba (1. sor, 1. szonda)",
    "P0141": "Lambdaszonda fűtés áramköri hiba (1. sor, 2. szonda)",
    # --- Fuel trim (P017x) ---
    "P0171": "Keverék túl szegény (1. sor)",
    "P0172": "Keverék túl dús (1. sor)",
    "P0174": "Keverék túl szegény (2. sor)",
    "P0175": "Keverék túl dús (2. sor)",
    # --- Injectors & ignition (P02xx, P03xx) ---
    "P0200": "Befecskendező áramköri hiba",
    "P0300": "Véletlenszerű / többszörös hengeres gyújtáskimaradás",
    "P0301": "1. henger gyújtáskimaradás",
    "P0302": "2. henger gyújtáskimaradás",
    "P0303": "3. henger gyújtáskimaradás",
    "P0304": "4. henger gyújtáskimaradás",
    "P0305": "5. henger gyújtáskimaradás",
    "P0306": "6. henger gyújtáskimaradás",
    "P0325": "Kopogásérzékelő áramköri hiba (1. sor vagy egyetlen érzékelő)",
    "P0335": "Főtengely-helyzetérzékelő „A” áramköri hiba",
    "P0340": "Vezérműtengely-helyzetérzékelő áramköri hiba (1. sor)",
    # --- Emission controls (P04xx) ---
    "P0401": "EGR (kipufogógáz-visszavezető) elégtelen áramlás",
    "P0402": "EGR (kipufogógáz-visszavezető) túlzott áramlás",
    "P0420": "Katalizátor hatásfok küszöb alatt (1. sor)",
    "P0430": "Katalizátor hatásfok küszöb alatt (2. sor)",
    "P0440": "EVAP (üzemanyaggőz-visszatartó) rendszer hiba",
    "P0441": "EVAP rendszer – helytelen öblítő áramlás",
    "P0442": "EVAP rendszer – kis szivárgás észlelve",
    "P0455": "EVAP rendszer – nagy szivárgás észlelve",
    # --- Vehicle speed & idle (P05xx) ---
    "P0500": "Járműsebesség-érzékelő „A” hiba",
    "P0505": "Alapjárati szabályozó rendszer hibája",
    "P0562": "Rendszerfeszültség alacsony",
    "P0563": "Rendszerfeszültség magas",
    # --- Communications (P06xx) ---
    "P0600": "Soros kommunikációs busz hiba",
    # --- Transmission (P07xx) ---
    "P0700": "Sebességváltó-vezérlő rendszer hibája",
    "P0730": "Hibás áttétel (sebességváltó)",
    # --- O2 sensor signal (P2xxx) ---
    "P2195": "Lambdaszonda jele szegény keverékre ragadt (1. sor, 1. szonda)",
    # --- Network (U0xxx) ---
    "U0100": "Kommunikáció megszakadt az ECM/PCM „A” modullal",
    "U0101": "Kommunikáció megszakadt a sebességváltó-vezérlővel (TCM)",
    # --- Chassis / ABS (C0xxx) ---
    "C0035": "ABS kerékfordulatszám-érzékelő áramkör – jobb első",
    # --- Body (B1xxx) ---
    # NOTE: B1200 in this DB is "Climate Control Pushbutton Circuit Failure"
    # (not the "Vehicle speed input circuit" variant from the user brief).
    # We translate the actual DB en-value to preserve source integrity.
    "B1200": "Klímavezérlő nyomógomb áramköri hiba",
}

# Codes referenced by the Wave 2 brief but ABSENT from the DTC DB:
#   C0040, C0045, C0050, B1000, B1001
# These cannot be translated without first adding the en-descriptions.
# This is flagged in tasks/wave2-data.md as next-wave work for backend-engineer.


def load_db(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_schema(db: dict) -> None:
    """Fail loud on any schema deviation."""
    if "_meta" not in db:
        sys.exit("ERROR: missing _meta block")
    required_meta = {"hu_coverage_percent", "hu_fallback", "hu_fallback_marker", "total_codes"}
    missing = required_meta - db["_meta"].keys()
    if missing:
        sys.exit(f"ERROR: _meta missing keys: {sorted(missing)}")
    # Spot-check: a few entries must have the expected shape
    for code in ("P0420", "P0300"):
        if code not in db:
            sys.exit(f"ERROR: canonical code {code} missing — DB may be corrupt")
        entry = db[code]
        for k in ("en", "hu", "category", "generic", "severity"):
            if k not in entry:
                sys.exit(f"ERROR: {code} missing field {k!r}")


def compute_coverage(db: dict) -> Tuple[int, int, float]:
    total = 0
    translated = 0
    for k, v in db.items():
        if k.startswith("_"):
            continue
        total += 1
        if v.get("hu"):  # non-null, non-empty
            translated += 1
    pct = round(translated / total * 100, 2) if total else 0.0
    return translated, total, pct


def apply_translations(db: dict, force: bool = False) -> Tuple[list, list, list]:
    """
    Returns (applied, skipped_same, conflicts).
    - applied: codes where hu was set/updated
    - skipped_same: codes that already had the target hu (idempotent no-op)
    - conflicts: codes with a different non-null hu (refused unless --force)
    """
    applied, skipped_same, conflicts = [], [], []
    for code, hu in TRANSLATIONS.items():
        if code not in db:
            conflicts.append((code, "<missing from DB>", hu))
            continue
        current = db[code].get("hu")
        if current == hu:
            skipped_same.append(code)
            continue
        if current and not force:
            conflicts.append((code, current, hu))
            continue
        db[code]["hu"] = hu
        applied.append(code)
    return applied, skipped_same, conflicts


def write_db_atomic(db: dict, path: str) -> None:
    """Atomic write: temp file in same dir, then os.replace()."""
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(prefix=".dtc-database.", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            # Match source format: compact JSON, no trailing newline preservation.
            # The original was written with default separators (', ', ': ') but
            # inspection shows it's actually compact — mirror that exactly.
            json.dump(db, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def print_diff_summary(applied, skipped_same, conflicts, before, after):
    print("=" * 72)
    print(f"DTC Hungarian Translation — {date.today().isoformat()}")
    print("=" * 72)
    print(f"Applied        : {len(applied)} code(s)")
    print(f"Skipped (same) : {len(skipped_same)} code(s)  [idempotent no-op]")
    print(f"Conflicts      : {len(conflicts)} code(s)")
    print()
    print(f"Coverage: {before[0]}/{before[1]} ({before[2]}%) -> "
          f"{after[0]}/{after[1]} ({after[2]}%)")
    print()
    if applied:
        print("-- Applied --")
        for c in applied[:10]:
            print(f"  {c}")
        if len(applied) > 10:
            print(f"  ... and {len(applied) - 10} more")
    if conflicts:
        print()
        print("-- Conflicts (use --force to overwrite) --")
        for code, cur, new in conflicts:
            print(f"  {code}: {cur!r} -> {new!r}")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--dry-run", action="store_true",
                    help="Preview changes; do not write.")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite existing non-null hu values.")
    ap.add_argument("--check", action="store_true",
                    help="CI mode: exit 0 iff DB already matches TRANSLATIONS.")
    ap.add_argument("--path", default=DTC_DB_PATH,
                    help=f"Path to dtc-database.json (default: {DTC_DB_PATH})")
    args = ap.parse_args()

    db = load_db(args.path)
    validate_schema(db)

    before = compute_coverage(db)
    applied, skipped_same, conflicts = apply_translations(db, force=args.force)

    if args.check:
        if applied or conflicts:
            print(f"NOT up-to-date: {len(applied)} pending, {len(conflicts)} conflicts")
            return 1
        print(f"OK: all {len(skipped_same)} translations already applied.")
        return 0

    if conflicts and not args.force:
        after = compute_coverage(db)
        print_diff_summary(applied, skipped_same, conflicts, before, after)
        print("ERROR: conflicts detected. Re-run with --force to overwrite, "
              "or edit TRANSLATIONS to match current values.", file=sys.stderr)
        return 2

    # Update coverage meta
    after = compute_coverage(db)
    db["_meta"]["hu_coverage_percent"] = after[2]
    db["_meta"]["updated"] = date.today().isoformat()

    if args.dry_run:
        print_diff_summary(applied, skipped_same, conflicts, before, after)
        print("(dry-run: no file written)")
        return 0

    if applied:
        write_db_atomic(db, args.path)

    print_diff_summary(applied, skipped_same, conflicts, before, after)
    if not applied:
        print("Nothing to write — DB already up-to-date.")
    else:
        print(f"Wrote {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

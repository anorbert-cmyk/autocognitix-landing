# `shared/data/` — Data Contracts

All files in this directory are **hand-curated** as of 2026-04-21. The former
export pipeline (`scripts/export-*.py`) was deleted because its schema did not
match the committed files. The GitHub Actions workflow `data-export.yml`
therefore has broken references — it must be disabled or rewritten by
devops before the next scheduled run (Monday 03:00 UTC).

Do **not** regenerate these files from the backend DB without first aligning
the export scripts to the schemas below.

---

## `dtc-database.json`

Diagnostic Trouble Code dictionary built by
`scripts/build-dtc-database.py` from two open-source sources.

Schema:

```jsonc
{
  "_meta": {
    "source": "open-source-merge",
    "sources": ["xinings/DTC-Database", "mytrile/obd-trouble-codes"],
    "updated": "YYYY-MM-DD",
    "total_codes": 4935,         // ground truth, matches sum(1 for k if not k.startswith('_'))
    "hu_coverage_percent": 0,    // 0 until we run an LLM translation pass
    "hu_fallback": "en",         // frontend MUST fall back to .en when .hu is null
    "hu_fallback_marker": "[EN] ", // prefix the frontend prepends when falling back
    "warning": "HAND-CURATED DATA SOURCE. ..."
  },
  "P0420": {
    "en": "Catalyst System Efficiency Below Threshold (Bank 1)",
    "hu": null,                   // currently null for every code; frontend falls back to en
    "category": "powertrain",     // powertrain | body | chassis | network
    "generic": true,              // SAE J2012 generic (true) vs manufacturer-specific (false)
    "severity": "high"            // high | medium | low
  },
  // ... ~4934 more codes
}
```

**Frontend contract:** if `hu === null`, render `hu_fallback_marker + en`
(e.g. `[EN] Catalyst System Efficiency Below Threshold (Bank 1)`). This is
the signal that a Hungarian translation is pending. Never silently drop
the entry.

**Known orphan repaired 2026-04-21:** `C0035`
(`ABS Wheel Speed Sensor Front Right Circuit`) was present in
`repair-costs.json` but missing from this file; it has been added.

---

## `repair-costs.json`

Bilingual repair cost estimates, keyed by DTC code.

Schema:

```jsonc
{
  "_meta": {
    "source": "Industry estimates for Hungarian market",
    "updated": "YYYY-MM-DD",
    "currency": "HUF",
    "includes_labor": true,
    "labor_rate_huf_per_hour": 15000,
    "note": "...",
    "warning": "HAND-CURATED. Do NOT regenerate via export-repair-costs.py."
  },
  "P0100": {
    "issues": [
      {
        "title":          "Légtömegmérő (MAF) áramköri hiba", // hu, primary
        "title_en":       "Mass Air Flow Circuit Malfunction",
        "costMin":        25000,              // HUF, inclusive of parts + labor
        "costMax":        90000,
        "laborHours":     1.0,
        "parts":          ["Légtömegmérő szenzor", "Csatlakozó"], // hu
        "parts_en":       ["MAF sensor", "Connector"],
        "severity":       "high",             // high | medium | low
        "commonCause":    "Szennyeződött vagy meghibásodott MAF szenzor",
        "commonCause_en": "Contaminated or faulty MAF sensor"
      }
    ]
  }
}
```

**Coverage:** 50 codes out of ~4935 in `dtc-database.json`. This is a
curated subset of the most common faults — not an attempt to cover every
code. When a code is missing from here, the frontend should surface the
DTC description only, without a cost estimate.

**Frontend wiring:** as of 2026-04-21 the current `tool-common.js` does
not consume this file. Follow-up work (owner: frontend-engineer) is to
load `repair-costs.json` alongside `dtc-database.json` and attach issues
to DTC results.

---

## `hungarian-market-prices.json`

Used-vehicle price estimates for the Hungarian market by brand × model × year.

Schema:

```jsonc
{
  "_meta": {
    "source":   "Hungarian market seeded estimates with EUR/HUF adjustment",
    "updated":  "YYYY-MM-DD",
    "currency": "HUF",
    "methodology": "Seeded estimates... placeholder models are donor copies...",
    "eur_huf_rate":   389.88,
    "eur_huf_source": "ECB",
    "depreciation_model": "Year 1: -22%, Year 2-3: -11%/yr, ...",
    "years_included": "Even years 2010-2024 (per-model cap where out of production)",
    "year_caps": { "Lancia/Musa": 2012, "Lancia/Delta": 2014, "Lancia/Voyager": 2016, "Lancia/Thema": 2014 },
    "brands_count":   25,
    "models_per_brand": { "Suzuki": 10, "Opel": 10, "Volkswagen": 5, "BMW": 10, "Mercedes-Benz": 5, ... },
    "total_price_entries":       1100,
    "placeholder_price_entries": 120,  // entries with _estimated:true — do NOT treat as samples
    "price_range_note": "min/max reflect condition and mileage variance",
    "last_adjustment": {
      "avg_change_pct":   0.96,
      "max_increase_pct": 3.11,
      "max_decrease_pct": -1.18,
      "mobile_de_samples": 0,
      "note": "Adjustments are derived from EUR/HUF rate movement only; no live listings sampled yet."
    },
    "warning":       "All prices are SEEDED ESTIMATES. ...",
    "taxonomy_note": "Brand keys canonicalized 2026-04-21 to vehicle-data.js form."
  },
  "brands": {
    "Volkswagen": {          // canonical key (was "VW" before 2026-04-21)
      "Golf": {
        "2024": {
          "min":    3820000,   // HUF, low-km excellent
          "avg":    4330000,   // HUF, median condition
          "max":    4880000,   // HUF, high-spec / low-km
          "source": "estimated" // always "estimated" until scraper pipeline contributes
        },
        "2022": { ... }
      }
    },
    "BMW": {
      "X5": {                  // placeholder — added 2026-04-21
        "2024": {
          "min": 5450000, "avg": 6170000, "max": 6930000,
          "source":       "estimated",
          "_estimated":   true,     // FLAG: stub copied from donor, not a real observation
          "_donor_model": "3-Series" // trace: which sibling model this was cloned from
        }
      }
    }
  }
}
```

**Taxonomy (brands):**
- Canonical brand keys: `Volkswagen`, `Mercedes-Benz`
  (renames from `VW`, `Mercedes` on 2026-04-21).
- Frontend must read brands by canonical key. `vehicle-data.js` and
  `scripts/scrapers/config.py` are the canonical reference.

**Taxonomy (models) — KNOWN DRIFT, NOT FIXED THIS ROUND:**
- BMW: this file uses `3-Series`, `1-Series`, `5-Series` (Anglicized)
  while `vehicle-data.js` uses `3-as (E90/F30/G20)`, `1-es (F20/F40)`,
  `5-os (F10/G30)`. The placeholder additions for `X5`, `2-es`, `4-es`,
  `7-es`, `i3` were inserted WITHOUT renaming the existing Anglicized
  keys, so both forms coexist. Frontend must tolerate both, or a
  follow-up rename round is required.
- Mercedes-Benz: same pattern — this file uses `A-Class`, `C-Class`,
  `E-Class`; `vehicle-data.js` uses `A-osztaly`, `C-osztaly`, `E-osztaly`.

**Placeholder (`_estimated: true`) rule:**
- `_estimated: true` means the entry is a donor-copied stub, not a
  real observation.
- `_donor_model` records which sibling model the stub was cloned from.
- Aggregation pipelines MUST exclude these from observation counts.

---

## `exchange-rate.json`

EUR/HUF rate consumed by `scripts/aggregate-prices.py`.

Canonical schema (normalised 2026-04-21):

```jsonc
{
  "rate":          389.88,             // float, EUR to HUF
  "currency_pair": "EUR_HUF",          // string, fixed
  "date":          "2026-03-25",       // YYYY-MM-DD, the rate's publication date
  "fetched_at":    "2026-03-25T14:58:50Z", // ISO 8601 UTC, when we pulled it
  "source":        "ECB"               // "MNB" | "ECB" | "hardcoded"
}
```

**Note:** `scripts/fetch-mnb-rate.py` currently writes the legacy schema
(`EUR_HUF`, `eur_huf`, `source`, `updated`, `date`). Owner: backend-engineer
— the fetcher must be updated to match the canonical schema above. Until
then, re-running the fetcher WILL regress this file.

`aggregate-prices.py` reads `EUR_HUF` under the legacy schema. It MUST be
updated to read `rate` when the fetcher is updated, in the same PR.

---

## Orphan files / scripts deleted on 2026-04-21

- `shared/data/vehicle-pricing.json` — 193-byte fallback stub, not read
  by any shipped frontend code. Removed.
- `scripts/export-dtc-data.py` — schema mismatch with committed
  `dtc-database.json`. Removed.
- `scripts/export-repair-costs.py` — schema mismatch with committed
  `repair-costs.json`. Removed.
- `scripts/export-vehicle-data.py` — only wrote `vehicle-pricing.json`
  (now deleted). Removed.

**Consequence:** `.github/workflows/data-export.yml` now references three
non-existent scripts. The workflow must be disabled or rewritten before
its next scheduled run. Owner: devops-conductor.

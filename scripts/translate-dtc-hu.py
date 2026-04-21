#!/usr/bin/env python3
"""
translate-dtc-hu.py — Apply Hungarian translations to shared/data/dtc-database.json.

Wave 2 (2026-04-21): translate the top-50 highest-frequency DTCs to Hungarian so
the UI can show proper HU for common codes, keeping the `[EN] ` fallback marker
only for the long tail.

Wave 3 (2026-04-21, --pattern-auto): pattern-based bulk translation of the long
tail (4889 remaining codes). Uses a curated glossary of automotive diagnostic
terminology and greedy longest-match replacement. Only writes entries whose
coverage ratio (glossary-matched chars / total alphabetic chars) >= threshold
(default 0.60) — low-coverage entries stay null so the UI renders `[EN] ` fallback.

Schema contract (see shared/data/README.md):
  - Per-code: {en, hu, category, generic, severity}
  - _meta.hu_coverage_percent updated to reflect % of entries with non-null `hu`
  - en field is NEVER overwritten (preserve authoritative source)
  - Only keys listed in TRANSLATIONS (or, in --pattern-auto mode, entries that
    pass the coverage threshold) are touched.
  - --pattern-auto NEVER overwrites an existing non-null hu (the 46 manual
    Wave-2 translations are always preserved).

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
    python3 scripts/translate-dtc-hu.py                # apply manual TRANSLATIONS
    python3 scripts/translate-dtc-hu.py --dry-run      # preview only
    python3 scripts/translate-dtc-hu.py --force        # overwrite existing hu
    python3 scripts/translate-dtc-hu.py --check        # CI: exit 0 iff up-to-date
    python3 scripts/translate-dtc-hu.py --pattern-auto            # bulk translate
    python3 scripts/translate-dtc-hu.py --pattern-auto --dry-run  # preview bulk
    python3 scripts/translate-dtc-hu.py --pattern-auto --coverage-threshold 0.7
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


# ---------------------------------------------------------------------------
# Wave 3 — Pattern-based bulk translator glossary
# ---------------------------------------------------------------------------
# Sources for terminology:
#   - SAE J2012 (DTC Definitions) — English canonical source
#   - Bosch Hivatalos Autóelektronika szakszótár (HU)
#   - Jármű-diagnosztika szakkifejezések (MSZT terminology)
#   - Existing Wave-2 manual translations (TRANSLATIONS dict above)
#
# Rules for entries:
#   - Multi-word entries MUST come before their sub-words (longest match wins)
#   - Keep canonical English abbreviations in parentheses when they're standard
#     industry jargon mechanics recognize: ECM, PCM, TCM, ABS, EGR, EVAP, MAF, MAP
#   - Avoid over-specific translations — prefer literal mechanic-readable HU
#   - Case-sensitive matches where case carries meaning ("A", "B" sensor IDs)
#   - Do NOT invent — if a phrase is not in glossary, coverage will drop and the
#     entry will remain null (the safest failure mode).
GLOSSARY_PHRASES: list[tuple[str, str]] = [
    # --- 5-word phrases (highest priority, most specific) ---
    ("SCP (J1850) Invalid or Missing Data for Primary Id",
     "SCP (J1850) érvénytelen vagy hiányzó adat – elsődleges azonosító"),
    ("Invalid or Missing Data for Primary Id",
     "érvénytelen vagy hiányzó adat az elsődleges azonosítóhoz"),
    ("Invalid or Missing Data for",
     "érvénytelen vagy hiányzó adat –"),
    ("Invalid Data Received From",
     "érvénytelen adat érkezett a(z)"),
    ("Lost Communication With",
     "kommunikáció megszakadt a(z)"),

    # --- 4-word phrases ---
    ("Circuit Short To Battery", "áramkör – rövidzárlat akkumulátorra"),
    ("Circuit Short to Battery", "áramkör – rövidzárlat akkumulátorra"),
    ("Circuit Short To Ground", "áramkör – rövidzárlat testre"),
    ("Circuit Short to Ground", "áramkör – rövidzárlat testre"),
    ("Short Circuit To Battery", "rövidzárlat akkumulátorra"),
    ("Short Circuit To Ground", "rövidzárlat testre"),
    ("Short Circuit to Battery", "rövidzárlat akkumulátorra"),
    ("Short Circuit to Ground", "rövidzárlat testre"),
    ("Circuit Range/Performance Problem",
     "áramkör tartomány/működés hiba"),
    ("Exhaust Gas Temperature Sensor",
     "kipufogógáz-hőmérséklet érzékelő"),
    ("Secondary Air Injection System",
     "szekunder levegőbefújás rendszer"),
    ("Pressure Control Solenoid", "nyomásszabályozó mágnesszelep"),
    ("Intake Manifold Runner Control",
     "szívócsőcsatorna szabályozó"),
    ("Transmission Fluid Pressure Sensor/Switch",
     "sebességváltó-nyomás érzékelő/kapcsoló"),
    ("Vehicle Communication Bus", "jármű kommunikációs busz"),

    # --- 3-word phrases ---
    ("Short To Battery", "rövidzárlat akkumulátorra"),
    ("Short to Battery", "rövidzárlat akkumulátorra"),
    ("Short To Ground", "rövidzárlat testre"),
    ("Short to Ground", "rövidzárlat testre"),
    ("Short to Vbatt", "rövidzárlat akkumulátorra"),
    ("Sensor Circuit Low", "érzékelő áramkör – alacsony jel"),
    ("Sensor Circuit High", "érzékelő áramkör – magas jel"),
    ("Sensor Circuit Intermittent",
     "érzékelő áramkör – időszakos jel"),
    ("Sensor Circuit Failure", "érzékelő áramkör hiba"),
    ("Sensor Circuit Malfunction", "érzékelő áramkör hiba"),
    ("Control Circuit Low", "vezérlő áramkör – alacsony jel"),
    ("Control Circuit High", "vezérlő áramkör – magas jel"),
    ("Control Circuit Failure", "vezérlő áramkör hiba"),
    ("Control Circuit Malfunction", "vezérlő áramkör hiba"),
    ("Control Circuit Intermittent", "vezérlő áramkör – időszakos jel"),
    ("Control Circuit/Open", "vezérlő áramkör / szakadás"),
    ("Control Circuit Open", "vezérlő áramkör – szakadás"),
    ("Switch Circuit Low", "kapcsoló áramkör – alacsony jel"),
    ("Switch Circuit High", "kapcsoló áramkör – magas jel"),
    ("Switch Circuit Failure", "kapcsoló áramkör hiba"),
    ("Switch Circuit Open", "kapcsoló áramkör – szakadás"),
    ("Input Circuit Low", "bemeneti áramkör – alacsony jel"),
    ("Input Circuit High", "bemeneti áramkör – magas jel"),
    ("Input Circuit Failure", "bemeneti áramkör hiba"),
    ("Input Circuit Open", "bemeneti áramkör – szakadás"),
    ("Input Circuit Malfunction", "bemeneti áramkör hiba"),
    ("Output Circuit Low", "kimeneti áramkör – alacsony jel"),
    ("Output Circuit High", "kimeneti áramkör – magas jel"),
    ("Output Circuit Failure", "kimeneti áramkör hiba"),
    ("Output Circuit Open", "kimeneti áramkör – szakadás"),
    ("Output Circuit Malfunction", "kimeneti áramkör hiba"),
    ("Relay Circuit Failure", "relé áramkör hiba"),
    ("Relay Circuit Open", "relé áramkör – szakadás"),
    ("Circuit Low Voltage", "áramkör – alacsony feszültség"),
    ("Circuit High Voltage", "áramkör – magas feszültség"),
    ("Circuit Low Input", "áramkör – alacsony bemeneti jel"),
    ("Circuit High Input", "áramkör – magas bemeneti jel"),
    ("Signal Circuit Failure", "jel áramkör hiba"),
    ("Signal Circuit Open", "jel áramkör – szakadás"),
    ("Circuit Low Bank 1", "áramkör – alacsony jel (1. hengersor)"),
    ("Circuit Low Bank 2", "áramkör – alacsony jel (2. hengersor)"),
    ("Circuit High Bank 1", "áramkör – magas jel (1. hengersor)"),
    ("Circuit High Bank 2", "áramkör – magas jel (2. hengersor)"),
    ("Bank 1 Sensor 1", "1. hengersor, 1. szonda"),
    ("Bank 1 Sensor 2", "1. hengersor, 2. szonda"),
    ("Bank 1 Sensor 3", "1. hengersor, 3. szonda"),
    ("Bank 2 Sensor 1", "2. hengersor, 1. szonda"),
    ("Bank 2 Sensor 2", "2. hengersor, 2. szonda"),
    ("Bank 2 Sensor 3", "2. hengersor, 3. szonda"),
    ("Circuit Range/Performance", "áramkör tartomány/működés"),
    ("Sensor A Circuit", "„A” érzékelő áramkör"),
    ("Sensor B Circuit", "„B” érzékelő áramkör"),
    ("Sensor C Circuit", "„C” érzékelő áramkör"),
    ("Sensor D Circuit", "„D” érzékelő áramkör"),
    ("Control Module Input", "vezérlőegység bemenet"),
    ("Control Module Ground", "vezérlőegység test"),
    ("Air Bag Memory", "légzsák memória"),
    ("Air Suspension", "légrugózás"),
    ("Crankshaft Position Sensor", "főtengely-helyzetérzékelő"),
    ("Camshaft Position Sensor", "vezérműtengely-helyzetérzékelő"),
    ("Wheel Speed Sensor", "kerékfordulatszám-érzékelő"),
    ("Vehicle Speed Sensor", "jármű-sebességérzékelő"),
    ("Throttle Position Sensor", "fojtószelep-helyzetérzékelő"),
    ("Intake Air Temperature", "szívott levegő hőmérséklete"),
    ("Mass Air Flow", "levegőtömeg-áramlás"),
    ("Ignition Coil", "gyújtótekercs"),
    ("Fuel Pump", "üzemanyagszivattyú"),
    ("Fuel Rail Pressure", "üzemanyag-nyomás (rail)"),
    ("Fuel Pressure Sensor", "üzemanyag-nyomás érzékelő"),
    ("Oil Pressure Sensor", "olajnyomás-érzékelő"),
    ("Coolant Temperature Sensor", "hűtőfolyadék-hőmérséklet érzékelő"),
    ("Evaporative Emission Control", "üzemanyaggőz-szabályozás"),
    ("Evaporative Emission System", "üzemanyaggőz-visszatartó rendszer"),
    ("Exhaust Gas Recirculation", "kipufogógáz-visszavezetés (EGR)"),
    ("Catalyst System Efficiency", "katalizátor hatásfoka"),
    ("Turn Signal Circuit", "index áramkör"),
    ("Brake Pedal Position", "fékpedál helyzet"),
    ("Brake Switch Circuit", "féklámpakapcsoló áramkör"),
    ("Cruise Control Signal", "tempomat jel"),
    ("Cruise Control Switch", "tempomat kapcsoló"),
    ("Transmission Control Module", "sebességváltó-vezérlő (TCM)"),
    ("Transfer Case", "elosztómű"),

    # --- 2-word phrases ---
    ("Range/Performance", "tartomány/működés"),
    ("Circuit Short", "áramkör – rövidzárlat"),
    ("Circuit Failure", "áramkör hiba"),
    ("Circuit Malfunction", "áramkör hiba"),
    ("Circuit Open", "áramkör – szakadás"),
    ("Circuit Low", "áramkör – alacsony jel"),
    ("Circuit High", "áramkör – magas jel"),
    ("Circuit Intermittent", "áramkör – időszakos jel"),
    ("Circuit Performance", "áramkör működési hiba"),
    ("Low Input", "alacsony bemeneti jel"),
    ("High Input", "magas bemeneti jel"),
    ("Low Voltage", "alacsony feszültség"),
    ("High Voltage", "magas feszültség"),
    ("Low Bank", "alacsony jel – hengersor"),
    ("High Bank", "magas jel – hengersor"),
    ("Bank 1", "1. hengersor"),
    ("Bank 2", "2. hengersor"),
    ("Bank 3", "3. hengersor"),
    ("Bank 4", "4. hengersor"),
    ("Sensor 1", "1. szonda"),
    ("Sensor 2", "2. szonda"),
    ("Sensor 3", "3. szonda"),
    ("Sensor 4", "4. szonda"),
    ("Sensor A", "„A” érzékelő"),
    ("Sensor B", "„B” érzékelő"),
    ("Sensor C", "„C” érzékelő"),
    ("Sensor D", "„D” érzékelő"),
    ("Unit 1", "1. egység"),
    ("Unit 2", "2. egység"),
    ("Unit 3", "3. egység"),
    ("Cylinder 1", "1. henger"),
    ("Cylinder 2", "2. henger"),
    ("Cylinder 3", "3. henger"),
    ("Cylinder 4", "4. henger"),
    ("Cylinder 5", "5. henger"),
    ("Cylinder 6", "6. henger"),
    ("Cylinder 7", "7. henger"),
    ("Cylinder 8", "8. henger"),
    ("Cylinder 9", "9. henger"),
    ("Cylinder 10", "10. henger"),
    ("Cylinder 11", "11. henger"),
    ("Cylinder 12", "12. henger"),
    ("Control Module", "vezérlőegység"),
    ("Control System", "szabályozó rendszer"),
    ("Control Solenoid", "szabályozó mágnesszelep"),
    ("Control Circuit", "vezérlő áramkör"),
    ("Sensor Circuit", "érzékelő áramkör"),
    ("Switch Circuit", "kapcsoló áramkör"),
    ("Input Circuit", "bemeneti áramkör"),
    ("Output Circuit", "kimeneti áramkör"),
    ("Relay Circuit", "relé áramkör"),
    ("Signal Circuit", "jel áramkör"),
    ("Heater Circuit", "fűtő áramkör"),
    ("Motor Circuit", "motor áramkör"),
    ("Injector Circuit", "befecskendező áramkör"),
    ("Lamp Circuit", "lámpa áramkör"),
    ("Valve Control", "szelepszabályozás"),
    ("Pressure Control", "nyomásszabályozás"),
    ("Pressure Sensor", "nyomásérzékelő"),
    ("Pressure Switch", "nyomáskapcsoló"),
    ("Position Sensor", "helyzetérzékelő"),
    ("Position Switch", "helyzetkapcsoló"),
    ("Speed Sensor", "sebességérzékelő"),
    ("Temperature Sensor", "hőmérséklet-érzékelő"),
    ("Temperature Switch", "hőmérséklet-kapcsoló"),
    ("Level Sensor", "szintérzékelő"),
    ("Level Switch", "szintkapcsoló"),
    ("Flow Sensor", "áramlásérzékelő"),
    ("Voltage Sensor", "feszültségérzékelő"),
    ("Current Sensor", "áramérzékelő"),
    ("Oxygen Sensor", "lambdaszonda"),
    ("O2 Sensor", "lambdaszonda"),
    ("HO2S Heater", "lambdaszonda fűtés"),
    ("HO2S Circuit", "lambdaszonda áramkör"),
    ("Knock Sensor", "kopogásérzékelő"),
    ("Wheel Speed", "kerékfordulatszám"),
    ("Vehicle Speed", "járműsebesség"),
    ("Engine Speed", "fordulatszám"),
    ("Engine RPM", "motor fordulatszám"),
    ("Engine Coolant", "motor hűtőfolyadék"),
    ("Coolant Temperature", "hűtőfolyadék-hőmérséklet"),
    ("Coolant Level", "hűtőfolyadékszint"),
    ("Coolant Thermostat", "hűtőfolyadék termosztát"),
    ("Oil Pressure", "olajnyomás"),
    ("Oil Temperature", "olajhőmérséklet"),
    ("Oil Level", "olajszint"),
    ("Fuel Pressure", "üzemanyag-nyomás"),
    ("Fuel Temperature", "üzemanyag-hőmérséklet"),
    ("Fuel Level", "üzemanyagszint"),
    ("Fuel Injection", "üzemanyag-befecskendezés"),
    ("Fuel Injector", "üzemanyag-befecskendező"),
    ("Fuel Cap", "üzemanyag-tanksapka"),
    ("Fuel Trim", "keverékszabályozás"),
    ("Air Flow", "levegőáramlás"),
    ("Air Pressure", "levegőnyomás"),
    ("Air Temperature", "levegőhőmérséklet"),
    ("Air Filter", "levegőszűrő"),
    ("Air Pump", "levegőszivattyú"),
    ("Air Valve", "levegőszelep"),
    ("Air Intake", "levegőbeszívás"),
    ("Air Bag", "légzsák"),
    ("Air Injection", "levegőbefújás"),
    ("Air Suspension", "légrugózás"),
    ("Intake Manifold", "szívócső"),
    ("Intake Valve", "szívószelep"),
    ("Exhaust Valve", "kipufogószelep"),
    ("Exhaust Gas", "kipufogógáz"),
    ("Exhaust Manifold", "kipufogócső"),
    ("Exhaust Pressure", "kipufogónyomás"),
    ("Exhaust Temperature", "kipufogóhőmérséklet"),
    ("Ignition Switch", "gyújtáskapcsoló"),
    ("Ignition Timing", "gyújtásidőzítés"),
    ("Ignition Control", "gyújtásszabályozás"),
    ("Spark Plug", "gyújtógyertya"),
    ("Misfire Detected", "gyújtáskimaradás észlelve"),
    ("Spark Test", "gyújtás teszt"),
    ("Cylinder Misfire", "hengeres gyújtáskimaradás"),
    ("Throttle Body", "fojtószeleptest"),
    ("Throttle Actuator", "fojtószelep-állító"),
    ("Throttle Position", "fojtószelep-helyzet"),
    ("Throttle Pedal", "gázpedál"),
    ("Accelerator Pedal", "gázpedál"),
    ("Idle Control", "alapjárati szabályozás"),
    ("Idle Air", "alapjárati levegő"),
    ("Idle Speed", "alapjárati fordulatszám"),
    ("Brake Pedal", "fékpedál"),
    ("Brake Switch", "féklámpakapcsoló"),
    ("Brake Light", "féklámpa"),
    ("Brake Fluid", "fékfolyadék"),
    ("Brake Pressure", "féknyomás"),
    ("Clutch Pedal", "kuplungpedál"),
    ("Clutch Switch", "kuplungkapcsoló"),
    ("Gear Shift", "sebességváltás"),
    ("Gear Ratio", "áttétel"),
    ("Shift Solenoid", "váltó mágnesszelep"),
    ("Shift Lever", "váltókar"),
    ("Shift Switch", "váltó kapcsoló"),
    ("Power Steering", "szervokormány"),
    ("Power Window", "elektromos ablakemelő"),
    ("Power Mirror", "elektromos tükör"),
    ("Power Seat", "elektromos ülés"),
    ("Power Supply", "tápellátás"),
    ("Rear Axle", "hátsó tengely"),
    ("Front Axle", "első tengely"),
    ("Transfer Case", "elosztómű"),
    ("Torque Converter", "hidraulikus nyomatékváltó"),
    ("Torque Management", "nyomatékvezérlés"),
    ("Seat Belt", "biztonsági öv"),
    ("Seat Horizontal", "ülés vízszintes"),
    ("Seat Vertical", "ülés függőleges"),
    ("Seat Motor", "ülésmotor"),
    ("Door Lock", "ajtózár"),
    ("Door Switch", "ajtókapcsoló"),
    ("Door Ajar", "nyitott ajtó"),
    ("Window Motor", "ablakmotor"),
    ("Window Switch", "ablakkapcsoló"),
    ("Window Up", "ablak felfelé"),
    ("Window Down", "ablak lefelé"),
    ("Wiper Motor", "ablaktörlő motor"),
    ("Wiper Switch", "ablaktörlő kapcsoló"),
    ("Wiper Park", "ablaktörlő nyugalmi helyzet"),
    ("Mirror Motor", "tükörmotor"),
    ("Mirror Switch", "tükörkapcsoló"),
    ("Parking Assist", "parkolássegítő"),
    ("Park Lamp", "helyzetjelző lámpa"),
    ("Parklamp Output", "helyzetjelző kimenet"),
    ("Park/Neutral", "P/N helyzet"),
    ("Tail Lamp", "hátsó lámpa"),
    ("Head Lamp", "fényszóró"),
    ("Fog Lamp", "ködlámpa"),
    ("Turn Signal", "index"),
    ("Hazard Switch", "vészvillogó kapcsoló"),
    ("Horn Switch", "kürt kapcsoló"),
    ("Radio Present", "rádió jelenlét"),
    ("Audio Voice", "audio hang"),
    ("Audio Remote", "audio távirányító"),
    ("Voice Module", "hangmodul"),
    ("Compass Module", "iránytű modul"),
    ("Climate Control", "klímavezérlő"),
    ("A/C Clutch", "klíma kompresszor kuplung"),
    ("A/C Compressor", "klímakompresszor"),
    ("A/C Pressure", "klíma nyomás"),
    ("A/C Refrigerant", "hűtőközeg"),
    ("Traction Control", "kipörgésgátló"),
    ("ABS Power", "ABS tápellátás"),
    ("ABS Wheel", "ABS kerék"),
    ("ABS Pump", "ABS szivattyú"),
    ("ABS Module", "ABS vezérlőegység"),
    ("Crash Sensor", "ütközésérzékelő"),
    ("Signal Link", "jelvezeték"),
    ("Reserved -", "fenntartott –"),
    ("Stuck Open", "nyitott helyzetben beragadt"),
    ("Stuck Closed", "zárt helyzetben beragadt"),
    ("Stuck High", "magas értéken beragadt"),
    ("Stuck Low", "alacsony értéken beragadt"),
    ("Too Lean", "túl szegény"),
    ("Too Rich", "túl dús"),
    ("Too High", "túl magas"),
    ("Too Low", "túl alacsony"),
    ("Too Few", "túl kevés"),
    ("Too Many", "túl sok"),
    ("Below Threshold", "küszöbérték alatt"),
    ("Above Threshold", "küszöbérték felett"),
    ("Not Responding", "nem válaszol"),
    ("Not Detected", "nem észlelhető"),
    ("Leak Detected", "szivárgás észlelve"),
    ("Small Leak", "kis szivárgás"),
    ("Large Leak", "nagy szivárgás"),
    ("Very Small Leak", "nagyon kis szivárgás"),
    ("Gross Leak", "jelentős szivárgás"),
    ("Memory Clear", "memóriatörlés"),
    ("Memory Position", "memória pozíció"),
    ("Out of Range", "tartományon kívül"),
    ("Battery Voltage", "akkumulátor-feszültség"),
    ("System Voltage", "rendszerfeszültség"),
    ("System Malfunction", "rendszer hiba"),
    ("System Failure", "rendszer hiba"),
    ("System Performance", "rendszer működési hiba"),
    ("System Too", "rendszer túl"),
    ("System Low", "rendszer alacsony"),
    ("System High", "rendszer magas"),
    ("Primary Id", "elsődleges azonosító"),
    ("Secondary Id", "másodlagos azonosító"),
    ("Front Left", "bal első"),
    ("Front Right", "jobb első"),
    ("Rear Left", "bal hátsó"),
    ("Rear Right", "jobb hátsó"),
    ("Driver Side", "vezetőoldal"),
    ("Passenger Side", "utasoldal"),
    ("Non SCP", "nem SCP"),
    ("Non-SCP", "nem-SCP"),

    # --- 1-word terms (lowest priority) ---
    ("Circuit", "áramkör"),
    ("Sensor", "érzékelő"),
    ("Switch", "kapcsoló"),
    ("Solenoid", "mágnesszelep"),
    ("Relay", "relé"),
    ("Motor", "motor"),
    ("Module", "modul"),
    ("Signal", "jel"),
    ("Voltage", "feszültség"),
    ("Current", "áram"),
    ("Ground", "test"),
    ("Battery", "akkumulátor"),
    ("Failure", "hiba"),
    ("Malfunction", "hiba"),
    ("Fault", "hiba"),
    ("Error", "hiba"),
    ("Open", "szakadás"),
    ("Short", "rövidzárlat"),
    ("Low", "alacsony jel"),
    ("High", "magas jel"),
    ("Input", "bemenet"),
    ("Output", "kimenet"),
    ("Intermittent", "időszakos"),
    ("Performance", "működés"),
    ("Range", "tartomány"),
    ("Valve", "szelep"),
    ("Pressure", "nyomás"),
    ("Temperature", "hőmérséklet"),
    ("Control", "szabályozó"),
    ("System", "rendszer"),
    ("Data", "adat"),
    ("Communication", "kommunikáció"),
    ("Received", "érkezett"),
    ("Missing", "hiányzó"),
    ("Invalid", "érvénytelen"),
    ("Lost", "megszakadt"),
    ("Fuel", "üzemanyag"),
    ("Air", "levegő"),
    ("Oil", "olaj"),
    ("Coolant", "hűtőfolyadék"),
    ("Cylinder", "henger"),
    ("Throttle", "fojtószelep"),
    ("Exhaust", "kipufogó"),
    ("Intake", "szívó"),
    ("Injector", "befecskendező"),
    ("Injection", "befecskendezés"),
    ("Ignition", "gyújtás"),
    ("Misfire", "gyújtáskimaradás"),
    ("Catalyst", "katalizátor"),
    ("Transmission", "sebességváltó"),
    ("Clutch", "kuplung"),
    ("Gear", "sebességfokozat"),
    ("Brake", "fék"),
    ("Steering", "kormány"),
    ("Speed", "sebesség"),
    ("Position", "helyzet"),
    ("Heater", "fűtő"),
    ("Lamp", "lámpa"),
    ("Bulb", "izzó"),
    ("Light", "világítás"),
    ("Door", "ajtó"),
    ("Window", "ablak"),
    ("Wiper", "ablaktörlő"),
    ("Mirror", "tükör"),
    ("Seat", "ülés"),
    ("Pump", "szivattyú"),
    ("Cap", "sapka"),
    ("Tank", "tartály"),
    ("Filter", "szűrő"),
    ("Flow", "áramlás"),
    ("Level", "szint"),
    ("Engine", "motor"),
    ("Wheel", "kerék"),
    ("Vehicle", "jármű"),
    ("Driver", "vezető"),
    ("Passenger", "utas"),
    ("Front", "elülső"),
    ("Rear", "hátsó"),
    ("Left", "bal"),
    ("Right", "jobb"),
    ("Side", "oldal"),
    ("Primary", "elsődleges"),
    ("Secondary", "másodlagos"),
    ("Bank", "hengersor"),
    ("Upstream", "katalizátor előtti"),
    ("Downstream", "katalizátor utáni"),
    ("Stuck", "beragadt"),
    ("Lean", "szegény"),
    ("Rich", "dús"),
    ("Leak", "szivárgás"),
    ("Detected", "észlelve"),
    ("Duration", "időtartam"),
    ("Ratio", "arány"),
    ("Feedback", "visszacsatolás"),
    ("Potentiometer", "potenciométer"),
    ("Actuator", "állító"),
    ("Coil", "tekercs"),
    ("Supply", "ellátás"),
    ("Increase", "növekedés"),
    ("Decrease", "csökkenés"),
    ("Insufficient", "elégtelen"),
    ("Excessive", "túlzott"),
    ("Correlation", "korreláció"),
    ("Biased", "eltolódott"),
    ("Erratic", "szabálytalan"),
    ("Crankshaft", "főtengely"),
    ("Camshaft", "vezérműtengely"),
    ("Manifold", "gyűjtőcső"),
    ("Compressor", "kompresszor"),
    ("Suspension", "felfüggesztés"),
    ("Alternator", "generátor"),
    ("Starter", "indítómotor"),
    ("Generator", "generátor"),
    ("Alternative", "alternatív"),
    ("Additive", "adalék"),
    ("Reductant", "redukáló (AdBlue)"),
    ("Particulate", "részecske"),
    ("Regeneration", "regeneráció"),
    ("Barometric", "barometrikus"),
    ("Doppler", "doppler"),
    ("Cruise", "tempomat"),
    ("Accel", "gyorsítás"),
    ("Acceleration", "gyorsulás"),
    ("Deceleration", "lassulás"),
    ("Identification", "azonosítás"),
    ("Number", "szám"),
    ("Memory", "memória"),
    ("Clear", "törlés"),
    ("Horizontal", "vízszintes"),
    ("Vertical", "függőleges"),
    ("Forward", "előre"),
    ("Rearward", "hátra"),
    ("Stalled", "elakadt"),
    ("Stopped", "leállt"),
    ("Self-Test", "öntesz"),
    ("Internal", "belső"),
    ("External", "külső"),
    ("Evaporative", "üzemanyaggőz"),
    ("Emission", "emisszió"),
    ("Emissions", "emissziós"),
    ("Resistance", "ellenállás"),
    ("Reserved", "fenntartott"),
    ("TBD", "meghatározandó"),
    ("Experimental", "kísérleti"),
    ("Pulses", "impulzusok"),
    ("Timing", "időzítés"),
    ("Reference", "referencia"),
    ("Resolution", "felbontás"),
    ("Sudden", "hirtelen"),
    ("Run", "üzem"),
    ("Start", "indítás"),
    ("Off", "ki"),
    ("Shut", "leállítás"),

    # --- Connectors / function words ---
    (" With ", " a(z) "),
    (" For ", " számára "),
    (" from ", " a(z) "),
    (" From ", " a(z) "),
    (" To ", " "),
    (" to ", " "),
    (" or ", " vagy "),
    (" and ", " és "),
    (" of ", " – "),
    (" Not ", " nem "),
    (" During ", " során "),

    # Preserve known acronyms as-is (identity mappings) so they count as covered
    ("SCP", "SCP"),
    ("J1850", "J1850"),
    ("ECM/PCM", "ECM/PCM"),
    ("ECM", "ECM"),
    ("PCM", "PCM"),
    ("TCM", "TCM"),
    ("ABS", "ABS"),
    ("EGR", "EGR"),
    ("EVAP", "EVAP"),
    ("MAF", "MAF"),
    ("MAP", "MAP"),
    ("IAT", "IAT"),
    ("ECT", "ECT"),
    ("RPM", "RPM"),
    ("EEC-IV", "EEC-IV"),
    ("TSS", "TSS"),
    ("ESO", "ESO"),
    ("HO2S", "HO2S"),
    ("LF", "bal első"),
    ("RF", "jobb első"),
    ("LR", "bal hátsó"),
    ("RR", "jobb hátsó"),
    ("A/C", "klíma"),
    ("EEC", "EEC"),
    ("PSD", "PSD"),
    ("CAN", "CAN"),
    ("ISS", "ISS"),
    ("OSS", "OSS"),
    ("DTC", "DTC"),
    ("EGI", "EGI"),
    ("CD", "CD"),
    ("DVD", "DVD"),
    ("DJ", "DJ"),
    ("FM", "FM"),
    ("AM", "AM"),
    ("BCM", "BCM"),
    ("ACM", "ACM"),
    ("SDM", "SDM"),
    ("GPS", "GPS"),
    ("Vbatt", "akkumulátor-feszültség"),
    ("Gnd", "test"),
    ("GND", "test"),

    # --- Added batch 2: fill gaps observed in near-threshold skips ---
    # Diesel / combustion terminology
    ("Glow Plug", "izzítógyertya"),
    ("Turbocharger Boost Sensor", "turbófeltöltő nyomásérzékelő"),
    ("Turbocharger Boost", "turbófeltöltő nyomás"),
    ("Turbocharger", "turbófeltöltő"),
    ("Boost Pressure", "feltöltőnyomás"),
    ("Boost Sensor", "nyomásérzékelő (turbó)"),
    ("Boost", "feltöltés"),
    ("Diesel Particulate Filter", "dízel részecskeszűrő"),
    ("Particulate Filter", "részecskeszűrő"),

    # Common secondary phrases
    ("Reference Voltage", "referenciafeszültség"),
    ("Negative Common", "közös negatív"),
    ("Positive Common", "közös pozitív"),
    ("Open Circuit", "szakadt áramkör"),
    ("Shorted", "rövidre zárt"),
    ("shorted", "rövidre zárt"),
    ("shorted to", "rövidre zárt"),
    ("Volume Regulator", "mennyiségszabályozó"),
    ("Fuel Volume", "üzemanyag-mennyiség"),
    ("Intermediate Speed Sensor", "köztes sebességérzékelő"),
    ("Intermediate Speed", "köztes fordulatszám"),
    ("Intermediate", "köztes"),
    ("Output Shaft Speed", "kihajtótengely-fordulatszám"),
    ("Input Shaft Speed", "behajtótengely-fordulatszám"),
    ("Input Shaft", "behajtótengely"),
    ("Output Shaft", "kihajtótengely"),

    # Body / lights
    ("Autolamp", "automata világítás"),
    ("Interior Lamp", "belső világítás"),
    ("Stop Lamp", "féklámpa"),
    ("Stop lamp", "féklámpa"),
    ("Stop Light", "féklámpa"),
    ("High Mount", "magasan szerelt"),
    ("Heated Windshield", "fűtött szélvédő"),
    ("Windshield", "szélvédő"),
    ("Solar Radiation Sensor", "napsugárzás-érzékelő"),
    ("Solar Radiation", "napsugárzás"),
    ("Solar", "nap"),
    ("Radiation", "sugárzás"),
    ("Decklid", "csomagtérajtó"),
    ("Tail Gate", "csomagtérajtó"),
    ("Tailgate", "csomagtérajtó"),
    ("Liftgate", "csomagtérajtó"),
    ("Trunk", "csomagtartó"),
    ("Hood", "motorháztető"),
    ("Release", "kioldás"),
    ("Released", "kioldva"),
    ("Latch", "zár"),
    ("Unlatch", "zárnyitás"),
    ("Switching", "kapcsolás"),
    ("Override", "felülbírálás"),
    ("Accessory Delay", "kiegészítő késleltetés"),
    ("Accessory", "kiegészítő"),
    ("Delay Increase", "késleltetés növelés"),
    ("Delay Decrease", "késleltetés csökkentés"),
    ("Delay", "késleltetés"),

    # Safety / restraints
    ("Seatbelt Driver", "vezetőoldali biztonsági öv"),
    ("Seatbelt Passenger", "utasoldali biztonsági öv"),
    ("Seatbelt", "biztonsági öv"),
    ("Pretensioner", "övfeszítő"),
    ("Air Bag Module", "légzsákmodul"),
    ("Detent", "rögzítő"),

    # Trim / assembly
    ("Park Brake", "rögzítőfék"),
    ("Parking Brake", "rögzítőfék"),
    ("Park/Brake", "rögzítőfék"),
    ("Park Switch", "rögzítőfék-kapcsoló"),
    ("Assembly", "egység"),
    ("Tone Ring", "jelzőgyűrű"),
    ("Tooth", "fog"),
    ("Center", "közép"),

    # HVAC
    ("Blower Motor", "fúvómotor"),
    ("Blower", "fúvó"),
    ("Heater Core", "fűtőradiátor"),
    ("Refrigerant", "hűtőközeg"),

    # Communication / modules
    ("Radio Transceiver", "rádió adó-vevő"),
    ("Personal Computer", "személyi számítógép"),
    ("Rear Lighting Control Module", "hátsó világítás vezérlőmodul"),
    ("Fuel Additive Control Module", "üzemanyag-adalék vezérlőmodul"),
    ("Alternative Fuel Control Module", "alternatív üzemanyag vezérlőmodul"),
    ("Starter / Generator Control Module", "indítómotor / generátor vezérlőmodul"),
    ("Transfer Case Control Module", "elosztómű vezérlőmodul"),
    ("Parking Assist Control Module", "parkolássegítő vezérlőmodul"),
    ("Throttle Actuator Control Module", "fojtószelep-állító vezérlőmodul"),
    ("Immobilizer", "indításgátló"),

    # Shift / transmission
    ("Downshift", "visszakapcsolás"),
    ("Upshift", "felkapcsolás"),
    ("Shift Fork", "váltóvilla"),
    ("Auto Shift", "automatikus váltás"),
    ("Manual Adaptive", "manuális adaptív"),

    # Flags / quality markers (low-value but common)
    ("Enabled", "engedélyezve"),
    ("Disabled", "letiltva"),
    ("Function", "funkció"),
    ("Feature", "funkció"),
    ("Features", "funkciók"),
    ("Personalization", "személyre szabás"),
    ("Exceeded", "meghaladva"),
    ("Movement", "mozgás"),
    ("Unrequested", "kéretlen"),
    ("Learning", "tanulás"),
    ("at Limit", "határértéken"),
    ("at limit", "határértéken"),
    ("Limit", "határérték"),
    ("Leakage", "szivárgás"),
    ("Hydraulic", "hidraulikus"),
    ("Unit", "egység"),
    ("Network", "hálózat"),
    ("Code", "kód"),
    ("code", "kód"),
    ("Codes", "kódok"),
    ("Interactive", "interaktív"),
    ("Manufacturer", "gyártó"),
    ("Controlled", "vezérelt"),
    ("Retained", "fenntartott"),
    ("Accessory Power", "kiegészítő tápellátás"),
    ("Current Sense", "áramérzékelés"),
    ("Voltage Sense", "feszültség-érzékelés"),
    ("Sense", "érzékelés"),

    # Sensor add-ons
    ("Accelerometer", "gyorsulásmérő"),

    # --- Added batch 3: remaining high-frequency terms ---
    ("Software Incompatibility", "szoftver-inkompatibilitás"),
    ("Incompatibility", "inkompatibilitás"),
    ("Software", "szoftver"),
    ("Anti-Theft", "lopásgátló"),
    ("Anti-Lock", "blokkolásgátló"),
    ("Theft", "lopás"),
    ("Anti", "ellen-"),
    ("Out of", "kívül –"),
    ("Incorrect", "hibás"),
    ("Self Test", "önteszt"),
    ("Self-test", "önteszt"),
    ("Lack of", "hiánya –"),
    ("Lack", "hiány"),
    ("Threshold", "küszöbérték"),
    ("Condition", "állapot"),
    ("Request", "kérés"),
    ("Calibration", "kalibráció"),
    ("Above", "felett"),
    ("Below", "alatt"),
    ("Knock", "kopogás"),
    ("Ckt", "áramkör"),
    ("Time", "idő"),
    ("Timer", "időzítő"),
    ("Timeout", "időtúllépés"),
    ("Contribution", "hozzájárulás"),
    ("Balance", "egyensúly"),
    ("Indicator", "jelző"),
    ("Failed", "nem sikerült"),
    ("Entry", "bemenet"),
    ("Illuminated Entry", "belső világítás"),
    ("Monitor", "felügyelet"),
    ("Disc", "lemez"),
    ("Disc Changer", "lemezcserélő"),
    ("Player", "lejátszó"),
    ("Changer", "cserélő"),
    ("Pedal", "pedál"),
    ("Indicates", "jelzi"),
    ("Fan", "ventilátor"),
    ("Beam", "fénysugár"),
    ("High Beam", "távolsági fényszóró"),
    ("Low Beam", "tompított fényszóró"),
    ("Reduction", "csökkentés"),
    ("Corner", "sarok"),
    ("Higher Than", "magasabb mint"),
    ("Lower Than", "alacsonyabb mint"),
    ("Higher", "magasabb"),
    ("Lower", "alacsonyabb"),
    ("Electrical", "elektromos"),
    ("Digital", "digitális"),
    ("Down", "le"),
    ("Up", "fel"),
    ("Key", "kulcs"),
    ("Select", "választó"),
    ("Mode", "mód"),
    ("Drive", "menet"),
    ("Neutral", "üres"),
    ("Expected", "várt"),
    ("Acknowledgment", "nyugtázás"),
    ("Programmed", "programozott"),
    ("Backlite", "hátsó szélvédő"),
    ("Hi/Low", "magas/alacsony"),
    ("Hi", "magas"),
    ("Headrest", "fejtámla"),
    ("Headlamp", "fényszóró"),
    ("Headlight", "fényszóró"),
    ("Aux", "kiegészítő"),
    ("Auxiliary", "kiegészítő"),
    ("Chime", "hangjelzés"),
    ("Medium", "közepes"),
    ("Warning", "figyelmeztető"),
    ("Forward", "előre"),
    ("Reverse", "hátramenet"),
    ("Park", "parkolási"),
    ("Test", "teszt"),
    ("Power", "tápellátás"),
    ("LAMP", "lámpa"),
    ("OUTPUT", "kimenet"),
    ("CIRCUIT", "áramkör"),
    ("INPUT", "bemenet"),
    ("SHORT", "rövidzárlat"),
    ("OPEN", "szakadás"),
    ("GROUND", "test"),
    ("BATTERY", "akkumulátor"),
    ("BEAM", "fényszóró"),
    ("Fluid", "folyadék"),
    ("Fluid Temperature", "folyadék hőmérséklet"),
    ("Fluid Pressure", "folyadék nyomás"),
    ("Fluid Level", "folyadékszint"),
    (" with ", " a(z) "),
    (" short ", " rövidzárlat "),
    (" sensor ", " érzékelő "),
    (" circuit ", " áramkör "),
    (" position ", " helyzet "),
    (" Temp ", " hőmérséklet "),
    (" Temp", " hőmérséklet"),
    ("Temp.", "hőmérséklet"),

    # --- Added batch 4: final polish — last stragglers ---
    ("Steering Column", "kormányoszlop"),
    ("Column", "oszlop"),
    ("Intermediate Shaft Speed Sensor",
     "köztes tengely fordulatszám-érzékelő"),
    ("Intermediate Shaft", "köztes tengely"),
    ("Drive Shaft", "kardántengely"),
    ("Shaft", "tengely"),
    ("Warm Up Catalyst", "felmelegítő katalizátor"),
    ("Warm Up", "bemelegítés"),
    ("Warm-up", "bemelegítés"),
    ("Washer Fluid", "szélvédőmosó-folyadék"),
    ("Washer", "szélvédőmosó"),
    ("Absolute Pressure", "abszolút nyomás"),
    ("Absolute", "abszolút"),
    ("Efficiency", "hatékonyság"),
    ("AC to DC Converter", "AC/DC átalakító"),
    ("DC to AC Converter", "DC/AC átalakító"),
    ("Converter", "átalakító"),
    ("Feed/Return", "ellátás/visszatérés"),
    ("Feed", "ellátás"),
    ("Return", "visszatérés"),
    ("Terminal", "csatlakozó"),
    ("Telltales", "visszajelzők"),
    ("Telltale", "visszajelző"),
    ("Bezel", "keret"),
    (" is ", " "),
    (" are ", " "),
    (" was ", " "),
    (" Not ", " nem "),
    (" not ", " nem "),

    # Door/body secondary
    ("Backup Lamp", "tolatólámpa"),
    ("Backup Light", "tolatólámpa"),
    ("Dome Lamp", "belső lámpa"),
    ("Dome Light", "belső lámpa"),
    ("Courtesy Lamp", "belső lámpa"),
    ("License Plate", "rendszámtábla"),
    ("Keyless Entry", "kulcsnélküli beléptető"),
    ("Remote Keyless", "távirányítós kulcsnélküli"),

    # Motor/engine misc
    ("Engine Oil", "motorolaj"),
    ("Engine Coolant Level", "hűtőfolyadékszint"),
    ("Idle Speed Control", "alapjárati fordulatszám-szabályozó"),
    ("Boost Controller", "feltöltésszabályozó"),
    ("Variable Valve Timing", "változó szelepvezérlés"),

    # Additional connectors we still miss
    (" by ", " által "),
    (" On ", " be "),
    (" Off ", " ki "),
    (" A ", " „A” "),
    (" B ", " „B” "),
    (" C ", " „C” "),
    (" D ", " „D” "),
    (" E ", " „E” "),
    (" F ", " „F” "),

    # Common single words observed stuck in output
    ("Amp", "erősítő"),
    ("Audio", "audio"),
    ("Radio", "rádió"),
    ("responding", "válaszol"),
    ("Responding", "válaszol"),
    ("Service", "szerviz"),
    ("Timer", "időzítő"),
    ("Regulator", "szabályozó"),
    ("Plug", "gyertya"),
    ("Probe", "szonda"),
    ("Thermistor", "termisztor"),
    ("Thermostat", "termosztát"),
    ("Oxygen", "oxigén"),
    ("Servo", "szervo"),
    ("Adaptive", "adaptív"),
    ("Manual", "manuális"),
    ("Auto", "automatikus"),
    ("Automatic", "automatikus"),
    ("Bus", "busz"),
    ("Ring", "gyűrű"),
]


def _build_greedy_regex(entries: list[tuple[str, str]]):
    """
    Compile entries into a single alternation regex sorted by length DESC so
    the longest phrase wins. Returns (compiled_regex, lookup_dict).

    Matching rules:
      - Case-sensitive (preserves 'Sensor A' vs 'sensor a')
      - Word-boundary-ish: we add \\b around alphabetic-only entries to avoid
        matching inside words ('Low' inside 'Yellow'). Multi-word entries that
        already include spaces don't need extra boundaries.
      - Entries that are just punctuation/spacers (e.g. ' To ') keep their
        surrounding whitespace — those are intentional.
    """
    import re as _re
    # Sort by length DESC, break ties by lexicographic for determinism
    entries_sorted = sorted(entries, key=lambda kv: (-len(kv[0]), kv[0]))
    lookup: dict[str, str] = {}
    parts: list[str] = []
    seen_keys: set[str] = set()
    for en, hu in entries_sorted:
        if en in seen_keys:
            continue  # silently dedupe — first (longest) wins
        seen_keys.add(en)
        lookup[en] = hu
        esc = _re.escape(en)
        # If the phrase starts/ends with an alnum char, guard with \b.
        # This prevents "Low" from matching inside "Flow".
        if en and en[0].isalnum():
            esc = r"\b" + esc
        if en and en[-1].isalnum():
            esc = esc + r"\b"
        parts.append(esc)
    pattern = _re.compile("|".join(parts))
    return pattern, lookup


_PHRASE_RE, _PHRASE_LOOKUP = _build_greedy_regex(GLOSSARY_PHRASES)


def translate_en_to_hu(en_text: str) -> Tuple[str | None, float]:
    """
    Pattern-translate an English DTC description to Hungarian.

    Returns:
        (hu_text, coverage_ratio) where coverage_ratio in [0.0, 1.0] measures
        the fraction of alphabetic characters in the *cleaned* source that
        were matched by the glossary. If < threshold, caller should skip.
        Returns (None, 0.0) only for empty input.

    Implementation:
      1. Normalize: collapse whitespace (tabs → space), strip trailing punct
      2. Greedy longest-match replacement via precompiled regex
      3. Measure coverage: sum of matched-chars / total-alphabetic-chars
      4. Post-process: clean double spaces, capitalize first letter
    """
    if not en_text or not en_text.strip():
        return None, 0.0

    import re as _re
    # Normalize whitespace (handles embedded \t in DB)
    cleaned = _re.sub(r"\s+", " ", en_text).strip()

    # Count alphabetic chars for coverage ratio baseline
    alpha_total = sum(1 for c in cleaned if c.isalpha())
    if alpha_total == 0:
        return None, 0.0

    # Greedy replacement with coverage tracking
    matched_alpha = [0]  # use list for closure mutation

    def repl(m: "_re.Match") -> str:
        token = m.group(0)
        matched_alpha[0] += sum(1 for c in token if c.isalpha())
        return _PHRASE_LOOKUP[token]

    hu_text = _PHRASE_RE.sub(repl, cleaned)

    coverage = matched_alpha[0] / alpha_total if alpha_total else 0.0

    # Tidy: collapse double spaces introduced by replacements
    hu_text = _re.sub(r"\s+", " ", hu_text).strip()
    # Strip standalone double-quote artifacts and duplicate dashes
    hu_text = _re.sub(r"\s+–\s+–\s+", " – ", hu_text)
    hu_text = _re.sub(r"\s+,", ",", hu_text)

    # Capitalize first char for presentation (Hungarian sentence case)
    if hu_text and hu_text[0].islower():
        hu_text = hu_text[0].upper() + hu_text[1:]

    return hu_text, coverage


def apply_pattern_translations(
    db: dict,
    coverage_threshold: float = 0.60,
    sample_size: int = 20,
) -> Tuple[list, list, list]:
    """
    Pattern-translate every entry with hu == null.

    Never overwrites existing non-null hu (safety: preserves Wave-2 manual work).

    Returns:
        (applied, skipped_low_coverage, samples)
        - applied: list of (code, en, hu, coverage)
        - skipped_low_coverage: list of (code, en, coverage) below threshold
        - samples: random 20 applied entries for spot-check reporting
    """
    import random as _random

    applied: list = []
    skipped_low_coverage: list = []

    for code, entry in db.items():
        if code.startswith("_"):
            continue
        if entry.get("hu"):
            continue  # Preserve existing translations (Wave-2 manual + anything else)
        en = entry.get("en") or ""
        hu, coverage = translate_en_to_hu(en)
        if hu is None or coverage < coverage_threshold:
            skipped_low_coverage.append((code, en, coverage))
            continue
        entry["hu"] = hu
        applied.append((code, en, hu, coverage))

    # Deterministic sample for reporting (seed for reproducibility)
    rng = _random.Random(42)
    samples = rng.sample(applied, min(sample_size, len(applied))) if applied else []

    return applied, skipped_low_coverage, samples


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


def print_pattern_summary(
    applied: list,
    skipped: list,
    samples: list,
    before: Tuple[int, int, float],
    after: Tuple[int, int, float],
    threshold: float,
) -> None:
    print("=" * 72)
    print(f"DTC Hungarian Pattern-Auto Translation — {date.today().isoformat()}")
    print("=" * 72)
    print(f"Coverage threshold : {threshold}")
    print(f"Applied            : {len(applied)} entries")
    print(f"Skipped (low cov.) : {len(skipped)} entries")
    print(f"HU coverage        : {before[0]}/{before[1]} ({before[2]}%) -> "
          f"{after[0]}/{after[1]} ({after[2]}%)")
    print()
    if samples:
        print("-- 20 random sample translations (spot-check) --")
        for code, en, hu, cov in samples:
            print(f"  {code} [cov={cov:.2f}]")
            print(f"    EN: {en}")
            print(f"    HU: {hu}")
    # Coverage distribution of skipped entries
    if skipped:
        buckets = {"0.00-0.20": 0, "0.20-0.40": 0, "0.40-0.60": 0}
        for _, _, cov in skipped:
            if cov < 0.20:
                buckets["0.00-0.20"] += 1
            elif cov < 0.40:
                buckets["0.20-0.40"] += 1
            else:
                buckets["0.40-0.60"] += 1
        print()
        print("-- Skipped (below threshold) coverage distribution --")
        for b, c in buckets.items():
            print(f"  {b}: {c}")
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
    ap.add_argument("--pattern-auto", action="store_true",
                    help="Wave 3: pattern-translate all hu==null entries.")
    ap.add_argument("--coverage-threshold", type=float, default=0.60,
                    help="Min coverage ratio to accept a pattern translation "
                         "(default: 0.60).")
    args = ap.parse_args()

    db = load_db(args.path)
    validate_schema(db)

    # -------- Wave 3 path: pattern-auto mode --------
    if args.pattern_auto:
        before = compute_coverage(db)
        applied, skipped, samples = apply_pattern_translations(
            db, coverage_threshold=args.coverage_threshold
        )
        after = compute_coverage(db)
        db["_meta"]["hu_coverage_percent"] = after[2]
        db["_meta"]["updated"] = date.today().isoformat()

        print_pattern_summary(applied, skipped, samples, before, after,
                              args.coverage_threshold)

        if args.dry_run:
            print("(dry-run: no file written)")
            return 0
        if applied:
            write_db_atomic(db, args.path)
            print(f"Wrote {args.path}")
        else:
            print("Nothing to write — no entries met coverage threshold.")
        return 0

    # -------- Wave 2 path: manual TRANSLATIONS dict --------
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

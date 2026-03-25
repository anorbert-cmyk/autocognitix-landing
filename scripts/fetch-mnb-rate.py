#!/usr/bin/env python3
"""
Fetch the official EUR/HUF exchange rate from the Magyar Nemzeti Bank (MNB).

Uses the MNB SOAP API (stdlib only, no pip dependencies).
Fallback chain: MNB SOAP -> ECB XML feed -> hardcoded recent rate.
"""

import json
import os
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import date

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# NOTE: The MNB SOAP endpoint only works over HTTP, not HTTPS.
# HTTPS returns 404. This is how the official WSDL defines the service address.
MNB_URL = "http://www.mnb.hu/arfolyamok.asmx"

MNB_SOAP_BODY = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:web="http://www.mnb.hu/webservices/">
  <soap:Header/>
  <soap:Body>
    <web:GetCurrentExchangeRates/>
  </soap:Body>
</soap:Envelope>"""

MNB_SOAP_ACTION = "http://www.mnb.hu/webservices/MNBArfolyamServiceSoap/GetCurrentExchangeRates"

ECB_DAILY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"

# Hardcoded fallback – update periodically
FALLBACK_RATE = 388.94
FALLBACK_DATE = "2026-03-25"

TIMEOUT_SECONDS = 15


# ---------------------------------------------------------------------------
# MNB SOAP API
# ---------------------------------------------------------------------------

def fetch_from_mnb() -> tuple[float, str, str]:
    """
    Call the MNB GetCurrentExchangeRates SOAP method.

    Returns (rate, date_str, source).
    Raises on failure.
    """
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": MNB_SOAP_ACTION,
    }
    req = urllib.request.Request(
        MNB_URL,
        data=MNB_SOAP_BODY.encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        raw = resp.read().decode("utf-8")

    # The SOAP response wraps the actual XML inside a <GetCurrentExchangeRatesResult> text node.
    # We need to extract that inner XML and parse it separately.
    # XXE Safety: Python 3's xml.etree.ElementTree does NOT resolve external entities by default,
    # so ET.fromstring() is safe against XXE attacks. If defusedxml is available, prefer it.
    try:
        import defusedxml.ElementTree as SafeET
        root = SafeET.fromstring(raw)
    except ImportError:
        root = ET.fromstring(raw)  # Python 3 ET is safe against XXE by default

    # Find the result element (namespace-agnostic search)
    result_text = None
    for elem in root.iter():
        if "GetCurrentExchangeRatesResult" in (elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag):
            result_text = elem.text
            break

    if not result_text:
        raise ValueError("GetCurrentExchangeRatesResult not found in MNB response")

    # Parse the inner XML which looks like:
    # <MNBCurrentExchangeRates>
    #   <Day date="2026-03-25">
    #     <Rate unit="1" curr="EUR">408,50</Rate>
    #     ...
    #   </Day>
    # </MNBCurrentExchangeRates>
    try:
        import defusedxml.ElementTree as SafeET
        inner = SafeET.fromstring(result_text)
    except ImportError:
        inner = ET.fromstring(result_text)  # Python 3 ET is safe against XXE by default

    for day in inner.iter("Day"):
        day_date = day.attrib.get("date", str(date.today()))
        for rate_elem in day.iter("Rate"):
            curr = rate_elem.attrib.get("curr", "")
            if curr == "EUR":
                # MNB uses comma as decimal separator
                rate_str = rate_elem.text.strip().replace(",", ".")
                return float(rate_str), day_date, "MNB"

    raise ValueError("EUR rate not found in MNB response")


# ---------------------------------------------------------------------------
# ECB fallback
# ---------------------------------------------------------------------------

def fetch_from_ecb() -> tuple[float, str, str]:
    """
    Fetch EUR/HUF from the ECB daily reference rates XML feed.

    The ECB publishes rates relative to EUR, so HUF is listed directly.
    Returns (rate, date_str, source).
    """
    req = urllib.request.Request(ECB_DAILY_URL)
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        raw = resp.read().decode("utf-8")

    # XXE Safety: Python 3 ET is safe by default; prefer defusedxml if available
    try:
        import defusedxml.ElementTree as SafeET
        root = SafeET.fromstring(raw)
    except ImportError:
        root = ET.fromstring(raw)  # Python 3 ET is safe against XXE by default

    # ECB namespaces
    ns = {
        "gesmes": "http://www.gesmes.org/xml/2002-08-01",
        "ecb": "http://www.ecb.int/vocabulary/2002-08-01/euref",
    }

    # Structure: <Cube><Cube time="2026-03-25"><Cube currency="HUF" rate="408.50"/>...
    for time_cube in root.findall(".//ecb:Cube[@time]", ns):
        cube_date = time_cube.attrib["time"]
        for cube in time_cube.findall("ecb:Cube", ns):
            if cube.attrib.get("currency") == "HUF":
                return float(cube.attrib["rate"]), cube_date, "ECB"

    raise ValueError("HUF rate not found in ECB response")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def get_eur_huf_rate() -> tuple[float, str, str]:
    """
    Fetch today's EUR/HUF rate with fallback chain.

    Returns (rate, date_str, source).
    """
    # 1) Try MNB
    try:
        rate, rate_date, source = fetch_from_mnb()
        print(f"[OK] Fetched from MNB: {rate} ({rate_date})")
        return rate, rate_date, source
    except Exception as e:
        print(f"[WARN] MNB fetch failed: {e}", file=sys.stderr)

    # 2) Try ECB
    try:
        rate, rate_date, source = fetch_from_ecb()
        print(f"[OK] Fetched from ECB: {rate} ({rate_date})")
        return rate, rate_date, source
    except Exception as e:
        print(f"[WARN] ECB fetch failed: {e}", file=sys.stderr)

    # 3) Hardcoded fallback
    print(f"[WARN] Using hardcoded fallback rate: {FALLBACK_RATE} ({FALLBACK_DATE})")
    return FALLBACK_RATE, FALLBACK_DATE, "hardcoded_fallback"


def main() -> None:
    rate, rate_date, source = get_eur_huf_rate()
    print(f"\nEUR/HUF rate: {rate}")
    print(f"Date: {rate_date}")
    print(f"Source: {source}")

    # Resolve output path relative to the project root (parent of scripts/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_path = os.path.join(project_root, "shared", "data", "exchange-rate.json")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    payload = {
        "EUR_HUF": rate,
        "date": rate_date,
        "source": source,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()

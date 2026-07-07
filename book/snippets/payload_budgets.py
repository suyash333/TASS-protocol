#!/usr/bin/env python3
"""
Chapter 11 companion — does the record fit the channel?

Computes exact byte/character costs for every constrained channel in
Ch. 11 — LoRaWAN, SMS, USSD, QR, NFC, URL — for TASS (signed and
unsigned) vs minified JSON of the same fields.

    python book/snippets/payload_budgets.py
"""

import json
import urllib.parse

from tass.crypto import TASSSigner, derive_key

# ── The records from the chapter ──────────────────────────────────────

CASES = {
    "IoT soil sensor (11.2)": (
        "~n:a3 ~t:23.4 ~m:31 ~p:6.8 ~b:87 ~s:ok",
        {"node_id": "a3", "soil_temp_c": 23.4, "moisture_pct": 31,
         "ph": 6.8, "battery_pct": 87, "status": "ok"},
    ),
    "Mobile-money SMS (11.3)": (
        "~x:p ~a:1450 ~c:KES ~r:254712345678 ~i:TX88412 ~s:ok",
        {"type": "p", "amount": 1450, "currency": "KES",
         "recipient": "254712345678", "tx_id": "TX88412", "status": "ok"},
    ),
    "Equipment QR tag (11.4)": (
        "~i:EQ-4471 ~k:pump ~l:B2 ~d:2026-03",
        {"asset_id": "EQ-4471", "kind": "pump", "location": "B2",
         "service_due": "2026-03"},
    ),
    "URL filter state (11.6)": (
        "~s:electronics ~x:100 ~y:500 ~o:pd",
        {"category": "electronics", "price_min": 100,
         "price_max": 500, "order": "pd"},
    ),
}

BUDGETS = [
    ("LoRaWAN DR0 (smallest)", 51),
    ("NFC NTAG213 usable", 137),
    ("SMS single segment", 160),
    ("USSD response", 182),
    ("LoRaWAN DR4+", 222),
]

signer = TASSSigner(derive_key(b"demo-secret", context=b"budgets"))


def fits(n: int, budget: int) -> str:
    return "fits" if n <= budget else "OVER"


if __name__ == "__main__":
    for name, (tass_line, record) in CASES.items():
        signed = signer.sign_line(tass_line)
        jsn = json.dumps(record, separators=(",", ":"))
        print(f"\n{name}")
        print(f"  TASS          {len(tass_line):>4} B   {tass_line}")
        print(f"  TASS + ~! tag {len(signed):>4} B")
        print(f"  JSON          {len(jsn):>4} B   "
              f"(TASS ↓{(len(jsn) - len(tass_line)) / len(jsn):.0%})")
        for bname, budget in BUDGETS:
            print(f"    {bname:<24} {budget:>3} B : "
                  f"TASS {fits(len(tass_line), budget):<5} "
                  f"signed {fits(len(signed), budget):<5} "
                  f"JSON {fits(len(jsn), budget)}")

    # URL case: percent-encoding cost (space → '+')
    line, record = CASES["URL filter state (11.6)"]
    url_tass = urllib.parse.quote_plus(line)
    url_params = urllib.parse.urlencode(record)
    print(f"\nURL encoding (11.6)")
    print(f"  ?q={url_tass}   ({len(url_tass) + 3} chars, one param)")
    print(f"  ?{url_params}   ({len(url_params) + 1} chars, "
          f"{len(record)} params)")

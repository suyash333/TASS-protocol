#!/usr/bin/env python3
"""
Chapter 11 §11.5 companion — TASS as a structured-logging format:
a stdlib logging.Formatter that emits TASS lines, plus the read side
("store compact, view expanded", Ch. 9 §9.6) and a byte comparison.

    python book/snippets/tass_logger.py

The unit here is BYTES ON DISK, not tokens: log volume × replicas ×
retention is the bill.
"""

import io
import json
import logging
import time

from tass import SchemaCompiler, TASSParser

# ── The log schema, compiled like any other TASS schema ───────────────

LOG_SCHEMA = {
    "ts":    "integer",   # unix time
    "level": "string",    # i|w|e  (codes: info/warn/error)
    "event": "string",    # short event code
    "user":  "string",
    "route": "string",
    "ms":    "integer",   # duration
}
LEVEL_CODES = {"INFO": "i", "WARNING": "w", "ERROR": "e"}
PARSER_MAP, _ = SchemaCompiler().compile(LOG_SCHEMA)
SYMBOLS = {field: sym for sym, (field, _t) in PARSER_MAP.items()}


class TASSLogFormatter(logging.Formatter):
    """Emit one TASS record per log call. Fields come via `extra=`."""

    def format(self, record: logging.LogRecord) -> str:
        fields = {
            "ts": int(record.created),
            "level": LEVEL_CODES.get(record.levelname, "i"),
            "event": record.getMessage(),
            "user": getattr(record, "user", "-"),
            "route": getattr(record, "route", "-"),
            "ms": getattr(record, "ms", 0),
        }
        return " ".join(f"~{SYMBOLS[k]}:{v}" for k, v in fields.items())


# ── Write side ────────────────────────────────────────────────────────

stream = io.StringIO()
handler = logging.StreamHandler(stream)
handler.setFormatter(TASSLogFormatter())
log = logging.getLogger("checkout")
log.addHandler(handler)
log.setLevel(logging.INFO)

log.info("co_start", extra={"user": "u_812", "route": "/pay", "ms": 0})
log.info("co_auth",  extra={"user": "u_812", "route": "/pay", "ms": 231})
log.error("co_fail", extra={"user": "u_812", "route": "/pay", "ms": 1204})

tass_lines = stream.getvalue().strip().splitlines()

# ── Read side: grep compact, view expanded ────────────────────────────

parser = TASSParser(dictionary_map=PARSER_MAP)
errors = [line for line in tass_lines if "~b:e" in line]        # "grep"
expanded = [parser.parse(line) for line in tass_lines]          # dashboard

# ── The bill: bytes vs an equivalent JSON logger ──────────────────────

json_lines = [json.dumps({**r, "level": {"i": "info", "w": "warning",
                                          "e": "error"}[r["level"]]},
                         separators=(",", ":")) for r in expanded]
tass_bytes = sum(len(l) for l in tass_lines)
json_bytes = sum(len(l) for l in json_lines)

if __name__ == "__main__":
    print("wire format (what disk sees):")
    for line in tass_lines:
        print("  " + line)
    print("\nexpanded view (what the dashboard sees):")
    for rec in expanded:
        print("  ", rec)
    print(f"\ngrep '~b:e' found {len(errors)} error line(s) on the raw log")
    print(f"\nbytes: TASS {tass_bytes}  vs JSON {json_bytes}  "
          f"(↓{(json_bytes - tass_bytes) / json_bytes:.0%} — compounds across "
          f"replicas × shippers × retention days)")

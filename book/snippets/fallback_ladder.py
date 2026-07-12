#!/usr/bin/env python3
"""
Chapters 5/9 companion — the fallback ladder with rung metrics and the
circuit-breaker signal.

    python book/snippets/fallback_ladder.py

The `ladder()` function is the production shape; `FLAKY_RESPONSES` simulates
a model with every failure class from Ch. 5's taxonomy.
"""

import collections
import json

from tass import SchemaCompiler, TASSParser, TASSParseError, TASSValidationError

SCHEMA = {"user_intent": "string", "urgency_level": "integer",
          "requires_routing": "boolean"}
PARSER_MAP, _ = SchemaCompiler().compile(SCHEMA)
PARSER = TASSParser(dictionary_map=PARSER_MAP)

RUNG_COUNTS = collections.Counter()          # → your metrics system
BREAKER_THRESHOLD = 0.05                     # rung-2+ rate that pages a human


def ladder(call_llm, call_llm_json, input_text: str) -> dict | None:
    """Four rungs (Ch. 5 §5.7). Returns a record or None (dead-letter)."""
    # Rung 1: parse what we got
    try:
        rec = PARSER.safe_parse(call_llm(input_text))
        PARSER.validate(rec)
        RUNG_COUNTS["r1_ok"] += 1
        return rec
    except (TASSParseError, TASSValidationError):
        pass

    # Rung 2: one retry, same TASS prompt (transient noise)
    try:
        rec = PARSER.safe_parse(call_llm(input_text))
        PARSER.validate(rec)
        RUNG_COUNTS["r2_retry_ok"] += 1
        return rec
    except (TASSParseError, TASSValidationError):
        pass

    # Rung 3: explicit JSON mode — pay full price this once
    try:
        rec = json.loads(call_llm_json(input_text))
        RUNG_COUNTS["r3_json_ok"] += 1
        return rec
    except (json.JSONDecodeError, TypeError):
        pass

    RUNG_COUNTS["r4_dead_letter"] += 1       # queue + alert in production
    return None


def breaker_tripped() -> bool:
    """Ch. 9 §9.5 — the ladder as circuit breaker."""
    total = sum(RUNG_COUNTS.values()) or 1
    beyond_r1 = total - RUNG_COUNTS["r1_ok"]
    return beyond_r1 / total > BREAKER_THRESHOLD


# ── Simulation: one of each failure class, then healthy traffic ───────

FLAKY_RESPONSES = iter(
    ["```\n~a:refund ~b:5 ~c:true\n```",              # F1 fences → rung 1
     "~a:cancel ~b:2.0 ~c:True",                       # F2 types  → rung 1
     "~a:upgrade",                                     # F3 missing → retry...
     "~a:upgrade ~b:1 ~c:false",                       #   → rung 2
     '{"user_intent":"question","urgency_level":3,"requires_routing":false}',  # F5 → rung 1 (safe_parse)
     ] + ["~a:question ~b:1 ~c:false"] * 45            # healthy traffic
)

if __name__ == "__main__":
    fake_llm = lambda _text: next(FLAKY_RESPONSES)
    fake_llm_json = lambda _text: '{"user_intent":"question","urgency_level":1,"requires_routing":false}'

    results = [ladder(fake_llm, fake_llm_json, f"ticket {i}") for i in range(49)]

    print("rung distribution :", dict(RUNG_COUNTS))
    print("records recovered :", sum(r is not None for r in results), "/", len(results))
    print("breaker tripped?  :", breaker_tripped(),
          f"(threshold {BREAKER_THRESHOLD:.0%})")

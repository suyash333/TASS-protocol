#!/usr/bin/env python3
"""
Chapter 1 companion — the annualized cost model, with measured token counts.

Edit SCHEMA, SAMPLE_RECORD, and PRICING for your workload, then:

    python book/snippets/cost_model.py

Uses tiktoken when available (exact), otherwise the labelled approximation.
"""

import json

# ── Edit these three blocks ───────────────────────────────────────────

SCHEMA = {
    "tier":      "string",
    "rate_low":  "integer",
    "rate_high": "integer",
    "gst":       "boolean",
}

SAMPLE_RECORD = {"tier": "micro", "rate_low": 18000, "rate_high": 42000, "gst": False}

PRICING = {
    "output_per_mtok": 10.00,   # $ per million output tokens
    "input_per_mtok":  3.00,    # $ per million input tokens
    "cache_discount":  0.90,    # cached-prefix discount (0.90 = 90% off)
    "calls_per_day":   100_000,
    "malformed_rate":  0.02,    # fallback-ladder rung-2 entry rate (Ch. 5)
}

# ── Measurement ───────────────────────────────────────────────────────

from tass import SchemaCompiler
from tass.benchmark import TASSBenchmark

parser_map, system_prompt = SchemaCompiler().compile(SCHEMA)
bench = TASSBenchmark(SCHEMA, [SAMPLE_RECORD])
results = {r.format_name: r.tokens for r in bench.run()}
t_json, t_tass = results["json"], results["tass"]
t_dict = bench._count_tokens(system_prompt)  # dictionary/prompt tax

# ── The model (Ch. 1 §1.4–1.6) ────────────────────────────────────────

P = PRICING
daily_out_saving = P["calls_per_day"] * (t_json - t_tass) * P["output_per_mtok"] / 1e6
daily_retry_tax = (
    P["calls_per_day"] * P["malformed_rate"] * t_json * P["output_per_mtok"] / 1e6
)
dict_price = P["input_per_mtok"] * (1 - P["cache_discount"])
daily_dict_tax = P["calls_per_day"] * t_dict * dict_price / 1e6
daily_net = daily_out_saving - daily_retry_tax - daily_dict_tax

print(f"Measured  : JSON {t_json} tok/record, TASS {t_tass} tok/record, "
      f"dictionary {t_dict} tok (cached)")
print(f"Daily     : save ${daily_out_saving:,.2f}  −retry ${daily_retry_tax:,.2f}"
      f"  −dict ${daily_dict_tax:,.2f}  = net ${daily_net:,.2f}")
print(f"Annual net: ${365 * daily_net:,.0f}"
      f"   ({(t_json - t_tass) / t_json:.0%} output-token reduction)")

if daily_net <= 0:
    print("\nNet is non-positive: below break-even (Ch. 1 §1.6). "
          "Raise volume, enable caching, or stay with JSON.")

# Chapter 1 — The Economics of Output Tokens

> *In which we establish that the problem is real, quantify it, and derive
> the conditions under which a compact output format pays for itself.*

## 1.1 The asymmetry nobody prices in

Every LLM API bill decomposes into two line items: input tokens and output
tokens. Across every major provider, output tokens cost a multiple of input
tokens — historically between 3× and 6×. The asymmetry is not arbitrary
pricing; it reflects the physics of inference. Input tokens are processed in
parallel in a single forward pass (*prefill*), while output tokens are
generated one at a time (*decode*), each requiring a full pass through the
model with an ever-growing KV cache. Prefill saturates the accelerator's
compute; decode saturates its memory bandwidth and holds the hardware
hostage for the duration of generation.

The consequence for pipeline design is blunt:

> **Latency and cost both scale with output length, and output length is
> the one variable the schema designer fully controls.**

You cannot make the model smarter per token. You *can* make every token
carry more information.

## 1.2 Where extraction pipelines spend

Consider the canonical high-volume workload TASS targets: fixed-schema
extraction. A classifier, a router, a scorer — anything of the shape
*"read this text, emit these N fields."* The response is pure structure:

```json
{"tier": "micro", "rate_low": 18000, "rate_high": 42000, "gst": false}
```

Tokenize that with `o200k_base` and count what you paid for:

| Token category | Examples | Share of output |
|---|---|---|
| Values (the information) | `micro`, `18000`, `false` | ~25–35% |
| Keys (known in advance) | `"tier"`, `"rate_low"` | ~35–45% |
| Syntax (pure ceremony) | `{`, `}`, `"`, `:`, `,` | ~25–35% |

Two thirds of the bill purchases nothing. The keys were fixed the moment
you designed the schema; the syntax exists so `JSON.parse` doesn't have to
think. In a machine-to-machine pipeline — no human ever reads the wire
format — this is dead weight at a 4–6× markup.

## 1.3 The information-theoretic floor

There is a floor below which no honest format can go: the entropy of the
values themselves. If a field takes one of four values (`nano | micro |
mid | macro`), the information content is 2 bits, and the practical floor
in a BPE token stream is **one token** — a short code like `mc`. TASS's
design goal is stated exactly in these terms:

> Spend approximately one token per value, plus approximately one token per
> field marker, and zero tokens on syntax.

For an N-field record the target is ≈ 2N + ε tokens. JSON for the same
record costs ≈ 6–9N. The ratio — not any particular percentage — is the
durable claim, robust across tokenizers, because both numerator and
denominator are measured in the same tokenizer.

## 1.4 A cost model you can argue with

Let:

- `C_out` — output price per million tokens
- `V` — calls per day
- `T_json`, `T_tass` — measured output tokens per record in each format

Annual saving:

```
S = 365 · V · (T_json − T_tass) · C_out / 10⁶
```

Worked example, deliberately mid-range (`C_out` = $10/M, a mid-tier 2025
model): the influencer-rate record above measures ~78 tokens as JSON and
~17 as TASS.

| Calls/day | JSON $/yr | TASS $/yr | Saved/yr |
|---:|---:|---:|---:|
| 10,000 | $2,847 | $620 | **$2,227** |
| 100,000 | $28,470 | $6,205 | **$22,265** |
| 1,000,000 | $284,700 | $62,050 | **$222,650** |

Run [`snippets/cost_model.py`](../snippets/cost_model.py) with your own
schema, volumes, and prices — it measures `T_json` and `T_tass` with the
real tokenizer rather than trusting this table.

There is a second, less visible saving: **decode latency**. At a typical
50–150 tokens/second decode rate, dropping 61 tokens per response removes
0.4–1.2 seconds of wall-clock latency per call — often worth more than the
money in interactive routing paths.

## 1.5 The costs on the other side of the ledger

A research-grade treatment prices the downsides too. TASS costs you:

1. **A system prompt tax.** The symbol dictionary adds ~50–150 input
   tokens. With prompt caching (Chapter 4) this amortizes to noise —
   cached input tokens are typically discounted 90%+ — but on providers
   without caching, very short conversations, or one-off calls, the tax
   can exceed the saving. **TASS is a high-volume instrument.**
2. **A reliability tax.** Models are heavily trained to emit JSON; some
   are constrained-decoded into it. TASS relies on instruction-following.
   Chapter 5 quantifies the observed failure modes (1–5% depending on
   model and schema size) and the mitigation ladder that recovers them.
3. **A debuggability tax.** `~t:mc ~l:18k` is hostile to a human reading
   logs at 2 a.m. Chapter 9's observability section addresses this with
   expand-on-ingest logging: store compact, view expanded.

## 1.6 The break-even inequality

Putting both sides together, TASS wins when:

```
V · (T_json − T_tass) · C_out            saving per day
    >
V · f · T_retry · C_total                retry overhead per day
  + P_cache_miss · T_dict · C_in · V     uncached dictionary tax
```

where `f` is the malformed-output rate and `T_retry` the cost of a fallback
call. With measured values (`f` ≈ 2%, retry in JSON mode, cached prompts)
the left side dominates by more than an order of magnitude for any schema
of 3+ fields. The inequality flips only when volume is low, caching is
unavailable, or the schema is so dynamic it changes per call — precisely
the "when not to use TASS" list in the README, now derived rather than
asserted.

## 1.7 Summary

- Output tokens are 4–6× input price and generated serially; they dominate
  both cost and latency in extraction workloads.
- In JSON output, roughly two thirds of tokens are keys and syntax whose
  content is known before the call is made.
- TASS targets ≈ 2 tokens per field against JSON's 6–9, a ratio that holds
  across tokenizers because it is measured, not assumed.
- The savings claim is conditional — high volume, fixed schema, cached
  prompts — and the break-even condition is explicit and computable.

*Next: why the tokenizer itself dictates the design of the format —
Chapter 2.*

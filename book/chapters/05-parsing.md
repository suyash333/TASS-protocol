# Chapter 5 — Parsing and Failure Modes

> *In which we treat the LLM as an unreliable transmitter, catalogue every
> way its output goes wrong, and build the receiver that survives all of
> them.*

## 5.1 The adversarial framing

The correct mental model for parsing LLM output is a noisy channel. The
transmitter is probabilistic, was trained mostly on *other* formats, and
occasionally decorates its output with apologies. A production parser is
therefore built like a protocol receiver: scan defensively, coerce
liberally, validate strictly, and always have a fallback.

`TASSParser` implements this in four layers, each independently testable.

## 5.2 Layer 1 — Cleaning (`_strip_markdown`)

The most common contamination is cosmetic: code fences and surrounding
prose.

```
Sure! Here is the extraction:
```
```text
~a:refund ~b:5 ~c:true
```

The cleaner strips fence markers, then — crucially — selects **the first
line that starts with the prefix character**. The `~` sentinel from
Chapter 2 pays its rent here: prose lines cannot begin with a field pair,
so line selection is structural, not heuristic.

## 5.3 Layer 2 — Scanning (`_parse_line`)

The scanner splits on whitespace and applies three filters per token:
must start with the prefix; must contain `:`; symbol must exist in the
dictionary. Everything else is *silently skipped* — stray words, unknown
symbols, the `~!` integrity tag (Chapter 8). This is Postel's law applied
deliberately: **liberal in scanning, strict in validation** (layer 4
catches what leniency lets through).

## 5.4 Layer 3 — Coercion (`_coerce`)

Wire values are untyped strings; the schema's type hints drive coercion:
integers and floats pass through `_expand_k` (`18k → 18000`,
`1.5k → 1500`), booleans accept `1/true/yes` case-insensitively, strings
pass through untouched. Coercion *absorbs* the "value type deviation"
failure class: a model that writes `~c:True` or `~b:5.0` where an int was
expected still parses.

## 5.5 Layer 4 — Validation (`_validate`)

Validation checks that every schema field is present, by name, and raises
`TASSValidationError` listing exactly what is missing. This is where the
one-token-per-field key investment (Chapter 3) matures: unlike positional
formats, a missing field is *identifiable*, and a partial record is
*usable* if your application can tolerate specific absences.

## 5.6 The failure taxonomy

Observed failure classes, their frequency envelope (varies by model tier
and schema width), and their handling:

| # | Failure | Typical rate | Caught by | Recovery |
|---|---|---|---|---|
| F1 | Markdown fences / prose wrapper | common, cosmetic | Layer 1 | free |
| F2 | Value type deviation (`True`, `5.0`) | 2–5% | Layer 3 | free |
| F3 | Missing field(s) | 1–3% | Layer 4 | retry or partial-accept |
| F4 | Unknown symbol invented | <1% | Layer 2 | skipped; F3 catches the gap |
| F5 | Model answers in JSON anyway | ~1% | `safe_parse` fallback | free |
| F6 | Unparseable prose | <0.5% | all layers fail | retry ladder |

F5 deserves note: models trained hard toward JSON sometimes revert to it
under pressure (long context, unusual input). `safe_parse` treats this as
*success in the wrong dialect* — it attempts JSON after TASS fails and
returns the same dict shape:

```python
result = parser.safe_parse(raw)   # TASS → validate → JSON → raise
```

## 5.7 The fallback ladder

Individual mitigations compose into a degradation strategy — runnable as
[`snippets/fallback_ladder.py`](../snippets/fallback_ladder.py):

```
Rung 1: safe_parse(raw)                     ~97–99% resolve here
Rung 2: one retry, same TASS prompt         transient noise; ~half the rest
Rung 3: retry in explicit JSON mode         pay full JSON price this once
Rung 4: dead-letter queue + alert           input is pathological; a human looks
```

Two properties make the ladder economically sound. First, expected cost:
at `f` ≈ 2% rung-2 rate, the overhead is `0.02 × T_tass` extra tokens per
record on average — negligible against the 60–80% baseline saving.
Second, **the ladder is also your monitor**: rung transition rates are the
health metric for the whole system (a rising rung-2 rate is how you learn
a provider silently swapped model versions — Chapter 9 §observability).

## 5.8 What the parser refuses to do

Boundaries, stated as design decisions:

- **No schema inference.** The parser never guesses types from values;
  ambiguity belongs to the schema author, not runtime.
- **No partial-field repair.** A mangled pair (`~a refund`) is dropped,
  not "fixed" — repairing corrupt fields invents data. F3 validation
  reports the gap honestly instead.
- **No semantic validation.** That `urgency_level ≤ 5` is business logic;
  it lives above the parser (see the pipeline snippet), keeping the
  library's contract purely structural.

## 5.9 Summary

- Treat LLM output as a noisy channel; the parser is a four-layer
  receiver: clean, scan, coerce, validate.
- Six failure classes cover practice; four are absorbed for free by
  design, and the remaining two are handled by a four-rung fallback
  ladder whose expected cost is ~2% overhead.
- The ladder doubles as the system's health instrumentation — rung rates
  are the metric that catches silent model drift.

*Next: schemas and records at rest — the `.tass` file — Chapter 6.*

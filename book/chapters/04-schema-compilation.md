# Chapter 4 — Schema Compilation

> *In which a plain dictionary becomes a system prompt, and prompt caching
> turns a fixed cost into a rounding error.*

## 4.1 The compiler contract

`SchemaCompiler` (in `tass/parser.py`) is deliberately tiny. It takes a
flat schema — field names to type hints — and returns two coupled
artifacts:

```python
from tass import SchemaCompiler

parser_map, system_prompt = SchemaCompiler().compile({
    "user_intent":      "string",
    "urgency_level":    "integer",
    "requires_routing": "boolean",
})
```

- **`system_prompt`** — injected verbatim into every LLM call.
- **`parser_map`** — `{symbol: (field_name, type_hint)}`, fed to
  `TASSParser` on the receiving side.

The two artifacts are generated in one pass from one source, which is the
point: **the prompt and the parser can never disagree about the
dictionary**, because neither is written by hand. Symbols are assigned
positionally (`a`, `b`, `c`… from a 52-slot pool); exceeding the pool
raises immediately with instructions to split the schema.

## 4.2 Anatomy of the generated prompt

```
You are a data extraction engine.
Output ONLY the TASS format below. No prose. No markdown. No explanation.
Format: ~a:<value> ~b:<value> ~c:<value>
Dictionary:
  ~a = user_intent
  ~b = urgency_level
  ~c = requires_routing
```

Each line earns its tokens:

1. **Role framing** ("data extraction engine") — moves the model out of
   conversational register, measurably reducing prose contamination.
2. **The triple prohibition** ("No prose. No markdown. No explanation.")
   — targets the three observed contamination modes separately. Models
   that ignore one prohibition often obey another.
3. **`Format:` line** — a *positive* template. Models imitate examples
   far more reliably than they follow abstract rules; this line is the
   single highest-value line in the prompt.
4. **`Dictionary:`** — grounds each symbol in the semantic field name, so
   the model's own understanding of "urgency_level" transfers to `~b`.

### Hardening for smaller models

The compiler's output is a floor, not a ceiling. Two additions measurably
improve compliance on small open models, at modest prompt cost:

- **One-shot example.** Append `Example: ~a:refund ~b:5 ~c:true`. A
  concrete record outperforms any additional rule.
- **Value constraints in the dictionary comments** — e.g.
  `~b = urgency_level (integer 1-5)`. Constraint violations drop
  sharply when the range is stated adjacent to the symbol.

## 4.3 Prompt caching: the enabling economics

The TASS dictionary is a fixed prefix repeated across thousands of calls —
the textbook prompt-caching workload. Every major provider now offers
prefix caching with cached-input discounts of roughly 90%.

The arithmetic for a 3-field schema (≈70-token dictionary), 100k
calls/day, at illustrative prices ($3/M input, 90% cache discount):

| | Uncached | Cached |
|---|---:|---:|
| Dictionary tokens/day | 7.0M | 7.0M |
| Effective price | $3.00/M | $0.30/M |
| Dictionary cost/day | $21.00 | **$2.10** |
| vs. output tokens saved/day (Ch. 1) | ~$61 | ~$61 |

Uncached, the dictionary consumes a third of the saving; cached, 3%.
Hence the design rule:

> **Keep the dictionary byte-stable.** Any change — reordered fields, a
> renamed comment, trailing whitespace — invalidates the cache prefix.
> Generate the prompt once from the schema, version it (Chapter 9), and
> never string-format per-request values into the system prompt. Dynamic
> content belongs in the user message, *after* the cached prefix.

## 4.4 Schema design guidelines

Field-level choices compound at volume:

1. **Order fields by stability, most stable first** — not for the wire
   (TASS is order-free) but for the cache: schema evolution that appends
   fields preserves the shared prompt prefix.
2. **Prefer enums to free strings.** Every field you can close over a
   code table (`@codes`, Chapter 6) removes both tokens and a failure
   mode (Chapter 5's "value type deviation").
3. **One record, one decision.** If two field groups are populated by
   logically separate reasoning (say, sentiment fields and billing
   fields), two small schemas beat one wide one — smaller dictionaries,
   independent failure domains, better cache granularity.
4. **Name fields for the model, not the database.** The dictionary line
   `~b = urgency_level` is *prompt text*; `urgency_level` primes the model
   better than `urg_lvl_v2`. Map to internal names after parsing.

## 4.5 The end-to-end loop

The complete lifecycle, runnable as
[`snippets/end_to_end_pipeline.py`](../snippets/end_to_end_pipeline.py):

```python
from tass import SchemaCompiler, TASSParser

schema = {"user_intent": "string", "urgency_level": "integer",
          "requires_routing": "boolean"}

parser_map, system_prompt = SchemaCompiler().compile(schema)
parser = TASSParser(dictionary_map=parser_map)

# response = llm(system=system_prompt, user=ticket_text)   # your provider
response = "~a:refund ~b:5 ~c:true"                         # (mock)

result = parser.safe_parse(response)
# {'user_intent': 'refund', 'urgency_level': 5, 'requires_routing': True}
```

Compile once at deploy time; parse per call. The compiler never appears on
the hot path.

## 4.6 Summary

- One schema compiles into a coupled (prompt, parser-map) pair, making
  prompt/parser drift structurally impossible.
- The generated prompt's lines each target a specific, observed failure
  mode; a one-shot example is the cheapest upgrade for small models.
- Prompt caching reduces the dictionary tax ~10×, and preserving it
  imposes one discipline: a byte-stable system prompt with all dynamic
  content in the user message.

*Next: what comes back, and everything that can be wrong with it —
Chapter 5.*

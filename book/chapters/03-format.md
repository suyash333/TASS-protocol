# Chapter 3 — The TASS Format

> *In which the format is specified precisely enough to reimplement from
> this chapter alone, and positioned honestly among its alternatives.*

## 3.1 The record

A **TASS record** is a single line of `field pairs` separated by single
spaces:

```
~t:mc ~f:45 ~e:4.2 ~l:18k ~h:42k ~g:0
```

Each pair is `PREFIX SYMBOL ":" VALUE`:

- **PREFIX** — one character, default `~` (configurable; Chapter 2 gives
  the selection criteria).
- **SYMBOL** — one ASCII letter `a–z A–Z`, assigned by the schema compiler
  in declaration order. The reserved symbol `!` carries a cryptographic
  tag (Chapter 8) and is never assigned to a schema field.
- **VALUE** — any run of non-whitespace characters. Values are untyped on
  the wire; types live in the schema and are applied at parse time.

### Grammar (EBNF)

```ebnf
record   = pair , { SP , pair } ;
pair     = prefix , symbol , ":" , value ;
prefix   = "~" ;                        (* configurable *)
symbol   = letter | "!" ;               (* "!" reserved: integrity tag *)
value    = vchar , { vchar } ;          (* any non-whitespace *)
letter   = "a"…"z" | "A"…"Z" ;
SP       = " " ;
```

Deliberate consequences of this grammar:

- **Order-free.** Keys are explicit, so field order never matters. This
  buys robustness against models that reorder, and enables canonical
  hashing (Chapter 8).
- **Self-delimiting.** No closing brace to forget — the most common LLM
  JSON failure (truncation mid-structure) cannot produce a
  half-record that silently parses as valid.
- **Unknown-tolerant.** Parsers skip pairs whose symbol is not in the
  dictionary and tokens that are not pairs. Additive schema evolution is
  free (Chapter 9 §schema registry).
- **No escaping.** A value cannot contain whitespace. This is the format's
  sharpest edge, examined in §3.4.

## 3.2 Value conventions

These conventions are contracts between prompt and parser, not grammar:

| Convention | Wire | Parsed | Mechanism |
|---|---|---|---|
| k-suffix magnitude | `18k`, `1.5k` | `18000`, `1500.0` | `_expand_k`, integer/float fields |
| Boolean | `1`/`true`/`yes`, `0`/`false`/`no` | `True` / `False` | boolean coercion, case-insensitive |
| Enum code | `mc` | `micro` | `@codes` table, expanded server-side |
| Float | `4.2` | `4.2` | float coercion |

The principle: **the LLM emits the minimum; the server does the
arithmetic.** Every expansion that can happen after the paid tokens stop,
should.

## 3.3 The format family: an honest comparison

| | JSON | TOON | CSV/pipe | Protobuf | **TASS** |
|---|---|---|---|---|---|
| Tokens / field (measured, o200k) | 6–9 | 4–6 | 2–3 | n/a¹ | **≈2** |
| Keys on wire | full | full | none | none | 1 char |
| Order-sensitive | no | no | **yes** | no | no |
| Truncation detectable | often silent² | varies | **silent** | yes | count check |
| Nesting | full | full | none | full | none³ |
| LLM training familiarity | very high | low | high | none | low |
| Human-readable | yes | yes | partly | no | with dictionary |

¹ Binary — LLMs cannot reliably emit it; included as the machine-format
reference point. ² A truncated JSON string can remain syntactically
parseable. ³ Flattening conventions cover one level (§3.4).

The interesting rival is **pipe-delimited**, which is nearly as cheap.
TASS spends one extra token per field to fix pipe's two production
failures: order sensitivity (a model that swaps two columns silently
corrupts data; a swapped TASS pair is identical data) and silent field
omission (a missing pipe column shifts every subsequent value; a missing
TASS field is caught by validation by name). That single token is the
best-spent token in the format.

## 3.4 Limits, stated plainly

1. **No whitespace in values.** Encode multi-word values as `@codes`
   entries (the code travels, the phrase stays server-side). For genuinely
   free-text fields — summaries, quotes — TASS is the wrong tool; use it
   for the structured fields and a separate call (or JSON) for prose.
2. **No nesting.** One level of structure can be flattened by convention
   (`address.city` → its own symbol), and lists of uniform objects become
   multiple records. Trees and recursive structures should stay in
   JSON/TOON; this is a boundary, not a bug.
3. **Instruction-following dependency.** Nothing forces a model to emit
   TASS the way constrained decoding forces JSON. The mitigation ladder in
   Chapter 5 is therefore not optional equipment — it is part of the
   protocol.

## 3.5 Design lineage

The record syntax will look familiar to greybeards, deliberately.
`key:value` pairs with single-character keys and a sigil prefix echo
**RFC 822 headers**, **SI/Metar weather codes**, and amateur-radio
exchange formats — all designed under a constraint TASS shares: an
expensive, error-prone channel where every character costs and the
receiver knows the schema. The novelty in TASS is not the shape but the
*costing function*: the channel's unit is the BPE token, and the format is
optimized against a measured vocabulary rather than a character count.

## 3.6 Summary

- A TASS record is a flat, order-free, self-delimiting line of
  `~x:value` pairs; grammar small enough to memorize.
- Types, magnitudes, and enums are schema-side contracts; the wire carries
  minimal untyped strings.
- Against its nearest competitor (pipe-delimited), TASS pays one token per
  field to eliminate order-corruption and silent-shift bugs.
- Its limits — no spaces, no nesting, instruction-following dependence —
  are explicit, and the rest of the book engineers around them.

*Next: turning a schema into a prompt the model actually follows —
Chapter 4.*

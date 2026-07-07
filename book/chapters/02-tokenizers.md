# Chapter 2 — Tokenizer Foundations

> *In which we open the black box that turns text into money, and derive
> TASS's alphabet from first principles.*

## 2.1 Byte-pair encoding in five minutes

Modern LLMs do not see characters. They see **tokens**: entries in a fixed
vocabulary (~100k–200k entries) learned by byte-pair encoding (BPE). BPE
training starts from raw bytes and greedily merges the most frequent
adjacent pairs until the vocabulary budget is exhausted. The result is a
frequency-ordered compression dictionary of its training corpus:

- `" the"` — one token (astronomically frequent)
- `"rate"` — one token
- `"~"` — one token (common in URLs, paths, code)
- `"ﬁ"` (ligature) — several bytes of UTF-8, byte-fallback tokens

Two properties matter for format design:

**P1 — Frequency is destiny.** A string is cheap iff it (or its pieces)
appeared often in the training corpus. ASCII letters, digits, and common
punctuation are the cheapest matter in the universe of BPE.

**P2 — Boundaries matter.** Tokenizers merge across what humans consider
word boundaries. `"rate_low"` may be 3 tokens (`rate`, `_`, `low`) while
`" ratelow"` is 2. Leading spaces are usually part of the token. You
cannot reason about token cost by eyeballing; you must measure
(Chapter 7).

## 2.2 The stenography hypothesis

TASS's founding observation reframes the tokenizer:

> **A BPE vocabulary is a stenographic dictionary the model already
> knows.** Instead of teaching the model new shorthand, choose output
> strings that already compress to single tokens.

Classical stenography (Pitman, Gregg, Duployan) maps frequent words to
short strokes. BPE has done the same statistically. The format designer's
job reduces to: *never emit a string that isn't near the top of the
frequency table.*

## 2.3 Why not real stenography symbols? (a cautionary tale)

The obvious romantic idea — use actual shorthand glyphs, e.g. Unicode's
Duployan block (U+1BC00–U+1BCAF) — fails empirically, and the failure
teaches the design rule. Duployan characters essentially never occur in
web-scale corpora, so no BPE merge was ever learned for them. Each glyph
falls back to raw UTF-8: **4 bytes → up to 4 byte-fallback tokens for a
single "shorthand" character.** The visually shortest notation is the most
expensive. The general rule:

> **Token cost is corpus frequency, not visual length.** Exotic symbols,
> emoji, and rare Unicode are anti-compression in a BPE world.

## 2.4 Deriving the TASS alphabet

Given P1 and P2, score candidate field-marker designs (counts via
`o200k_base`; the ordering is stable across `cl100k_base` and open-model
tokenizers):

| Candidate marker | Example | Typical tokens | Verdict |
|---|---|---|---|
| Full JSON key | `"rate_low":` | 4–6 | baseline pathology |
| Bare word key | `rate_low:` | 3–4 | still paying for the name |
| Two-letter code | `rl:` | 2 | good |
| `~` + letter | `~l:` | **2** (` ~l` merges; `:` rides with value) | good **and collision-proof** |
| Duployan glyph | `𛰀` | 3–5 | worst case |

Why `~` specifically, rather than nothing at all?

1. **Unambiguous scanning.** A sentinel prefix lets the parser split on
   whitespace and cheaply discard anything that isn't a field
   (`pair.startswith("~")` in `tass/parser.py`). Prose contamination,
   markdown fences, and model apologies are filtered structurally rather
   than with fragile regex.
2. **Low collision with values.** `~` rarely begins natural-language
   words, so a value containing spaces or colons can't be mistaken for a
   field marker.
3. **It is a single frequent token** in every major tokenizer, usually
   merging with a leading space (` ~`) for free.

The symbol pool is `a–z` then `A–Z` — 52 single-token markers
(`SchemaCompiler.token_pool`). Beyond 52 fields you are past the sweet
spot of a flat record anyway; split the schema (the compiler enforces
this with a clear error).

## 2.5 Value encoding under the same rule

The same frequency logic governs values:

- **Enums → 2-letter codes.** `mc` is one token; `micro` may be one or
  two; `"micro"` (JSON-quoted) is three. The `@codes` block (Chapter 6)
  makes the mapping declarative and expansion server-side.
- **Magnitude suffixes.** `18000` tokenizes digit-group by digit-group;
  `18k` is typically two tokens and parses deterministically
  (`_expand_k` in the parser: `18k → 18000`, `1.5k → 1500`).
- **Booleans → `0`/`1`.** Single ASCII digits are single tokens; the
  parser's boolean coercion accepts `1/true/yes`.
- **No quoting, ever.** Quotes are pure syntax; TASS values end at
  whitespace.

## 2.6 Portability of the argument

A fair objection: "you optimized for one tokenizer." The design deflects
it in three ways. First, TASS uses only the *intersection* of what is
cheap everywhere — ASCII letters, digits, `~`, `:` — rather than quirks of
one vocabulary. Second, the claim is a ratio measured within a single
tokenizer, so it survives vocabulary changes. Third, the benchmark harness
(Chapter 7) takes `--encoding` precisely so you can re-verify on the
tokenizer you actually deploy against. On every vocabulary tested, the
ordering `TASS < pipe < TOON < JSON < prose` is preserved even as absolute
counts drift.

## 2.7 Summary

- BPE token cost is corpus frequency; visual brevity is irrelevant and
  exotic symbols are actively harmful (the Duployan lesson).
- TASS's alphabet — `~` + one ASCII letter per field, short ASCII codes
  per value — is the cheapest *reliable* encoding the intersection of
  major tokenizers admits.
- The `~` sentinel buys structural robustness (cheap scanning, prose
  rejection) for one token, which Chapter 5 will spend well.

*Next: the format itself, specified precisely — Chapter 3.*

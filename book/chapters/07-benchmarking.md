# Chapter 7 — Benchmarking Honestly

> *In which we measure token savings without fooling ourselves — and
> catalogue the ways benchmark numbers get inflated.*

## 7.1 The only valid measurement

There is exactly one defensible way to compare formats: **render the same
records in each format and count tokens with the tokenizer of the model
you will actually call.** Everything else — character counts, "roughly 4
chars per token" folklore, eyeballing — produces numbers that do not
survive contact with a real vocabulary (Chapter 2 P2: boundaries are
unintuitive).

The repository's harness does precisely this:

```bash
tass benchmark examples/weather.tass                  # tiktoken, o200k_base
tass benchmark examples/weather.tass --encoding cl100k_base
tass benchmark --schema schema.json --records records.json
```

`TASSBenchmark` renders each record four ways — TASS, minified JSON,
pipe-delimited, prose — and reports absolute tokens plus percentage
against the JSON baseline, with per-format samples printed so the reader
can verify the renderings are fair.

## 7.2 The seven ways to lie with a token benchmark

A checklist for reading (or publishing) any format-savings claim. Each
item is a mistake that inflates numbers, and the harness's corresponding
defense:

1. **Pretty-printed baseline.** Indented JSON adds whitespace tokens the
   API would never emit. *Defense:* the harness renders JSON with
   `separators=(",", ":")` — minified, the strongest reasonable baseline.
2. **Cherry-picked field names.** Long snake_case keys flatter any
   key-eliding format. *Defense:* benchmark **your** schema, not the
   author's demo. The harness takes arbitrary schemas for this reason.
3. **Ignoring the prompt tax.** Output savings quoted without the
   dictionary's input cost. *Defense:* Chapter 1's break-even inequality;
   the tax belongs in any end-to-end claim (with and without caching).
4. **Ignoring the retry tax.** A 2% fallback-to-JSON rate shaves ~1–2
   points off net savings. *Defense:* multiply it in (Ch. 5 §5.7).
5. **Single-record samples.** Token counts are jumpy at small N; one
   record's percentage is noise. *Defense:* benchmark whole record sets;
   the harness aggregates across all records in the file.
6. **Wrong tokenizer.** Savings measured on `cl100k_base`, deployed
   against a different vocabulary. Ratios are *similar* across
   tokenizers, not identical. *Defense:* `--encoding` — measure what you
   deploy.
7. **Conflating estimate with measurement.** The harness's `--approx`
   mode (whitespace/punctuation splitting, for offline use) is
   deliberately labelled `approx (whitespace)` in its output. Approximate
   numbers are for direction, never for publication.

## 7.3 Reading the numbers in this repository

Applying the checklist to the repo's own claims, as a worked example of
the discipline:

- The README's headline table (17 vs 78 tokens, ↓78%) is a **single
  4-field record** — legitimate as an illustration, item 5 says don't
  quote it as *the* number.
- The weather case study (↓92% vs the full API response) compares against
  **nested provider JSON including fields the schema drops**. That is the
  honest number for "replace this API-relay pipeline with TASS" but not
  for "TASS vs minified flat JSON of the same fields" — the latter is
  ↓69–73%. Both numbers are real; they answer different questions.
  **State which question you are answering.**
- The quantum telemetry example (↓69% vs flat JSON, 6 records) is the
  most conservative and most generalizable figure in the repo.

The honest generic claim, then: **60–80% output-token reduction versus
minified flat JSON on typical 4–12 field schemas, before the (small,
cache-dependent) prompt and retry taxes.** Larger figures require the
nested-baseline framing and should say so.

## 7.4 Beyond static counts: compliance benchmarking

Token counts are static analysis. The dynamic question — *does model M
reliably emit TASS for schema S?* — requires a live harness: send N
representative inputs, run the full parse-validate pipeline, report the
rung distribution of Chapter 5's ladder. The repository's roadmap tracks
this as the 100-call cross-model harness. Until your own numbers exist,
budget with the envelope from Chapter 5 (`f` ≈ 1–5%), and re-run the
compliance benchmark on every model version change — silent model
upgrades are the largest source of compliance drift in production.

## 7.5 Summary

- Count tokens with the deployment tokenizer over rendered records;
  everything else is folklore.
- Seven specific inflation mistakes cover most bad benchmark claims; the
  harness defends against them structurally where it can.
- This repository's own numbers, audited: ↓60–80% is the defensible
  general claim; ↓90%+ requires (and must declare) the nested-API
  baseline.
- Static token counts must be paired with dynamic compliance measurement,
  re-run on every model change.

*Next: making records tamper-evident — Chapter 8.*

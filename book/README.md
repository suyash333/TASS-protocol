# Tokeniser-Aware Structured Shorthand

### *The Engineering of Token-Efficient Machine-to-Machine LLM Pipelines*

**Companion book to the [TASS protocol](https://github.com/suyash333/TASS-protocol)** · White paper DOI: [10.5281/zenodo.20403219](https://doi.org/10.5281/zenodo.20403219)

---

> *"The cheapest token is the one you never generate."*

This book is a complete, research-grade treatment of TASS: the economic
argument, the tokenizer theory underneath it, the format specification, the
reference implementation, and — most importantly — the system-design
patterns for deploying it in production. Every code listing runs against
the library in this repository; every benchmark is reproducible with the
included tooling.

**Who this is for.** Engineers building high-volume LLM extraction
pipelines; architects deciding between JSON, TOON, CSV, and compact
formats; researchers studying inference-cost optimization; and anyone who
has looked at an invoice from an LLM provider and wondered where the
money went.

**How to read it.** Chapters 1–3 are the theory and can be read on a
train. Chapters 4–8 are the engineering and are best read next to a
terminal with `pip install tass-protocol` done. Chapter 9 is the system
design chapter — if you are an architect evaluating TASS, you may start
there and work backwards. Chapter 10 grounds everything in three complete
case studies.

---

**📕 Prefer a single file?** The book ships as a built PDF ebook:
[`TASS-book.pdf`](TASS-book.pdf) (46 pages). Rebuild it anytime with
`pip install markdown weasyprint && python book/build_pdf.py`.

## Table of Contents

| # | Chapter | One-line summary |
|---|---------|------------------|
| 1 | [The Economics of Output Tokens](chapters/01-economics.md) | Why output tokens dominate extraction costs, with a cost model you can run |
| 2 | [Tokenizer Foundations](chapters/02-tokenizers.md) | BPE mechanics, why `~a` is cheap and Duployan shorthand is expensive |
| 3 | [The TASS Format](chapters/03-format.md) | Complete specification: records, grammar, design rationale, comparison to TOON/CSV/protobuf |
| 4 | [Schema Compilation](chapters/04-schema-compilation.md) | From schema to system prompt; prompt caching as the enabling economics |
| 5 | [Parsing and Failure Modes](chapters/05-parsing.md) | The parser, type coercion, the failure taxonomy, and defensive `safe_parse` |
| 6 | [The `.tass` File Format](chapters/06-file-format.md) | `@dict` / `@codes` / `@records`: schemas and data at rest |
| 7 | [Benchmarking Honestly](chapters/07-benchmarking.md) | Measurement methodology, tiktoken, and the mistakes that inflate savings claims |
| 8 | [Cryptographic Integrity](chapters/08-crypto.md) | Tamper-evident records with post-quantum-safe symmetric primitives |
| 9 | [System Design with TASS](chapters/09-system-design.md) | Reference architectures: pipelines, queues, schema registries, fallback ladders, observability |
| 10 | [Case Studies](chapters/10-case-studies.md) | Influencer rates, weather APIs, quantum-device telemetry — end to end |
| 11 | [TASS Beyond the LLM](chapters/11-beyond-llm.md) | The format on byte- and character-priced channels: IoT/LPWAN, SMS, QR/NFC, logs, URLs, field data |
| A | [API Reference](chapters/appendix-a-api.md) | Every public class and function, with signatures |
| B | [Glossary & Bibliography](chapters/appendix-b-glossary.md) | Terms and further reading |
| C | [Use-Case Catalog](chapters/appendix-c-use-cases.md) | Every use case → its schema, code, and analysis chapter, runnable |

## Runnable companion code

Each snippet is standalone and referenced from the chapters:

| File | Used in | What it shows |
|------|---------|---------------|
| [`snippets/cost_model.py`](snippets/cost_model.py) | Ch. 1 | Annualized cost model: JSON vs TASS at your volumes |
| [`snippets/end_to_end_pipeline.py`](snippets/end_to_end_pipeline.py) | Ch. 4, 5, 9 | Complete extraction pipeline: compile → (mock) LLM → parse → validate → sign |
| [`snippets/fallback_ladder.py`](snippets/fallback_ladder.py) | Ch. 5, 9 | The three-rung degradation strategy under malformed output |
| [`snippets/schema_registry.py`](snippets/schema_registry.py) | Ch. 9 | A minimal versioned schema registry with `.tass` files as the source of truth |
| [`snippets/signed_audit_trail.py`](snippets/signed_audit_trail.py) | Ch. 8, 9, 10 | The signed firehose end to end: tamper caught, replay deduped, archive re-verified |
| [`snippets/tass_logger.py`](snippets/tass_logger.py) | Ch. 11 | TASS as a structured-logging format: stdlib `logging.Formatter` + expand-on-view + byte bill |
| [`snippets/payload_budgets.py`](snippets/payload_budgets.py) | Ch. 11 | Does the record fit? Exact byte costs vs LoRaWAN/SMS/USSD/QR/NFC/URL budgets, signed & unsigned |

Run any of them from the repository root:

```bash
pip install -e .
python book/snippets/end_to_end_pipeline.py
```

---

*MIT licensed, like the rest of the repository. Corrections and PRs welcome.*

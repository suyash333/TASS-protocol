# Appendix C — Use-Case Catalog

Every use case developed in this book and repository, with its complete
implementation trail: the schema artifact, the code that exercises it,
and the chapter that analyzes it. Each row is runnable today from the
repository root.

---

## C.1 Support-ticket classification & routing

*The interactive workload: intent, urgency, sentiment, routing — per
ticket, thousands of times a day. Latency savings matter as much as cost.*

| Artifact | Location |
|---|---|
| Schema (registry-ready, with `~z` version pin) | [`examples/ticket_routing.tass`](../../examples/ticket_routing.tass) |
| Synchronous pipeline (compile → parse → validate → sign) | [`snippets/end_to_end_pipeline.py`](../snippets/end_to_end_pipeline.py) |
| Degradation strategy + circuit breaker | [`snippets/fallback_ladder.py`](../snippets/fallback_ladder.py) |
| Versioned registry + version-skew demo | [`snippets/schema_registry.py`](../snippets/schema_registry.py) |
| Analysis | Ch. 4 (compilation), Ch. 5 (failures), Ch. 9 Patterns I/III/IV |

```bash
tass read examples/ticket_routing.tass --records-only
python book/snippets/end_to_end_pipeline.py
```

## C.2 Influencer rate-card extraction

*The origin workload: 10-field commercial records where the LLM bill was
a top-three cost line. Every value convention in one schema.*

| Artifact | Location |
|---|---|
| Schema + records | [`spec/sample.tass`](../../spec/sample.tass) |
| Cost model (edit for your volumes) | [`snippets/cost_model.py`](../snippets/cost_model.py) |
| Analysis | Ch. 1 (economics), Ch. 3 (conventions), Ch. 10 §10.1 |

```bash
tass benchmark spec/sample.tass --approx
python book/snippets/cost_model.py
```

## C.3 Weather-API relay

*The adoption template: an LLM already summarizes an upstream API — move
the output contract from provider-shaped JSON to a reduced TASS schema.
Demonstrates schema reduction (~60 fields → 21) and multi-namespace codes
tables (conditions, 16-point compass, AQI labels).*

| Artifact | Location |
|---|---|
| Raw provider response (before) | [`examples/weather_raw.json`](../../examples/weather_raw.json) |
| TASS schema + records (after) | [`examples/weather.tass`](../../examples/weather.tass) |
| Analysis | Ch. 6 (codes), Ch. 7 (the two honest baselines), Ch. 10 §10.2 |

```bash
tass read examples/weather.tass --records-only
tass benchmark examples/weather.tass --approx
```

## C.4 Quantum-device calibration telemetry

*The integrity workload: qubit coherence times, gate fidelities, and
readout errors that downstream compilers act on — silent corruption is a
wrong answer on hardware, not a logging bug.*

| Artifact | Location |
|---|---|
| Schema + records (T1/T2, errors, lifecycle codes) | [`examples/quantum_telemetry.tass`](../../examples/quantum_telemetry.tass) |
| Signed firehose, end to end (C.5's machinery applied) | [`snippets/signed_audit_trail.py`](../snippets/signed_audit_trail.py) |
| Analysis | Ch. 8 (integrity), Ch. 9 Pattern II, Ch. 10 §10.3 |

```bash
tass read examples/quantum_telemetry.tass --records-only
python book/snippets/signed_audit_trail.py
```

## C.5 Tamper-evident audit pipelines (the cryptographic use case)

*Not a schema but a capability that attaches to any of the above: sign at
the trust boundary, ship raw signed lines, verify at every consumer,
dedup by content address, re-verify archives years later.*

| Artifact | Location |
|---|---|
| Library (`TASSSigner`, `hash_record`, `derive_key`, `canonicalize`) | [`tass/crypto.py`](../../tass/crypto.py) |
| CLI | `tass sign` / `tass verify` |
| Working pipeline: tamper caught, replay deduped, reorder tolerated, archive re-verified | [`snippets/signed_audit_trail.py`](../snippets/signed_audit_trail.py) |
| Threat model | [`docs/CRYPTO.md`](../../docs/CRYPTO.md) |
| Analysis | Ch. 8, Ch. 9 §9.3/§9.6 |

```bash
export TASS_KEY="pipeline-secret"
tass sign "~a:rf ~b:5 ~c:1" --context tickets-v1
python book/snippets/signed_audit_trail.py
```

---

## C.6 Choosing your own

Map a candidate workload onto the catalog by its dominant constraint:

| Your constraint looks like… | Start from | Because |
|---|---|---|
| Interactive latency, per-request calls | C.1 | ladder + breaker are mandatory on user-facing paths |
| Raw cost at batch scale | C.2 | the cost model prices your exact schema first |
| An upstream API you're already relaying | C.3 | schema reduction is where most of the saving hides |
| Data that downstream automation *acts on* | C.4 + C.5 | integrity is part of the schema, not an add-on |

Then run the Chapter 9 §9.7 decision framework before committing — the
five questions apply to every row above.

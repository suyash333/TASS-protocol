# Chapter 10 — Case Studies

> *In which three real schemas exercise everything in this book, each
> chosen to stress a different part of the design.*

All three live in the repository and parse today:

```bash
tass read spec/sample.tass --records-only
tass read examples/weather.tass --records-only
tass read examples/quantum_telemetry.tass --records-only
```

---

## 10.1 Influencer rate cards — the origin workload

**File:** [`spec/sample.tass`](../../spec/sample.tass) ·
**Stresses:** value-convention design, the economics at business scale.

The schema that motivated TASS: 10 fields per influencer profile — tier,
follower count, engagement, three rate points, two multipliers, GST flag,
template id — extracted thousands of times daily at a bootstrapped
startup, where the LLM bill was a top-three cost line.

What to study in the file:

- **Every value convention from Chapter 3 in one record.**
  `~t:mc` (enum code), `~l:18k` (magnitude suffix), `~n:1.2` (bare
  float), `~g:0` (boolean digit), `~p:fmm` (code that stays a code — the
  template id is resolved by a *different* service, so the codes table
  documents it without expanding it).
- **Units live in the dictionary comments**, not on the wire:
  `~f = followers  # integer in thousands` — `~f:45` means 45,000. The
  comment is documentation *and* prompt text (Ch. 4): one line serving
  both audiences.
- The economics: at 78 → 17 tokens and this workload's volume, Chapter
  1's model prices the format change as a mid-five-figure annual saving —
  the difference between "optimization" and "runway."

---

## 10.2 Weather ingestion — the API-relay pattern

**Files:** [`examples/weather_raw.json`](../../examples/weather_raw.json)
→ [`examples/weather.tass`](../../examples/weather.tass) ·
**Stresses:** schema *reduction*, codes tables at full power, honest
baselines.

The input is a provider-style weather response: ~60 fields, four levels of
nesting, Kelvin temperatures, internal station ids. The TASS schema is the
result of asking, field by field, *"does any consumer read this?"* — 21
fields survive, flattened, unit-converted (K→°C, m/s→km/h) by the
pre-processing layer so the wire carries decision-ready values.

What to study:

- **Three codes namespaces in one file** — conditions (`lr = Light
  Rain`), 16-point compass (`SW = Southwest`), WHO AQI labels
  (`4 = Poor`) — kept collision-free by construction (Ch. 6 discipline:
  conditions are lowercase pairs, compass is uppercase, AQI is digits).
- **Multi-word expansion** doing real work: the wire never carries a
  space; consumers still receive `"Broken Clouds"`.
- **The two honest numbers** (Ch. 7): ↓92% against the full nested API
  response — the right figure for "replace this relay pipeline" — and
  ↓69–73% against minified flat JSON of the same 21 fields, the right
  figure for format-vs-format claims. The file's own comment block quotes
  both, with the baseline named.

This case is the template for the most common TASS adoption path:
*an LLM already summarizes an upstream API; move the contract from "emit
JSON like the API's" to "emit these N fields in TASS."*

---

## 10.3 Quantum-device telemetry — the integrity workload

**File:** [`examples/quantum_telemetry.tass`](../../examples/quantum_telemetry.tass) ·
**Stresses:** precision handling, signing, the firehose pattern.

Superconducting-qubit calibration: every few hours, every qubit on a
device reports T1/T2 coherence times, gate error rates, readout error,
frequency, anharmonicity, and a status code. A 100-qubit machine emits
tens of thousands of identical-schema records weekly — and downstream
*compilers* consume them to choose which qubits run which circuits, so a
silently corrupted `~s:0.00021` is not a logging bug, it is a wrong
answer on hardware.

What to study:

- **Precision as schema contract.** Gate errors carry 5 decimals, T1/T2
  one decimal, frequency four — stated in the dictionary comments, so
  the prompt communicates precision expectations and reviewers can check
  them (Ch. 4 §4.2 hardening).
- **Status codes model a lifecycle** (`ok/dg/fl/rt` → calibrated/
  degraded/failed/retuning) — enums earning their two characters, since
  a consumer routing on `fl` must never fuzzy-match prose like
  `"calibration failed (see log)"`.
- **This is Pattern II from Chapter 9 end to end:** sign each line at the
  parser (`tass sign`, key context `quantum-cal-v1`), ship signed lines
  on the queue, verify at the warehouse, archive raw lines for audit.
  `hash_record()` dedups the at-least-once queue. The MAC's post-quantum
  rationale (Ch. 8) is pleasingly non-decorative in a quantum lab.

```bash
export TASS_KEY="lab-master-secret"
tass sign "~q:0 ~d:hr ~a:312.4 ~s:0.00021 ~g:ok" --context quantum-cal-v1
tass verify "<signed line>" --context quantum-cal-v1   # exit 0
```

---

## 10.4 What the three cases teach jointly

| | Rates | Weather | Telemetry |
|---|---|---|---|
| Schema width | 10 | 21 | 11 |
| Records source | LLM extraction | LLM over API relay | pipeline + LLM summaries |
| Codes tables | 2 | 3 | 2 |
| Savings (honest baseline) | ↓78% (illustrative single record) | ↓69–73% flat / ↓92% nested | ↓69% |
| Distinctive lesson | value conventions | schema reduction | integrity at scale |

The convergence across three unrelated domains — the savings landing in
the same 60–80% band predicted by Chapter 1's ≈2-vs-6–9 tokens-per-field
analysis — is the empirical spine of this book: the ratio is a property
of the *format*, not of any flattering example.

*Appendices follow: the API reference, and a glossary with further
reading.*

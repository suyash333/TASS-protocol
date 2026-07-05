# TASS: Tokeniser-Aware Structured Shorthand

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20403219.svg)](https://doi.org/10.5281/zenodo.20403219)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/suyash333/TASS-protocol)

A stenography-inspired output format for reducing LLM inference costs by **75–92%** in structured extraction pipelines.

Originally developed to optimise the high-volume data extraction pipelines at [InfluencersBuddy.com](https://influencersbuddy.com) and [IndianAIApps.com](https://indianaiapps.com).

---

## The problem: JSON is expensive dead weight

When an LLM communicates directly with a server, human-readable formatting — curly braces, quoted keys, colons, spacing — serves no purpose. Because LLM output tokens cost **4–6× more** than input tokens, returning standard JSON for high-volume, fixed-schema extraction results in massive unnecessary spend.

```
{"tier":"micro","rate_low":18000,"rate_high":42000,"gst":false}
```
↑ 78 output tokens. Most of them are punctuation you pay for and immediately discard.

---

## The solution: TASS

TASS treats the LLM's byte-pair encoding (tokeniser) as a stenographic dictionary. A single-character symbol map is defined once in the system prompt and cached — slashing every subsequent response to a flat key-value string.

```
~t:mc ~l:18k ~h:42k ~g:0
```
↑ 17 output tokens. Same four values. **78% cheaper.**

Read the full white paper: [Tokeniser-Aware Shorthand (TASS) — Zenodo](https://doi.org/10.5281/zenodo.20403219)

---

## Install

```bash
pip install tass-protocol                  # core — zero dependencies
pip install tass-protocol[benchmark]       # + tiktoken for exact BPE token counts
```

---

## Quickstart — Python

```python
from tass import SchemaCompiler, TASSParser

# 1. Define your schema
my_schema = {
    "user_intent":      "string",
    "urgency_level":    "integer",
    "requires_routing": "boolean"
}

# 2. Compile → get system prompt + parser map
compiler = SchemaCompiler()
parser_map, system_prompt = compiler.compile(my_schema)

print(system_prompt)
# You are a data extraction engine.
# Output ONLY the TASS format below. No prose. No markdown. No explanation.
# Format: ~a:<value> ~b:<value> ~c:<value>
# Dictionary:
#   ~a = user_intent
#   ~b = urgency_level
#   ~c = requires_routing

# 3. Query your LLM using system_prompt, then parse the response
raw_llm_output = "~a:refund ~b:5 ~c:true"
parser = TASSParser(dictionary_map=parser_map)

result = parser.parse(raw_llm_output)
print(result)
# {'user_intent': 'refund', 'urgency_level': 5, 'requires_routing': True}
```

### JSON fallback

```python
# safe_parse() tries TASS first, falls back to JSON if the LLM slips up
result = parser.safe_parse(raw_llm_output)
```

---

## Quickstart — JavaScript

```javascript
const { SchemaCompiler, TASSParser } = require('./tass');

const schema = {
  user_intent:      'string',
  urgency_level:    'integer',
  requires_routing: 'boolean'
};

const compiler = new SchemaCompiler();
const { parserMap, systemPrompt } = compiler.compile(schema);

// After querying your LLM:
const raw = '~a:refund ~b:5 ~c:true';
const parser = new TASSParser({ dictionaryMap: parserMap });
console.log(parser.parse(raw));
// { user_intent: 'refund', urgency_level: 5, requires_routing: true }
```

---

## CLI

After `pip install tass-protocol` a `tass` command is available:

```bash
# Generate a system prompt from a schema file
tass compile schema.json

# Parse a raw LLM response into JSON
tass parse "~a:refund ~b:5 ~c:true" --schema schema.json

# Parse a .tass file and output records as JSON
tass read spec/sample.tass --records-only

# Benchmark token savings vs JSON, pipe, and prose
tass benchmark examples/weather.tass --approx   # offline (no tiktoken needed)
tass benchmark examples/weather.tass            # exact BPE counts via tiktoken

# Sign / verify records (HMAC-SHA3-256, post-quantum-safe, zero deps)
export TASS_KEY="pipeline-secret"
tass sign "~t:mc ~l:18k ~h:42k ~g:0"
tass verify "~t:mc ~l:18k ~h:42k ~g:0 ~!:3vX9kQ..."   # exit 0 = valid
```

---

## The `.tass` file format

TASS defines a human-readable file format for storing schemas, value dictionaries, and records. Three blocks:

| Block | Purpose |
|-------|---------|
| `@dict` | Maps `~symbol` → field name (injected into the LLM system prompt) |
| `@codes` | Maps short tokens → full values (server-side expansion after parsing) |
| `@records` | One TASS record per line |

```
@dict
  ~t = tier        # mc=micro | md=mid | mk=macro
  ~l = rate_low    # INR, k suffix = thousands
  ~h = rate_high
  ~g = gst         # 0=not applicable | 1=charge 18%
@end

@codes
  mc = micro
  md = mid
  mk = macro
@end

@records
~t:mc ~l:18k ~h:42k ~g:0
~t:md ~l:55k ~h:130k ~g:1
@end
```

Parse it in Python:

```python
from tass import TASSFileParser

tfile = TASSFileParser().parse_file("spec/sample.tass")
print(tfile.records[0])
# {'tier': 'micro', 'rate_low': '18k', 'rate_high': '42k', 'gst': '0'}

print(tfile.codes)
# {'mc': 'micro', 'md': 'mid', 'mk': 'macro', ...}
```

See [`spec/sample.tass`](spec/sample.tass) for a full influencer-rate example.

---

## Real-world example: Weather API

A standard OpenWeatherMap response is deeply nested JSON with ~60 fields, internal IDs, icon codes, and Kelvin temperatures. Here is what the same data looks like side by side:

**JSON (what the API returns — 620 tokens for current conditions alone):**

```json
{
  "coord": { "lon": 77.209, "lat": 28.6139 },
  "weather": [{ "id": 721, "main": "Haze", "description": "haze", "icon": "50d" }],
  "main": {
    "temp": 308.15, "feels_like": 311.42, "temp_min": 306.48, "temp_max": 309.82,
    "pressure": 1002, "humidity": 52, "sea_level": 1002, "grnd_level": 974
  },
  "wind": { "speed": 4.12, "deg": 230, "gust": 6.80 },
  "clouds": { "all": 40 },
  "sys": { "country": "IN", "sunrise": 1750634220, "sunset": 1750683540 },
  "air_quality": { "aqi": 4, "pm2_5": 62.18, "pm10": 88.43 },
  "name": "Delhi",
  ...
}
```

**TASS (what the LLM emits — 52 tokens, including 5-slot forecast: 115 tokens total):**

```
~t:1750665600 ~a:Delhi ~b:IN ~c:hz ~d:35.0 ~e:38.3 ~f:33.3 ~g:36.7 ~h:52 ~i:1002 ~j:14.8 ~k:SW ~l:24.5 ~m:3.5 ~n:40 ~o:4 ~p:62.18 ~q:88.43 ~r:1750634220 ~s:1750683540 ~u:0.0
~t:1750708800 ~a:Delhi ~b:IN ~c:lr ~d:30.6 ~e:33.3 ~f:29.4 ~g:31.7 ~h:62 ~i:1003 ~j:22.2 ~k:S ~l:0.0 ~m:4.5 ~n:85 ~o:4 ~p:62.18 ~q:88.43 ~r:1750634220 ~s:1750683540 ~u:0.68
```

After parsing, `hz` → `Haze`, `SW` → `Southwest`, `4` → `Poor`, `lr` → `Light Rain` — all expanded server-side from the `@codes` block, never sent back over the wire.

**Token comparison (o200k_base, current conditions + 5-slot forecast):**

| Format | Tokens | vs JSON |
|--------|--------|---------|
| JSON (full response) | ~1,400 | baseline |
| JSON (flat, fields only) | ~380 | ↓ 73% |
| Pipe-delimited | ~135 | ↓ 90% |
| **TASS** | **~115** | **↓ 92%** |

See [`examples/weather_raw.json`](examples/weather_raw.json) and [`examples/weather.tass`](examples/weather.tass) for the complete files.

---

## Cryptographic integrity (post-quantum-safe)

TASS records travel through pipelines no human ever reads — which is exactly
where silent tampering goes unnoticed. `tass.crypto` attaches a compact
HMAC-SHA3-256 tag *inside* the record line, using only symmetric primitives
(nothing for Shor's algorithm to break; Grover's at most halves 256-bit
security to a still-infeasible 2¹²⁸):

```python
from tass.crypto import TASSSigner, derive_key

key = derive_key(b"master-secret", context=b"weather-pipeline-v1")
signer = TASSSigner(key)

signed = signer.sign_line("~a:Delhi ~c:hz ~d:35.0")
# '~a:Delhi ~c:hz ~d:35.0 ~!:Yx2mP8sT1uW4yZ6bCgQvRw'

signer.verify_line(signed)                        # True
signer.verify_line(signed.replace("35.0", "99"))  # False — tampered
```

The `~!:` tag is outside the schema symbol pool, so signed records still
parse normally. Verification is constant-time and order-independent
(records are canonicalized before MAC computation). Full threat model,
primitive rationale, and explicit non-goals: [`docs/CRYPTO.md`](docs/CRYPTO.md).

**Quantum-telemetry example:** [`examples/quantum_telemetry.tass`](examples/quantum_telemetry.tass)
shows a superconducting-qubit calibration schema (T1/T2, gate fidelities,
readout error) — high-volume fixed-schema records at ~69% token savings,
signable end-to-end.

---

## Token savings at a glance (simple schema)

| Format | Output tokens | vs JSON | Parse complexity |
|--------|--------------|---------|-----------------|
| Naive prose | ~600 | +670% worse | Regex |
| JSON | ~78 | baseline | `JSON.parse()` |
| TOON (2025) | ~58 | ↓ 26% | npm parser |
| Pipe-delimited | ~32 | ↓ 59% | `split('|')` |
| **TASS** | **~17** | **↓ 78%** | **split + dict lookup** |

*Token counts estimated via `o200k_base` tokeniser, consistent with TOON benchmark methodology.*

---

## When to use TASS

**Good fit:**
- High-volume, fixed-schema LLM extraction (classification, scoring, routing)
- Machine-to-machine pipelines where no human reads the raw output
- Any use case where the same schema repeats across thousands of calls

**Not suitable for:**
- Variable or dynamic schemas
- Deeply nested or tree-structured output (use TOON or JSON)
- Outputs that developers will read and debug directly

---

## Why not literal stenography symbols?

The Unicode Standard includes a Duployan shorthand block (U+1BC00–U+1BCAF). These characters are not in LLM training corpora, so tokenisers lack dedicated tokens for them — triggering byte-level fallback that costs *more* tokens per character, not fewer. TASS uses `~` + ASCII letters because they are single tokens in every major tokeniser.

---

## Failure modes and mitigations

| Failure | Est. frequency | Mitigation |
|---------|---------------|------------|
| Unknown symbol emitted | <1% | Retry in JSON fallback mode |
| Field count mismatch | 1–3% | Validate count post-parse; retry once |
| Value type deviation | 2–5% | Accept variants; normalise in parser |
| Markdown fences added | Rare | Strip fences; extract matching line |

---

## Roadmap

- [ ] Empirical benchmark — 100-call test harness across Claude Haiku 4.5, Gemini 2.5 Flash, Llama 4 Maverick
- [x] Python parser with JSON fallback (`tass.safe_parse`)
- [x] JavaScript parser (`tass.js`)
- [x] CLI — `tass compile / parse / read / benchmark`
- [x] `.tass` file format parser
- [x] Benchmark harness with tiktoken + offline approximation mode
- [x] Cryptographic integrity layer — HMAC-SHA3-256 signing, HKDF key derivation (`tass.crypto`)
- [ ] Post-quantum signature support (ML-DSA / SLH-DSA) for third-party verification
- [ ] Go parser (`tass-go`)
- [ ] Streaming support — field-level delimiters for streamed responses
- [ ] Fine-tuning study — smaller open models on TASS schema compliance

---

## Citation

```bibtex
@misc{sharma2026tass,
  author    = {Sharma, Suyash},
  title     = {Tokeniser-Aware Shorthand (TASS): A Stenography-Inspired Output Format
               for Reducing LLM Inference Cost in Structured Extraction Pipelines},
  year      = {2026},
  doi       = {10.5281/zenodo.20403219},
  url       = {https://doi.org/10.5281/zenodo.20403219},
  publisher = {Zenodo}
}
```

---

## License

MIT © 2026 Suyash Sharma — see [LICENSE](LICENSE)

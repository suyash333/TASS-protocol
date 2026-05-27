# TASS: Tokeniser-Aware Structured Shorthand

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20403219.svg)](https://doi.org/10.5281/zenodo.20403219)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/suyash333/TASS-protocol)

A stenography-inspired output format for reducing LLM inference costs by **75–85%** in structured extraction pipelines.

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
# You are an extraction engine. Output ONLY the following format. No prose.
# Format: ~a:<value> ~b:<value> ~c:<value>
# Dictionary:
# ~a = user_intent
# ~b = urgency_level
# ~c = requires_routing

# 3. Query your LLM using system_prompt, then parse the response
raw_llm_output = "~a:refund ~b:5 ~c:true"
parser = TASSParser(dictionary_map=parser_map)

result = parser.parse(raw_llm_output)
print(result)
# {'user_intent': 'refund', 'urgency_level': 5, 'requires_routing': True}
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

## The `.tass` file format

TASS defines a human-readable file format for storing schemas, dictionaries, and records. See [`spec/sample.tass`](spec/sample.tass) for a full example.

```
@dict
  ~t = tier        # mc=micro | md=mid | mk=macro
  ~l = rate_low    # INR, k suffix = thousands
  ~h = rate_high
  ~g = gst         # 0=not applicable | 1=charge 18%
@end

@records
~t:mc ~l:18k ~h:42k ~g:0
~t:md ~l:55k ~h:130k ~g:1
@end
```

---

## Token savings at a glance

| Format | Output tokens | vs JSON | Parse complexity |
|--------|--------------|---------|-----------------|
| Naive prose | ~600 | +670% worse | Regex |
| JSON | ~78 | baseline | `JSON.parse()` |
| TOON (2025) | ~58 | ↓ 26% | npm parser |
| Pipe-delimited | ~32 | ↓ 59% | `split('|')` |
| **TASS** | **~17** | **↓ 78%** | **split + dict lookup** |

*Token counts estimated via GPT-5 `o200k_base` tokeniser, consistent with TOON benchmark methodology.*

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
- [ ] Python parser with JSON fallback (`tass.safe_parse`)
- [ ] JavaScript / TypeScript parser package (`tass-js`)
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

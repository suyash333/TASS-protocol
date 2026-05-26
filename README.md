# TASS: Tokeniser-Aware Structured Shorthand

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A stenography-inspired output format for reducing LLM inference costs by 75–85% in structured extraction pipelines. 

Originally developed to optimize the high-volume data extraction pipelines at [InfluencersBuddy.com](https://influencersbuddy.com) and [IndianAIapps.com](https://indianaiapps.com).

## 🛑 The Problem: JSON is Expensive Dead Weight
When an LLM communicates directly with a server, human-readable formatting (curly braces, quoted keys, spacing) is dead weight. Because LLM output tokens cost 4-6x more than input tokens, returning standard JSON for high-volume, fixed-schema extraction results in massive, unnecessary financial overhead.

## 💡 The Solution: TASS
TASS treats the LLM's byte-pair encoding (tokeniser) as a stenographic dictionary. By dynamically generating a single-character symbol map and caching it in the system prompt, TASS flattens extraction into a pure, delimiter-driven key-value string (`~a:value ~b:value`).

Read the full whitepaper on Zenodo: [Tokeniser-Aware Shorthand (TASS)](https://doi.org/10.5281/zenodo.XXXXXXX)

## 🚀 Quickstart

```python
from tass import SchemaCompiler, TASSParser

# 1. You have a standard JSON schema requirement
my_schema = {
    "user_intent": "string",
    "urgency_level": "integer",
    "requires_routing": "boolean"
}

# 2. Compile it to get the prompt injection and the parser map
compiler = SchemaCompiler()
parser_map, system_prompt = compiler.compile(my_schema)

print(system_prompt)
# Output:
# Format: ~a:<value> ~b:<value> ~c:<value>
# Dictionary:
# ~a = user_intent
# ~b = urgency_level
# ~c = requires_routing

# 3. (Query your LLM using the system_prompt...)

# 4. Parse the cheap, raw LLM response back to standard JSON
raw_llm_output = "~a:refund ~b:5 ~c:true"
parser = TASSParser(dictionary_map=parser_map)

final_json = parser.parse(raw_llm_output)
print(final_json)
# Output: {'user_intent': 'refund', 'urgency_level': '5', 'requires_routing': 'true'}

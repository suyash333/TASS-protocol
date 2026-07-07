# Appendix B — Glossary & Bibliography

## Glossary

**BPE (byte-pair encoding)** — Subword tokenization algorithm that
greedily merges frequent byte pairs into a fixed vocabulary; the reason
token cost equals corpus frequency, not visual length (Ch. 2).

**Canonical form** — A TASS record reduced to sorted, single-spaced
`~key:value` pairs with the signature field removed; the input to all
hashing and MAC operations (Ch. 8).

**Codes table (`@codes`)** — Declarative mapping from short wire codes to
full values, expanded server-side after parsing (Ch. 6).

**Decode / prefill** — The two phases of LLM inference: parallel
processing of the input (prefill) versus serial, per-token generation of
the output (decode). Decode is why output tokens cost more (Ch. 1).

**Dictionary (`@dict` / parser map)** — The symbol→field mapping shared
by prompt and parser, generated from one schema source (Ch. 4, 6).

**Fallback ladder** — The four-rung degradation strategy: `safe_parse` →
retry → JSON mode → dead-letter; doubles as the pipeline health metric
and circuit breaker (Ch. 5, 9).

**Grover's algorithm** — Quantum search with quadratic speedup; halves
effective symmetric security bits, leaving 256-bit primitives with a
~2¹²⁸ margin (Ch. 8).

**HKDF** — HMAC-based key derivation (RFC 5869); used with context
strings to give each pipeline an independent signing key (Ch. 8).

**k-suffix** — Magnitude convention `18k = 18000`, `1.5k = 1500`;
expanded by the parser's numeric coercion (Ch. 3).

**o200k_base / cl100k_base** — tiktoken encodings used by recent OpenAI
model families; the reference vocabularies for this book's measurements
(Ch. 7).

**Prompt caching** — Provider-side reuse of a repeated prompt prefix at
~90% discount; the mechanism that amortizes the TASS dictionary to noise
and imposes the byte-stable-prompt discipline (Ch. 4).

**Rung rate** — Fraction of requests resolved at each rung of the
fallback ladder; the primary observability signal for a TASS pipeline
(Ch. 9).

**Shor's algorithm** — Quantum algorithm breaking RSA/ECC; irrelevant to
TASS's integrity layer because no public-key material exists in it
(Ch. 8).

**Symbol pool** — The 52 single-token field markers `a–z`, `A–Z`; `!` is
reserved for the integrity tag (Ch. 3, 8).

**TASS record** — One line of whitespace-separated `~symbol:value`
pairs; order-free, self-delimiting, escaping-free (Ch. 3).

**TOON** — Token-Oriented Object Notation (2025); a token-reduced but
still key-carrying and nesting-capable format; TASS's nearest published
relative (Ch. 3).

## Bibliography & further reading

**Primary source**

- Sharma, S. (2026). *Tokeniser-Aware Shorthand (TASS): A
  Stenography-Inspired Output Format for Reducing LLM Inference Cost in
  Structured Extraction Pipelines.* Zenodo.
  [doi:10.5281/zenodo.20403219](https://doi.org/10.5281/zenodo.20403219)

**Tokenization**

- Sennrich, R., Haddow, B., & Birch, A. (2016). *Neural Machine
  Translation of Rare Words with Subword Units.* ACL 2016 — the BPE
  paper.
- Gage, P. (1994). *A New Algorithm for Data Compression.* C Users
  Journal 12(2) — BPE's compression-era origin.
- OpenAI, *tiktoken* — reference tokenizer implementation.
  https://github.com/openai/tiktoken

**Cryptography (Ch. 8's standards trail)**

- NIST FIPS 202 (2015). *SHA-3 Standard.*
- NIST SP 800-107r1 (2012). *Recommendation for Applications Using
  Approved Hash Algorithms* — HMAC truncation.
- Krawczyk, H., & Eronen, P. (2010). *RFC 5869: HKDF.*
- NIST FIPS 204 / 205 (2024). *ML-DSA / SLH-DSA* — the post-quantum
  signature schemes referenced for future non-repudiation support.
- Grover, L. (1996). *A Fast Quantum Mechanical Algorithm for Database
  Search.* STOC '96. · Shor, P. (1997). *Polynomial-Time Algorithms for
  Prime Factorization…* SIAM J. Comput. 26(5).

**Systems context**

- Postel, J. (1980). *RFC 761*, §2.10 — the robustness principle behind
  the parser's liberal-scan/strict-validate split (Ch. 5).
- Provider documentation on prompt caching and batch inference —
  consult your provider's current docs; pricing figures in this book are
  illustrative and dated to early 2026.

**Format relatives**

- RFC 822 header syntax; METAR aviation weather code — prior art for
  terse, schema-known channel formats (Ch. 3 §3.5).
- TOON — Token-Oriented Object Notation, 2025 (Ch. 3's comparison
  baseline for token-reduced structured formats).

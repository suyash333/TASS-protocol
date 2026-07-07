# Chapter 8 — Cryptographic Integrity

> *In which records acquire tamper evidence, and every primitive choice is
> justified against both classical and quantum adversaries.*

*(Companion reference: [`docs/CRYPTO.md`](../../docs/CRYPTO.md) — the
operational threat model. This chapter covers the reasoning.)*

## 8.1 Why integrity is TASS's problem

TASS's target workload — high-volume, machine-to-machine, no human ever
reads the wire — is precisely the workload where silent corruption thrives.
A flipped digit in a JSON invoice a human reviews gets caught; a flipped
digit in record 384,112 of a calibration stream does not. And the records
travel:

```
LLM → parser (trust boundary) → queue → storage → analytics, months later
```

Every hop after the parser is an opportunity for bugs, misconfigured
consumers, or attackers to alter data. The integrity layer (`tass/crypto.py`)
lets the first trusted hop attach a MAC so every later hop — or an auditor
long after — can verify nothing changed.

One boundary before anything else, because it is the most common design
error in LLM-adjacent cryptography:

> **Never ask the model to emit its own signature.** A model cannot keep a
> secret key; its output is attacker-influenceable text. Signing happens
> at the first trusted hop — your parser — after validation, never before.

## 8.2 Canonicalization: hashing meaning, not bytes

TASS is order-free (Chapter 3), so two byte-different lines can be the
same record. MACs over raw bytes would make semantically identical
records verify differently — a reordering hop (a queue that re-serializes,
a proxy that normalizes whitespace) would break every tag. The layer
therefore MACs the **canonical form**: keep only `~key:value` pairs, drop
the signature field itself, sort by key, join with single spaces.

```python
canonicalize("~b:2  ~a:1 ~!:oldtag")   # → "~a:1 ~b:2"
```

Corollaries: field reordering and whitespace changes never invalidate a
tag; `hash_record()` (SHA3-256 of canonical form) gives every record a
stable content address usable for deduplication and audit logs.

## 8.3 The primitive choices, and the quantum question

The layer uses three primitives, all symmetric, all stdlib:

| Role | Primitive | Why |
|---|---|---|
| Hash / content address | SHA3-256 | modern margin, distinct lineage from SHA-2 |
| Authentication | HMAC-SHA3-256, truncated to 128-bit tags | NIST SP 800-107-approved truncation; compact on the wire |
| Key derivation | HKDF (RFC 5869) over SHA3-256 | context-separated per-pipeline keys |

The quantum reasoning, spelled out once, carefully:

- **Shor's algorithm** breaks RSA and elliptic-curve cryptography outright
  on a cryptographically relevant quantum computer. The layer contains
  **no public-key material at all**, so Shor has nothing to attack. This
  is post-quantum safety *by construction*, not by adopting new math.
- **Grover's algorithm** provides at most a quadratic speedup on
  brute-force search, reducing a 256-bit key search to ~2¹²⁸ quantum
  operations — beyond any projected feasibility, and even that ignores
  Grover's poor parallelization. This is the same reasoning under which
  NIST classifies AES-256 and SHA-3 as quantum-resistant.
- **Tag truncation** to 128 bits does not help a quantum forger: forgery
  against HMAC requires either the key (Grover-hard) or a lucky guess
  (2⁻¹²⁸ per attempt, online, rate-limitable).

What symmetric MACs *cannot* give is **non-repudiation** — any key holder
can create valid tags, so a MAC proves "someone with the key signed this,"
never "specifically Alice signed this." When third parties must verify
without holding the secret, the correct tool is a post-quantum signature
scheme — ML-DSA (FIPS 204) or SLH-DSA (FIPS 205) — layered at the
application level. That is the roadmap's PQ-signature item, and the
canonical form defined here is deliberately reusable as its message input.

## 8.4 The in-band tag

The tag travels *inside* the record as a `~!:` pair:

```
~t:mc ~l:18k ~h:42k ~g:0 ~!:3vX9kQ2mP8sT1uW4yZ6bCg
```

`!` sits outside the `a–zA–Z` symbol pool, so no schema field can ever
collide with it, and Chapter 5's scanner skips it as an unknown symbol —
**a signed record parses identically to an unsigned one** (test-enforced:
`test_signed_record_still_parses`). The 16-byte tag encodes to 22
base64url characters; signed records need no envelope, no sidecar
metadata, and survive any TASS-clean transport.

## 8.5 Key hygiene in three rules

1. **Derive, don't share.** `derive_key(master, context=b"pipeline-v1")` —
   HKDF context separation means a key extracted from one pipeline's
   config is useless against another's records.
2. **Rotate by context.** Bump the context string (`...-v2`); old records
   verify under the old derived key, which you keep for audit.
3. **Verification is constant-time** (`hmac.compare_digest`) — the
   library refuses to leak tag prefixes through timing, so keep it that
   way: never pre-compare tags with `==` "as a fast path."

And the boundaries, restated from the threat model: the layer provides
integrity only — **no confidentiality** (TLS or payload encryption for
secret values), **no replay protection** (put a timestamp/nonce in the
schema; the MAC covers it, your consumer checks it), and **no proof of
LLM correctness** (a valid tag means unaltered-since-signing, not
extracted-correctly).

## 8.6 Summary

- Sign at the first trusted hop, never inside the model.
- MACs cover a canonical form, so semantically identical records verify
  identically; the same form doubles as a content address.
- Symmetric-only primitives are post-quantum-safe by construction (no
  target for Shor; Grover leaves ≥128-bit margins).
- The in-band `~!` tag makes signed records self-contained and fully
  backward-compatible with every parser in this book.

*Next: assembling all eight chapters into production architectures —
Chapter 9.*

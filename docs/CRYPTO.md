# TASS Cryptographic Integrity Layer

`tass.crypto` adds tamper evidence to TASS records using exclusively
symmetric, post-quantum-safe primitives from the Python standard library
(zero dependencies).

```python
from tass.crypto import TASSSigner, derive_key, hash_record

key = derive_key(b"master-secret-from-your-vault", context=b"weather-pipeline-v1")
signer = TASSSigner(key)

signed = signer.sign_line("~a:Delhi ~c:hz ~d:35.0")
# '~a:Delhi ~c:hz ~d:35.0 ~!:Yx2mP8sT1uW4yZ6bCgQvRw'

signer.verify_line(signed)                       # True
signer.verify_line(signed.replace("35.0", "99")) # False — value tampered
```

Or from the CLI:

```bash
export TASS_KEY="master-secret-from-your-vault"
tass sign "~a:Delhi ~c:hz ~d:35.0" --context weather-pipeline-v1
tass verify "~a:Delhi ~c:hz ~d:35.0 ~!:Yx2m..." --context weather-pipeline-v1
```

---

## Why records need integrity at all

A typical TASS deployment looks like:

```
LLM → parser → message queue → storage → downstream analytics
```

Only the first hop talks to the LLM. Every later hop trusts that the
record it receives is the record the parser emitted. Attaching a MAC at
the trust boundary lets any later hop — or an auditor months later —
prove the record was not modified in the queue, in storage, or by a bug.

This matters most for the workloads TASS targets: high-volume,
machine-to-machine records that no human ever eyeballs, such as
financial extraction results or **quantum-device calibration telemetry**
(see [`examples/quantum_telemetry.tass`](../examples/quantum_telemetry.tass)),
where silently corrupted gate-fidelity numbers would poison every
downstream compilation decision.

---

## Primitive choices and post-quantum rationale

| Purpose | Primitive | Classical security | Post-quantum security |
|---|---|---|---|
| Content hashing | SHA3-256 | 128-bit collision | ~128-bit preimage (Grover: 2^128) |
| Authentication | HMAC-SHA3-256 | 256-bit key | ~128-bit (Grover key search: 2^128) |
| Key derivation | HKDF (RFC 5869) over SHA3-256 | — | inherits the above |

The design rule is simple: **no public-key cryptography anywhere.**
Shor's algorithm breaks RSA and elliptic curves outright on a large
quantum computer; it does nothing against hashes and MACs. Grover's
algorithm gives at most a quadratic speed-up, which 256-bit primitives
absorb with ~128 bits of security to spare. This is the same reasoning
under which NIST considers AES-256 and SHA-3 quantum-resistant.

Truncating the HMAC tag to 128 bits (the default, `tag_bytes=16`) is an
approved construction (NIST SP 800-107). Forgery probability remains
2⁻¹²⁸ per attempt, and truncation does not help a quantum attacker,
because the full internal state never leaves the signer.

## Canonicalization

MACs are computed over a **canonical form** of the record, not its raw
bytes: only `~key:value` pairs are kept, sorted by key, joined by single
spaces, with the signature field excluded. Consequences:

- Field reordering and whitespace changes do **not** invalidate a tag —
  two semantically identical records verify identically.
- The tag is stored *inside* the line (`~!:<tag>`), so a signed record
  is still a valid TASS record: parsers ignore the `!` symbol because it
  is outside the `a-zA-Z` schema pool.

## Key management

- Derive per-pipeline keys with `derive_key(master, context=b"...")`.
  A key leaked from one pipeline then reveals nothing about another.
- Rotate by changing the `context` (e.g. append a version: `...-v2`).
- Feed the CLI via `--key-file` (preferred) or the `TASS_KEY`
  environment variable.

---

## Explicit non-goals (read this before relying on it)

| Property | Provided? | If you need it |
|---|---|---|
| Integrity / tamper evidence | ✅ | — |
| Post-quantum resistance | ✅ | — |
| Confidentiality | ❌ | Encrypt transport (TLS) or payload (AES-256-GCM) |
| Non-repudiation | ❌ | HMAC is symmetric: any key holder can sign. Use ML-DSA (FIPS 204) or SLH-DSA (FIPS 205) if third parties must verify without the secret |
| Replay protection | ❌ | Put a timestamp/nonce field in your schema; the MAC covers it, your consumer must check it |
| LLM output *correctness* | ❌ | A MAC proves the record wasn't altered after signing — not that the LLM extracted the right values |

That last row deserves emphasis: signing happens at the first **trusted**
hop (your parser), never inside the LLM. Do not ask a model to emit its
own signature — it cannot keep a secret key, and anything it produces is
attacker-influenceable text, not cryptography.

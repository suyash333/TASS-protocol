"""
TASS — Tokeniser-Aware Structured Shorthand
Cryptographic integrity layer: canonical hashing, signing, verification.

Design goals
------------
1. Tamper evidence for machine-to-machine pipelines. A TASS record often
   travels: LLM → parser → queue → downstream service. This module lets the
   first trusted hop attach a compact MAC so every later hop can verify the
   record was not altered.

2. Post-quantum safety by construction. Only symmetric primitives are used:
   SHA3-256 for hashing and HMAC-SHA3-256 for authentication. Against a
   quantum adversary, Grover's algorithm reduces the brute-force cost of a
   256-bit primitive to ~2^128 operations — still far beyond feasibility —
   and no quantum algorithm meaningfully breaks HMAC. There is no RSA or
   elliptic-curve material anywhere in this module, hence nothing for
   Shor's algorithm to attack.

3. Token economy. The signature travels inside the record line itself as a
   `~!:<tag>` pair (the `!` symbol is outside the a-zA-Z schema pool, so it
   can never collide with a schema field). A truncated 16-byte tag encodes
   to 22 base64url characters — a handful of tokens on top of the record.

What this module does NOT do
----------------------------
- Confidentiality. Records are authenticated, not encrypted. If the values
  are secret, encrypt the transport (TLS) or the payload separately.
- Non-repudiation. HMAC is symmetric: any key holder can create valid tags.
  For third-party-verifiable signatures use a post-quantum signature scheme
  (ML-DSA / SLH-DSA, FIPS 204/205) at the application layer.
- Replay protection. Include a timestamp or nonce field in your schema and
  check it downstream; the MAC covers it automatically.

Usage
-----
::

    from tass.crypto import TASSSigner, hash_record, derive_key

    key = derive_key(master_secret, context=b"influencer-pipeline-v1")
    signer = TASSSigner(key)

    signed = signer.sign_line("~t:mc ~l:18k ~h:42k ~g:0")
    # '~t:mc ~l:18k ~h:42k ~g:0 ~!:3vX9kQ2mP8sT1uW4yZ6bCg'

    signer.verify_line(signed)   # True — raises nothing, constant-time
"""

from __future__ import annotations

import base64
import hashlib
import hmac

# Signature field marker. '!' is deliberately outside the a-zA-Z symbol pool
# used by SchemaCompiler, so it can never collide with a schema field.
SIG_SYMBOL = "!"

# 16-byte (128-bit) truncated HMAC tag. Truncating HMAC output is an
# approved construction (NIST SP 800-107); 128 bits keeps forgery
# probability negligible while costing ~22 base64url characters per record.
DEFAULT_TAG_BYTES = 16

_HASH = hashlib.sha3_256
_HASH_LEN = 32


# ── Canonicalization ──────────────────────────────────────────────────


def canonicalize(line: str, prefix_char: str = "~") -> str:
    """
    Reduce a TASS record line to a canonical byte-stable form so that
    cosmetic differences (field order, extra whitespace) do not change
    its hash or MAC.

    Rules: keep only `~key:value` pairs, sort by key, join with single
    spaces. The signature field itself is always excluded.
    """
    pairs = []
    for token in line.strip().split():
        if not token.startswith(prefix_char) or ":" not in token:
            continue
        key, _, value = token[len(prefix_char):].partition(":")
        if key == SIG_SYMBOL:
            continue
        pairs.append((key, value))
    pairs.sort()
    return " ".join(f"{prefix_char}{k}:{v}" for k, v in pairs)


def hash_record(line: str, prefix_char: str = "~") -> str:
    """
    Content-address a TASS record: SHA3-256 over its canonical form,
    returned as lowercase hex. Two records with the same fields and
    values hash identically regardless of field order.
    """
    canonical = canonicalize(line, prefix_char)
    return _HASH(canonical.encode("utf-8")).hexdigest()


# ── Key derivation (HKDF, RFC 5869, with SHA3-256) ────────────────────


def derive_key(
    master_secret: bytes,
    context: bytes = b"",
    salt: bytes = b"",
    length: int = 32,
) -> bytes:
    """
    Derive a per-pipeline signing key from a master secret using
    HKDF-SHA3-256. Give each pipeline / schema its own `context` string
    so a key compromised in one pipeline is useless in another.
    """
    if not master_secret:
        raise ValueError("master_secret must not be empty")
    if not 1 <= length <= 255 * _HASH_LEN:
        raise ValueError(f"length must be in [1, {255 * _HASH_LEN}]")

    # HKDF-Extract
    prk = hmac.new(salt or b"\x00" * _HASH_LEN, master_secret, _HASH).digest()

    # HKDF-Expand
    okm = b""
    block = b""
    counter = 1
    while len(okm) < length:
        block = hmac.new(prk, block + context + bytes([counter]), _HASH).digest()
        okm += block
        counter += 1
    return okm[:length]


# ── Signing / verification ────────────────────────────────────────────


class TASSSigner:
    """
    Attach and verify compact HMAC-SHA3-256 tags on TASS record lines.

    Parameters
    ----------
    key : bytes
        Signing key, minimum 16 bytes; 32 bytes recommended
        (use :func:`derive_key`).
    tag_bytes : int
        Truncated tag length in bytes (default 16 = 128-bit tags).
    prefix_char : str
        The TASS prefix symbol (default "~").
    """

    def __init__(self, key: bytes, tag_bytes: int = DEFAULT_TAG_BYTES,
                 prefix_char: str = "~"):
        if len(key) < 16:
            raise ValueError("key must be at least 16 bytes")
        if not 8 <= tag_bytes <= _HASH_LEN:
            raise ValueError(f"tag_bytes must be in [8, {_HASH_LEN}]")
        self._key = key
        self.tag_bytes = tag_bytes
        self.prefix = prefix_char

    # -- single records -------------------------------------------------

    def sign_line(self, line: str) -> str:
        """Return the record line with a `~!:<tag>` pair appended."""
        tag = self._tag(line)
        return f"{line.strip()} {self.prefix}{SIG_SYMBOL}:{tag}"

    def verify_line(self, signed_line: str) -> bool:
        """
        Constant-time verification. Returns True if the embedded tag
        matches the record content; False if the tag is absent or wrong.
        """
        embedded = self._extract_tag(signed_line)
        if embedded is None:
            return False
        expected = self._tag(signed_line)
        return hmac.compare_digest(embedded, expected)

    # -- batches (e.g. an entire @records block) ------------------------

    def sign_records(self, lines: list[str]) -> list[str]:
        """Sign every line in a batch."""
        return [self.sign_line(line) for line in lines]

    def verify_records(self, signed_lines: list[str]) -> list[bool]:
        """Verify every line; returns one bool per line."""
        return [self.verify_line(line) for line in signed_lines]

    # -- internals -------------------------------------------------------

    def _tag(self, line: str) -> str:
        canonical = canonicalize(line, self.prefix)
        mac = hmac.new(self._key, canonical.encode("utf-8"), _HASH).digest()
        return base64.urlsafe_b64encode(mac[: self.tag_bytes]).rstrip(b"=").decode("ascii")

    def _extract_tag(self, line: str) -> str | None:
        marker = f"{self.prefix}{SIG_SYMBOL}:"
        for token in line.strip().split():
            if token.startswith(marker):
                return token[len(marker):]
        return None


class TASSIntegrityError(ValueError):
    """Raised by callers that treat a failed verification as fatal."""

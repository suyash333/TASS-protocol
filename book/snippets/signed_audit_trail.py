#!/usr/bin/env python3
"""
Chapters 8/9/10 companion — Pattern II (the signed firehose) end to end,
using the real quantum-telemetry example file as the workload:

    sign at the trust boundary → ship raw lines → verify at the consumer
    → dedup via content address → detect tampering and replay.

    python book/snippets/signed_audit_trail.py

This is the cryptographic use case as a complete, working pipeline.
"""

from pathlib import Path

from tass import TASSFileParser
from tass.crypto import TASSSigner, derive_key, hash_record

REPO = Path(__file__).resolve().parents[2]
TELEMETRY = REPO / "examples" / "quantum_telemetry.tass"

# ── Producer side: the calibration pipeline (trust boundary) ──────────

master = b"lab-master-secret-from-vault"
signer = TASSSigner(derive_key(master, context=b"quantum-cal-v1"))

tfile = TASSFileParser().parse_file(TELEMETRY)
queue = signer.sign_records(tfile.raw_records)        # what actually ships

# ── Transit: things that happen to messages in real systems ───────────

queue.append(queue[0])                                # at-least-once redelivery
tampered = queue[2].replace("~s:0.00044", "~s:0.00004")  # gate error "improved"
queue[2] = tampered
reordered = " ".join(reversed(queue[3].split()))      # a hop reorders fields
queue[3] = reordered

# ── Consumer side: verify → dedup → accept ────────────────────────────

parser_map = tfile.to_parser_map()
seen: set[str] = set()
accepted, rejected, duplicates = [], [], []

for line in queue:
    if not signer.verify_line(line):                  # constant-time MAC check
        rejected.append(line)
        continue
    digest = hash_record(line)                        # canonical content address
    if digest in seen:                                # replay/redelivery dedup
        duplicates.append(line)
        continue
    seen.add(digest)
    accepted.append(line)

print(f"shipped    : {len(queue)} messages "
      f"({len(tfile.raw_records)} records + 1 redelivery, 1 tampered in transit)")
print(f"accepted   : {len(accepted)}  (includes the field-reordered line — "
      f"canonicalization makes reordering harmless)")
print(f"rejected   : {len(rejected)}  (the tampered gate-error record)")
print(f"deduplicated: {len(duplicates)}  (redelivered copy, caught by hash_record)")

assert len(rejected) == 1 and "0.00004" in rejected[0]
assert len(duplicates) == 1
assert any(line == reordered for line in accepted)

# The audit property: months later, anyone holding the derived key can
# re-verify the archive without trusting the storage layer.
archive_ok = all(signer.verify_line(line) for line in accepted)
print(f"audit replay: all {len(accepted)} archived records re-verify → {archive_ok}")

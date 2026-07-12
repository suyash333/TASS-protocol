# Chapter 11 — TASS Beyond the LLM

> *In which the format outgrows its origin story. The tokenizer motivated
> TASS; nothing in the format requires one.*

## 11.1 What TASS actually is, once you remove the LLM

Strip away Chapters 1–2 and examine what remains: a **flat, order-free,
self-delimiting, single-line, pure-ASCII record format with out-of-band
key and value dictionaries and in-band authentication.** That property
list is valuable on any channel where one or more of these units is
scarce:

| Scarce unit | Channel examples | §
|---|---|---|
| Bytes on air | LoRaWAN, NB-IoT, satellite, APRS | 11.2 |
| Characters per message | SMS, USSD, pager, chain memos | 11.3 |
| Pixels / modules | QR codes, NFC tags, barcodes | 11.4 |
| Storage × retention | structured logs, audit archives | 11.5 |
| URL length & readability | deep links, webhook state | 11.6 |
| Human attention | field data collection, ops runbooks | 11.7 |

One framing change first. In LLM pipelines the budget unit was the token;
here it is the **byte or character**, and the honest comparison set
changes with it: the competitor is no longer JSON alone but binary
formats — CBOR, protobuf, custom bitfields — which will *always* beat
TASS on pure bytes. TASS's claim on these channels is therefore never
"smallest possible" but a specific trade:

> **Within ~1.5–2× of binary size, TASS stays printable, grep-able,
> diff-able, hand-typable, and debuggable over a serial console — with
> no schema compiler, no codegen step, and no special tooling on either
> end.**

Where that trade is wrong (firmware-to-firmware links with mature
protobuf toolchains, multi-megabyte payloads), use the binary format.
The sections below are the channels where it is right.

## 11.2 Constrained telemetry: IoT, LPWAN, and remote sensing

**The constraint.** LoRaWAN payloads run 51–222 bytes depending on data
rate; every byte costs airtime, battery, and regulatory duty-cycle
budget. Satellite IoT (Swarm-class) bills per ~192-byte packet.

**The fit.** A fixed-schema sensor record is the LLM-extraction workload
with the transmitter swapped: same fields every time, receiver knows the
schema, nobody reads the wire — except that *somebody occasionally does*,
over a serial console at a muddy field site, which is exactly when a
printable format saves the day.

[`examples/iot_sensor.tass`](../../examples/iot_sensor.tass) implements
an agricultural soil-sensor fleet:

```
~n:a3 ~t:23.4 ~m:31 ~p:6.8 ~b:87 ~s:ok
```

38 bytes for node id, temperature, moisture, pH, battery, and status —
inside even the 51-byte LoRa DR0 budget, against 93 bytes as minified
JSON (measured by `payload_budgets.py`). A CBOR encoding runs ~28 bytes;
the ~10-byte premium buys `grep '~s:lo' fleet.log` working on the raw
capture and a technician reading packets off a UART with no tooling.

Two channel-specific practices:

- **The dictionary ships in the device docs, not the packet** — the
  `.tass` file (Ch. 6) is the interface contract between firmware and
  ingest, versioned in git like any registry schema (Ch. 9 §9.4).
- **Signing at the gateway, not the node** (Ch. 8's trust-boundary rule
  transplanted): constrained nodes use the link layer's native crypto;
  the gateway — the first hop that speaks TCP — signs the TASS line
  before it enters your queue, and Pattern II (Ch. 9 §9.3) proceeds
  unchanged.

## 11.3 Character-budget messaging: SMS, USSD, and chain memos

**The constraint.** One SMS segment is 160 GSM-7 characters; exceed it
and cost doubles and delivery atomicity vanishes. USSD sessions cap
around 182. Blockchain memo fields are harsher still (Stellar: 28 bytes
text). These channels are ASCII-hostile to binary formats — base64
inflates binary by 33% and survives being *typed by a human* poorly.

**The fit.** TASS is already in the channel's native alphabet. A mobile
money confirmation:

```
~x:p ~a:1450 ~c:KES ~r:254712345678 ~i:TX88412 ~s:ok
```

52 characters — one third of an SMS segment, leaving room for a `~!` tag
(78 signed) so the receiving system can authenticate the confirmation
*through* an untrusted SMS aggregator. The same record as JSON is 102
characters and one added field away from a second segment.
[`snippets/payload_budgets.py`](../snippets/payload_budgets.py) computes
exact fits for every budget in this chapter, signed and unsigned.

This is also where TASS's ancestry (Ch. 3 §3.5) completes its circle:
METAR and amateur-radio exchange formats solved character-priced
channels a century ago with the same move — short codes plus a shared
dictionary. TASS is that move with a validation-and-signing layer.

## 11.4 Optical and near-field: QR codes and NFC tags

**The constraint.** QR capacity is quantized: a shorter payload means a
lower QR version, physically larger modules, and better scans at
distance, at angle, and on damaged labels. NTAG213 NFC stickers hold
~144 bytes total.

**The fit.** Asset tags, event tickets, lab-sample labels — flat records
with a known schema, read by machines, occasionally squinted at by
humans. A signed equipment tag:

```
~i:EQ-4471 ~k:pump ~l:B2 ~d:2026-03 ~!:hV2nQ8rT1mW4yZ6b
```

~60 bytes → QR version 3 with medium error correction, and the `~!` tag
makes the *sticker itself* tamper-evident: a photocopied tag with an
edited location fails `tass verify` at the scanner. The alternative —
URL-to-database-row — requires connectivity at scan time; the TASS tag
carries its payload and its proof offline. (Deep-link hybrids belong in
§11.6.)

## 11.5 Structured logging and audit archives

**The constraint.** Log volume × retention is a storage bill and a query
latency; and modern practice already rejected JSON logs once — that is
what **logfmt** (`level=info msg="..." dur=23ms`) is.

**The fit.** TASS is logfmt taken one step further: single-char keys via
a dictionary, codes for enums, and — the part logfmt lacks entirely — a
canonical form with in-band MACs (Ch. 8), which turns an application log
into an *audit log* whose lines can be re-verified years later
(`signed_audit_trail.py` demonstrated exactly this for telemetry).

[`snippets/tass_logger.py`](../snippets/tass_logger.py) implements the
whole idea as a stdlib `logging.Formatter`:

```python
handler.setFormatter(TASSLogFormatter(LOG_SCHEMA))
log.info("checkout", extra={"user": "u_812", "route": "/pay", "ms": 231})
# emits: ~t:1751888100 ~l:i ~e:co ~u:u_812 ~r:/pay ~d:231
```

The "store compact, view expanded" pattern (Ch. 9 §9.6) was designed for
this: `grep`/`awk` operate on raw lines; the dashboard expands through
the dictionary at view time. Measured on the snippet's synthetic
workload, TASS lines run ~40% smaller than equivalent JSON log lines —
compounding across every replica, shipper, index, and retention day.

## 11.6 URL state and deep links

**The constraint.** URLs face practical length limits, aggressive
truncation in chat apps and email clients, and human eyes.

**The fit.** Filter state, referral context, pagination cursors —
`?q=~s:electronics+~x:100+~y:500+~o:pd` is shorter than its query-param
equivalent, one *value* rather than N parameters (survives frameworks
that mangle repeated params), and order-free (two users' links to the
same view canonicalize to the same string — a cache key, via
`hash_record`). Percent-encoding cost is minimal since the alphabet is
already URL-safe ASCII apart from the space separator (encode as `+`).
For share-links that must not be forged — signed discount state, signed
report views — the `~!` tag rides along.

## 11.7 Human-mediated records: field data collection

**The constraint.** Clipboard-and-biro digitization: agricultural
surveys, cold-chain checks, utility meter reads. The scarce resources are
transcription effort and error rate, not bytes.

**The fit.** A TASS line is *dictate-able and typeable*: "tilde-t 23.4,
tilde-m 31, tilde-s ok" — and the parser's validation catches the two
classic transcription failures (missing field: F3 by name; malformed
pair: dropped, not guessed — Ch. 5 §5.8). Codes tables double as the
enumerator's cheat card, which is printed on the *back of the clipboard*.
This is the lowest-tech use case in the book and the one closest to
classical stenography — a human writing shorthand against a shared
dictionary — which is where the whole idea began.

## 11.8 The general selection rule

Six channels, one pattern. TASS fits a channel when **all four** hold:

1. Records are **flat and fixed-schema** (Ch. 3's boundary is unchanged).
2. The channel prices **characters or bytes** (or human effort) —
   and something in the loop is helped by the payload staying
   **printable ASCII**: a console, a human, an SMS gateway, a QR
   scanner, `grep`.
3. The **dictionary can travel out of band** — device docs, registry,
   clipboard card.
4. If the record will be *acted on*, the channel can afford ~22 extra
   characters for the `~!` tag.

Fail condition 2 and binary wins; fail 1 and JSON/CBOR's nesting wins;
fail 3 and self-describing formats win. Everything else in this book —
the registry, the ladder discipline (minus the LLM-specific rungs), the
signing patterns, the observability stance — transfers to these channels
without modification, because none of it ever depended on the tokenizer.

## 11.9 Summary

- Remove the LLM and TASS remains a compact printable record format for
  byte-, character-, and attention-priced channels: LPWAN telemetry,
  SMS/USSD/memo fields, QR/NFC payloads, structured logs, URL state,
  and field data capture.
- Against binary formats the pitch is explicit: ~1.5–2× the bytes for
  zero toolchain and full grep-ability; where that trade is wrong, use
  the binary format.
- The dictionary-out-of-band and sign-at-the-trust-boundary disciplines
  transfer unchanged; only the budget arithmetic (tokens → bytes) is
  new, and `payload_budgets.py` does it for every channel here.

*This closes the format's story arc: born from a tokenizer's pricing
table, generalized to every channel that prices what it carries.*

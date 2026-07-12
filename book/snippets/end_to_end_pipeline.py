#!/usr/bin/env python3
"""
Chapters 4/5/9 companion — Pattern I, the synchronous extraction service,
end to end: compile → (mock) LLM → parse → validate → business rules → sign.

    python book/snippets/end_to_end_pipeline.py

Replace `mock_llm` with your provider call; everything else is production
shape. Note what happens at deploy time vs per request.
"""

from tass import SchemaCompiler, TASSParser, TASSValidationError
from tass.crypto import TASSSigner, derive_key

# ── Deploy time (once) — Ch. 4 ────────────────────────────────────────

SCHEMA = {
    "user_intent":      "string",    # enum: refund|cancel|upgrade|question
    "urgency_level":    "integer",   # 1-5
    "requires_routing": "boolean",
}

PARSER_MAP, SYSTEM_PROMPT = SchemaCompiler().compile(SCHEMA)
PARSER = TASSParser(dictionary_map=PARSER_MAP)
SIGNER = TASSSigner(derive_key(b"demo-master-secret", context=b"ticket-routing-v1"))

# One-shot example appended for small-model hardening (Ch. 4 §4.2)
SYSTEM_PROMPT += "\nExample: ~a:refund ~b:5 ~c:true"


def mock_llm(system: str, user: str) -> str:
    """Stand-in for your provider. Note the realistic contamination."""
    return "Sure! Here you go:\n```\n~a:refund ~b:5 ~c:true\n```"


def business_rules(record: dict) -> dict:
    """Semantic validation lives ABOVE the parser (Ch. 5 §5.8)."""
    if not 1 <= record["urgency_level"] <= 5:
        raise ValueError(f"urgency out of range: {record['urgency_level']}")
    if record["user_intent"] not in {"refund", "cancel", "upgrade", "question"}:
        raise ValueError(f"unknown intent: {record['user_intent']}")
    return record


# ── Hot path (per request) — Ch. 5, Ch. 9 §9.2 ────────────────────────

def handle(ticket_text: str) -> tuple[dict, str]:
    """The parse boundary: one function, one owner, one metrics emitter."""
    raw = mock_llm(SYSTEM_PROMPT, ticket_text)

    record = PARSER.safe_parse(raw)      # rung 1 of the ladder
    PARSER.validate(record)              # F3: missing fields, by name
    record = business_rules(record)      # semantic layer

    # Sign the canonical wire line at the trust boundary (Ch. 8, 9 §9.3)
    wire_line = raw.splitlines()[-2].strip()          # the record line
    signed = SIGNER.sign_line(wire_line)
    return record, signed


if __name__ == "__main__":
    record, signed = handle("I was double charged, please refund ASAP!!")
    print("system prompt (cached prefix):\n" + SYSTEM_PROMPT, end="\n\n")
    print("typed record :", record)
    print("signed line  :", signed)
    print("verifies     :", SIGNER.verify_line(signed))

    try:
        PARSER.validate({"user_intent": "refund"})
    except TASSValidationError as e:
        print("F3 example   :", e)

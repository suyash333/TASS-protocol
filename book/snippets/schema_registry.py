#!/usr/bin/env python3
"""
Chapter 9 §9.4 companion — a minimal versioned schema registry with
`.tass` files as the source of truth.

    python book/snippets/schema_registry.py

Demonstrates: immutable versions, producer-pins/consumer-tolerates, and
additive evolution surviving version skew (a v1 consumer reading v2
records). Uses a temp directory; point REGISTRY_ROOT at a git repo in
production.
"""

import tempfile
from pathlib import Path

from tass import TASSFileParser, TASSParser

V1 = """\
@dict
  ~a = user_intent
  ~b = urgency_level
@end
@codes
  rf = refund
  cn = cancel
@end
"""

# Additive-only evolution (Ch. 9 rule 3): v2 appends ~c, touches nothing else.
V2 = V1.replace("@end\n@codes", "  ~c = requires_routing\n@end\n@codes")


class SchemaRegistry:
    """Versions are immutable files: publish never overwrites."""

    def __init__(self, root: Path):
        self.root = root

    def publish(self, name: str, version: int, content: str) -> Path:
        path = self.root / name / f"v{version}.tass"
        if path.exists():
            raise FileExistsError(f"{path.name} is published and immutable")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def load(self, name: str, version: int):
        """→ (parser, codes) for a pinned version."""
        tfile = TASSFileParser().parse_file(self.root / name / f"v{version}.tass")
        return TASSParser(dictionary_map=tfile.to_parser_map()), tfile.codes


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        reg = SchemaRegistry(Path(tmp))
        reg.publish("ticket_routing", 1, V1)
        reg.publish("ticket_routing", 2, V2)

        try:                                   # immutability enforced
            reg.publish("ticket_routing", 2, "@dict\n  ~a = hacked\n@end\n")
        except FileExistsError as e:
            print("immutable      :", e)

        # Producer pins v2; consumer still runs v1 (version skew)
        v2_record = "~a:rf ~b:5 ~c:true"
        v1_parser, v1_codes = reg.load("ticket_routing", 1)

        parsed = v1_parser.parse(v2_record)    # unknown ~c skipped (Ch. 3)
        parsed = {k: v1_codes.get(v, v) if isinstance(v, str) else v
                  for k, v in parsed.items()}  # expand codes server-side

        print("v1 reads v2    :", parsed)
        print("               : new field ignored, no error — additive evolution")

        v2_parser, v2_codes = reg.load("ticket_routing", 2)
        parsed_v2 = {k: v2_codes.get(v, v) for k, v in v2_parser.parse(v2_record).items()}
        print("v2 reads v2    :", parsed_v2)

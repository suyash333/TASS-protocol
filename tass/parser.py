"""
TASS — Tokeniser-Aware Structured Shorthand
Parser and Schema Compiler

White paper: https://doi.org/10.5281/zenodo.20403219
License    : MIT
"""

import string
import json
import re


class SchemaCompiler:
    """
    Compiles a plain Python dict schema into a TASS system prompt
    and the corresponding parser map.

    Usage
    -----
    compiler = SchemaCompiler()
    parser_map, system_prompt = compiler.compile({
        "tier":       "string",
        "rate_low":   "integer",
        "gst":        "boolean",
    })
    """

    def __init__(self, prefix_char: str = "~"):
        self.prefix = prefix_char
        # Single-char pool: a-z then A-Z = 52 slots
        self.token_pool = list(string.ascii_lowercase + string.ascii_uppercase)

    def compile(self, client_json_schema: dict) -> tuple[dict, str]:
        """
        Parameters
        ----------
        client_json_schema : dict
            Keys are field names; values are type hints
            ("string" | "integer" | "float" | "boolean").

        Returns
        -------
        reverse_map : dict
            Maps short char → (field_name, type_hint)
        system_prompt : str
            Ready to inject as the LLM system prompt.
        """
        schema_keys = list(client_json_schema.keys())

        if len(schema_keys) > len(self.token_pool):
            raise ValueError(
                f"Schema has {len(schema_keys)} fields but the single-byte "
                f"token pool only supports {len(self.token_pool)}. "
                "Split into sub-schemas or use two-char symbols."
            )

        reverse_map = {}
        format_parts = []
        dict_lines = []

        for i, key in enumerate(schema_keys):
            sym = self.token_pool[i]
            type_hint = client_json_schema[key]
            reverse_map[sym] = (key, type_hint)
            format_parts.append(f"{self.prefix}{sym}:<value>")
            dict_lines.append(f"  {self.prefix}{sym} = {key}")

        lines = [
            "You are a data extraction engine.",
            "Output ONLY the TASS format below. No prose. No markdown. No explanation.",
            f"Format: {' '.join(format_parts)}",
            "Dictionary:",
        ] + dict_lines

        return reverse_map, "\n".join(lines)


class TASSParser:
    """
    Parses a raw TASS string back into a typed Python dict.

    Features
    --------
    - Type coercion  : integer, float, boolean, string
    - k-suffix       : "18k" → 18000, "1.5k" → 1500
    - Validation     : checks all expected fields are present
    - JSON fallback  : safe_parse() retries with a JSON parser on failure

    Usage
    -----
    parser = TASSParser(dictionary_map=parser_map)
    result = parser.parse("~a:refund ~b:5 ~c:true")
    # {'user_intent': 'refund', 'urgency_level': 5, 'requires_routing': True}
    """

    def __init__(self, dictionary_map: dict, prefix_char: str = "~"):
        """
        Parameters
        ----------
        dictionary_map : dict
            Output of SchemaCompiler.compile() — maps char → (field, type).
            Also accepts legacy maps of char → field_name (str) for
            backwards compatibility.
        prefix_char : str
            The prefix symbol used (default "~").
        """
        self.prefix = prefix_char
        # Normalise legacy maps that store only field names (not tuples)
        self.dictionary = {}
        for k, v in dictionary_map.items():
            if isinstance(v, tuple):
                self.dictionary[k] = v
            else:
                self.dictionary[k] = (v, "string")

    # ── Public API ────────────────────────────────────────────────────

    def parse(self, raw_llm_output: str) -> dict:
        """
        Parse a TASS string.  Raises TASSParseError on failure.
        """
        cleaned = self._strip_markdown(raw_llm_output)
        return self._parse_line(cleaned)

    def safe_parse(self, raw_llm_output: str) -> dict:
        """
        Try TASS parsing first.  If it fails or returns incomplete
        fields, attempt JSON parsing as a fallback.
        Returns a dict on success; raises TASSParseError if both fail.
        """
        try:
            result = self.parse(raw_llm_output)
            self._validate(result)
            return result
        except (TASSParseError, TASSValidationError):
            pass

        # JSON fallback
        try:
            cleaned = self._strip_markdown(raw_llm_output)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        raise TASSParseError(
            f"Could not parse output as TASS or JSON: {raw_llm_output!r}"
        )

    def validate(self, parsed: dict) -> None:
        """Raise TASSValidationError if any expected fields are missing."""
        self._validate(parsed)

    # ── Internal helpers ──────────────────────────────────────────────

    def _parse_line(self, line: str) -> dict:
        parsed = {}
        pairs = line.strip().split()

        for pair in pairs:
            if not pair.startswith(self.prefix) or ":" not in pair:
                continue
            rest = pair[len(self.prefix):]
            key, _, raw_val = rest.partition(":")
            if key not in self.dictionary:
                continue
            field_name, type_hint = self.dictionary[key]
            parsed[field_name] = self._coerce(raw_val, type_hint)

        return parsed

    def _coerce(self, value: str, type_hint: str):
        """Convert a raw string value to the declared Python type."""
        v = value.strip()

        if type_hint == "boolean":
            return v.lower() in ("true", "1", "yes")

        if type_hint == "integer":
            return int(self._expand_k(v))

        if type_hint == "float":
            return float(self._expand_k(v))

        # string — return as-is (may still be a numeric code like "mc")
        return v

    @staticmethod
    def _expand_k(value: str) -> str:
        """Expand k-suffix shorthand: '18k' → '18000', '1.5k' → '1500'."""
        if value.lower().endswith("k"):
            numeric = value[:-1]
            try:
                return str(int(float(numeric) * 1000))
            except ValueError:
                pass
        return value

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Remove code fences that some models add around output."""
        text = re.sub(r"```[a-z]*\n?", "", text)
        text = text.strip("`").strip()
        # Return only the first line that looks like a TASS record
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("~"):
                return line
        return text

    def _validate(self, parsed: dict) -> None:
        expected = {v[0] for v in self.dictionary.values()}
        missing = expected - set(parsed.keys())
        if missing:
            raise TASSValidationError(
                f"Missing fields in TASS output: {sorted(missing)}"
            )


# ── Exceptions ────────────────────────────────────────────────────────

class TASSParseError(ValueError):
    """Raised when a TASS string cannot be parsed."""


class TASSValidationError(ValueError):
    """Raised when a parsed TASS record is missing expected fields."""

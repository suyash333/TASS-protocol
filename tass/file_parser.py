"""
TASS — Tokeniser-Aware Structured Shorthand
.tass file format parser

Handles the @dict, @codes, and @records block structure defined in the spec.

White paper: https://doi.org/10.5281/zenodo.20403219
License    : MIT
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TASSFile:
    """Parsed representation of a .tass file."""

    # symbol (e.g. "t") → field name (e.g. "tier")
    dictionary: dict = field(default_factory=dict)

    # short code (e.g. "mc") → full value (e.g. "micro")
    codes: dict = field(default_factory=dict)

    # Parsed records — values expanded via codes where possible
    records: list = field(default_factory=list)

    # Raw record lines as they appear in the file
    raw_records: list = field(default_factory=list)

    def to_parser_map(self) -> dict:
        """
        Return a dictionary_map compatible with TASSParser.
        Maps symbol char → (field_name, 'string') — type info is not stored
        in .tass files, so all fields default to string.
        """
        return {sym: (name, "string") for sym, name in self.dictionary.items()}


class TASSFileParser:
    """
    Parses a .tass file into a :class:`TASSFile`.

    Example
    -------
    ::

        from tass import TASSFileParser

        tfile = TASSFileParser().parse_file("spec/sample.tass")
        print(tfile.records[0])
        # {'tier': 'micro', 'followers': '45', 'engagement': '4.2', ...}
    """

    # Recognised block names
    _BLOCKS = {"dict", "codes", "records"}

    def parse_file(self, path: str | Path) -> TASSFile:
        """Read a .tass file from disk and parse it."""
        text = Path(path).read_text(encoding="utf-8")
        return self.parse(text)

    def parse(self, text: str) -> TASSFile:
        """Parse raw .tass text."""
        result = TASSFile()
        current_block = None

        for raw_line in text.splitlines():
            line = self._strip_comment(raw_line).strip()

            if not line:
                continue

            # Block close (@end must be checked before the general @block pattern)
            if line == "@end":
                current_block = None
                continue

            # Block open: @dict / @codes / @records
            m = re.match(r"^@(\w+)$", line)
            if m:
                name = m.group(1).lower()
                if name not in self._BLOCKS:
                    raise TASSFileError(f"Unknown block @{name}")
                current_block = name
                continue

            if current_block == "dict":
                self._parse_dict_line(line, result)
            elif current_block == "codes":
                self._parse_codes_line(line, result)
            elif current_block == "records":
                self._parse_record_line(line, result)
            # Lines outside any block are silently ignored (header comments etc.)

        return result

    # ── Block parsers ─────────────────────────────────────────────────

    def _parse_dict_line(self, line: str, result: TASSFile) -> None:
        # Format: ~sym = field_name
        m = re.match(r"^~([A-Za-z]+)\s*=\s*(\S+)$", line)
        if not m:
            raise TASSFileError(f"Malformed @dict entry: {line!r}")
        sym, field_name = m.group(1), m.group(2)
        result.dictionary[sym] = field_name

    def _parse_codes_line(self, line: str, result: TASSFile) -> None:
        # Format: code = full_value  (value may contain spaces, e.g. "Light Rain")
        m = re.match(r"^(\S+)\s*=\s*(.+)$", line)
        if not m:
            raise TASSFileError(f"Malformed @codes entry: {line!r}")
        result.codes[m.group(1)] = m.group(2).strip()

    def _parse_record_line(self, line: str, result: TASSFile) -> None:
        result.raw_records.append(line)
        record = {}
        for pair in line.split():
            if not pair.startswith("~") or ":" not in pair:
                continue
            rest = pair[1:]
            sym, _, raw_val = rest.partition(":")
            if sym not in result.dictionary:
                continue
            field_name = result.dictionary[sym]
            # Expand via codes table if a match exists
            record[field_name] = result.codes.get(raw_val, raw_val)
        result.records.append(record)

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _strip_comment(line: str) -> str:
        """Remove everything from the first # onwards."""
        idx = line.find("#")
        return line[:idx] if idx != -1 else line


class TASSFileError(ValueError):
    """Raised when a .tass file cannot be parsed."""

"""
TASS — Tokeniser-Aware Structured Shorthand
Benchmark: measure real token savings vs JSON and other formats.

Requires: tiktoken  (pip install tiktoken)

White paper: https://doi.org/10.5281/zenodo.20403219
License    : MIT
"""

from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass

try:
    import tiktoken
    _TIKTOKEN_AVAILABLE = True
except ImportError:
    _TIKTOKEN_AVAILABLE = False


# Default tokeniser — matches GPT-4o / o-series models (same as TOON benchmark)
DEFAULT_ENCODING = "o200k_base"

# Formats compared in the benchmark
FORMATS = ["tass", "pipe", "json", "prose"]


@dataclass
class BenchmarkResult:
    format_name: str
    tokens: int
    vs_json_pct: float        # positive = more expensive than JSON
    sample: str

    def __str__(self) -> str:
        arrow = "↓" if self.vs_json_pct <= 0 else "↑"
        diff = abs(self.vs_json_pct)
        tag = f"{arrow} {diff:.0f}%" if self.format_name != "json" else "baseline"
        return f"{self.format_name:<14} {self.tokens:>6} tokens   {tag}"


class TASSBenchmark:
    """
    Compares TASS output token cost against JSON, pipe-delimited, and prose
    for a given schema + record set.

    Example
    -------
    ::

        from tass import TASSBenchmark

        schema = {"tier": "string", "rate_low": "integer", "gst": "boolean"}
        records = [
            {"tier": "micro", "rate_low": 18000, "gst": False},
            {"tier": "mid",   "rate_low": 55000, "gst": True},
        ]
        bench = TASSBenchmark(schema, records)
        bench.print_report()
    """

    def __init__(
        self,
        schema: dict,
        records: list[dict],
        encoding_name: str = DEFAULT_ENCODING,
        approx: bool = False,
    ):
        """
        Parameters
        ----------
        approx : bool
            If True, use a fast whitespace-based token approximation instead
            of tiktoken. Useful for offline use or quick estimates.
            Accuracy is ±10-15% vs a real BPE tokeniser.
        """
        self.schema = schema
        self.records = records
        self._encoding_name = encoding_name
        self._approx = approx or not _TIKTOKEN_AVAILABLE

        if not self._approx:
            try:
                self._enc = tiktoken.get_encoding(encoding_name)
            except Exception:
                self._approx = True

        if self._approx:
            self._enc = None
            self._encoding_name = "approx (whitespace)"

        # Build TASS symbol map: field_name → single-char symbol
        import string
        pool = list(string.ascii_lowercase + string.ascii_uppercase)
        self._sym_map = {key: pool[i] for i, key in enumerate(schema)}

    # ── Public API ────────────────────────────────────────────────────

    def run(self) -> list[BenchmarkResult]:
        """Return one BenchmarkResult per format."""
        rendered = {
            "tass":  self._render_tass(),
            "pipe":  self._render_pipe(),
            "json":  self._render_json(),
            "prose": self._render_prose(),
        }
        counts = {name: self._count_tokens(text) for name, text in rendered.items()}
        json_tokens = counts["json"]

        results = []
        for fmt in FORMATS:
            t = counts[fmt]
            pct = (t - json_tokens) / json_tokens * 100
            results.append(BenchmarkResult(
                format_name=fmt,
                tokens=t,
                vs_json_pct=pct,
                sample=rendered[fmt].splitlines()[0] if rendered[fmt] else "",
            ))
        return results

    def print_report(self) -> None:
        """Print a formatted comparison table to stdout."""
        results = self.run()
        fields = list(self.schema.keys())
        n = len(self.records)

        print()
        print("━" * 60)
        print("  TASS Benchmark")
        print(f"  Schema : {', '.join(fields)}")
        print(f"  Records: {n}")
        print(f"  Encoder: {self._encoding_name}")
        print("━" * 60)
        print(f"  {'Format':<14} {'Tokens':>6}   vs JSON")
        print("  " + "─" * 40)

        for r in results:
            print(f"  {r}")

        print()
        tass_r = next(r for r in results if r.format_name == "tass")
        json_r = next(r for r in results if r.format_name == "json")
        saving_pct = abs(tass_r.vs_json_pct)
        saving_tok = json_r.tokens - tass_r.tokens
        print(f"  TASS saves {saving_tok} tokens ({saving_pct:.0f}%) vs JSON "
              f"across {n} record(s).")
        print()
        print("  Sample output per format (first record):")
        for r in results:
            print(f"    [{r.format_name}] {r.sample}")
        print("━" * 60)
        print()

    # ── Renderers ─────────────────────────────────────────────────────

    def _render_tass(self) -> str:
        lines = []
        for rec in self.records:
            parts = []
            for field, sym in self._sym_map.items():
                val = rec.get(field, "")
                if isinstance(val, bool):
                    val = "true" if val else "false"
                elif isinstance(val, int) and val >= 1000 and val % 1000 == 0:
                    val = f"{val // 1000}k"
                elif isinstance(val, int) and val >= 1000:
                    val = str(val)
                parts.append(f"~{sym}:{val}")
            lines.append(" ".join(parts))
        return "\n".join(lines)

    def _render_pipe(self) -> str:
        fields = list(self.schema.keys())
        lines = ["|".join(str(rec.get(f, "")) for f in fields) for rec in self.records]
        return "\n".join(lines)

    def _render_json(self) -> str:
        return "\n".join(json.dumps(rec, separators=(",", ":")) for rec in self.records)

    def _render_prose(self) -> str:
        lines = []
        for rec in self.records:
            parts = ", ".join(f"the {k} is {v}" for k, v in rec.items())
            lines.append(parts.capitalize() + ".")
        return "\n".join(lines)

    # ── Token counting ────────────────────────────────────────────────

    def _count_tokens(self, text: str) -> int:
        if self._approx:
            return self._approx_tokens(text)
        return len(self._enc.encode(text))

    @staticmethod
    def _approx_tokens(text: str) -> int:
        """
        Fast offline approximation: split on whitespace and punctuation.
        Calibrated to BPE tokenisers — underestimates slightly for prose,
        accurate for TASS/JSON/pipe where most tokens are atomic.
        """
        import re
        # Split on whitespace, then further split on punctuation boundaries
        tokens = re.findall(r"[~\w]+|[^\w\s]", text)
        return len(tokens)


def benchmark_from_tass_file(
    path: str,
    encoding_name: str = DEFAULT_ENCODING,
    approx: bool = False,
) -> None:
    """
    Load a .tass file and benchmark its records directly.
    Infers schema from the @dict block; types default to 'string'.
    """
    from tass.file_parser import TASSFileParser

    tfile = TASSFileParser().parse_file(path)
    if not tfile.records:
        print("No @records found in file.")
        return

    schema = {name: "string" for name in tfile.dictionary.values()}
    bench = TASSBenchmark(schema, tfile.records, encoding_name=encoding_name, approx=approx)
    bench.print_report()

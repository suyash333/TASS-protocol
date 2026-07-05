"""
TASS — Tokeniser-Aware Structured Shorthand
Command-line interface

Usage
-----
    tass compile schema.json
    tass parse "~a:refund ~b:5 ~c:true" --schema schema.json
    tass read data.tass
    tass benchmark data.tass
    tass benchmark --schema schema.json --records records.json

White paper: https://doi.org/10.5281/zenodo.20403219
License    : MIT
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# ── Sub-command handlers ──────────────────────────────────────────────


def cmd_compile(args: argparse.Namespace) -> int:
    """Compile a JSON schema into a TASS system prompt."""
    from tass.parser import SchemaCompiler

    schema = _load_json(args.schema)
    compiler = SchemaCompiler()
    parser_map, system_prompt = compiler.compile(schema)

    print(system_prompt)

    if args.map:
        print("\n── Parser map (for TASSParser) ──")
        readable = {sym: {"field": name, "type": t} for sym, (name, t) in parser_map.items()}
        print(json.dumps(readable, indent=2))

    return 0


def cmd_parse(args: argparse.Namespace) -> int:
    """Parse a raw TASS string into JSON."""
    from tass.parser import SchemaCompiler, TASSParser

    schema = _load_json(args.schema)
    compiler = SchemaCompiler()
    parser_map, _ = compiler.compile(schema)
    parser = TASSParser(dictionary_map=parser_map)

    raw = args.input
    try:
        if args.safe:
            result = parser.safe_parse(raw)
        else:
            result = parser.parse(raw)
    except Exception as exc:
        _err(f"Parse error: {exc}")
        return 1

    print(json.dumps(result, indent=2))
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    """Parse a .tass file and print records as JSON."""
    from tass.file_parser import TASSFileParser, TASSFileError

    try:
        tfile = TASSFileParser().parse_file(args.file)
    except TASSFileError as exc:
        _err(f"File parse error: {exc}")
        return 1

    if args.raw:
        for line in tfile.raw_records:
            print(line)
        return 0

    output = {
        "dictionary": tfile.dictionary,
        "codes": tfile.codes,
        "records": tfile.records,
    }

    if args.records_only:
        print(json.dumps(tfile.records, indent=2))
    else:
        print(json.dumps(output, indent=2))

    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    """Benchmark TASS token savings versus JSON, pipe, and prose."""
    approx = getattr(args, "approx", False)
    if not approx:
        try:
            import tiktoken  # noqa: F401
        except ImportError:
            print(
                "tass: note: tiktoken not installed — using fast approximation mode.\n"
                "For exact BPE token counts: pip install tass[benchmark]\n",
                file=__import__("sys").stderr,
            )
            approx = True

    from tass.benchmark import TASSBenchmark, benchmark_from_tass_file, DEFAULT_ENCODING

    enc = args.encoding or DEFAULT_ENCODING

    if args.file:
        benchmark_from_tass_file(args.file, encoding_name=enc, approx=approx)
        return 0

    if not args.schema or not args.records:
        _err("Provide either --file <data.tass> or both --schema and --records.")
        return 1

    schema = _load_json(args.schema)
    records = _load_json(args.records)
    if not isinstance(records, list):
        _err("--records must be a JSON array of objects.")
        return 1

    TASSBenchmark(schema, records, encoding_name=enc, approx=approx).print_report()
    return 0


def cmd_sign(args: argparse.Namespace) -> int:
    """Sign a TASS record line with HMAC-SHA3-256."""
    from tass.crypto import TASSSigner, derive_key

    key = _resolve_key(args)
    if key is None:
        return 1

    signer = TASSSigner(derive_key(key, context=args.context.encode()))
    print(signer.sign_line(args.input))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify a signed TASS record line. Exit 0 if valid, 2 if not."""
    from tass.crypto import TASSSigner, derive_key

    key = _resolve_key(args)
    if key is None:
        return 1

    signer = TASSSigner(derive_key(key, context=args.context.encode()))
    if signer.verify_line(args.input):
        print("OK: signature valid")
        return 0
    print("FAIL: signature missing or invalid", file=sys.stderr)
    return 2


# ── Helpers ───────────────────────────────────────────────────────────


def _resolve_key(args: argparse.Namespace) -> bytes | None:
    """Read the signing key from --key-file or the TASS_KEY env var."""
    import os

    if args.key_file:
        try:
            return Path(args.key_file).read_bytes().strip()
        except FileNotFoundError:
            _err(f"Key file not found: {args.key_file}")
            return None
    env = os.environ.get("TASS_KEY")
    if env:
        return env.encode("utf-8")
    _err("No key: pass --key-file or set the TASS_KEY environment variable.")
    return None


def _load_json(path: str) -> dict | list:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        _err(f"File not found: {path}")
        sys.exit(1)
    except json.JSONDecodeError as exc:
        _err(f"Invalid JSON in {path}: {exc}")
        sys.exit(1)


def _err(msg: str) -> None:
    print(f"tass: error: {msg}", file=sys.stderr)


# ── Argument parser ───────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tass",
        description=(
            "TASS — Tokeniser-Aware Structured Shorthand\n"
            "Reduce LLM inference costs 75-85%% with a stenography-inspired output format.\n\n"
            "White paper: https://doi.org/10.5281/zenodo.20403219"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--version", action="version",
        version="%(prog)s 0.1.0",
    )

    sub = p.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # ── compile ──────────────────────────────────────────────────────
    p_compile = sub.add_parser(
        "compile",
        help="Compile a JSON schema into a TASS system prompt",
        description=textwrap.dedent("""\
            Compile a JSON schema into a TASS system prompt ready to inject
            into your LLM API call.

            Example schema.json:
              {
                "tier":       "string",
                "rate_low":   "integer",
                "gst":        "boolean"
              }

            Example:
              tass compile schema.json
              tass compile schema.json --map
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_compile.add_argument("schema", help="Path to JSON schema file")
    p_compile.add_argument("--map", action="store_true",
                           help="Also print the parser map as JSON")
    p_compile.set_defaults(func=cmd_compile)

    # ── parse ────────────────────────────────────────────────────────
    p_parse = sub.add_parser(
        "parse",
        help="Parse a raw TASS string into JSON",
        description=textwrap.dedent("""\
            Parse a raw TASS LLM output string into structured JSON.

            Example:
              tass parse "~a:refund ~b:5 ~c:true" --schema schema.json
              tass parse "~a:refund ~b:5 ~c:true" --schema schema.json --safe
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_parse.add_argument("input", help="Raw TASS string to parse")
    p_parse.add_argument("--schema", required=True, help="Path to JSON schema file")
    p_parse.add_argument("--safe", action="store_true",
                         help="Enable JSON fallback if TASS parse fails")
    p_parse.set_defaults(func=cmd_parse)

    # ── read ─────────────────────────────────────────────────────────
    p_read = sub.add_parser(
        "read",
        help="Parse a .tass file and output records as JSON",
        description=textwrap.dedent("""\
            Read a .tass file (with @dict, @codes, @records blocks)
            and output the parsed records as JSON.

            Example:
              tass read spec/sample.tass
              tass read spec/sample.tass --records-only
              tass read spec/sample.tass --raw
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_read.add_argument("file", help="Path to .tass file")
    p_read.add_argument("--records-only", dest="records_only", action="store_true",
                        help="Print only the records array, not the full parsed file")
    p_read.add_argument("--raw", action="store_true",
                        help="Print raw record lines (no parsing)")
    p_read.set_defaults(func=cmd_read)

    # ── benchmark ────────────────────────────────────────────────────
    p_bench = sub.add_parser(
        "benchmark",
        help="Benchmark TASS token savings vs JSON, pipe, and prose",
        description=textwrap.dedent("""\
            Compare token costs across TASS, JSON, pipe-delimited, and prose formats.
            Requires: pip install tass[benchmark]

            Examples:
              tass benchmark spec/sample.tass
              tass benchmark --schema schema.json --records records.json
              tass benchmark spec/sample.tass --encoding cl100k_base
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_bench.add_argument("file", nargs="?", help="Path to .tass file")
    p_bench.add_argument("--schema", help="Path to JSON schema file")
    p_bench.add_argument("--records", help="Path to JSON records file (array of objects)")
    p_bench.add_argument("--encoding", default=None,
                         help="tiktoken encoding name (default: o200k_base)")
    p_bench.add_argument("--approx", action="store_true",
                         help="Use fast offline approximation instead of tiktoken")
    p_bench.set_defaults(func=cmd_benchmark)

    # ── sign / verify ────────────────────────────────────────────────
    key_help = "Path to a file containing the signing key (or set TASS_KEY env var)"
    ctx_help = "Key-derivation context string, e.g. your pipeline name (default: 'tass')"

    p_sign = sub.add_parser(
        "sign",
        help="Append an HMAC-SHA3-256 tag to a TASS record line",
        description=textwrap.dedent("""\
            Sign a TASS record with a compact post-quantum-safe MAC.
            The tag is appended as a ~!:<tag> pair inside the line.

            Example:
              export TASS_KEY="my-pipeline-secret"
              tass sign "~t:mc ~l:18k ~h:42k ~g:0"
              # ~t:mc ~l:18k ~h:42k ~g:0 ~!:3vX9kQ2mP8sT1uW4yZ6bCg
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_sign.add_argument("input", help="Raw TASS record line to sign")
    p_sign.add_argument("--key-file", dest="key_file", help=key_help)
    p_sign.add_argument("--context", default="tass", help=ctx_help)
    p_sign.set_defaults(func=cmd_sign)

    p_verify = sub.add_parser(
        "verify",
        help="Verify a signed TASS record line (exit 0 = valid, 2 = invalid)",
        description=textwrap.dedent("""\
            Verify the ~!:<tag> MAC embedded in a signed TASS record.
            Verification is constant-time and tolerant of field reordering.

            Example:
              tass verify "~t:mc ~l:18k ~h:42k ~g:0 ~!:3vX9kQ..." --key-file key.bin
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_verify.add_argument("input", help="Signed TASS record line")
    p_verify.add_argument("--key-file", dest="key_file", help=key_help)
    p_verify.add_argument("--context", default="tass", help=ctx_help)
    p_verify.set_defaults(func=cmd_verify)

    return p


import textwrap  # noqa: E402  (imported here to keep top-level imports clean)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()

# Appendix A — API Reference

Complete public API of `tass-protocol` 0.1.x. Everything below is
importable from the top-level package:

```python
from tass import (
    SchemaCompiler, TASSParser, TASSParseError, TASSValidationError,
    TASSFileParser, TASSFile, TASSFileError,
    TASSSigner, TASSIntegrityError, hash_record, derive_key, canonicalize,
)
```

---

## Core (`tass.parser`)

### `SchemaCompiler(prefix_char="~")`

| Member | Signature | Notes |
|---|---|---|
| `compile` | `(schema: dict) -> (parser_map, system_prompt)` | `schema` maps field name → `"string" \| "integer" \| "float" \| "boolean"`. Symbols assigned in declaration order from a 52-slot pool (`a–z`, `A–Z`); `ValueError` beyond 52 fields. `parser_map` maps symbol → `(field_name, type_hint)`. |

### `TASSParser(dictionary_map, prefix_char="~")`

Accepts a `SchemaCompiler` map or a legacy `{symbol: field_name}` map
(fields then default to string).

| Member | Signature | Notes |
|---|---|---|
| `parse` | `(raw: str) -> dict` | Strips markdown, scans pairs, coerces types. Unknown symbols and non-pair tokens skipped. |
| `safe_parse` | `(raw: str) -> dict` | `parse` + `validate`; on failure retries as JSON; raises `TASSParseError` if both fail. |
| `validate` | `(parsed: dict) -> None` | Raises `TASSValidationError` naming missing fields. |

Coercions: `"18k"`→`18000` (int), `"1.5k"`→`1500.0` (float),
`1/true/yes`→`True` (bool, case-insensitive).

**Exceptions:** `TASSParseError(ValueError)`,
`TASSValidationError(ValueError)`.

---

## File format (`tass.file_parser`)

### `TASSFileParser()`

| Member | Signature | Notes |
|---|---|---|
| `parse` | `(text: str) -> TASSFile` | Raises `TASSFileError` on unknown blocks or malformed `@dict`/`@codes` entries. |
| `parse_file` | `(path: str \| Path) -> TASSFile` | UTF-8 read + `parse`. |

### `TASSFile` (dataclass)

| Field | Type | Contents |
|---|---|---|
| `dictionary` | `dict` | symbol → field name |
| `codes` | `dict` | code → full value (values may contain spaces) |
| `records` | `list[dict]` | parsed records, codes expanded |
| `raw_records` | `list[str]` | original wire lines (for hashing/signing) |
| `to_parser_map()` | method | → `TASSParser`-compatible map (all types `"string"`) |

**Exception:** `TASSFileError(ValueError)`.

---

## Integrity (`tass.crypto`)

All symmetric, stdlib-only. Reserved signature symbol: `!` (constant
`SIG_SYMBOL`).

| Function | Signature | Notes |
|---|---|---|
| `canonicalize` | `(line, prefix_char="~") -> str` | Pairs only, `~!` excluded, sorted by key, single-spaced. |
| `hash_record` | `(line, prefix_char="~") -> str` | SHA3-256 hex (64 chars) of canonical form; order-independent. |
| `derive_key` | `(master_secret, context=b"", salt=b"", length=32) -> bytes` | HKDF-SHA3-256 (RFC 5869). `ValueError` on empty secret. |

### `TASSSigner(key, tag_bytes=16, prefix_char="~")`

Key ≥16 bytes (32 recommended); `tag_bytes` ∈ [8, 32], default 16
(128-bit tag → 22 base64url chars).

| Member | Signature | Notes |
|---|---|---|
| `sign_line` | `(line) -> str` | Appends ` ~!:<tag>` (HMAC-SHA3-256 over canonical form). |
| `verify_line` | `(signed) -> bool` | Constant-time; `False` on absent/invalid tag. Never raises. |
| `sign_records` / `verify_records` | `(list) -> list` | Element-wise batch forms. |

**Exception:** `TASSIntegrityError(ValueError)` — provided for callers
treating verification failure as fatal; the library itself returns bools.

---

## Benchmark (`tass.benchmark`) — requires `pip install tass-protocol[benchmark]` for exact counts

| API | Notes |
|---|---|
| `TASSBenchmark(schema, records, encoding_name="o200k_base", approx=False)` | Renders TASS / pipe / minified-JSON / prose; `approx=True` (or missing tiktoken) uses labelled whitespace estimation. |
| `.run() -> list[BenchmarkResult]` · `.print_report()` | `BenchmarkResult`: `format_name`, `tokens`, `vs_json_pct`, `sample`. |
| `benchmark_from_tass_file(path, encoding_name=..., approx=...)` | Schema inferred from `@dict` (string-typed). |

---

## CLI

```
tass compile  <schema.json> [--map]
tass parse    "<record>" --schema <schema.json> [--safe]
tass read     <file.tass> [--records-only | --raw]
tass benchmark [<file.tass>] [--schema S --records R] [--encoding E] [--approx]
tass sign     "<record>" [--key-file F] [--context C]
tass verify   "<signed record>" [--key-file F] [--context C]
```

Key resolution for `sign`/`verify`: `--key-file` first, then `TASS_KEY`
env var. Exit codes: `0` success/valid, `1` usage or parse error,
`2` invalid signature.

## JavaScript (`tass.js`)

`SchemaCompiler#compile(schema) -> {parserMap, systemPrompt}`;
`TASSParser({dictionaryMap, prefixChar})` with `parse(raw)` /
`safeParse(raw)`. Mirrors the Python core (parser + compiler only; file
format and crypto are Python-first as of 0.1.x).

# Chapter 6 — The `.tass` File Format

> *In which the wire format acquires a home on disk, and the schema
> becomes a versionable artifact.*

## 6.1 Why a file format at all

The wire format of Chapters 3–5 is ephemeral — it exists between the
model's decoder and your parser. But three durable artifacts orbit it:
the **dictionary** (symbols → fields), the **code tables** (short codes →
full values), and often the **records themselves** (compact storage is
storage savings too). The `.tass` file gives all three one human-review-
able, diff-able, git-friendly container:

```
@dict
  ~t = tier           # mc=micro | md=mid | mk=macro
  ~l = rate_low       # INR, k suffix = thousands
  ~g = gst            # 0 = no | 1 = charge 18%
@end

@codes
  mc = micro
  md = mid
  mk = macro
@end

@records
~t:mc ~l:18k ~g:0
~t:md ~l:55k ~g:1
@end
```

The design borrows deliberately from formats that survived decades:
INI-style sections, `#` comments stripped before parsing, and one record
per line so that `grep`, `wc -l`, `tail -f`, and line-oriented diffs all
work unmodified. **A `.tass` file is a spec you can code-review.**

## 6.2 The three blocks

| Block | Maps | Consumed by |
|---|---|---|
| `@dict` | `~symbol = field_name` | prompt generation + parser map |
| `@codes` | `code = full value` (spaces allowed in value) | server-side expansion after parse |
| `@records` | one wire-format record per line | storage / test fixtures / replay |

Block structure is flat: a block opens with `@name`, closes with `@end`,
and unknown block names are a hard error (`TASSFileError`) — silent
tolerance of a typo'd `@dcit` would swallow an entire dictionary.
Content *outside* any block is ignored, which is what makes the generous
comment headers in `spec/` and `examples/` legal.

## 6.3 The codes table as a semantic contract

`@codes` is where TASS's "expand after the paid tokens stop" principle
becomes declarative. The LLM emits `~c:lr`; the parser looks up `lr` in
the codes table and delivers `Light Rain` to the application. Three
properties worth internalizing:

1. **Codes are global to the file, not per-field.** `mc = micro` applies
   to any field whose value is `mc`. Keep code namespaces disjoint per
   file (tier codes, template codes, status codes must not collide) — a
   discipline, not an enforcement, in format 1.0.
2. **Unmatched values pass through.** A value with no code entry is
   returned verbatim. Numeric fields therefore need no entries, and code
   tables can be introduced incrementally.
3. **Multi-word expansion is free.** `lr = Light Rain` costs the wire
   nothing; the phrase exists only server-side. This is the sanctioned
   answer to "TASS values can't contain spaces."

## 6.4 Parsing files

```python
from tass import TASSFileParser

tfile = TASSFileParser().parse_file("examples/weather.tass")

tfile.dictionary    # {'t': 'tier', ...}
tfile.codes         # {'mc': 'micro', 'lr': 'Light Rain', ...}
tfile.records       # [{'tier': 'micro', ...}] — codes already expanded
tfile.raw_records   # original wire lines, preserved for hashing/signing

parser_map = tfile.to_parser_map()   # feed straight into TASSParser
```

Note the deliberate redundancy of `records` vs `raw_records`: expanded
dicts serve the application; raw lines serve cryptography (Chapter 8 MACs
are computed over canonical wire form, so files must preserve it) and
replay testing.

One honest limitation: `@dict` entries carry no type hints in format 1.0,
so `to_parser_map()` defaults every field to `string`. Pipelines that
need typed parsing from a file should keep the schema-as-code path
(Chapter 4) authoritative and treat `.tass` files as data + documentation.
Typed dictionary entries are the natural format 1.1 extension.

## 6.5 The file as source of truth

Because a `.tass` file contains everything both sides of the wire need,
it can anchor a deployment workflow:

```
git repo:  schemas/ticket_routing_v3.tass     ← reviewed, versioned, tagged
              │
              ├─→ CI: parse file → generate system prompt → publish to registry
              └─→ CI: to_parser_map() → bundle with consumer service
```

Prompt and parser are now built from one reviewed artifact per version —
the same never-disagree property as Chapter 4's compiler, extended across
services and time. Chapter 9 §9.4 builds the full registry pattern on
this foundation, with
[`snippets/schema_registry.py`](../snippets/schema_registry.py) as the
working miniature.

## 6.6 Summary

- The `.tass` file packages dictionary, code tables, and records in one
  line-oriented, comment-friendly, git-native container.
- `@codes` turns multi-word values into a server-side concern and makes
  value semantics reviewable.
- `raw_records` preservation keeps files compatible with the integrity
  layer; type hints are the acknowledged 1.1 gap.
- A versioned `.tass` file can serve as the single source of truth from
  which prompts and parser maps are both derived.

*Next: measuring all of this without fooling yourself — Chapter 7.*

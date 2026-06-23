"""Tests for the TASS CLI."""

import json
import textwrap
import pytest
from unittest.mock import patch
from tass.cli import build_parser, cmd_compile, cmd_parse, cmd_read


@pytest.fixture
def schema_file(tmp_path):
    schema = {
        "user_intent":      "string",
        "urgency_level":    "integer",
        "requires_routing": "boolean",
    }
    p = tmp_path / "schema.json"
    p.write_text(json.dumps(schema))
    return str(p)


@pytest.fixture
def tass_file(tmp_path):
    content = textwrap.dedent("""\
        @dict
          ~t = tier
          ~f = followers
        @end
        @codes
          mc = micro
        @end
        @records
        ~t:mc ~f:45
        @end
    """)
    p = tmp_path / "test.tass"
    p.write_text(content)
    return str(p)


class TestCLICompile:
    def test_compile_prints_prompt(self, schema_file, capsys):
        parser = build_parser()
        args = parser.parse_args(["compile", schema_file])
        rc = args.func(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "~a:<value>" in out
        assert "user_intent" in out

    def test_compile_with_map_flag(self, schema_file, capsys):
        parser = build_parser()
        args = parser.parse_args(["compile", schema_file, "--map"])
        args.func(args)
        out = capsys.readouterr().out
        assert "Parser map" in out


class TestCLIParse:
    def test_parse_valid_tass(self, schema_file, capsys):
        parser = build_parser()
        args = parser.parse_args(["parse", "~a:refund ~b:5 ~c:true", "--schema", schema_file])
        rc = args.func(args)
        assert rc == 0
        result = json.loads(capsys.readouterr().out)
        assert result["user_intent"] == "refund"
        assert result["urgency_level"] == 5
        assert result["requires_routing"] is True

    def test_parse_safe_flag(self, schema_file, capsys):
        raw_json = '{"user_intent":"x","urgency_level":1,"requires_routing":false}'
        parser = build_parser()
        args = parser.parse_args(["parse", raw_json, "--schema", schema_file, "--safe"])
        rc = args.func(args)
        assert rc == 0


class TestCLIRead:
    def test_read_records_only(self, tass_file, capsys):
        parser = build_parser()
        args = parser.parse_args(["read", tass_file, "--records-only"])
        rc = args.func(args)
        assert rc == 0
        records = json.loads(capsys.readouterr().out)
        assert isinstance(records, list)
        assert records[0]["tier"] == "micro"

    def test_read_full_output(self, tass_file, capsys):
        parser = build_parser()
        args = parser.parse_args(["read", tass_file])
        rc = args.func(args)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert "dictionary" in out
        assert "records" in out

    def test_read_raw_flag(self, tass_file, capsys):
        parser = build_parser()
        args = parser.parse_args(["read", tass_file, "--raw"])
        rc = args.func(args)
        assert rc == 0
        out = capsys.readouterr().out.strip()
        assert out == "~t:mc ~f:45"

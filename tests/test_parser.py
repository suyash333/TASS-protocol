"""Tests for TASSParser and SchemaCompiler."""

import pytest
from tass.parser import SchemaCompiler, TASSParser, TASSParseError, TASSValidationError

SCHEMA = {
    "user_intent":      "string",
    "urgency_level":    "integer",
    "requires_routing": "boolean",
    "confidence":       "float",
}


@pytest.fixture
def compiled():
    compiler = SchemaCompiler()
    parser_map, system_prompt = compiler.compile(SCHEMA)
    return parser_map, system_prompt


@pytest.fixture
def parser(compiled):
    parser_map, _ = compiled
    return TASSParser(dictionary_map=parser_map)


class TestSchemaCompiler:
    def test_compile_returns_map_and_prompt(self, compiled):
        parser_map, system_prompt = compiled
        assert len(parser_map) == 4
        assert "~a:<value>" in system_prompt

    def test_symbol_assignment(self, compiled):
        parser_map, _ = compiled
        assert parser_map["a"] == ("user_intent", "string")
        assert parser_map["b"] == ("urgency_level", "integer")
        assert parser_map["c"] == ("requires_routing", "boolean")
        assert parser_map["d"] == ("confidence", "float")

    def test_too_many_fields_raises(self):
        compiler = SchemaCompiler()
        big_schema = {f"field_{i}": "string" for i in range(53)}
        with pytest.raises(ValueError, match="token pool"):
            compiler.compile(big_schema)


class TestTASSParser:
    def test_basic_parse(self, parser):
        result = parser.parse("~a:refund ~b:5 ~c:true ~d:0.92")
        assert result == {
            "user_intent": "refund",
            "urgency_level": 5,
            "requires_routing": True,
            "confidence": 0.92,
        }

    def test_k_suffix_integer(self, parser):
        schema = {"rate": "integer"}
        m, _ = SchemaCompiler().compile(schema)
        p = TASSParser(dictionary_map=m)
        assert p.parse("~a:18k")["rate"] == 18000

    def test_k_suffix_float(self):
        schema = {"amount": "float"}
        m, _ = SchemaCompiler().compile(schema)
        p = TASSParser(dictionary_map=m)
        assert p.parse("~a:1.5k")["amount"] == 1500.0

    def test_boolean_variants(self, parser):
        for val, expected in [("true", True), ("1", True), ("yes", True),
                               ("false", False), ("0", False), ("no", False)]:
            result = parser.parse(f"~a:x ~b:0 ~c:{val} ~d:0.0")
            assert result["requires_routing"] is expected

    def test_unknown_symbols_ignored(self, parser):
        result = parser.parse("~a:refund ~z:garbage ~b:3 ~c:false ~d:0.5")
        assert "user_intent" in result
        assert len(result) == 4

    def test_strips_markdown_fences(self, parser):
        raw = "```\n~a:cancel ~b:2 ~c:false ~d:0.7\n```"
        result = parser.parse(raw)
        assert result["user_intent"] == "cancel"

    def test_safe_parse_falls_back_to_json(self, parser):
        raw = '{"user_intent":"cancel","urgency_level":2,"requires_routing":false,"confidence":0.7}'
        result = parser.safe_parse(raw)
        assert result["user_intent"] == "cancel"

    def test_validate_raises_on_missing_fields(self, parser):
        result = parser.parse("~a:x")   # only one field
        with pytest.raises(TASSValidationError, match="Missing fields"):
            parser.validate(result)

    def test_float_string_coerces_to_integer(self):
        """F2 deviation: model emits '2.0' for an integer field."""
        m, _ = SchemaCompiler().compile({"level": "integer"})
        p = TASSParser(dictionary_map=m)
        assert p.parse("~a:2.0")["level"] == 2

    def test_uncoercible_value_raises_parse_error(self):
        """Coercion failures must raise TASSParseError, never bare ValueError,
        so safe_parse's fallback ladder can catch them."""
        m, _ = SchemaCompiler().compile({"level": "integer"})
        p = TASSParser(dictionary_map=m)
        with pytest.raises(TASSParseError, match="coerce"):
            p.parse("~a:banana")

    def test_legacy_map(self):
        legacy = {"a": "name", "b": "age"}
        p = TASSParser(dictionary_map=legacy)
        result = p.parse("~a:Alice ~b:30")
        assert result == {"name": "Alice", "age": "30"}

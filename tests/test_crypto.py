"""Tests for tass.crypto — canonicalization, hashing, signing, HKDF."""

import pytest
from tass.crypto import (
    TASSSigner,
    canonicalize,
    hash_record,
    derive_key,
)

KEY = derive_key(b"test-master-secret", context=b"unit-tests")
RECORD = "~t:mc ~l:18k ~h:42k ~g:0"


@pytest.fixture
def signer():
    return TASSSigner(KEY)


class TestCanonicalize:
    def test_sorts_fields(self):
        assert canonicalize("~b:2 ~a:1") == "~a:1 ~b:2"

    def test_normalizes_whitespace(self):
        assert canonicalize("  ~a:1    ~b:2  ") == "~a:1 ~b:2"

    def test_drops_non_pairs(self):
        assert canonicalize("~a:1 garbage ~b:2") == "~a:1 ~b:2"

    def test_excludes_signature_field(self):
        assert canonicalize("~a:1 ~!:sometag") == "~a:1"


class TestHashRecord:
    def test_order_independent(self):
        assert hash_record("~a:1 ~b:2") == hash_record("~b:2 ~a:1")

    def test_value_sensitive(self):
        assert hash_record("~a:1") != hash_record("~a:2")

    def test_hex_sha3_length(self):
        assert len(hash_record(RECORD)) == 64


class TestDeriveKey:
    def test_deterministic(self):
        assert derive_key(b"s", context=b"c") == derive_key(b"s", context=b"c")

    def test_context_separates_keys(self):
        assert derive_key(b"s", context=b"a") != derive_key(b"s", context=b"b")

    def test_length(self):
        assert len(derive_key(b"s", length=64)) == 64

    def test_empty_secret_raises(self):
        with pytest.raises(ValueError):
            derive_key(b"")


class TestTASSSigner:
    def test_roundtrip(self, signer):
        assert signer.verify_line(signer.sign_line(RECORD)) is True

    def test_tag_embedded_as_bang_field(self, signer):
        assert " ~!:" in signer.sign_line(RECORD)

    def test_tamper_detected(self, signer):
        signed = signer.sign_line(RECORD)
        assert signer.verify_line(signed.replace("18k", "99k")) is False

    def test_missing_tag_fails(self, signer):
        assert signer.verify_line(RECORD) is False

    def test_wrong_key_fails(self, signer):
        signed = signer.sign_line(RECORD)
        other = TASSSigner(derive_key(b"other-secret", context=b"unit-tests"))
        assert other.verify_line(signed) is False

    def test_field_reorder_still_verifies(self, signer):
        signed = signer.sign_line("~a:1 ~b:2")
        tag = signed.split(" ~!:")[1]
        reordered = f"~b:2 ~!:{tag} ~a:1"
        assert signer.verify_line(reordered) is True

    def test_batch_sign_verify(self, signer):
        lines = ["~a:1 ~b:2", "~a:3 ~b:4"]
        signed = signer.sign_records(lines)
        assert signer.verify_records(signed) == [True, True]
        signed[1] = signed[1].replace("~a:3", "~a:9")
        assert signer.verify_records(signed) == [True, False]

    def test_short_key_rejected(self):
        with pytest.raises(ValueError, match="at least 16 bytes"):
            TASSSigner(b"short")

    def test_signed_record_still_parses(self, signer):
        """The ~!: tag must be invisible to the normal parser."""
        from tass.parser import SchemaCompiler, TASSParser

        parser_map, _ = SchemaCompiler().compile({"tier": "string", "rate": "integer"})
        parser = TASSParser(dictionary_map=parser_map)
        signed = signer.sign_line("~a:mc ~b:18k")
        assert parser.parse(signed) == {"tier": "mc", "rate": 18000}


class TestCLISignVerify:
    def test_sign_then_verify(self, tmp_path, capsys):
        from tass.cli import build_parser

        key_file = tmp_path / "key.bin"
        key_file.write_bytes(b"cli-test-master-secret")

        p = build_parser()
        args = p.parse_args(["sign", RECORD, "--key-file", str(key_file)])
        assert args.func(args) == 0
        signed = capsys.readouterr().out.strip()

        args = p.parse_args(["verify", signed, "--key-file", str(key_file)])
        assert args.func(args) == 0

    def test_verify_tampered_exits_2(self, tmp_path, capsys):
        from tass.cli import build_parser

        key_file = tmp_path / "key.bin"
        key_file.write_bytes(b"cli-test-master-secret")

        p = build_parser()
        args = p.parse_args(["sign", RECORD, "--key-file", str(key_file)])
        args.func(args)
        signed = capsys.readouterr().out.strip().replace("18k", "77k")

        args = p.parse_args(["verify", signed, "--key-file", str(key_file)])
        assert args.func(args) == 2

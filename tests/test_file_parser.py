"""Tests for TASSFileParser."""

import textwrap
import pytest
from tass.file_parser import TASSFileParser, TASSFile, TASSFileError

SAMPLE_TASS = textwrap.dedent("""\
    # TASS test file

    @dict
      ~t = tier           # mc=micro | md=mid
      ~f = followers      # integer in thousands
      ~g = gst            # 0 = not applicable | 1 = charge 18%
    @end

    @codes
      mc = micro
      md = mid
      mk = macro
    @end

    @records
    ~t:mc ~f:45 ~g:0
    ~t:md ~f:180 ~g:1
    @end
""")


@pytest.fixture
def tfile():
    return TASSFileParser().parse(SAMPLE_TASS)


class TestTASSFileParser:
    def test_dictionary_parsed(self, tfile):
        assert tfile.dictionary == {
            "t": "tier",
            "f": "followers",
            "g": "gst",
        }

    def test_codes_parsed(self, tfile):
        assert tfile.codes["mc"] == "micro"
        assert tfile.codes["md"] == "mid"

    def test_records_count(self, tfile):
        assert len(tfile.records) == 2

    def test_records_expand_codes(self, tfile):
        # "mc" in @codes → "micro"
        assert tfile.records[0]["tier"] == "micro"
        assert tfile.records[1]["tier"] == "mid"

    def test_raw_records_preserved(self, tfile):
        assert tfile.raw_records[0] == "~t:mc ~f:45 ~g:0"
        assert tfile.raw_records[1] == "~t:md ~f:180 ~g:1"

    def test_values_without_code_pass_through(self, tfile):
        assert tfile.records[0]["followers"] == "45"
        assert tfile.records[0]["gst"] == "0"

    def test_to_parser_map(self, tfile):
        m = tfile.to_parser_map()
        assert m["t"] == ("tier", "string")
        assert m["f"] == ("followers", "string")

    def test_codes_multiword_value(self):
        tass = "@codes\n  lr = Light Rain\n  bc = Broken Clouds\n@end\n"
        tf = TASSFileParser().parse(tass)
        assert tf.codes["lr"] == "Light Rain"
        assert tf.codes["bc"] == "Broken Clouds"

    def test_comments_stripped(self):
        tass = "@dict\n  ~a = name # this is a comment\n@end\n"
        tf = TASSFileParser().parse(tass)
        assert tf.dictionary == {"a": "name"}

    def test_unknown_block_raises(self):
        with pytest.raises(TASSFileError, match="Unknown block"):
            TASSFileParser().parse("@unknown\n@end\n")

    def test_malformed_dict_entry_raises(self):
        with pytest.raises(TASSFileError, match="Malformed @dict"):
            TASSFileParser().parse("@dict\n  bad line\n@end\n")

    def test_parse_file(self, tmp_path):
        p = tmp_path / "test.tass"
        p.write_text(SAMPLE_TASS)
        tf = TASSFileParser().parse_file(p)
        assert len(tf.records) == 2

    def test_parse_sample_tass(self):
        """Smoke test against the real spec/sample.tass file."""
        import os
        spec_path = os.path.join(
            os.path.dirname(__file__), "..", "spec", "sample.tass"
        )
        tf = TASSFileParser().parse_file(spec_path)
        assert len(tf.records) == 6
        assert tf.records[0]["tier"] == "micro"

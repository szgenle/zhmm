"""Tests for zhmm.utils.data_conversion."""

import pytest

from zhmm.utils import data_conversion as dc


class TestToHexString:
    def test_from_list(self):
        assert dc.to_hex_string([0x00, 0x01, 0xFF]) == "0001ff"

    def test_from_bytes(self):
        assert dc.to_hex_string(b"\x00\xab\xcd") == "00abcd"

    def test_from_bytearray(self):
        assert dc.to_hex_string(bytearray([0xDE, 0xAD, 0xBE, 0xEF])) == "deadbeef"

    def test_empty(self):
        assert dc.to_hex_string([]) == ""
        assert dc.to_hex_string(b"") == ""


class TestCharsToBytes:
    def test_ascii(self):
        assert dc.chars_to_bytes("ABC") == [65, 66, 67]

    def test_list_of_chars(self):
        assert dc.chars_to_bytes(["A", "B", "C"]) == [65, 66, 67]

    def test_unicode(self):
        # 汉字「中」的 code point 为 0x4E2D
        assert dc.chars_to_bytes("中") == [0x4E2D]

    def test_empty(self):
        assert dc.chars_to_bytes("") == []


class TestHexToArray:
    def test_even_length(self):
        assert dc.hex_to_array("0001ff") == [0, 1, 255]

    def test_odd_length_pads_leading_zero(self):
        # 奇数长度时应在前面补 "0"。
        assert dc.hex_to_array("1ff") == [0x01, 0xFF]

    def test_empty(self):
        assert dc.hex_to_array("") == []

    @pytest.mark.parametrize(
        "hex_str, expected",
        [
            ("deadbeef", [0xDE, 0xAD, 0xBE, 0xEF]),
            ("ff", [0xFF]),
            ("00", [0]),
        ],
    )
    def test_roundtrip_with_to_hex_string(self, hex_str, expected):
        assert dc.hex_to_array(hex_str) == expected
        assert dc.to_hex_string(expected) == hex_str

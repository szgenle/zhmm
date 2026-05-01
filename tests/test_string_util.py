"""Tests for zhmm.utils.string_util."""

import pytest

from zhmm.utils import string_util


class TestTruncate:
    def test_truncate_short_string_unchanged(self):
        assert string_util.truncate("hello", 32) == "hello"

    def test_truncate_boundary(self):
        # 恰好等于 max_length 时不截断。
        assert string_util.truncate("a" * 32, 32) == "a" * 32

    def test_truncate_long_string(self):
        long = "a" * 40
        result = string_util.truncate(long, 32)
        assert result == "a" * 32 + "..."

    def test_truncate_custom_length(self):
        assert string_util.truncate("helloworld", 3) == "hel..."

    def test_truncate_empty(self):
        assert string_util.truncate("", 32) == ""


class TestCountChineseChars:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("", 0),
            ("hello", 0),
            ("你好", 2),
            ("hello你好world", 2),
            ("中 文 混 合 abc", 4),
        ],
    )
    def test_count(self, text, expected):
        assert string_util.count_chinese_chars(text) == expected


class TestCountUnicodeChars:
    def test_chinese_punctuation_counted(self):
        assert string_util.count_unicode_chars("，。！？") == 4

    def test_ascii_not_counted(self):
        assert string_util.count_unicode_chars("hello, world!") == 0

    def test_mixed(self):
        # 中文字 + 中文标点 + 英文：应只计中文相关。
        assert string_util.count_unicode_chars("你好，world") == 3


class TestIsString:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ("", True),
            ("hello", True),
            (123, False),
            (None, False),
            ([], False),
            ({}, False),
        ],
    )
    def test_is_string(self, value, expected):
        assert string_util.is_string(value) is expected

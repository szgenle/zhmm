"""Tests for :mod:`zhmm.core.password_strength`."""

from __future__ import annotations

import pytest

from zhmm.core.password_strength import StrengthLevel, assess_strength


class TestBasic:
    def test_empty_is_very_weak(self):
        r = assess_strength("")
        assert r.score == 0
        assert r.level is StrengthLevel.VERY_WEAK
        assert r.label == "极弱"
        # 空串不给出改进建议，避免在未输入时就打扰
        assert r.hint == ""

    def test_very_short_is_capped_very_weak(self):
        r = assess_strength("ab")
        assert r.score <= 15
        assert r.level is StrengthLevel.VERY_WEAK

    def test_short_under_8_is_capped(self):
        # 即便字符集很宽，长度 < 8 时分数被钉死在 ≤30
        r = assess_strength("Aa1!Aa")
        assert r.score <= 30
        assert r.level in {StrengthLevel.VERY_WEAK, StrengthLevel.WEAK}
        assert "长度" in r.hint


class TestCommonWeak:
    @pytest.mark.parametrize(
        "pwd",
        ["password", "Password123", "qwerty", "admin888", "123456", "letmein!"],
    )
    def test_common_weak_is_capped(self, pwd: str):
        r = assess_strength(pwd)
        # 命中常见弱密码子串时分数被打底到弱档上限
        assert r.score <= 30
        assert r.level in {StrengthLevel.VERY_WEAK, StrengthLevel.WEAK}


class TestSequence:
    @pytest.mark.parametrize(
        "pwd",
        [
            "Aabcdefg!1",  # 字母升序 abc
            "Az987654!",  # 数字降序
            "Qwerty!!23",  # 键盘序 qwe
            "asdfgh!!1A",  # 键盘序 asd
        ],
    )
    def test_sequence_penalized(self, pwd: str):
        r = assess_strength(pwd)
        # 与 _disable_seq 对照版本相比，含序应更弱；这里只验证不会误判为极强
        assert r.level is not StrengthLevel.VERY_STRONG


class TestRepeat:
    def test_three_repeat_chars_penalized(self):
        r_good = assess_strength("Kx9#Nz2$Qm7")
        r_bad = assess_strength("Kxxx#Nz2$Qm")
        assert r_bad.score < r_good.score


class TestStrong:
    def test_12_char_mixed_is_at_least_strong(self):
        r = assess_strength("Kx9#Nz2$Qm7!")
        assert r.level >= StrengthLevel.STRONG
        assert r.score >= 60

    def test_long_passphrase_is_very_strong(self):
        # 16 字符混合字符集，熵 ~ 16 * log2(94) ≈ 105 bits
        r = assess_strength("Kx9#Nz2$Qm7!Rv4@")
        assert r.level is StrengthLevel.VERY_STRONG
        assert r.score >= 80


class TestHint:
    def test_only_lower_gets_charset_hint(self):
        r = assess_strength("abcdefghij")
        # 仅小写 → charset=26，应提示混合字符类型
        assert r.hint != ""

    def test_strong_needs_no_hint(self):
        r = assess_strength("Kx9#Nz2$Qm7!Rv4@Bc8")
        assert r.hint == ""


class TestBoundary:
    def test_score_in_range(self):
        for pwd in ("", "a", "abc", "Password1", "Kx9#Nz2$Qm7!Rv4@"):
            r = assess_strength(pwd)
            assert 0 <= r.score <= 100
            assert (
                r.label
                == {
                    StrengthLevel.VERY_WEAK: "极弱",
                    StrengthLevel.WEAK: "弱",
                    StrengthLevel.FAIR: "一般",
                    StrengthLevel.STRONG: "强",
                    StrengthLevel.VERY_STRONG: "极强",
                }[r.level]
            )

    def test_monotonic_length(self):
        """同字符集下，长度越长分数应不降（允许相等）。"""
        base = "Kx9#Nz"
        prev = assess_strength(base).score
        for ext in ("Kx9#Nz2", "Kx9#Nz2$", "Kx9#Nz2$Qm", "Kx9#Nz2$Qm7!"):
            cur = assess_strength(ext).score
            assert cur >= prev
            prev = cur

    def test_non_ascii_counts_as_charset(self):
        # 含中文时不应被当成"极弱"
        r = assess_strength("密码abc123!")
        assert r.level is not StrengthLevel.VERY_WEAK

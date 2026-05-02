"""密码强度评估（离线、零依赖）。

纯函数 [assess_strength][zhmm.core.password_strength.assess_strength]
基于字符集大小估算熵值，叠加启发式规则（长度下限、连续/键盘序、重复字符、
常见弱密码子串），输出 0-100 分与 5 档等级，供 GUI 强度条实时提示使用。

设计原则：
- 不联网，不查任何远端字典（HIBP 等留待将来可选插件）
- 无额外依赖（不引入 zxcvbn），保证 PyInstaller 打包体积与启动速度
- 纯函数、无 I/O、易于单测
"""

from __future__ import annotations

import math
import re
import string
from dataclasses import dataclass
from enum import IntEnum


class StrengthLevel(IntEnum):
    """5 档强度等级。等级枚举值同时作为序号便于 UI 比较。

    分数区间：
    - VERY_WEAK:   [0, 20)
    - WEAK:        [20, 40)
    - FAIR:        [40, 60)
    - STRONG:      [60, 80)
    - VERY_STRONG: [80, 100]
    """

    VERY_WEAK = 0
    WEAK = 1
    FAIR = 2
    STRONG = 3
    VERY_STRONG = 4


_LEVEL_LABEL: dict[StrengthLevel, str] = {
    StrengthLevel.VERY_WEAK: "极弱",
    StrengthLevel.WEAK: "弱",
    StrengthLevel.FAIR: "一般",
    StrengthLevel.STRONG: "强",
    StrengthLevel.VERY_STRONG: "极强",
}


# 常见弱密码子串（全部小写）。命中即对分数打底。
# 只覆盖最高频的若干，避免把小字典塞进二进制。
_COMMON_WEAK: tuple[str, ...] = (
    "password",
    "passwd",
    "qwerty",
    "admin",
    "root",
    "letmein",
    "welcome",
    "monkey",
    "dragon",
    "master",
    "login",
    "iloveyou",
    "abc123",
    "123456",
    "111111",
    "000000",
    "888888",
    "123123",
)

# 键盘行（小写），用于检测连续 3+ 字符的键盘序
_KEYBOARD_ROWS: tuple[str, ...] = (
    "qwertyuiop",
    "asdfghjkl",
    "zxcvbnm",
    "1234567890",
)

_REPEAT_RE = re.compile(r"(.)\1\1")


@dataclass(frozen=True, slots=True)
class StrengthResult:
    """强度评估结果。

    属性：
    - score:  0-100 的分数，已做边界裁剪
    - level:  对应 [StrengthLevel][zhmm.core.password_strength.StrengthLevel]
    - label:  中文等级标签，直接给 UI 显示
    - hint:   一条最相关的改进建议；若无建议则为空串
    """

    score: int
    level: StrengthLevel
    label: str
    hint: str


def _charset_size(password: str) -> int:
    """估算字符集大小，决定单字符熵值上限。"""
    size = 0
    if any(c.islower() for c in password):
        size += 26
    if any(c.isupper() for c in password):
        size += 26
    if any(c.isdigit() for c in password):
        size += 10
    if any(c in string.punctuation for c in password):
        size += 32
    # 非 ASCII（中文、emoji 等）按中等规模估，避免高估
    if any(ord(c) > 127 for c in password):
        size += 50
    return size


def _has_sequence(password: str) -> bool:
    """检测是否包含 3+ 连续字符：
    - 字符码递增 / 递减（abc / 321）
    - 键盘序（qwe / asdf / 123）
    """
    if len(password) < 3:
        return False

    # 码点连续
    for i in range(len(password) - 2):
        a, b, c = password[i], password[i + 1], password[i + 2]
        if a.isalnum() and b.isalnum() and c.isalnum():
            d1 = ord(b) - ord(a)
            d2 = ord(c) - ord(b)
            if d1 == 1 and d2 == 1:
                return True
            if d1 == -1 and d2 == -1:
                return True

    # 键盘序
    lower = password.lower()
    for row in _KEYBOARD_ROWS:
        for i in range(len(row) - 2):
            if row[i : i + 3] in lower:
                return True
        # 反向键盘序
        rev = row[::-1]
        for i in range(len(rev) - 2):
            if rev[i : i + 3] in lower:
                return True
    return False


def _has_repeat(password: str) -> bool:
    """是否包含 3+ 连续相同字符（aaa / 111）。"""
    return _REPEAT_RE.search(password) is not None


def _score_to_level(score: int) -> StrengthLevel:
    if score < 20:
        return StrengthLevel.VERY_WEAK
    if score < 40:
        return StrengthLevel.WEAK
    if score < 60:
        return StrengthLevel.FAIR
    if score < 80:
        return StrengthLevel.STRONG
    return StrengthLevel.VERY_STRONG


def _build_hint(
    password: str,
    length: int,
    charset: int,
    has_seq: bool,
    has_rep: bool,
    hit_common: bool,
) -> str:
    """按「最该提醒」的优先级给一条建议。"""
    if length < 8:
        return "建议长度 ≥ 8"
    if hit_common:
        return "含常见弱密码子串，建议替换"
    if charset < 26:
        return "建议混用大小写 / 数字 / 符号"
    if has_seq:
        return "含连续字符或键盘序，建议打乱顺序"
    if has_rep:
        return "含重复字符，建议减少重复"
    if charset < 52 and length < 12:
        return "增加字符类型或长度可显著提升强度"
    return ""


def assess_strength(password: str) -> StrengthResult:
    """评估密码强度。

    参数:
        password: 待评估密码（原文明文）

    返回:
        [StrengthResult][zhmm.core.password_strength.StrengthResult]；
        空串返回 score=0、level=VERY_WEAK。
    """
    if not password:
        return StrengthResult(
            score=0,
            level=StrengthLevel.VERY_WEAK,
            label=_LEVEL_LABEL[StrengthLevel.VERY_WEAK],
            hint="",
        )

    length = len(password)
    charset = _charset_size(password)

    # 基础熵值（bits） = length * log2(charset)
    entropy = length * math.log2(charset) if charset > 0 else 0.0
    # 映射到 0-100：经验系数 1.2，使熵 ~64 bit 落在 75 附近
    score_f = entropy * 1.2

    # --- 惩罚项 ---
    unique_ratio = len(set(password)) / length
    if unique_ratio < 0.5:
        score_f *= 0.7

    has_seq = _has_sequence(password)
    if has_seq:
        score_f -= 15

    has_rep = _has_repeat(password)
    if has_rep:
        score_f -= 10

    lower = password.lower()
    hit_common = any(w in lower for w in _COMMON_WEAK)
    if hit_common:
        # 命中常见弱密码直接打底到弱档上限
        score_f = min(score_f, 25)

    # --- 长度硬下限打底 ---
    if length < 6:
        score_f = min(score_f, 15)
    elif length < 8:
        score_f = min(score_f, 30)

    score = max(0, min(100, int(round(score_f))))
    level = _score_to_level(score)
    hint = _build_hint(password, length, charset, has_seq, has_rep, hit_common)

    return StrengthResult(score=score, level=level, label=_LEVEL_LABEL[level], hint=hint)

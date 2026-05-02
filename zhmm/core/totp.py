"""TOTP 2FA 实现（RFC 6238）+ 国密 SM3-TOTP 扩展。

本模块为纯函数实现，无 I/O、无全局状态，便于单元测试。

支持的算法
---------

- ``SHA1`` / ``SHA256`` / ``SHA512``：标准 RFC 6238，与 Google Authenticator 等
  所有主流 2FA App 兼容。
- ``SM3``：项目扩展，使用国密 SM3 作为 HMAC 底层哈希。**非国际标准**，仅
  zhmm 自身识别；`otpauth://` URI 中会写为 ``algorithm=SM3``。

安全说明
-------

- secret 永远以 Base32 字符串在接口层流转，解码后的原始密钥只在本模块
  的一次函数调用中短暂存在；调用方不要把 secret 放进日志。
- 本模块不负责 secret 的持久化加密，secret 随整个 Vault 经 SM4-CBC +
  HMAC-SM3 加密落盘（见 :mod:`zhmm.core.crypto`）。
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import struct
import time
from collections.abc import Callable
from typing import Any, Final, TypedDict
from urllib.parse import parse_qs, unquote, urlparse

from zhmm.core.crypto import _Sm3Hash
from zhmm.core.errors import ValidationError

SUPPORTED_ALGOS: Final[tuple[str, ...]] = ("SHA1", "SHA256", "SHA512", "SM3")
DEFAULT_ALGO: Final[str] = "SHA1"
DEFAULT_DIGITS: Final[int] = 6
DEFAULT_PERIOD: Final[int] = 30

_MIN_DIGITS: Final[int] = 6
_MAX_DIGITS: Final[int] = 10
_MIN_PERIOD: Final[int] = 1
_MAX_PERIOD: Final[int] = 300


class OtpAuthParams(TypedDict, total=False):
    """otpauth:// URI 解析结果。"""

    secret: str
    algo: str
    digits: int
    period: int
    label: str
    issuer: str


def _digestmod(algo: str) -> Callable[..., Any]:
    """把算法名映射到 hashlib 风格的构造器。

    返回 `Callable[..., Any]` 以同时容纳 hashlib 内置 hash 构造器
    与 _Sm3Hash 类，hmac.new 底层走 duck typing。
    """
    a = algo.upper()
    if a == "SM3":
        return _Sm3Hash
    if a == "SHA1":
        return hashlib.sha1
    if a == "SHA256":
        return hashlib.sha256
    if a == "SHA512":
        return hashlib.sha512
    raise ValidationError(f"unsupported totp algorithm: {algo}")


def decode_secret(secret_b32: str) -> bytes:
    """把用户输入的 Base32 secret 解码为原始字节。

    允许：
    - 大小写混用（内部统一转大写）
    - 含空格（常见复制粘贴场景）
    - 缺 ``=`` 填充（按 8 的倍数自动补齐）

    Raises:
        ValidationError: 输入非法、含非 Base32 字符或解码失败。
    """
    if not isinstance(secret_b32, str) or not secret_b32.strip():
        raise ValidationError("totp secret must be a non-empty str")
    s = secret_b32.strip().replace(" ", "").replace("-", "").upper()
    # Base32 要求长度为 8 的倍数，缺的补 "="
    pad = (-len(s)) % 8
    s = s + ("=" * pad)
    try:
        return base64.b32decode(s, casefold=True)
    except (binascii.Error, ValueError) as ex:
        raise ValidationError(f"invalid base32 secret: {ex}") from ex


def _validate_params(digits: int, period: int) -> None:
    if not isinstance(digits, int) or not (_MIN_DIGITS <= digits <= _MAX_DIGITS):
        raise ValidationError(f"totp digits out of range: {digits}")
    if not isinstance(period, int) or not (_MIN_PERIOD <= period <= _MAX_PERIOD):
        raise ValidationError(f"totp period out of range: {period}")


def generate(
    secret_b32: str,
    *,
    algo: str = DEFAULT_ALGO,
    digits: int = DEFAULT_DIGITS,
    period: int = DEFAULT_PERIOD,
    now: float | None = None,
) -> str:
    """计算当前时间片对应的 TOTP 验证码。

    Args:
        secret_b32: Base32 编码的 secret。
        algo: 算法名，见 :data:`SUPPORTED_ALGOS`。
        digits: 生成的位数，典型为 6 或 8。
        period: 时间步长（秒）。
        now: 自 UNIX epoch 起的秒数；None 表示使用当前系统时间。

    Returns:
        长度为 ``digits`` 的数字字符串（左侧补 0）。

    Raises:
        ValidationError: 参数不合法（secret 格式错、algo 不支持、digits/period 越界）。
    """
    _validate_params(digits, period)
    key = decode_secret(secret_b32)
    dm = _digestmod(algo)
    t_now = time.time() if now is None else now
    counter = int(t_now // period)
    msg = struct.pack(">Q", counter)
    # hmac.new 对 digestmod 走 duck typing；_Sm3Hash 实现了所需最小集
    digest = hmac.new(key, msg, digestmod=dm).digest()
    # RFC 4226 动态截断
    offset = digest[-1] & 0x0F
    code_int = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFF_FFFF
    modulus = 10**digits
    return str(code_int % modulus).zfill(digits)


def remaining_seconds(period: int = DEFAULT_PERIOD, now: float | None = None) -> int:
    """返回当前时间片距离下一次刷新的剩余秒数（至少 1）。"""
    if not isinstance(period, int) or period <= 0:
        raise ValidationError(f"totp period out of range: {period}")
    t_now = time.time() if now is None else now
    elapsed = int(t_now) % period
    left = period - elapsed
    # 刚好落在边界时返回整个 period，避免返回 0
    return left if left > 0 else period


def parse_otpauth_uri(uri: str) -> OtpAuthParams:
    """解析 ``otpauth://totp/<label>?secret=...&...`` URI。

    支持可选参数 ``algorithm`` / ``digits`` / ``period`` / ``issuer``；算法名
    大小写不敏感，允许 ``SM3`` 作为项目扩展。

    Raises:
        ValidationError: 非 otpauth URI、type 不是 totp、缺少 secret 或参数非法。
    """
    if not isinstance(uri, str) or not uri.strip():
        raise ValidationError("otpauth uri must be a non-empty str")
    parsed = urlparse(uri.strip())
    if parsed.scheme.lower() != "otpauth":
        raise ValidationError("not an otpauth uri")
    if parsed.netloc.lower() != "totp":
        raise ValidationError(f"unsupported otpauth type: {parsed.netloc}")

    query = parse_qs(parsed.query, keep_blank_values=False)

    def _first(name: str) -> str:
        vals = query.get(name) or []
        return vals[0] if vals else ""

    secret = _first("secret")
    if not secret:
        raise ValidationError("otpauth uri missing secret")

    algo_raw = _first("algorithm") or DEFAULT_ALGO
    algo = algo_raw.upper()
    if algo not in SUPPORTED_ALGOS:
        raise ValidationError(f"unsupported otpauth algorithm: {algo_raw}")

    digits_raw = _first("digits")
    digits = int(digits_raw) if digits_raw else DEFAULT_DIGITS
    period_raw = _first("period")
    period = int(period_raw) if period_raw else DEFAULT_PERIOD
    _validate_params(digits, period)

    issuer = _first("issuer")
    # label: otpauth://totp/Issuer:Account 或 otpauth://totp/Account
    label_path = unquote(parsed.path.lstrip("/"))
    if not issuer and ":" in label_path:
        issuer_part, _, _ = label_path.partition(":")
        issuer = issuer_part.strip()

    result: OtpAuthParams = {
        "secret": secret,
        "algo": algo,
        "digits": digits,
        "period": period,
        "label": label_path,
        "issuer": issuer,
    }
    return result


__all__ = [
    "SUPPORTED_ALGOS",
    "DEFAULT_ALGO",
    "DEFAULT_DIGITS",
    "DEFAULT_PERIOD",
    "OtpAuthParams",
    "decode_secret",
    "generate",
    "remaining_seconds",
    "parse_otpauth_uri",
]

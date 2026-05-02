"""TOTP 核心模块单元测试。

- 使用 RFC 6238 附录 B 的官方测试向量覆盖 SHA1/SHA256/SHA512。
- SM3 作为项目扩展，无官方向量，做自证（结果稳定 + 边界行为）。
"""

from __future__ import annotations

import base64

import pytest

from zhmm.core.errors import ValidationError
from zhmm.core.totp import (
    DEFAULT_ALGO,
    DEFAULT_DIGITS,
    DEFAULT_PERIOD,
    decode_secret,
    generate,
    parse_otpauth_uri,
    remaining_seconds,
)

# RFC 6238 Appendix B 指定的 ASCII 密钥
_SHA1_KEY = b"12345678901234567890"  # 20 bytes
_SHA256_KEY = b"12345678901234567890123456789012"  # 32 bytes
_SHA512_KEY = b"1234567890123456789012345678901234567890123456789012345678901234"  # 64 bytes

_SHA1_SECRET = base64.b32encode(_SHA1_KEY).decode()
_SHA256_SECRET = base64.b32encode(_SHA256_KEY).decode()
_SHA512_SECRET = base64.b32encode(_SHA512_KEY).decode()

# (time_seconds, sha1, sha256, sha512) —— 来自 RFC 6238 附录 B
_RFC6238_VECTORS = [
    (59, "94287082", "46119246", "90693936"),
    (1111111109, "07081804", "68084774", "25091201"),
    (1111111111, "14050471", "67062674", "99943326"),
    (1234567890, "89005924", "91819424", "93441116"),
    (2000000000, "69279037", "90698825", "38618901"),
    (20000000000, "65353130", "77737706", "47863826"),
]


@pytest.mark.parametrize("t,sha1,sha256,sha512", _RFC6238_VECTORS)
def test_rfc6238_vectors_sha1(t: int, sha1: str, sha256: str, sha512: str) -> None:
    assert generate(_SHA1_SECRET, algo="SHA1", digits=8, period=30, now=t) == sha1


@pytest.mark.parametrize("t,sha1,sha256,sha512", _RFC6238_VECTORS)
def test_rfc6238_vectors_sha256(t: int, sha1: str, sha256: str, sha512: str) -> None:
    assert generate(_SHA256_SECRET, algo="SHA256", digits=8, period=30, now=t) == sha256


@pytest.mark.parametrize("t,sha1,sha256,sha512", _RFC6238_VECTORS)
def test_rfc6238_vectors_sha512(t: int, sha1: str, sha256: str, sha512: str) -> None:
    assert generate(_SHA512_SECRET, algo="SHA512", digits=8, period=30, now=t) == sha512


def test_default_parameters_produce_6_digits() -> None:
    code = generate(_SHA1_SECRET, now=59)
    assert len(code) == DEFAULT_DIGITS
    assert code.isdigit()


def test_sm3_stable_output() -> None:
    """SM3 无官方向量，做稳定性自证：同输入必须等于同输出。"""
    a = generate(_SHA1_SECRET, algo="SM3", digits=6, period=30, now=1700000000)
    b = generate(_SHA1_SECRET, algo="SM3", digits=6, period=30, now=1700000000)
    assert a == b
    assert len(a) == 6
    assert a.isdigit()


def test_sm3_differs_from_sha1() -> None:
    a = generate(_SHA1_SECRET, algo="SHA1", digits=6, period=30, now=1700000000)
    b = generate(_SHA1_SECRET, algo="SM3", digits=6, period=30, now=1700000000)
    # 两种不同哈希即便输入相同，结果几乎必然不同；若相同说明实现有误
    assert a != b


def test_decode_secret_tolerates_whitespace_and_case() -> None:
    raw = base64.b32encode(b"hello world").decode()
    variants = [raw, raw.lower(), raw + " ", " " + raw, raw.replace("", " ", 1)]
    for v in variants:
        assert decode_secret(v) == b"hello world"


def test_decode_secret_pads_missing_equals() -> None:
    # base32 of "ab" = "MFRA" plus 4 padding "====" → 完整是 "MFRA===="
    # 去掉 padding 后仍应正确解码
    assert decode_secret("MFRA") == b"ab"


def test_decode_secret_invalid_raises() -> None:
    with pytest.raises(ValidationError):
        decode_secret("")
    with pytest.raises(ValidationError):
        decode_secret("!!!not-base32!!!")


def test_generate_rejects_unsupported_algo() -> None:
    with pytest.raises(ValidationError):
        generate(_SHA1_SECRET, algo="MD5", now=0)


def test_generate_rejects_bad_digits_period() -> None:
    with pytest.raises(ValidationError):
        generate(_SHA1_SECRET, digits=3, now=0)
    with pytest.raises(ValidationError):
        generate(_SHA1_SECRET, period=0, now=0)


def test_remaining_seconds_boundary() -> None:
    # 30 秒周期：t=0 剩余 30，t=1 剩余 29，t=29 剩余 1，t=30 再次剩余 30
    assert remaining_seconds(30, now=0.0) == 30
    assert remaining_seconds(30, now=1.0) == 29
    assert remaining_seconds(30, now=29.0) == 1
    assert remaining_seconds(30, now=30.0) == 30


def test_parse_otpauth_uri_basic() -> None:
    uri = f"otpauth://totp/Example:alice%40google.com?secret={_SHA1_SECRET}&issuer=Example"
    out = parse_otpauth_uri(uri)
    assert out["secret"] == _SHA1_SECRET
    assert out["algo"] == DEFAULT_ALGO
    assert out["digits"] == DEFAULT_DIGITS
    assert out["period"] == DEFAULT_PERIOD
    assert out["issuer"] == "Example"
    assert "alice@google.com" in out["label"]


def test_parse_otpauth_uri_with_sm3_extension() -> None:
    uri = f"otpauth://totp/zhmm?secret={_SHA1_SECRET}&algorithm=SM3&digits=8&period=60"
    out = parse_otpauth_uri(uri)
    assert out["algo"] == "SM3"
    assert out["digits"] == 8
    assert out["period"] == 60


def test_parse_otpauth_uri_infers_issuer_from_label() -> None:
    uri = f"otpauth://totp/GitHub:ws?secret={_SHA1_SECRET}"
    out = parse_otpauth_uri(uri)
    assert out["issuer"] == "GitHub"


def test_parse_otpauth_uri_rejects_non_otpauth() -> None:
    with pytest.raises(ValidationError):
        parse_otpauth_uri("https://example.com/?secret=ABC")


def test_parse_otpauth_uri_rejects_missing_secret() -> None:
    with pytest.raises(ValidationError):
        parse_otpauth_uri("otpauth://totp/label?issuer=X")


def test_parse_otpauth_uri_rejects_non_totp_type() -> None:
    with pytest.raises(ValidationError):
        parse_otpauth_uri(f"otpauth://hotp/label?secret={_SHA1_SECRET}")

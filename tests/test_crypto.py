"""Tests for :mod:`zhmm.core.crypto`.

覆盖：
- 正常 seal/open 往返（ASCII / Unicode / 大文件 / 单字节）
- 参数校验（空密码、非 str 账号、非 bytes 明文、非 bytes blob）
- 密文篡改检测（tag、iv、salt、ciphertext 各位置）
- 版本/魔数不匹配（含 v3 硬切拒绝）
- 短密文
- 不同账号/不同密码派生不同密钥
- 每次 seal 结果不同（salt/iv 随机性）
- 账号参与 KDF 的专项用例
"""

from __future__ import annotations

import pytest

from zhmm.core.crypto import (
    _HEADER_LEN,
    IV_LEN,
    MAGIC,
    SALT_LEN,
    TAG_LEN,
    VERSION,
    Vault,
)
from zhmm.core.errors import CryptoError, ValidationError


class TestSealOpenRoundtrip:
    """seal → open 往返验证。"""

    def test_ascii_roundtrip(self):
        pt = b"hello, world!"
        blob = Vault.seal("alice", "password", pt)
        assert Vault.open("alice", "password", blob) == pt

    def test_unicode_roundtrip(self):
        pt = "你好，世界 🌍 zhmm".encode()
        blob = Vault.seal("张三", "密码😀", pt)
        assert Vault.open("张三", "密码😀", blob) == pt

    def test_empty_plaintext(self):
        # 空明文是合法输入；SM4-CBC PKCS7 会产出一个全 padding 的块
        blob = Vault.seal("acc", "pw", b"")
        assert Vault.open("acc", "pw", blob) == b""

    def test_single_byte_plaintext(self):
        blob = Vault.seal("acc", "pw", b"x")
        assert Vault.open("acc", "pw", blob) == b"x"

    def test_large_plaintext(self):
        pt = b"A" * 100_000
        blob = Vault.seal("acc", "pw", pt)
        assert Vault.open("acc", "pw", blob) == pt

    @pytest.mark.parametrize("size", [15, 16, 17, 31, 32, 33])
    def test_block_boundary(self, size: int):
        """明文长度跨 SM4 块边界 (16B)。"""
        pt = bytes(range(size))
        blob = Vault.seal("acc", "pw", pt)
        assert Vault.open("acc", "pw", blob) == pt


class TestValidation:
    """输入校验。"""

    def test_seal_empty_password_rejected(self):
        with pytest.raises(ValidationError):
            Vault.seal("acc", "", b"x")

    def test_seal_non_str_password_rejected(self):
        with pytest.raises(ValidationError):
            Vault.seal("acc", b"pw", b"x")  # type: ignore[arg-type]

    def test_seal_non_str_account_rejected(self):
        with pytest.raises(ValidationError):
            Vault.seal(b"acc", "pw", b"x")  # type: ignore[arg-type]

    def test_seal_non_bytes_plaintext_rejected(self):
        with pytest.raises(ValidationError):
            Vault.seal("acc", "pw", "not bytes")  # type: ignore[arg-type]

    def test_open_empty_password_rejected(self):
        blob = Vault.seal("acc", "pw", b"x")
        with pytest.raises(ValidationError):
            Vault.open("acc", "", blob)

    def test_open_non_str_account_rejected(self):
        blob = Vault.seal("acc", "pw", b"x")
        with pytest.raises(ValidationError):
            Vault.open(b"acc", "pw", blob)  # type: ignore[arg-type]

    def test_open_non_bytes_blob_rejected(self):
        with pytest.raises(ValidationError):
            Vault.open("acc", "pw", "not bytes")  # type: ignore[arg-type]

    def test_open_too_short_blob_rejected(self):
        with pytest.raises(ValidationError):
            Vault.open("acc", "pw", b"\x00" * 10)


class TestTamperDetection:
    """篡改检测（AEAD 完整性）。"""

    @pytest.fixture
    def blob(self) -> bytes:
        return Vault.seal("alice", "password", b"secret message")

    def test_wrong_password(self, blob: bytes):
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "wrong-password", blob)

    def test_wrong_account_raises_crypto_error(self, blob: bytes):
        """账号错误与密码错误表现一致（HMAC 认证失败）。"""
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("bob", "password", blob)

    def test_tampered_tag(self, blob: bytes):
        tampered = blob[:-1] + bytes([blob[-1] ^ 0x01])
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "password", tampered)

    def test_tampered_ciphertext(self, blob: bytes):
        # 翻转密文区域首字节的一个 bit
        idx = _HEADER_LEN
        tampered = blob[:idx] + bytes([blob[idx] ^ 0x01]) + blob[idx + 1 :]
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "password", tampered)

    def test_tampered_iv(self, blob: bytes):
        idx = len(MAGIC) + 1 + SALT_LEN  # iv 起始
        tampered = blob[:idx] + bytes([blob[idx] ^ 0x01]) + blob[idx + 1 :]
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "password", tampered)

    def test_tampered_salt(self, blob: bytes):
        idx = len(MAGIC) + 1  # salt 起始
        tampered = blob[:idx] + bytes([blob[idx] ^ 0x01]) + blob[idx + 1 :]
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "password", tampered)

    def test_bad_magic(self, blob: bytes):
        tampered = b"XXXX" + blob[4:]
        with pytest.raises(CryptoError, match="magic mismatch"):
            Vault.open("alice", "password", tampered)

    def test_unsupported_version(self, blob: bytes):
        tampered = blob[:4] + bytes([VERSION + 1]) + blob[5:]
        with pytest.raises(CryptoError, match="unsupported vault version"):
            Vault.open("alice", "password", tampered)

    def test_v3_blob_is_rejected(self, blob: bytes):
        """历史 v3 blob 必须被硬拒（升级到 v4 后不再兼容）。"""
        tampered = blob[:4] + bytes([3]) + blob[5:]
        with pytest.raises(CryptoError, match="unsupported vault version"):
            Vault.open("alice", "password", tampered)


class TestRandomness:
    """每次 seal 产生不同 blob（salt/iv 随机）。"""

    def test_seal_is_non_deterministic(self):
        a = Vault.seal("acc", "pw", b"same plaintext")
        b = Vault.seal("acc", "pw", b"same plaintext")
        assert a != b
        # 但都能解开
        assert Vault.open("acc", "pw", a) == Vault.open("acc", "pw", b) == b"same plaintext"


class TestAccountInKdf:
    """账号参与 KDF 的专项用例。"""

    def test_different_account_same_password_gives_different_ciphertext(self):
        """相同密码 + 不同账号 → 密文完全不同，且彼此不可解。"""
        pt = b"shared plaintext"
        blob_a = Vault.seal("alice", "weak123", pt)
        blob_b = Vault.seal("bob", "weak123", pt)
        assert blob_a != blob_b
        # 两个 blob 都能被各自的账号解开
        assert Vault.open("alice", "weak123", blob_a) == pt
        assert Vault.open("bob", "weak123", blob_b) == pt
        # 但相互不能解开
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "weak123", blob_b)
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("bob", "weak123", blob_a)

    def test_same_account_same_password_roundtrip(self):
        """基本幂等性：同账号同密码可正常往返。"""
        pt = b"consistency check"
        blob = Vault.seal("charlie", "s3cret", pt)
        assert Vault.open("charlie", "s3cret", blob) == pt

    def test_empty_account_allowed_in_crypto_layer(self):
        """crypto 层允许空字符串账号（由业务层拒绝空值）。"""
        pt = b"no account bound"
        blob = Vault.seal("", "pw", pt)
        assert Vault.open("", "pw", blob) == pt
        # 空账号与非空账号派生的密钥不同
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "pw", blob)


class TestFormatInvariants:
    """文件格式不变式。"""

    def test_blob_starts_with_magic(self):
        blob = Vault.seal("acc", "pw", b"x")
        assert blob.startswith(MAGIC)

    def test_version_byte_is_4(self):
        blob = Vault.seal("acc", "pw", b"x")
        assert blob[len(MAGIC)] == VERSION == 4

    def test_minimum_overhead(self):
        # 单字节明文 -> 1 个 SM4 块 (16B) -> 总开销 = header + 16 + tag = 69B
        blob = Vault.seal("acc", "pw", b"x")
        expected = _HEADER_LEN + 16 + TAG_LEN
        assert len(blob) == expected

    def test_header_len_constant(self):
        assert _HEADER_LEN == len(MAGIC) + 1 + SALT_LEN + IV_LEN == 37

    def test_tag_len_constant(self):
        assert TAG_LEN == 32

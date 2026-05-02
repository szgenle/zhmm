"""Tests for :mod:`zhmm.core.crypto`.

覆盖：
- 正常 seal/open 往返（ASCII / Unicode / 大文件 / 单字节）
- 参数校验（空密码、非 str 账号、非 bytes 明文、非 bytes blob）
- 密文篡改检测（tag、iv、salt、ciphertext、Argon2 参数各位置）
- 版本/魔数不匹配（含 v3、v4 硬切拒绝）
- 短密文
- 不同账号/不同密码派生不同密钥
- 每次 seal 结果不同（salt/iv 随机性）
- 账号参与 KDF 的专项用例
- v5 文件格式不变式（头部内嵌 Argon2 参数）
- Argon2 参数越界拒绝
"""

from __future__ import annotations

import struct

import pytest

from zhmm.core import crypto as _crypto_module
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

# Header 偏移量（用于测试级解析）
_OFF_VERSION = len(MAGIC)
_OFF_M_COST = _OFF_VERSION + 1
_OFF_T_COST = _OFF_M_COST + 4
_OFF_P_COST = _OFF_T_COST + 4
_OFF_SALT = _OFF_P_COST + 4
_OFF_IV = _OFF_SALT + SALT_LEN


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
        idx = _OFF_IV  # iv 起始
        tampered = blob[:idx] + bytes([blob[idx] ^ 0x01]) + blob[idx + 1 :]
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "password", tampered)

    def test_tampered_salt(self, blob: bytes):
        idx = _OFF_SALT  # salt 起始
        tampered = blob[:idx] + bytes([blob[idx] ^ 0x01]) + blob[idx + 1 :]
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "password", tampered)

    def test_tampered_m_cost(self, blob: bytes):
        """篡改 header 中的 Argon2 m_cost 会被 HMAC 检测。"""
        # 将 m_cost 从 8（测试值）改为 16，合法范围内但 HMAC 不对
        tampered = blob[:_OFF_M_COST] + struct.pack(">I", 16) + blob[_OFF_M_COST + 4 :]
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "password", tampered)

    def test_tampered_t_cost(self, blob: bytes):
        tampered = blob[:_OFF_T_COST] + struct.pack(">I", 2) + blob[_OFF_T_COST + 4 :]
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
        """历史 v3 blob 必须被硬拒（已升级到 v5 后不再兼容）。"""
        tampered = blob[:4] + bytes([3]) + blob[5:]
        with pytest.raises(CryptoError, match="unsupported vault version"):
            Vault.open("alice", "password", tampered)

    def test_v4_blob_is_rejected(self, blob: bytes):
        """历史 v4 blob（PBKDF2）必须被硬拒（已升级到 v5 后不再兼容）。"""
        tampered = blob[:4] + bytes([4]) + blob[5:]
        with pytest.raises(CryptoError, match="unsupported vault version"):
            Vault.open("alice", "password", tampered)


class TestArgon2ParameterValidation:
    """Argon2 参数越界拒绝（防 DoS）。"""

    @pytest.fixture
    def blob(self) -> bytes:
        return Vault.seal("alice", "password", b"x")

    def test_m_cost_too_large_rejected(self, blob: bytes):
        """恶意 blob 构造 m_cost=1 GiB 应被拒绝（避免 OOM）。"""
        # 1_048_576 KiB = 1 GiB，超出 _ARGON2_M_MAX
        tampered = blob[:_OFF_M_COST] + struct.pack(">I", 1_048_576) + blob[_OFF_M_COST + 4 :]
        with pytest.raises(CryptoError, match="m_cost out of range"):
            Vault.open("alice", "password", tampered)

    def test_m_cost_too_small_rejected(self, blob: bytes):
        tampered = blob[:_OFF_M_COST] + struct.pack(">I", 1) + blob[_OFF_M_COST + 4 :]
        with pytest.raises(CryptoError, match="m_cost out of range"):
            Vault.open("alice", "password", tampered)

    def test_t_cost_zero_rejected(self, blob: bytes):
        tampered = blob[:_OFF_T_COST] + struct.pack(">I", 0) + blob[_OFF_T_COST + 4 :]
        with pytest.raises(CryptoError, match="t_cost out of range"):
            Vault.open("alice", "password", tampered)

    def test_t_cost_too_large_rejected(self, blob: bytes):
        tampered = blob[:_OFF_T_COST] + struct.pack(">I", 1_000) + blob[_OFF_T_COST + 4 :]
        with pytest.raises(CryptoError, match="t_cost out of range"):
            Vault.open("alice", "password", tampered)

    def test_p_cost_zero_rejected(self, blob: bytes):
        tampered = blob[:_OFF_P_COST] + struct.pack(">I", 0) + blob[_OFF_P_COST + 4 :]
        with pytest.raises(CryptoError, match="p_cost out of range"):
            Vault.open("alice", "password", tampered)

    def test_p_cost_too_large_rejected(self, blob: bytes):
        tampered = blob[:_OFF_P_COST] + struct.pack(">I", 1_024) + blob[_OFF_P_COST + 4 :]
        with pytest.raises(CryptoError, match="p_cost out of range"):
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
    """文件格式不变式（v5）。"""

    def test_blob_starts_with_magic(self):
        blob = Vault.seal("acc", "pw", b"x")
        assert blob.startswith(MAGIC)

    def test_version_byte_is_5(self):
        blob = Vault.seal("acc", "pw", b"x")
        assert blob[len(MAGIC)] == VERSION == 5

    def test_minimum_overhead(self):
        # 单字节明文 -> 1 个 SM4 块 (16B) -> 总开销 = header + 16 + tag = 81B
        blob = Vault.seal("acc", "pw", b"x")
        expected = _HEADER_LEN + 16 + TAG_LEN
        assert len(blob) == expected

    def test_header_len_constant(self):
        # header = magic(4) + version(1) + m_cost(4) + t_cost(4) + p_cost(4)
        #         + salt(16) + iv(16) = 49
        assert _HEADER_LEN == len(MAGIC) + 1 + 12 + SALT_LEN + IV_LEN == 49

    def test_tag_len_constant(self):
        assert TAG_LEN == 32

    def test_blob_embeds_current_kdf_params(self):
        """blob 头部内嵌的 Argon2 参数应与模块当前默认值一致。

        这样未来调整默认强度时，老 blob 仍可用其原始参数解密。
        """
        blob = Vault.seal("acc", "pw", b"x")
        m_cost, t_cost, p_cost = struct.unpack(">III", blob[_OFF_M_COST : _OFF_M_COST + 12])
        assert m_cost == _crypto_module.ARGON2_M_COST
        assert t_cost == _crypto_module.ARGON2_T_COST
        assert p_cost == _crypto_module.ARGON2_P_COST

    def test_blob_with_different_m_cost_still_decryptable(self, monkeypatch: pytest.MonkeyPatch):
        """老 blob 用旧参数加密，默认参数升级后仍应可解密（头部内嵌机制）。"""
        # 第一次 seal 使用 m=8
        monkeypatch.setattr(_crypto_module, "ARGON2_M_COST", 8)
        blob = Vault.seal("acc", "pw", b"legacy")
        # 默认参数升级为 m=16
        monkeypatch.setattr(_crypto_module, "ARGON2_M_COST", 16)
        # 仍能解密（用 blob 中记录的 m=8，而非当前默认 m=16）
        assert Vault.open("acc", "pw", blob) == b"legacy"

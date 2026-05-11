"""Tests for :mod:`zhmm.core.crypto`.

覆盖：
- 正常 seal/open 往返（ASCII / Unicode / 大文件 / 单字节 / 空明文）
- 参数校验（空密码、非 str 账号、非 bytes 明文、非 bytes blob）
- 密文篡改检测（tag、iv、salt、ciphertext、Argon2 参数各位置，header 任意字节）
- 版本/魔数不匹配（v3 / v4 硬拒绝）
- v5 legacy blob 向后兼容读
- 不同账号/不同密码派生不同密钥
- 每次 seal 结果不同（salt/iv 随机性）
- 账号参与 KDF 的专项用例
- v6 文件格式不变式
- Argon2 参数越界拒绝
- SM4-GCM 内部原语（GHASH / CTR 自洽）
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
    _gf128_mul,
    _ghash,
    _hmac_sm3,
    _inc32,
    _sm4_ctr_xor,
    _sm4_encrypt_block,
    _sm4_gcm_open,
    _sm4_gcm_seal,
)
from zhmm.core.errors import CryptoError, ValidationError

# Header 偏移量（v6：magic(4) ver(1) m(4) t(4) p(4) salt(16) iv(12) = 45）
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
        # v6 (GCM/CTR) 天然支持空明文，无 padding 概念
        blob = Vault.seal("acc", "pw", b"")
        assert Vault.open("acc", "pw", blob) == b""
        # 开销 = header(45) + tag(16) = 61
        assert len(blob) == _HEADER_LEN + TAG_LEN

    def test_single_byte_plaintext(self):
        blob = Vault.seal("acc", "pw", b"x")
        assert Vault.open("acc", "pw", blob) == b"x"
        # 单字节明文不会补齐，总长 = header + 1 + tag
        assert len(blob) == _HEADER_LEN + 1 + TAG_LEN

    def test_large_plaintext(self):
        pt = b"A" * 100_000
        blob = Vault.seal("acc", "pw", pt)
        assert Vault.open("acc", "pw", blob) == pt
        # CTR 密文长度 == 明文长度
        assert len(blob) == _HEADER_LEN + 100_000 + TAG_LEN

    @pytest.mark.parametrize("size", [0, 1, 15, 16, 17, 31, 32, 33, 255, 256])
    def test_arbitrary_length(self, size: int):
        """v6 (CTR) 支持任意字节长度，不再受限于 16B 对齐。"""
        pt = bytes(range(size % 256)) * (size // 256 + 1)
        pt = pt[:size]
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
        with pytest.raises((ValidationError, CryptoError)):
            Vault.open("acc", "pw", b"\x00" * 4)


class TestTamperDetection:
    """篡改检测（AEAD 完整性）。"""

    @pytest.fixture
    def blob(self) -> bytes:
        return Vault.seal("alice", "password", b"secret message")

    def test_wrong_password(self, blob: bytes):
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "wrong-password", blob)

    def test_wrong_account_raises_crypto_error(self, blob: bytes):
        """账号错误与密码错误表现一致（AEAD 认证失败）。"""
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("bob", "password", blob)

    def test_tampered_tag(self, blob: bytes):
        tampered = blob[:-1] + bytes([blob[-1] ^ 0x01])
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "password", tampered)

    def test_tampered_ciphertext(self, blob: bytes):
        idx = _HEADER_LEN
        tampered = blob[:idx] + bytes([blob[idx] ^ 0x01]) + blob[idx + 1 :]
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "password", tampered)

    def test_tampered_iv(self, blob: bytes):
        idx = _OFF_IV
        tampered = blob[:idx] + bytes([blob[idx] ^ 0x01]) + blob[idx + 1 :]
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "password", tampered)

    def test_tampered_salt(self, blob: bytes):
        idx = _OFF_SALT
        tampered = blob[:idx] + bytes([blob[idx] ^ 0x01]) + blob[idx + 1 :]
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "password", tampered)

    def test_tampered_m_cost(self, blob: bytes):
        """header 中 Argon2 m_cost 是 AAD 的一部分，改动会触发认证失败。"""
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
        """历史 v3 blob 仍被硬拒（已弃用）。"""
        tampered = blob[:4] + bytes([3]) + blob[5:]
        with pytest.raises(CryptoError, match="unsupported vault version"):
            Vault.open("alice", "password", tampered)

    def test_v4_blob_is_rejected(self, blob: bytes):
        """历史 v4 blob 仍被硬拒（已弃用）。"""
        tampered = blob[:4] + bytes([4]) + blob[5:]
        with pytest.raises(CryptoError, match="unsupported vault version"):
            Vault.open("alice", "password", tampered)


class TestArgon2ParameterValidation:
    """Argon2 参数越界拒绝（防 DoS）。

    注意：v6 里 Argon2 参数是 AAD 的一部分，任何值的改动都会先触发
    AAD 认证失败（而非显式的 out-of-range）。本组测试直接调用内部
    ``_validate_argon2_params`` / 构造合法 AAD 来验证 range 检查仍然生效。
    """

    def test_m_cost_range_enforced(self):
        with pytest.raises(CryptoError, match="m_cost out of range"):
            _crypto_module._validate_argon2_params(1_048_576, 3, 1)  # 1 GiB, 越界
        with pytest.raises(CryptoError, match="m_cost out of range"):
            _crypto_module._validate_argon2_params(1, 3, 1)

    def test_t_cost_range_enforced(self):
        with pytest.raises(CryptoError, match="t_cost out of range"):
            _crypto_module._validate_argon2_params(64_000, 0, 1)
        with pytest.raises(CryptoError, match="t_cost out of range"):
            _crypto_module._validate_argon2_params(64_000, 1_000, 1)

    def test_p_cost_range_enforced(self):
        with pytest.raises(CryptoError, match="p_cost out of range"):
            _crypto_module._validate_argon2_params(64_000, 3, 0)
        with pytest.raises(CryptoError, match="p_cost out of range"):
            _crypto_module._validate_argon2_params(64_000, 3, 1024)


class TestRandomness:
    """每次 seal 产生不同 blob（salt/iv 随机）。"""

    def test_seal_is_non_deterministic(self):
        a = Vault.seal("acc", "pw", b"same plaintext")
        b = Vault.seal("acc", "pw", b"same plaintext")
        assert a != b
        assert Vault.open("acc", "pw", a) == Vault.open("acc", "pw", b) == b"same plaintext"


class TestAccountInKdf:
    """账号参与 KDF 的专项用例。"""

    def test_different_account_same_password_gives_different_ciphertext(self):
        pt = b"shared plaintext"
        blob_a = Vault.seal("alice", "weak123", pt)
        blob_b = Vault.seal("bob", "weak123", pt)
        assert blob_a != blob_b
        assert Vault.open("alice", "weak123", blob_a) == pt
        assert Vault.open("bob", "weak123", blob_b) == pt
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "weak123", blob_b)
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("bob", "weak123", blob_a)

    def test_same_account_same_password_roundtrip(self):
        pt = b"consistency check"
        blob = Vault.seal("charlie", "s3cret", pt)
        assert Vault.open("charlie", "s3cret", blob) == pt

    def test_empty_account_allowed_in_crypto_layer(self):
        pt = b"no account bound"
        blob = Vault.seal("", "pw", pt)
        assert Vault.open("", "pw", blob) == pt
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "pw", blob)


class TestFormatInvariants:
    """文件格式不变式（v6）。"""

    def test_blob_starts_with_magic(self):
        blob = Vault.seal("acc", "pw", b"x")
        assert blob.startswith(MAGIC)

    def test_version_byte_is_6(self):
        blob = Vault.seal("acc", "pw", b"x")
        assert blob[len(MAGIC)] == VERSION == 6

    def test_iv_len_is_12(self):
        assert IV_LEN == 12

    def test_tag_len_is_16(self):
        assert TAG_LEN == 16

    def test_header_len_constant(self):
        # header = magic(4) + version(1) + m/t/p(12) + salt(16) + iv(12) = 45
        assert _HEADER_LEN == len(MAGIC) + 1 + 12 + SALT_LEN + IV_LEN == 45

    def test_minimum_overhead(self):
        # CTR 无 padding：1B 明文 -> 45 + 1 + 16 = 62
        blob = Vault.seal("acc", "pw", b"x")
        assert len(blob) == _HEADER_LEN + 1 + TAG_LEN

    def test_blob_embeds_current_kdf_params(self):
        blob = Vault.seal("acc", "pw", b"x")
        m_cost, t_cost, p_cost = struct.unpack(">III", blob[_OFF_M_COST : _OFF_M_COST + 12])
        assert m_cost == _crypto_module.ARGON2_M_COST
        assert t_cost == _crypto_module.ARGON2_T_COST
        assert p_cost == _crypto_module.ARGON2_P_COST

    def test_blob_with_different_m_cost_still_decryptable(self, monkeypatch: pytest.MonkeyPatch):
        """老 blob 用旧参数加密，默认参数升级后仍应可解密（头部内嵌机制）。"""
        monkeypatch.setattr(_crypto_module, "ARGON2_M_COST", 8)
        blob = Vault.seal("acc", "pw", b"legacy")
        monkeypatch.setattr(_crypto_module, "ARGON2_M_COST", 16)
        assert Vault.open("acc", "pw", blob) == b"legacy"


class TestV5BackwardCompat:
    """v5 (SM4-CBC + HMAC-SM3) blob 应仍可由 v6 版本的 Vault.open 读出。"""

    @staticmethod
    def _build_v5_blob(account: str, password: str, plaintext: bytes) -> bytes:
        """按 v5 格式手工构造 blob（不再由 seal 产出，只在测试里模拟旧文件）。"""
        from gmssl import sm4  # noqa: PLC0415

        from zhmm.core.crypto import (
            _V5_IV_LEN,
            _V5_KEY_ENC_LEN,
            DERIVED_KEY_LEN,
            _derive_key,
        )

        m_cost = _crypto_module.ARGON2_M_COST
        t_cost = _crypto_module.ARGON2_T_COST
        p_cost = _crypto_module.ARGON2_P_COST
        # 测试级固定 salt/iv 便于复现
        salt = b"\x01" * SALT_LEN
        iv = b"\x02" * _V5_IV_LEN
        derived = _derive_key(account, password, salt, m_cost, t_cost, p_cost)
        assert len(derived) == DERIVED_KEY_LEN
        key_enc = derived[:_V5_KEY_ENC_LEN]
        key_mac = derived[_V5_KEY_ENC_LEN:]
        cipher = sm4.CryptSM4()
        cipher.set_key(key_enc, sm4.SM4_ENCRYPT)
        ct: bytes = bytes(cipher.crypt_cbc(iv, plaintext))
        header = MAGIC + bytes([5]) + struct.pack(">III", m_cost, t_cost, p_cost) + salt + iv
        tag = _hmac_sm3(key_mac, header + ct)
        return header + ct + tag

    def test_v5_roundtrip(self):
        pt = b"legacy vault payload"
        blob = self._build_v5_blob("alice", "password", pt)
        assert blob[len(MAGIC)] == 5
        assert Vault.open("alice", "password", blob) == pt

    def test_v5_wrong_password(self):
        blob = self._build_v5_blob("alice", "password", b"x")
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "wrong", blob)

    def test_v5_tampered_ciphertext(self):
        blob = self._build_v5_blob("alice", "password", b"x" * 32)
        # v5 header = 49
        idx = 49
        tampered = blob[:idx] + bytes([blob[idx] ^ 0x01]) + blob[idx + 1 :]
        with pytest.raises(CryptoError, match="authentication failed"):
            Vault.open("alice", "password", tampered)

    def test_seal_always_writes_v6_even_for_old_data(self):
        """v5 blob 解密后，重新 seal 的结果是 v6（保证自然升级）。"""
        pt = b"some data"
        v5_blob = self._build_v5_blob("alice", "password", pt)
        recovered = Vault.open("alice", "password", v5_blob)
        new_blob = Vault.seal("alice", "password", recovered)
        assert new_blob[len(MAGIC)] == VERSION == 6


class TestGcmInternals:
    """SM4-GCM 内部原语的自洽性测试。"""

    def test_sm4_block_is_deterministic(self):
        key = bytes(range(16))
        blk = b"\x00" * 16
        a = _sm4_encrypt_block(key, blk)
        b = _sm4_encrypt_block(key, blk)
        assert a == b
        assert len(a) == 16

    def test_inc32_wraps_correctly(self):
        prefix = b"\xaa" * 12
        assert _inc32(prefix + b"\x00\x00\x00\x00") == prefix + b"\x00\x00\x00\x01"
        assert _inc32(prefix + b"\x00\x00\x00\xff") == prefix + b"\x00\x00\x01\x00"
        # 32-bit 溢出回绕；前 12 字节不变
        assert _inc32(prefix + b"\xff\xff\xff\xff") == prefix + b"\x00\x00\x00\x00"

    def test_ctr_self_inverse(self):
        """CTR 是自逆的：同一 key + icb 下，encrypt(encrypt(pt)) == pt。"""
        key = bytes(range(16))
        icb = b"\x00" * 16
        pt = b"the quick brown fox jumps over the lazy dog" * 5
        ct = _sm4_ctr_xor(key, icb, pt)
        assert ct != pt
        assert _sm4_ctr_xor(key, icb, ct) == pt

    def test_ctr_length_preserved(self):
        key = bytes(range(16))
        icb = b"\x00" * 16
        for n in [0, 1, 15, 16, 17, 1000]:
            assert len(_sm4_ctr_xor(key, icb, b"A" * n)) == n

    def test_gf128_mul_identities(self):
        """GF(2^128) 乘法代数性质。"""
        # 0 * y = 0；x * 0 = 0
        y = 0x66E94BD4EF8A2C3B884CFA59CA342B2E
        assert _gf128_mul(0, y) == 0
        assert _gf128_mul(y, 0) == 0
        # 交换律
        a = 0x11223344556677889900AABBCCDDEEFF
        b = 0x0102030405060708090A0B0C0D0E0F10
        assert _gf128_mul(a, b) == _gf128_mul(b, a)
        # 1（x^0）为乘法单位元：GCM bit-序下对应整数 1 << 127
        one = 1 << 127
        assert _gf128_mul(a, one) == a
        assert _gf128_mul(one, a) == a

    def test_ghash_aligned_required(self):
        with pytest.raises(ValidationError):
            _ghash(b"\x00" * 16, b"not aligned")

    def test_ghash_deterministic(self):
        h = _sm4_encrypt_block(bytes(range(16)), b"\x00" * 16)
        data = b"\x11" * 32
        assert _ghash(h, data) == _ghash(h, data)

    def test_gcm_roundtrip_direct(self):
        """直接调用 _sm4_gcm_seal / _sm4_gcm_open 的往返。"""
        key = bytes(range(16))
        iv = b"\x00" * IV_LEN
        aad = b"header-as-aad"
        pt = b"plaintext of arbitrary length 0123" * 3
        ct, tag = _sm4_gcm_seal(key, iv, aad, pt)
        assert len(tag) == TAG_LEN
        assert len(ct) == len(pt)
        assert _sm4_gcm_open(key, iv, aad, ct, tag) == pt

    def test_gcm_aad_tamper_detected(self):
        key = bytes(range(16))
        iv = b"\x00" * IV_LEN
        aad = b"original"
        pt = b"x" * 32
        ct, tag = _sm4_gcm_seal(key, iv, aad, pt)
        with pytest.raises(CryptoError, match="authentication failed"):
            _sm4_gcm_open(key, iv, b"tampered", ct, tag)

    def test_gcm_wrong_tag_detected(self):
        key = bytes(range(16))
        iv = b"\x00" * IV_LEN
        ct, tag = _sm4_gcm_seal(key, iv, b"", b"pt")
        bad_tag = bytes(b ^ 0xFF for b in tag)
        with pytest.raises(CryptoError, match="authentication failed"):
            _sm4_gcm_open(key, iv, b"", ct, bad_tag)


class TestArgon2Calibration:
    """calibrate_argon2 + Vault.seal(argon2_params=...) 联合验证。"""

    def test_calibrate_returns_in_valid_range(self):
        # 用最小允许的 m_cost 采样以加速，t_cost=1 加快测试
        m, t, p = _crypto_module.calibrate_argon2(
            target_ms=50,
            t_cost=1,
            p_cost=1,
            probe_m_cost=_crypto_module._ARGON2_M_MIN,
        )
        assert _crypto_module._ARGON2_M_MIN <= m <= _crypto_module._ARGON2_M_MAX
        assert t == 1
        assert p == 1

    def test_calibrate_rejects_nonpositive_target(self):
        with pytest.raises(ValidationError):
            _crypto_module.calibrate_argon2(target_ms=0)
        with pytest.raises(ValidationError):
            _crypto_module.calibrate_argon2(target_ms=-1)

    def test_calibrate_validates_probe_params(self):
        from zhmm.core.errors import CorruptedVault

        with pytest.raises(CorruptedVault):
            _crypto_module.calibrate_argon2(
                target_ms=100,
                t_cost=1,
                p_cost=1,
                probe_m_cost=1,  # < _ARGON2_M_MIN
            )

    def test_seal_accepts_custom_argon2_params(self):
        params = (_crypto_module._ARGON2_M_MIN, 1, 1)
        pt = b"calibrated params roundtrip"
        blob = Vault.seal("alice", "pw", pt, argon2_params=params)
        # header 中的参数应与传入一致
        m, t, p = struct.unpack(">III", blob[_OFF_M_COST : _OFF_M_COST + 12])
        assert (m, t, p) == params
        # 解密无需额外参数，自 header 重算
        assert Vault.open("alice", "pw", blob) == pt

    def test_seal_rejects_out_of_range_params(self):
        from zhmm.core.errors import CorruptedVault

        with pytest.raises(CorruptedVault):
            Vault.seal("alice", "pw", b"x", argon2_params=(1, 3, 1))
        with pytest.raises(CorruptedVault):
            Vault.seal("alice", "pw", b"x", argon2_params=(65536, 0, 1))

"""国密加密模块（Argon2id + SM4-GCM 原生 AEAD）。

本模块提供一个基于国密算法的 AEAD 加密封装：:class:`Vault`。

算法栈
-----

- **密钥派生 (KDF)**: Argon2id（memory-hard，抗 GPU/ASIC 暴力破解）
  输入以 ``account + b"\\x00" + password`` 拼接后的 UTF-8 字节串为口令材料。
  账号作为 KDF 盐值等效输入，使不同账号 + 相同弱密码的用户得到完全不同的密钥。
  账号本身不写入加密文件。
- **对称加密 + 认证 (AEAD)**: **SM4-GCM**
  CTR 模式加密 + GHASH 认证，NIST SP 800-38D 规范的 GCM 构造迁移到 SM4 块密码。
  相比 v5 的 Encrypt-then-MAC（SM4-CBC + HMAC-SM3），GCM 是单次扫描的原生 AEAD，
  加密与认证共享同一个密钥，无需显式 MAC 子密钥，且文件头部所有字段作为 AAD
  一并受认证保护（含 Argon2 参数、magic、version）。

.. note::
   `gmssl 3.2.2` 仅暴露 SM4-ECB/CBC，没有原生 GCM。本模块基于
   ``CryptSM4.one_round`` 的单块 SM4 加密原语，按 NIST SP 800-38D 自行实现
   GCM 的 CTR 流 + GHASH 认证。仅支持 96-bit (12B) IV（NIST 推荐的标准形态），
   认证标签固定 128-bit (16B)。

文件格式 (v6，默认)
------------------

::

    magic(4B="ZHMM") | version(1B=6) | m_cost(4B BE) | t_cost(4B BE) | p_cost(4B BE)
                    | salt(16B) | iv(12B) | ciphertext(N) | tag(16B)

- ``ciphertext`` 长度 = 明文长度（CTR 无填充），不再受限于 16B 对齐；
- ``tag`` 覆盖 **整个 header（含 magic/version/Argon2 参数/salt/iv）+ ciphertext**，
  任何字段（含 KDF 参数）被篡改都会导致认证失败，防止降级攻击。
- 账号（account）不写入 blob；解密时由调用方重新提供，账号错误与密码错误
  表现一致（GCM 认证失败）。

文件格式 (v5，仅读兼容)
----------------------

旧版 v5 采用 SM4-CBC + HMAC-SM3：

::

    magic(4B="ZHMM") | version(1B=5) | m_cost(4B) | t_cost(4B) | p_cost(4B)
                    | salt(16B) | iv(16B) | ciphertext(N, 16B 对齐) | tag(32B)

v5 blob 仍可由 :func:`Vault.open` 透明解密；下次 :func:`Vault.seal` 将自动
以 v6 重新写入（由 :class:`VaultFile` 触发）。

兼容性
------

- v6 **默认**：当前 seal 只产出 v6 blob。
- v5 **读兼容**：`Vault.open` 识别到 version=5 自动走 legacy 路径。
- v3 / v4 已废弃：遇到直接抛 :class:`CryptoError`。

安全提示
--------

- 故意不在异常信息中暴露敏感细节（key、iv、salt、account 等）。
- 所有失败路径统一为 :class:`CryptoError`，便于 UI 层给出中性提示。
- 恶意 blob 防护：解密前校验 Argon2 m/t/p 在安全范围内，防止 OOM。
"""

from __future__ import annotations

import hmac
import os
import struct
from typing import Final

from argon2.exceptions import Argon2Error
from argon2.low_level import Type as Argon2Type
from argon2.low_level import hash_secret_raw
from gmssl import sm3, sm4

from zhmm.core.errors import BadPassword, CorruptedVault, CryptoError, UnsupportedVersion, ValidationError

# ----------------------------------------------------------------------
# 协议常量（一旦发布请勿随意修改；修改必须 bump VERSION）
# ----------------------------------------------------------------------

MAGIC: Final[bytes] = b"ZHMM"
VERSION: Final[int] = 6  # SM4-GCM (v6)

SALT_LEN: Final[int] = 16
IV_LEN: Final[int] = 12  # GCM 标准 96-bit IV
TAG_LEN: Final[int] = 16  # GCM 128-bit tag

KEY_LEN: Final[int] = 16  # SM4 128-bit key
# 保持 32B 以兼容 Argon2 调用一致性（仅取前 16B 作为 SM4 密钥；余量预留）
DERIVED_KEY_LEN: Final[int] = 32

# v5 legacy 常量（仅用于解码历史 blob）
_V5_VERSION: Final[int] = 5
_V5_IV_LEN: Final[int] = 16
_V5_TAG_LEN: Final[int] = 32  # HMAC-SM3
_V5_KEY_ENC_LEN: Final[int] = 16
_V5_KEY_MAC_LEN: Final[int] = 16

# Argon2id 默认参数
ARGON2_M_COST: Final[int] = 65_536  # KiB = 64 MiB
ARGON2_T_COST: Final[int] = 3
ARGON2_P_COST: Final[int] = 1

# 解密时接受的 Argon2 参数范围（防 DoS）
_ARGON2_M_MIN: Final[int] = 8
_ARGON2_M_MAX: Final[int] = 524_288  # 512 MiB
_ARGON2_T_MIN: Final[int] = 1
_ARGON2_T_MAX: Final[int] = 100
_ARGON2_P_MIN: Final[int] = 1
_ARGON2_P_MAX: Final[int] = 64

# v6 header 长度: magic(4) + ver(1) + m(4) + t(4) + p(4) + salt(16) + iv(12) = 45
_HEADER_LEN: Final[int] = len(MAGIC) + 1 + 12 + SALT_LEN + IV_LEN  # 45
_MIN_BLOB_LEN: Final[int] = _HEADER_LEN + TAG_LEN  # 空明文仍有 header+tag

# v5 header 长度: magic(4) + ver(1) + m(4) + t(4) + p(4) + salt(16) + iv(16) = 49
_V5_HEADER_LEN: Final[int] = len(MAGIC) + 1 + 12 + SALT_LEN + _V5_IV_LEN  # 49
_V5_MIN_BLOB_LEN: Final[int] = _V5_HEADER_LEN + _V5_TAG_LEN + 16

# GCM 约化多项式（NIST SP 800-38D）：R = 11100001 || 0^120
_GHASH_R: Final[int] = 0xE1 << 120


# ----------------------------------------------------------------------
# SM3 hashlib 风格包装（HMAC-SM3 仅给 v5 legacy 路径与 totp 模块使用）
# ----------------------------------------------------------------------


class _Sm3Hash:
    """``hashlib`` 风格的 SM3 包装器，仅实现 ``hmac.HMAC`` 所需的方法。"""

    digest_size: Final[int] = 32
    block_size: Final[int] = 64
    name: Final[str] = "sm3"

    def __init__(self, data: bytes = b"") -> None:
        self._buf = bytearray(data)

    def update(self, data: bytes) -> None:
        self._buf.extend(data)

    def digest(self) -> bytes:
        return bytes.fromhex(sm3.sm3_hash(list(self._buf)))

    def hexdigest(self) -> str:
        result: str = sm3.sm3_hash(list(self._buf))
        return result

    def copy(self) -> _Sm3Hash:
        new = _Sm3Hash()
        new._buf = bytearray(self._buf)
        return new


def _hmac_sm3(key: bytes, msg: bytes) -> bytes:
    """HMAC-SM3（RFC 2104）。仅 v5 legacy 解密使用。"""
    return hmac.new(key, msg, digestmod=_Sm3Hash).digest()  # type: ignore[arg-type, unused-ignore]


# ----------------------------------------------------------------------
# Argon2id 密钥派生
# ----------------------------------------------------------------------


def _derive_key(
    account: str,
    password: str,
    salt: bytes,
    m_cost: int,
    t_cost: int,
    p_cost: int,
) -> bytes:
    """使用 Argon2id 从 (账号, 口令) 派生 :data:`DERIVED_KEY_LEN` 字节密钥。"""
    if not isinstance(account, str):
        raise ValidationError("account must be a str")
    if not isinstance(password, str) or not password:
        raise ValidationError("password must be a non-empty str")
    material = account.encode("utf-8") + b"\x00" + password.encode("utf-8")
    try:
        key: bytes = hash_secret_raw(
            secret=material,
            salt=salt,
            time_cost=t_cost,
            memory_cost=m_cost,
            parallelism=p_cost,
            hash_len=DERIVED_KEY_LEN,
            type=Argon2Type.ID,
        )
        return key
    except Argon2Error:
        raise CryptoError("key derivation failed") from None


def _validate_argon2_params(m_cost: int, t_cost: int, p_cost: int) -> None:
    """检查 Argon2 参数在安全范围内，防止恶意 blob 构造 OOM。"""
    if not (_ARGON2_M_MIN <= m_cost <= _ARGON2_M_MAX):
        raise CorruptedVault(f"argon2 m_cost out of range: {m_cost}")
    if not (_ARGON2_T_MIN <= t_cost <= _ARGON2_T_MAX):
        raise CorruptedVault(f"argon2 t_cost out of range: {t_cost}")
    if not (_ARGON2_P_MIN <= p_cost <= _ARGON2_P_MAX):
        raise CorruptedVault(f"argon2 p_cost out of range: {p_cost}")


# ----------------------------------------------------------------------
# SM4 原语（单块 ECB，无填充；基于 gmssl.CryptSM4.one_round）
# ----------------------------------------------------------------------


def _sm4_encrypt_block(key: bytes, block: bytes) -> bytes:
    """SM4 单块加密（16B → 16B，无填充）。

    gmssl 的 ``crypt_ecb`` 会自动做 PKCS7 padding，不适合 CTR 用途。
    直接调用内部 ``one_round`` 方法跑 32 轮 Feistel 即可拿到纯 ECB 单块结果。
    """
    if len(block) != 16:
        raise ValidationError("sm4 block must be exactly 16 bytes")
    cipher = sm4.CryptSM4()
    cipher.set_key(key, sm4.SM4_ENCRYPT)
    out = cipher.one_round(cipher.sk, list(block))
    return bytes(out)


# ----------------------------------------------------------------------
# GCM 内部实现（CTR + GHASH）
# ----------------------------------------------------------------------


def _gf128_mul(x: int, y: int) -> int:
    """GF(2^128) 乘法（NIST SP 800-38D 位序：bit 127 为最高位）。

    约化多项式 R = 0xE1 || 0x00...0（128 位），低位右移 + 溢出反馈。
    纯 Python 实现，性能足够密码管理器场景（典型密库 < 100 KB）。
    """
    z = 0
    v = y
    for i in range(128):
        # MSB-first：x 的第 i 位（从左数）= bit (127 - i)
        if (x >> (127 - i)) & 1:
            z ^= v
        if v & 1:
            v = (v >> 1) ^ _GHASH_R
        else:
            v >>= 1
    return z


def _ghash(h: bytes, data: bytes) -> bytes:
    """GHASH_H(data)：对 16B 对齐的字节串做 GF(2^128) 多项式哈希。"""
    if len(h) != 16:
        raise ValidationError("ghash subkey must be 16 bytes")
    if len(data) % 16 != 0:
        raise ValidationError("ghash input must be 16-byte aligned")
    h_int = int.from_bytes(h, "big")
    y = 0
    for off in range(0, len(data), 16):
        block = int.from_bytes(data[off : off + 16], "big")
        y = _gf128_mul(y ^ block, h_int)
    return y.to_bytes(16, "big")


def _inc32(counter: bytes) -> bytes:
    """counter 的末 4 字节大端 +1 (mod 2^32)；前 12 字节保持不变。"""
    prefix = counter[:12]
    ctr = int.from_bytes(counter[12:], "big")
    ctr = (ctr + 1) & 0xFFFFFFFF
    return prefix + ctr.to_bytes(4, "big")


def _sm4_ctr_xor(key: bytes, icb: bytes, data: bytes) -> bytes:
    """SM4-CTR：用从 ``icb`` 开始递增的 keystream 对 ``data`` 做 XOR。"""
    out = bytearray(len(data))
    counter = icb
    for off in range(0, len(data), 16):
        ks = _sm4_encrypt_block(key, counter)
        end = min(off + 16, len(data))
        chunk = data[off:end]
        for j, b in enumerate(chunk):
            out[off + j] = b ^ ks[j]
        counter = _inc32(counter)
    return bytes(out)


def _ghash_pad(b: bytes) -> bytes:
    """按 16B 右补 0（不足则补，已对齐则不动）。"""
    r = len(b) % 16
    return b + b"\x00" * (16 - r) if r else b


def _sm4_gcm_seal(key: bytes, iv: bytes, aad: bytes, plaintext: bytes) -> tuple[bytes, bytes]:
    """SM4-GCM 加密（仅支持 96-bit IV）。返回 ``(ciphertext, tag)``。"""
    if len(key) != KEY_LEN:
        raise ValidationError("gcm key must be 16 bytes")
    if len(iv) != IV_LEN:
        raise ValidationError("gcm iv must be 12 bytes")

    # 哈希子密钥 H = SM4_ENC(K, 0^128)
    h = _sm4_encrypt_block(key, b"\x00" * 16)
    # 96-bit IV 下，J0 = IV || 0x00000001
    j0 = iv + b"\x00\x00\x00\x01"

    # CTR 从 J0+1 开始加密明文
    icb = _inc32(j0)
    ciphertext = _sm4_ctr_xor(key, icb, plaintext)

    # GHASH 输入 = pad(AAD) || pad(C) || len(AAD)_64 || len(C)_64（单位：bit）
    lens = (len(aad) * 8).to_bytes(8, "big") + (len(plaintext) * 8).to_bytes(8, "big")
    s = _ghash(h, _ghash_pad(aad) + _ghash_pad(ciphertext) + lens)

    # T = GHASH XOR SM4_ENC(K, J0)
    ek_j0 = _sm4_encrypt_block(key, j0)
    tag = bytes(a ^ b for a, b in zip(s, ek_j0, strict=True))
    return ciphertext, tag


def _sm4_gcm_open(key: bytes, iv: bytes, aad: bytes, ciphertext: bytes, tag: bytes) -> bytes:
    """SM4-GCM 解密。认证失败抛 :class:`CryptoError`。"""
    if len(key) != KEY_LEN:
        raise ValidationError("gcm key must be 16 bytes")
    if len(iv) != IV_LEN:
        raise ValidationError("gcm iv must be 12 bytes")
    if len(tag) != TAG_LEN:
        raise ValidationError("gcm tag must be 16 bytes")

    h = _sm4_encrypt_block(key, b"\x00" * 16)
    j0 = iv + b"\x00\x00\x00\x01"

    # 先校验 tag（常量时间），成功后再解密，符合 AEAD 语义
    lens = (len(aad) * 8).to_bytes(8, "big") + (len(ciphertext) * 8).to_bytes(8, "big")
    s = _ghash(h, _ghash_pad(aad) + _ghash_pad(ciphertext) + lens)
    ek_j0 = _sm4_encrypt_block(key, j0)
    expected = bytes(a ^ b for a, b in zip(s, ek_j0, strict=True))
    if not hmac.compare_digest(expected, tag):
        raise BadPassword("authentication failed (wrong account/password or tampered data)")

    icb = _inc32(j0)
    return _sm4_ctr_xor(key, icb, ciphertext)


# ----------------------------------------------------------------------
# 公开 API
# ----------------------------------------------------------------------


class Vault:
    """国密 AEAD 加密封装器（v6 = SM4-GCM，向后兼容 v5 = SM4-CBC+HMAC-SM3）。

    用法::

        blob = Vault.seal("account", "my-password", b"plaintext")
        data = Vault.open("account", "my-password", blob)

    本类为无状态工具类，只暴露两个静态方法。``seal`` 永远写 v6；``open``
    根据 blob 头部 version 字节自动分发。
    """

    __slots__ = ()

    # ------------------------------------------------------------------
    # seal：只写 v6（SM4-GCM）
    # ------------------------------------------------------------------

    @staticmethod
    def seal(account: str, password: str, plaintext: bytes) -> bytes:
        """用 ``(account, password)`` 加密 ``plaintext``，返回 v6 blob。

        - 使用当前默认 Argon2id 参数派生密钥；参数写入 header 并纳入 AAD 保护。
        - 每次调用生成新的随机 salt (16B) 与 iv (12B)。
        """
        if not isinstance(account, str):
            raise ValidationError("account must be a str")
        if not isinstance(password, str) or not password:
            raise ValidationError("password must be a non-empty str")
        if not isinstance(plaintext, bytes | bytearray):
            raise ValidationError("plaintext must be bytes")

        salt = os.urandom(SALT_LEN)
        iv = os.urandom(IV_LEN)
        m_cost = ARGON2_M_COST
        t_cost = ARGON2_T_COST
        p_cost = ARGON2_P_COST

        header = MAGIC + bytes([VERSION]) + struct.pack(">III", m_cost, t_cost, p_cost) + salt + iv
        try:
            derived = _derive_key(account, password, salt, m_cost, t_cost, p_cost)
            key = derived[:KEY_LEN]
            ciphertext, tag = _sm4_gcm_seal(key, iv, header, bytes(plaintext))
        except (ValidationError, CryptoError):
            raise
        except Exception:
            raise CryptoError("encryption failed") from None
        return header + ciphertext + tag

    # ------------------------------------------------------------------
    # open：按 version 分发
    # ------------------------------------------------------------------

    @staticmethod
    def open(account: str, password: str, blob: bytes) -> bytes:
        """用 ``(account, password)`` 解密 ``blob``，返回明文字节。"""
        if not isinstance(account, str):
            raise ValidationError("account must be a str")
        if not isinstance(password, str) or not password:
            raise ValidationError("password must be a non-empty str")
        if not isinstance(blob, bytes | bytearray):
            raise ValidationError("blob must be bytes")

        blob = bytes(blob)
        if len(blob) < 1 + len(MAGIC):
            raise ValidationError(f"blob too short: {len(blob)}")

        if blob[: len(MAGIC)] != MAGIC:
            raise CorruptedVault("not a zhmm vault (magic mismatch)")

        version = blob[len(MAGIC)]
        if version == VERSION:
            return _open_v6(account, password, blob)
        if version == _V5_VERSION:
            return _open_v5(account, password, blob)
        raise UnsupportedVersion(f"unsupported vault version: {version}")


# ----------------------------------------------------------------------
# v6 解密路径（SM4-GCM）
# ----------------------------------------------------------------------


def _open_v6(account: str, password: str, blob: bytes) -> bytes:
    if len(blob) < _MIN_BLOB_LEN:
        raise ValidationError(f"v6 blob too short: {len(blob)} < {_MIN_BLOB_LEN}")

    off = len(MAGIC) + 1
    m_cost, t_cost, p_cost = struct.unpack(">III", blob[off : off + 12])
    _validate_argon2_params(m_cost, t_cost, p_cost)
    off += 12
    salt = blob[off : off + SALT_LEN]
    off += SALT_LEN
    iv = blob[off : off + IV_LEN]
    off += IV_LEN
    assert off == _HEADER_LEN

    header = blob[:_HEADER_LEN]
    tag = blob[-TAG_LEN:]
    ciphertext = blob[_HEADER_LEN:-TAG_LEN]

    derived = _derive_key(account, password, salt, m_cost, t_cost, p_cost)
    key = derived[:KEY_LEN]
    try:
        return _sm4_gcm_open(key, iv, header, ciphertext, tag)
    except CryptoError:
        raise
    except Exception:
        raise CorruptedVault("decryption failed") from None


# ----------------------------------------------------------------------
# v5 legacy 解密路径（SM4-CBC + HMAC-SM3，仅读）
# ----------------------------------------------------------------------


def _sm4_cbc_decrypt(key: bytes, iv: bytes, ciphertext: bytes) -> bytes:
    """SM4-CBC 解密（gmssl 会自动去除 PKCS7 padding）。"""
    cipher = sm4.CryptSM4()
    cipher.set_key(key, sm4.SM4_DECRYPT)
    pt: bytes = cipher.crypt_cbc(iv, ciphertext)
    return pt


def _open_v5(account: str, password: str, blob: bytes) -> bytes:
    """解密 v5 blob（SM4-CBC + HMAC-SM3）。仅用于向后兼容老密库。"""
    if len(blob) < _V5_MIN_BLOB_LEN:
        raise ValidationError(f"v5 blob too short: {len(blob)} < {_V5_MIN_BLOB_LEN}")

    off = len(MAGIC) + 1
    m_cost, t_cost, p_cost = struct.unpack(">III", blob[off : off + 12])
    _validate_argon2_params(m_cost, t_cost, p_cost)
    off += 12
    salt = blob[off : off + SALT_LEN]
    off += SALT_LEN
    iv = blob[off : off + _V5_IV_LEN]
    off += _V5_IV_LEN
    assert off == _V5_HEADER_LEN

    tag = blob[-_V5_TAG_LEN:]
    ciphertext = blob[_V5_HEADER_LEN:-_V5_TAG_LEN]
    if len(ciphertext) == 0 or len(ciphertext) % 16 != 0:
        raise CorruptedVault("ciphertext length invalid")

    derived = _derive_key(account, password, salt, m_cost, t_cost, p_cost)
    key_enc = derived[:_V5_KEY_ENC_LEN]
    key_mac = derived[_V5_KEY_ENC_LEN : _V5_KEY_ENC_LEN + _V5_KEY_MAC_LEN]

    expected = _hmac_sm3(key_mac, blob[:-_V5_TAG_LEN])
    if not hmac.compare_digest(tag, expected):
        raise BadPassword("authentication failed (wrong account/password or tampered data)")

    try:
        return _sm4_cbc_decrypt(key_enc, iv, ciphertext)
    except Exception:
        raise CorruptedVault("decryption failed") from None


__all__ = [
    "Vault",
    "MAGIC",
    "VERSION",
    "ARGON2_M_COST",
    "ARGON2_T_COST",
    "ARGON2_P_COST",
    "SALT_LEN",
    "IV_LEN",
    "TAG_LEN",
    "KEY_LEN",
]

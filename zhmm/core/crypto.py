"""国密加密模块（Argon2id + SM4-CBC + HMAC-SM3 认证）。

本模块提供一个基于国密算法的 AEAD 风格加密封装：:class:`Vault`。

算法栈
-----

- **密钥派生 (KDF)**: Argon2id（memory-hard，抗 GPU/ASIC 暴力破解）
  输入以 ``account + b"\\x00" + password`` 拼接后的 UTF-8 字节串为口令材料。
  账号作为 KDF 盐值等效输入，使不同账号 + 相同弱密码的用户得到完全不同的密钥，
  用于对抗离线字典/彩虹表攻击。账号本身不写入加密文件。
- **对称加密**: SM4-CBC（PKCS7 padding 由 gmssl 内置处理）
- **消息认证 (MAC)**: HMAC-SM3

.. note::
   KDF 从 v4 的 PBKDF2-HMAC-SHA256 升级为 Argon2id。Argon2id 是 2015 年
   Password Hashing Competition 冠军算法，通过 memory-hard 特性显著抬升
   GPU/ASIC 离线破解成本。数据加密与完整性保护仍由国密算法 (SM4 + SM3) 承担。

   默认参数 ``m=64 MiB, t=3, p=1``，单次派生约 300-500 ms（桌面场景）。
   OWASP 2024 最低基线为 ``m=19 MiB, t=2, p=1``，本项目取更保守的 64 MiB。

文件格式 (v5)
-------------

::

    magic(4B="ZHMM") | version(1B=5) | m_cost(4B BE) | t_cost(4B BE) | p_cost(4B BE)
                    | salt(16B) | iv(16B) | ciphertext(N) | tag(32B)

- ``m_cost`` / ``t_cost`` / ``p_cost`` 以大端无符号 32 位整数存储于 header，
  这样未来调整强度无需再 bump 版本号，老文件也能正确解密。
- ``salt`` 和 ``iv`` 均为 ``os.urandom`` 产生的随机字节。
- ``tag`` 覆盖 ``magic + version + m_cost + t_cost + p_cost + salt + iv + ciphertext`` 整体，
  防止降级攻击与头部字段（含 KDF 参数）被篡改。
- ``ciphertext`` 长度必须是 SM4 块长 16 的整数倍。
- 账号（account）不写入 blob；解密时由调用方重新提供，账号错误将与
  密码错误产生相同的 HMAC 认证失败。

兼容性
------

旧版 v3（PBKDF2-HMAC-SM3，仅密码参与 KDF）、v4（PBKDF2-HMAC-SHA256，账号 + 密码）
不再支持；遇到版本不匹配直接抛 :class:`CryptoError`，用户需通过 xlsx
导入重建密库。

安全提示
--------

- 故意不在异常信息中暴露敏感细节（key、iv、salt、account 等）。
- 所有失败路径统一为 :class:`CryptoError`，便于 UI 层给出中性提示。
- 密钥分离：Argon2id 输出 32B，前 16B 作为 SM4 密钥，后 16B 作为 HMAC 密钥。
- 恶意 blob 防护：解密前校验 m/t/p 在安全范围内，防止攻击者构造超大
  m_cost 导致 GB 级内存分配拒绝服务。
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

from zhmm.core.errors import CryptoError, ValidationError

# ----------------------------------------------------------------------
# 协议常量（一旦发布请勿随意修改；修改必须 bump VERSION）
# ----------------------------------------------------------------------

MAGIC: Final[bytes] = b"ZHMM"
VERSION: Final[int] = 5

SALT_LEN: Final[int] = 16
IV_LEN: Final[int] = 16
TAG_LEN: Final[int] = 32  # SM3 摘要长度

KEY_ENC_LEN: Final[int] = 16  # SM4 要求 128-bit key
KEY_MAC_LEN: Final[int] = 16  # HMAC-SM3 的 key 对长度无严格要求，这里选 128-bit
DERIVED_KEY_LEN: Final[int] = KEY_ENC_LEN + KEY_MAC_LEN  # 32

# Argon2id 默认参数。
# OWASP 2024 Password Storage Cheat Sheet 推荐最低 m=19456, t=2, p=1；
# 本项目（桌面密码管理器，非高频解锁）取更保守的 m=65536, t=3, p=1，
# 单次派生约 300-500 ms（M 系 Mac / 现代 PC）。
# 调整本值需同步更新 SECURITY.md 中的「加密算法详解」章节。
ARGON2_M_COST: Final[int] = 65_536  # KiB = 64 MiB
ARGON2_T_COST: Final[int] = 3
ARGON2_P_COST: Final[int] = 1

# 解密时接受的 Argon2 参数范围（防 DoS：恶意 blob 构造超大 m_cost 导致 OOM）。
# 上限 512 MiB / 100 轮 / 64 并行度足以覆盖未来合理升级空间；
# 下限 8 KiB / 1 轮 / 1 并行度是 argon2-cffi 的协议最低要求。
_ARGON2_M_MIN: Final[int] = 8
_ARGON2_M_MAX: Final[int] = 524_288  # 512 MiB
_ARGON2_T_MIN: Final[int] = 1
_ARGON2_T_MAX: Final[int] = 100
_ARGON2_P_MIN: Final[int] = 1
_ARGON2_P_MAX: Final[int] = 64

# Header: magic(4) + version(1) + m_cost(4) + t_cost(4) + p_cost(4) + salt(16) + iv(16) = 49
_HEADER_LEN: Final[int] = len(MAGIC) + 1 + 4 + 4 + 4 + SALT_LEN + IV_LEN  # 49
_MIN_BLOB_LEN: Final[int] = _HEADER_LEN + TAG_LEN + 16  # 至少一个密文块


# ----------------------------------------------------------------------
# SM3 hashlib 风格包装（供 hmac.new 的 digestmod 使用）
# ----------------------------------------------------------------------


class _Sm3Hash:
    """``hashlib`` 风格的 SM3 包装器。

    只实现 ``hmac.HMAC`` 所需的方法和属性，不追求与 ``hashlib`` 完全等价。
    """

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


# ----------------------------------------------------------------------
# 基础密码学原语
# ----------------------------------------------------------------------


def _hmac_sm3(key: bytes, msg: bytes) -> bytes:
    """HMAC-SM3（RFC 2104），返回 32 字节摘要。"""
    # _Sm3Hash 实现了 hashlib 接口的子集，hmac 会在内部做 duck typing 调用
    # 两套 mypy 运行环境下 digestmod 的类型推断不同：
    # - 项目环境（poetry run mypy）依赖齐全，需要忽略 arg-type
    # - pre-commit mirrors-mypy 隔离环境缺依赖，类型推断更松，ignore 会变 unused
    # 同时忽略 unused-ignore 以兼容两种环境。
    return hmac.new(key, msg, digestmod=_Sm3Hash).digest()  # type: ignore[arg-type, unused-ignore]


def _derive_key(
    account: str,
    password: str,
    salt: bytes,
    m_cost: int,
    t_cost: int,
    p_cost: int,
) -> bytes:
    """使用 Argon2id 从 (账号, 口令) 派生 32 字节密钥。

    KDF 输入材料 = ``account.utf8 + b"\\x00" + password.utf8``，用 NUL 做
    分隔符避免账号/密码边界融合引起的歧义性；同密码不同账号将派
    生出完全不同的密钥，等效为应用层常量盐。

    Raises:
        ValidationError: account / password 类型不合法。
        CryptoError: Argon2 底层错误（如参数越界）。
    """
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


def _sm4_encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    """SM4-CBC 加密。gmssl 会自动做 PKCS7 padding。"""
    cipher = sm4.CryptSM4()
    cipher.set_key(key, sm4.SM4_ENCRYPT)
    ct: bytes = cipher.crypt_cbc(iv, plaintext)
    return ct


def _sm4_decrypt(key: bytes, iv: bytes, ciphertext: bytes) -> bytes:
    """SM4-CBC 解密。gmssl 会自动去除 PKCS7 padding。"""
    cipher = sm4.CryptSM4()
    cipher.set_key(key, sm4.SM4_DECRYPT)
    pt: bytes = cipher.crypt_cbc(iv, ciphertext)
    return pt


def _validate_argon2_params(m_cost: int, t_cost: int, p_cost: int) -> None:
    """检查 Argon2 参数在安全范围内，防止恶意 blob 构造 OOM。"""
    if not (_ARGON2_M_MIN <= m_cost <= _ARGON2_M_MAX):
        raise CryptoError(f"argon2 m_cost out of range: {m_cost}")
    if not (_ARGON2_T_MIN <= t_cost <= _ARGON2_T_MAX):
        raise CryptoError(f"argon2 t_cost out of range: {t_cost}")
    if not (_ARGON2_P_MIN <= p_cost <= _ARGON2_P_MAX):
        raise CryptoError(f"argon2 p_cost out of range: {p_cost}")


# ----------------------------------------------------------------------
# 公开 API
# ----------------------------------------------------------------------


class Vault:
    """国密加密封装器（AEAD 风格）。

    用法::

        blob = Vault.seal("account", "my-password", b"plaintext")
        data = Vault.open("account", "my-password", blob)

    本类为无状态工具类，只暴露两个静态方法。
    """

    __slots__ = ()

    @staticmethod
    def seal(account: str, password: str, plaintext: bytes) -> bytes:
        """用 ``(account, password)`` 加密 ``plaintext``，返回自包含的 blob。

        ``account`` 作为 KDF 输入的一部分参与密钥派生，本身不写入 blob。
        允许空字符串（由业务层决定是否拒绝空值）。

        使用当前默认 Argon2id 参数派生密钥；参数写入 blob 头部，读取时
        使用 blob 中存储的参数（而非解密时的默认值），从而保证未来调强
        默认参数不会破坏老文件的可读性。

        Raises:
            ValidationError: 参数非法（非 str 账号、空密码、非 bytes 明文等）。
            CryptoError: 加密过程中出现底层错误（极少见）。
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

        try:
            derived = _derive_key(account, password, salt, m_cost, t_cost, p_cost)
            key_enc = derived[:KEY_ENC_LEN]
            key_mac = derived[KEY_ENC_LEN:]
            ciphertext = _sm4_encrypt(key_enc, iv, bytes(plaintext))
        except (ValidationError, CryptoError):
            raise
        except Exception:
            raise CryptoError("encryption failed") from None

        header = MAGIC + bytes([VERSION]) + struct.pack(">III", m_cost, t_cost, p_cost) + salt + iv
        tag = _hmac_sm3(key_mac, header + ciphertext)
        return header + ciphertext + tag

    @staticmethod
    def open(account: str, password: str, blob: bytes) -> bytes:
        """用 ``(account, password)`` 解密 ``blob``，返回明文字节。

        Argon2id 参数从 blob 头部读取，允许未来升级默认参数而不破坏老文件。
        账号错误会导致 HMAC 认证失败，与密码错误/数据被篡改表现一致。

        Raises:
            ValidationError: blob 长度/格式非法（非 str 账号、空密码、非 bytes blob、长度过短）。
            CryptoError: 魔数/版本不匹配、Argon2 参数越界、认证失败（账号或密码错误或数据被篡改）。
        """
        if not isinstance(account, str):
            raise ValidationError("account must be a str")
        if not isinstance(password, str) or not password:
            raise ValidationError("password must be a non-empty str")
        if not isinstance(blob, bytes | bytearray):
            raise ValidationError("blob must be bytes")
        if len(blob) < _MIN_BLOB_LEN:
            raise ValidationError(f"blob too short: {len(blob)} < {_MIN_BLOB_LEN}")

        blob = bytes(blob)
        if blob[: len(MAGIC)] != MAGIC:
            raise CryptoError("not a zhmm vault (magic mismatch)")

        version = blob[len(MAGIC)]
        if version != VERSION:
            raise CryptoError(f"unsupported vault version: {version}")

        off = len(MAGIC) + 1
        m_cost, t_cost, p_cost = struct.unpack(">III", blob[off : off + 12])
        _validate_argon2_params(m_cost, t_cost, p_cost)
        off += 12
        salt = blob[off : off + SALT_LEN]
        off += SALT_LEN
        iv = blob[off : off + IV_LEN]
        off += IV_LEN
        assert off == _HEADER_LEN

        tag = blob[-TAG_LEN:]
        ciphertext = blob[_HEADER_LEN:-TAG_LEN]

        if len(ciphertext) == 0 or len(ciphertext) % 16 != 0:
            raise CryptoError("ciphertext length invalid")

        derived = _derive_key(account, password, salt, m_cost, t_cost, p_cost)
        key_enc = derived[:KEY_ENC_LEN]
        key_mac = derived[KEY_ENC_LEN:]

        expected_tag = _hmac_sm3(key_mac, blob[:-TAG_LEN])
        if not hmac.compare_digest(tag, expected_tag):
            # 无法区分「账号/密码错」和「被篡改」，这是 AEAD 的设计特性
            raise CryptoError("authentication failed (wrong account/password or tampered data)")

        try:
            return _sm4_decrypt(key_enc, iv, ciphertext)
        except Exception:
            raise CryptoError("decryption failed") from None


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
]

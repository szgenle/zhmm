"""国密加密模块（PBKDF2-HMAC-SHA256 + SM4-CBC + HMAC-SM3 认证）。

本模块提供一个基于国密算法的 AEAD 风格加密封装：:class:`Vault`。

算法栈
-----

- **密钥派生 (KDF)**: PBKDF2-HMAC-SHA256（标准库 hashlib 的 C 实现）
- **对称加密**: SM4-CBC（PKCS7 padding 由 gmssl 内置处理）
- **消息认证 (MAC)**: HMAC-SM3

.. note::
   KDF 选用 SHA256 而非 SM3 是实用上的折中：gmssl 的 SM3 是纯 Python
   实现，用作 PBKDF2 的 PRF 时迭代成本过高（十万轮级别即需 1 分钟以上）。
   而 PBKDF2-HMAC-SHA256 的 C 实现能轻松跑 600000 轮（OWASP 2024 推荐基准）。
   数据加密与完整性保护仍由国密算法 (SM4 + SM3) 承担。

文件格式 (v3)
-------------

::

    magic(4B="ZHMM") | version(1B=3) | salt(16B) | iv(16B) | ciphertext(N) | tag(32B)

- ``salt`` 和 ``iv`` 均为 ``os.urandom`` 产生的随机字节。
- ``tag`` 覆盖 ``magic + version + salt + iv + ciphertext`` 整体，
  防止降级攻击与头部字段被篡改。
- ``ciphertext`` 长度必须是 SM4 块长 16 的整数倍。

安全提示
--------

- 故意不在异常信息中暴露敏感细节（key、iv、salt 等）。
- 所有失败路径统一为 :class:`CryptoError`，便于 UI 层给出中性提示。
- 密钥分离：PBKDF2 输出 32B，前 16B 作为 SM4 密钥，后 16B 作为 HMAC 密钥。
"""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Final

from gmssl import sm3, sm4

from zhmm.core.errors import CryptoError, ValidationError

# ----------------------------------------------------------------------
# 协议常量（一旦发布请勿随意修改；修改必须 bump VERSION）
# ----------------------------------------------------------------------

MAGIC: Final[bytes] = b"ZHMM"
VERSION: Final[int] = 3

SALT_LEN: Final[int] = 16
IV_LEN: Final[int] = 16
TAG_LEN: Final[int] = 32  # SM3 摘要长度

KEY_ENC_LEN: Final[int] = 16  # SM4 要求 128-bit key
KEY_MAC_LEN: Final[int] = 16  # HMAC-SM3 的 key 对长度无严格要求，这里选 128-bit
DERIVED_KEY_LEN: Final[int] = KEY_ENC_LEN + KEY_MAC_LEN  # 32

# PBKDF2-HMAC-SHA256 迭代轮数。
# OWASP 2024 Password Storage Cheat Sheet 推荐最低 600000 轮。
# 调整本值需同步更新 SECURITY.md 中的"加密算法详解"章节。
KDF_ITERATIONS: Final[int] = 600_000
KDF_HASH_NAME: Final[str] = "sha256"

_HEADER_LEN: Final[int] = len(MAGIC) + 1 + SALT_LEN + IV_LEN  # 37
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
    return hmac.new(key, msg, digestmod=_Sm3Hash).digest()  # type: ignore[arg-type]


def _derive_key(password: str, salt: bytes) -> bytes:
    """使用 PBKDF2-HMAC-SHA256 从口令派生 32 字节密钥。

    选用 SHA256 而非 SM3：标准库 ``hashlib.pbkdf2_hmac`` 为 C 实现，
    可在安全迭代次数 (>= 600000) 下保持交互级响应速度。
    """
    if not isinstance(password, str) or not password:
        raise ValidationError("password must be a non-empty str")
    return hashlib.pbkdf2_hmac(
        KDF_HASH_NAME,
        password.encode("utf-8"),
        salt,
        KDF_ITERATIONS,
        dklen=DERIVED_KEY_LEN,
    )


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


# ----------------------------------------------------------------------
# 公开 API
# ----------------------------------------------------------------------


class Vault:
    """国密加密封装器（AEAD 风格）。

    用法::

        blob = Vault.seal("my-password", b"plaintext")
        data = Vault.open("my-password", blob)

    本类为无状态工具类，只暴露两个静态方法。
    """

    __slots__ = ()

    @staticmethod
    def seal(password: str, plaintext: bytes) -> bytes:
        """用 ``password`` 加密 ``plaintext``，返回自包含的 blob。

        Raises:
            ValidationError: 参数非法（空密码、非 bytes 明文等）。
            CryptoError: 加密过程中出现底层错误（极少见）。
        """
        if not isinstance(password, str) or not password:
            raise ValidationError("password must be a non-empty str")
        if not isinstance(plaintext, bytes | bytearray):
            raise ValidationError("plaintext must be bytes")

        salt = os.urandom(SALT_LEN)
        iv = os.urandom(IV_LEN)

        try:
            derived = _derive_key(password, salt)
            key_enc = derived[:KEY_ENC_LEN]
            key_mac = derived[KEY_ENC_LEN:]
            ciphertext = _sm4_encrypt(key_enc, iv, bytes(plaintext))
        except ValidationError:
            raise
        except Exception:
            raise CryptoError("encryption failed") from None

        header = MAGIC + bytes([VERSION]) + salt + iv
        tag = _hmac_sm3(key_mac, header + ciphertext)
        return header + ciphertext + tag

    @staticmethod
    def open(password: str, blob: bytes) -> bytes:
        """用 ``password`` 解密 ``blob``，返回明文字节。

        Raises:
            ValidationError: blob 长度/格式非法。
            CryptoError: 魔数/版本不匹配、密码错误或数据被篡改。
        """
        if not isinstance(password, str) or not password:
            raise ValidationError("password must be a non-empty str")
        if not isinstance(blob, bytes | bytearray):
            raise ValidationError("blob must be bytes")
        if len(blob) < _MIN_BLOB_LEN:
            raise ValidationError(
                f"blob too short: {len(blob)} < {_MIN_BLOB_LEN}"
            )

        blob = bytes(blob)
        if blob[: len(MAGIC)] != MAGIC:
            raise CryptoError("not a zhmm vault (magic mismatch)")

        version = blob[len(MAGIC)]
        if version != VERSION:
            raise CryptoError(f"unsupported vault version: {version}")

        salt = blob[len(MAGIC) + 1 : len(MAGIC) + 1 + SALT_LEN]
        iv = blob[
            len(MAGIC) + 1 + SALT_LEN : _HEADER_LEN
        ]
        tag = blob[-TAG_LEN:]
        ciphertext = blob[_HEADER_LEN:-TAG_LEN]

        if len(ciphertext) == 0 or len(ciphertext) % 16 != 0:
            raise CryptoError("ciphertext length invalid")

        try:
            derived = _derive_key(password, salt)
            key_enc = derived[:KEY_ENC_LEN]
            key_mac = derived[KEY_ENC_LEN:]
        except ValidationError:
            raise
        except Exception:
            raise CryptoError("key derivation failed") from None

        expected_tag = _hmac_sm3(key_mac, blob[:-TAG_LEN])
        if not hmac.compare_digest(tag, expected_tag):
            # 无法区分"密码错"和"被篡改"，这是 AEAD 的设计特性
            raise CryptoError(
                "authentication failed (wrong password or tampered data)"
            )

        try:
            return _sm4_decrypt(key_enc, iv, ciphertext)
        except Exception:
            raise CryptoError("decryption failed") from None


__all__ = [
    "Vault",
    "MAGIC",
    "VERSION",
    "KDF_ITERATIONS",
    "SALT_LEN",
    "IV_LEN",
    "TAG_LEN",
]

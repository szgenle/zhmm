"""加密密码库文件读写：JSON + SM4-CBC + HMAC-SM3。

组合 [crypto.Vault] 作加解密 + [models.Vault] 作内存态，封装原子性落盘。

职责：
    - load(path, password) → models.Vault
    - save(path, password, vault) → None，原子性写入
    - rekey(path, account, old_password, new_password) → None，原地换密

不涉及业务 CRUD（那是 password_service 的活），也不关心 UI。
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path

from zhmm.core.crypto import Vault as CryptoVault
from zhmm.core.errors import CryptoError, StorageError
from zhmm.core.models import Vault


class VaultFile:
    """负责把 `Vault` 与磁盘文件双向转换。"""

    @staticmethod
    def load(path: str | os.PathLike[str], account: str, password: str) -> Vault:
        """读取并解密密码库文件。

        Raises:
            StorageError: 文件不存在 / 读取失败 / JSON 无效
            CryptoError:  账号或密码错误 / 文件被篡改 / 版本不匹配（由 CryptoVault.open 抛出）
        """
        p = Path(path)
        try:
            blob = p.read_bytes()
        except FileNotFoundError as e:
            raise StorageError(f"file not found: {p}") from e
        except OSError as e:
            raise StorageError(f"read failed: {p}: {e}") from e

        plaintext = CryptoVault.open(account, password, blob)

        try:
            data = json.loads(plaintext.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            # 解密成功但 JSON 解析失败 = 被篡改后恰好通过认证的概率极低，
            # 但仍视为 CryptoError 比较合理
            raise CryptoError("vault payload is not valid JSON") from e
        if not isinstance(data, dict):
            raise CryptoError("vault payload is not a JSON object")
        return Vault.from_dict(data)

    @staticmethod
    def save(path: str | os.PathLike[str], account: str, password: str, vault: Vault) -> None:
        """加密并原子性写入密码库文件。

        Raises:
            StorageError: 写入失败
        """
        p = Path(path)
        plaintext = json.dumps(vault.to_dict(), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        blob = CryptoVault.seal(account, password, plaintext)

        parent = p.parent if str(p.parent) else Path(".")
        parent.mkdir(parents=True, exist_ok=True)

        tmp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=str(parent),
                prefix=f".{p.name}.",
                suffix=".tmp",
                delete=False,
            ) as tmp:
                tmp_path = tmp.name
                tmp.write(blob)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_path, p)
            tmp_path = None
        except OSError as e:
            raise StorageError(f"write failed: {p}: {e}") from e
        finally:
            if tmp_path and os.path.exists(tmp_path):
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)

    @staticmethod
    def rekey(
        path: str | os.PathLike[str],
        account: str,
        old_password: str,
        new_password: str,
    ) -> None:
        """原地更换主密码（重新派生密钥并重写密文）。

        流程：
            1) 读取 blob，用 ``old_password`` 通过 :func:`CryptoVault.open`
               验证并得到明文；
            2) 用 ``new_password`` 通过 :func:`CryptoVault.seal` 重新加密
               （生成新的随机 salt/iv、按当前默认 Argon2id 参数）；
            3) 写入同目录临时文件 → fsync → ``os.replace`` 原子替换。

        不处理备份 / 会话刷新 / 配置同步 —— 这些由调用方（GUI 层）负责，
        以保持本模块纯净。

        Raises:
            StorageError: 读写失败。
            CryptoError:  ``old_password`` 错误、文件被篡改、版本不匹配等。
        """
        p = Path(path)
        try:
            blob = p.read_bytes()
        except FileNotFoundError as e:
            raise StorageError(f"file not found: {p}") from e
        except OSError as e:
            raise StorageError(f"read failed: {p}: {e}") from e

        # 用旧口令解密；任何失败均不触碰原文件。
        plaintext = CryptoVault.open(account, old_password, blob)
        new_blob = CryptoVault.seal(account, new_password, plaintext)

        parent = p.parent if str(p.parent) else Path(".")
        parent.mkdir(parents=True, exist_ok=True)

        tmp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=str(parent),
                prefix=f".{p.name}.",
                suffix=".tmp",
                delete=False,
            ) as tmp:
                tmp_path = tmp.name
                tmp.write(new_blob)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_path, p)
            tmp_path = None
        except OSError as e:
            raise StorageError(f"write failed: {p}: {e}") from e
        finally:
            if tmp_path and os.path.exists(tmp_path):
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)

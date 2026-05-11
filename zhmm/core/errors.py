"""统一异常类型。

所有 core 层抛出的异常都继承自 :class:`ZhmmError`，UI/CLI 层只需捕获该基类
或具体子类，即可映射到对应的用户提示。
"""

from __future__ import annotations


class ZhmmError(Exception):
    """zhmm 所有自定义异常的基类。"""


class ValidationError(ZhmmError):
    """输入参数不合法（长度、类型、空值等）。"""


class CryptoError(ZhmmError):
    """加密/解密/密钥派生/认证失败。

    故意不在异常信息中暴露敏感细节（salt、iv、key 等），也不链式保留底层异常，
    以免侧信道泄露。

    该基类下派生的更细粒度子类（:class:`BadPassword` / :class:`CorruptedVault` /
    :class:`UnsupportedVersion`）供 UI 层给出有针对性的用户提示；仍支持
    ``except CryptoError`` 统一兜底，保持向后兼容。
    """


class BadPassword(CryptoError):
    """AEAD/HMAC 认证失败：账号/密码错误或密文被篡改。

    AEAD 构造无法从密码学上区分「密码错」与「数据被篡改」，UI 层提示文案
    应同时覆盖两种可能（例如：\"账号或密码错误，或文件已损坏\"），避免暗示
    攻击者更多信息。
    """


class CorruptedVault(CryptoError):
    """密库文件结构损坏：magic 不匹配、长度非法、JSON 解析失败、KDF 参数越界等。

    与 :class:`BadPassword` 的区别：本类异常不依赖密钥即可判定，属于
    \"一眼可见的坏文件\"，UI 层可提示用户换一份备份打开。
    """


class UnsupportedVersion(CryptoError):
    """密库文件版本号不在当前程序支持范围内。

    通常发生在用户用旧版 zhmm 打开了新版程序写出的密库，UI 层应提示升级。
    """


class AuthError(ZhmmError):
    """用户身份认证失败（账号或密码错误等）。

    这是 :class:`CryptoError` 的一个高层语义，UI 层可据此给出友好提示。
    """


class StorageError(ZhmmError):
    """本地文件读写失败、目录不存在、磁盘满等。"""


class ConfigError(ZhmmError):
    """配置文件损坏、字段缺失或类型错误。"""

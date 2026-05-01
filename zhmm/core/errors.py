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
    """


class AuthError(ZhmmError):
    """用户身份认证失败（密码错误、openId 不匹配等）。

    这是 :class:`CryptoError` 的一个高层语义，UI 层可据此给出友好提示。
    """


class StorageError(ZhmmError):
    """本地文件读写失败、目录不存在、磁盘满等。"""


class ConfigError(ZhmmError):
    """配置文件损坏、字段缺失或类型错误。"""

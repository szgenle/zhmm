#!/usr/bin/env python3
# coding=utf-8
"""加密解密模块"""

from zhmm import sm_util
from zhmm.utils import data_conversion
from zhmm.data.sm_data_types import SmDataConstants


class SmCrypto:
    """加密解密管理器"""

    def __init__(self):
        self.pwd = ""
        self.openId = ""
        self.pwdHash = ""
        self.encryptHash = ""
        self.suffixHash = ""

    def init(self, open_id: str, pwd: str):
        """
        初始化加密管理器（设置加密密钥）

        Args:
            open_id: 用户标识
            pwd: 密码

        Raises:
            ValueError: 当open_id或pwd为空时

        Note:
            该方法必须在使用encrypt/decrypt方法之前调用
        """
        if not open_id:
            raise ValueError("用户标识不能为空")
        if not pwd:
            raise ValueError("密码不能为空")

        self.openId = open_id
        self.pwd = pwd

        # 计算密码哈希
        self.pwdHash = sm_util.hash_by_sm3(
            data_conversion.chars_to_bytes(self.pwd), self.openId
        )
        self.encryptHash = self.pwdHash[0:SmDataConstants.HASH_KEY_ENCRYPT_LENGTH]  # 前32位用于加密
        self.suffixHash = self.pwdHash[
            SmDataConstants.HASH_KEY_ENCRYPT_LENGTH : SmDataConstants.HASH_KEY_ENCRYPT_LENGTH + SmDataConstants.HASH_KEY_SUFFIX_LENGTH
        ]  # 后32位用于验证

    def get_encrypt_mmdata(self, mm_data: str) -> str | None:
        """
        获取并验证加密的数据

        Args:
            mm_data: 加密的数据字符串

        Returns:
            验证通过后的数据字符串，验证失败则返回None
        """
        if not mm_data:
            return None

        mm_data_len = len(mm_data)
        if mm_data_len <= SmDataConstants.HASH_SUFFIX_LENGTH:
            return None

        # 分离数据和验证哈希
        suffix = mm_data[-SmDataConstants.HASH_SUFFIX_LENGTH:]  # 后64位是验证哈希
        data_part = mm_data[: -SmDataConstants.HASH_SUFFIX_LENGTH]  # 前面部分是实际数据

        # 验证数据完整性
        hash_en_data = sm_util.hash_by_sm3(
            data_conversion.chars_to_bytes(data_part), self.suffixHash
        )
        if hash_en_data == suffix:
            return data_part

        return None

    def decrypt(self, encrypt_data: str) -> str | None:
        """
        解密数据

        Args:
            encrypt_data: 加密的数据字符串

        Returns:
            解密后的字符串，解密失败则返回None
        """
        # 验证并获取加密数据
        encrypt_mmdata = self.get_encrypt_mmdata(encrypt_data)
        if not encrypt_mmdata:
            return None

        try:
            # 解密数据
            decrypt_data = sm_util.decrypt_by_sm4(
                encrypt_mmdata, self.encryptHash
            )  # 解密，cbc 模式
            return decrypt_data.decode("utf-8")
        except Exception as e:
            print(f"[错误] 解密失败: {e}")
            return None

    def encrypt(self, data: str) -> str:
        """
        加密数据

        Args:
            data: 要加密的数据字符串

        Returns:
            加密后的数据字符串（包含数据+64位验证哈希）

        Raises:
            ValueError: 当数据为空或加密失败时
        """
        if not data:
            raise ValueError("加密数据不能为空")

        try:
            # 加密数据
            encrypt_data = sm_util.encrypt_by_sm4(data.encode("utf-8"), self.encryptHash)

            # 将加密后的字节数据转换为十六进制字符串
            hex_data = data_conversion.to_hex_string(encrypt_data)

            # 计算验证哈希
            suffix = sm_util.hash_by_sm3(
                data_conversion.chars_to_bytes(hex_data), self.suffixHash
            )

            # 返回加密数据和验证哈希的组合
            return hex_data + suffix
        except Exception as e:
            raise ValueError(f"加密失败: {e}")

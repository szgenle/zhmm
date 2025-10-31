#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02
import os
from typing import List, Union

from gmssl import func, sm3, sm4

from zhmm.utils import data_conversion

# SM3 HMAC 相关常量
BLOCK_LEN = 64  # SM3 块长度（字节）
IPAD = bytearray([0x36] * BLOCK_LEN)  # 内部填充
OPAD = bytearray([0x5C] * BLOCK_LEN)  # 外部填充

# SM4 加密相关常量
SM4_KEY_LENGTH = 32  # SM4 密钥长度（十六进制字符数，对应128位）
SM4_IV_LENGTH = 16  # SM4 IV 长度（字节数）
ENCRYPT_VERSION_PREFIX = "v2:"  # 新版加密数据版本标识


def _validate_sm4_key(key: str) -> None:
    """
    验证 SM4 密钥长度

    Args:
        key: 十六进制字符串形式的密钥

    Raises:
        ValueError: 当密钥长度不正确时
    """
    if len(key) != SM4_KEY_LENGTH:
        raise ValueError(
            f"密钥长度必须为{SM4_KEY_LENGTH}个十六进制字符（对应128位），当前为{len(key)}"
        )


def hash_by_sm3(
    input_bytes: Union[List[int], bytes, bytearray], key: str
) -> str:
    """
    使用 SM3 算法计算 HMAC 哈希值

    Args:
        input_bytes: 输入字节数据（整数列表、bytes 或 bytearray）
        key: HMAC 密钥字符串（必填）

    Returns:
        64位十六进制哈希字符串
    """
    # 将密钥转换为哈希值
    key_hash = sm3.sm3_hash(data_conversion.chars_to_bytes(key))
    key_array = data_conversion.hex_to_array(key_hash)

    # 填充至 BLOCK_LEN（64字节）
    while len(key_array) < BLOCK_LEN:
        key_array.append(0)

    # 计算内外填充
    ipad_key = func.xor(key_array, IPAD)
    opad_key = func.xor(key_array, OPAD)

    # 确保 input_bytes 是列表格式
    if isinstance(input_bytes, (bytes, bytearray)):
        input_bytes = list(input_bytes)

    # 计算 HMAC 哈希
    hash_ = sm3.sm3_hash(ipad_key + input_bytes)
    final_input = opad_key + data_conversion.hex_to_array(hash_)
    return sm3.sm3_hash(final_input)


def decrypt_by_sm4(encrypt_value: str, key: str) -> bytes:
    """
    使用 SM4 算法解密数据（CBC 模式）

    支持两种格式：
    1. 新格式：十六进制字符串中包含 'v2:' 前缀（对应二进制 b'v2:' = 763a32）
       格式：763a32 + IV(32位十六进制) + 密文
    2. 旧格式：直接是密文（使用固定 IV 解密）

    Args:
        encrypt_value: 十六进制字符串形式的加密数据
        key: 十六进制字符串形式的密钥（SM4要求128位，即32个十六进制字符）

    Returns:
        解密后的字节数据

    Raises:
        ValueError: 当密钥长度不正确或数据无效时
    """
    _validate_sm4_key(key)

    if not encrypt_value:
        raise ValueError("加密数据不能为空")

    try:
        encrypt_bytes = data_conversion.hex_to_array(encrypt_value)
    except ValueError as e:
        raise ValueError(f"十六进制字符串转换失败: {e}") from e

    # 检测是否为新版本格式（检查字节数组前3个字节是否为 b'v2:'）
    version_marker = ENCRYPT_VERSION_PREFIX.encode('ascii')
    is_v2 = (len(encrypt_bytes) > len(version_marker) and
             bytes(encrypt_bytes[:len(version_marker)]) == version_marker)

    if is_v2:
        print("检测到 新 版本加密数据格式")
        # 新格式：提取 IV 和密文
        offset = len(version_marker)
        iv_end = offset + SM4_IV_LENGTH

        if len(encrypt_bytes) < iv_end:
            raise ValueError("加密数据格式错误：IV 数据不完整")

        iv = bytes(encrypt_bytes[offset:iv_end])
        cipher_bytes = encrypt_bytes[iv_end:]
    else:
        raise ValueError("检测到 旧 版本加密数据格式")

    try:
        key_bytes = data_conversion.hex_to_array(key)
    except ValueError as e:
        raise ValueError(f"密钥十六进制字符串转换失败: {e}") from e

    crypt_sm4 = sm4.CryptSM4()
    crypt_sm4.set_key(key_bytes, sm4.SM4_DECRYPT)

    return crypt_sm4.crypt_cbc(iv, cipher_bytes)


def encrypt_by_sm4(encrypt_bytes: bytes, key: str) -> bytes:
    """
    使用 SM4 算法加密数据（CBC 模式）

    新版本：使用随机 IV，将 IV 附加在密文前面
    返回格式：版本标记(3字节 'v2:') + IV(16字节) + 密文(N字节)

    Args:
        encrypt_bytes: 要加密的字节数据
        key: 十六进制字符串形式的密钥（SM4要求128位，即32个十六进制字符）

    Returns:
        加密后的字节数据（版本标记 + IV + 密文）

    Raises:
        ValueError: 当密钥长度不正确或数据无效时
    """
    _validate_sm4_key(key)

    if not encrypt_bytes:
        raise ValueError("加密数据不能为空")

    # 生成随机 IV（16字节）
    iv = os.urandom(SM4_IV_LENGTH)

    try:
        key_bytes = data_conversion.hex_to_array(key)
    except ValueError as e:
        raise ValueError(f"密钥十六进制字符串转换失败: {e}") from e

    crypt_sm4 = sm4.CryptSM4()
    crypt_sm4.set_key(key_bytes, sm4.SM4_ENCRYPT)

    cipher_bytes = crypt_sm4.crypt_cbc(iv, encrypt_bytes)

    # 返回格式：版本标记(ASCII) + IV(二进制) + 密文(二进制)
    version_bytes = ENCRYPT_VERSION_PREFIX.encode('ascii')
    return version_bytes + iv + cipher_bytes

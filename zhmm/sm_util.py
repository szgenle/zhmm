#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02
from typing import List, Union

from gmssl import func, sm3, sm4

from zhmm.utils import data_conversion

block_len = 64
iPad = bytearray([0x36] * block_len)
oPad = bytearray([0x5C] * block_len)
iv = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x27\x00\x00\x00\x00\x03"  # bytes类型


def hash_by_sm3(
    input_bytes: List[int], key: str = "9gx^1-z:ixYWe(@JAJKFu1*k@913^ka1"
) -> str:
    """
    使用SM3算法计算哈希值

    Args:
        input_bytes: 输入字节数组（整数列表）
        key: 密钥字符串

    Returns:
        哈希字符串
    """
    # 将密钥转换为哈希值
    key_hash = sm3.sm3_hash(data_conversion.chars_to_bytes(key))
    key_array = data_conversion.hex_to_array(key_hash)

    # 直接填充至block_len（64字节）
    while len(key_array) < block_len:
        key_array.append(0)

    # 计算内外填充
    ipad_key = func.xor(key_array, iPad)
    opad_key = func.xor(key_array, oPad)

    # 计算哈希
    hash_ = sm3.sm3_hash(ipad_key + input_bytes)
    input_bytes = opad_key + data_conversion.hex_to_array(hash_)
    return sm3.sm3_hash(input_bytes)


def decrypt_by_sm4(encrypt_value: str, key: str) -> bytes:
    """
    使用SM4算法解密数据

    Args:
        encrypt_value: 十六进制字符串形式的加密数据
        key: 十六进制字符串形式的密钥（SM4要求128位，即32个十六进制字符）

    Returns:
        解密后的字节数据

    Raises:
        ValueError: 当密钥长度不正确或数据无效时
    """
    # 校验密钥长度（SM4要求128位 = 32个hex字符）
    if len(key) != 32:
        raise ValueError(f"密钥长度必须为32个十六进制字符，当前为{len(key)}")

    if not encrypt_value:
        raise ValueError("加密数据不能为空")

    # 将十六进制字符串转换为字节数组
    try:
        encrypt_bytes = data_conversion.hex_to_array(encrypt_value)
        key_bytes = data_conversion.hex_to_array(key)
    except Exception as e:
        raise ValueError(f"十六进制字符串转换失败: {e}")

    # 初始化SM4加密器
    crypt_sm4 = sm4.CryptSM4()
    crypt_sm4.set_key(key_bytes, sm4.SM4_DECRYPT)

    # 解密数据
    return crypt_sm4.crypt_cbc(iv, encrypt_bytes)


def encrypt_by_sm4(encrypt_bytes: bytes, key: str) -> bytes:
    """
    使用SM4算法加密数据

    Args:
        encrypt_bytes: 要加密的字节数据
        key: 十六进制字符串形式的密钥（SM4要求128位，即32个十六进制字符）

    Returns:
        加密后的字节数据

    Raises:
        ValueError: 当密钥长度不正确或数据无效时
    """
    # 校验密钥长度（SM4要求128位 = 32个hex字符）
    if len(key) != 32:
        raise ValueError(f"密钥长度必须为32个十六进制字符，当前为{len(key)}")

    if not encrypt_bytes:
        raise ValueError("加密数据不能为空")

    # 将密钥转换为字节数组
    try:
        key_bytes = data_conversion.hex_to_array(key)
    except Exception as e:
        raise ValueError(f"密钥十六进制字符串转换失败: {e}")

    # 初始化SM4加密器
    crypt_sm4 = sm4.CryptSM4()
    crypt_sm4.set_key(key_bytes, sm4.SM4_ENCRYPT)

    # 加密数据
    return crypt_sm4.crypt_cbc(iv, encrypt_bytes)

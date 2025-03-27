#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02

from typing import List, Union, Any


def to_hex_string(data: Union[List[int], bytes, bytearray]) -> str:
    """将整数列表、bytes或bytearray转换为十六进制字符串

    Args:
        data: 整数列表、bytes或bytearray对象

    Returns:
        十六进制字符串
    """
    if isinstance(data, (bytes, bytearray)):
        return ''.join([format(b, '02x') for b in data])
    else:  # List[int]
        return ''.join([format(num, '02x') for num in data])


# 保留原函数名以保持兼容性
def array_to_hex_string(arr: List[int]) -> str:
    """将整数列表转换为十六进制字符串 - 兼容旧API

    Args:
        arr: 整数列表

    Returns:
        十六进制字符串
    """
    return to_hex_string(arr)


# 保留原函数名以保持兼容性
def bytes_to_hex_string(data: Union[bytes, bytearray]) -> str:
    """将bytes或bytearray转换为十六进制字符串 - 兼容旧API

    Args:
        data: bytes或bytearray对象

    Returns:
        十六进制字符串
    """
    return to_hex_string(data)


def string_to_bytes(input_string: str) -> List[int]:
    """将字符串转换为字节数组（整数列表）

    Args:
        input_string: 输入字符串

    Returns:
        整数列表，每个整数代表字符的ASCII/Unicode值
    """
    return [ord(char) for char in input_string]


# 保留原函数名以保持兼容性
def string_to_hex_array(input_string: str) -> List[int]:
    """将字符串转换为字节数组（整数列表）- 兼容旧API

    Args:
        input_string: 输入字符串
        
    Returns:
        整数列表，每个整数代表字符的ASCII/Unicode值
    """
    return string_to_bytes(input_string)


def char_array_to_hex_array(char_array: List[str]) -> List[int]:
    """将字符列表转换为字节数组

    Args:
        char_array: 字符列表

    Returns:
        整数列表，每个整数代表字符的ASCII/Unicode值
    """
    return [ord(char) for char in char_array]


def hex_to_array(hex_str: str) -> List[int]:
    """将十六进制字符串转换为整数列表

    Args:
        hex_str: 十六进制字符串

    Returns:
        整数列表
    """
    # 如果字符串长度不是偶数，添加一个前导'0'
    if len(hex_str) % 2 != 0:
        hex_str = '0' + hex_str

    # 将十六进制字符串转换为字节数组
    bytes_array = bytearray.fromhex(hex_str)

    # 将字节数组转换为整数列表
    return list(bytes_array)


def bytes_to_int_list(data: Union[bytes, bytearray]) -> List[int]:
    """将bytes或bytearray转换为整数列表

    Args:
        data: bytes或bytearray对象

    Returns:
        整数列表
    """
    return list(data)

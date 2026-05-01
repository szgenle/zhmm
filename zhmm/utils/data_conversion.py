#!/usr/bin/env python3
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02



def to_hex_string(data: list[int] | bytes | bytearray) -> str:
    """将整数列表、bytes或bytearray转换为十六进制字符串

    Args:
        data: 整数列表、bytes或bytearray对象

    Returns:
        十六进制字符串
    """
    return "".join([format(b, "02x") for b in data])


def chars_to_bytes(chars: str | list[str]) -> list[int]:
    """将字符串或字符列表转换为字节数组（整数列表）

    Args:
        chars: 输入字符串或字符列表

    Returns:
        整数列表，每个整数代表字符的ASCII/Unicode值
    """
    return [ord(char) for char in chars]


def hex_to_array(hex_str: str) -> list[int]:
    """将十六进制字符串转换为整数列表

    Args:
        hex_str: 十六进制字符串

    Returns:
        整数列表
    """
    # 如果字符串长度不是偶数，添加一个前导'0'
    if len(hex_str) % 2 != 0:
        hex_str = "0" + hex_str

    # 将十六进制字符串转换为字节数组
    bytes_array = bytearray.fromhex(hex_str)

    # 将字节数组转换为整数列表
    return list(bytes_array)

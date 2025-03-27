#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02


def string_to_hex_array(input_string):
    hex_array = [ord(char) for char in input_string]
    return hex_array


def char_array_to_hex_array(char_array):
    hex_array = [ord(char) for char in char_array]
    return hex_array


def hex_to_array(hex_str) -> list[int]:
    # 如果字符串长度不是偶数，添加一个前导'0'
    if len(hex_str) % 2 != 0:
        hex_str = '0' + hex_str

    # 将十六进制字符串转换为字节数组
    bytes_array = bytearray.fromhex(hex_str)

    # 将字节数组转换为整数列表（如果需要）
    words = [int(byte) for byte in bytes_array]

    return words

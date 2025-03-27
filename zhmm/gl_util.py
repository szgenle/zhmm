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


def count_chinese_chars(s):
    count = 0
    for char in s:
        if '\u4e00' <= char <= '\u9fff':
            count += 1
    return count


chinese_punctuation = {'，', '。', '？', '！', '、', '；', '：', '“', '”', '‘', '’', '（', '）', '《', '》', '『', '』', '【', '】'}


def count_unicode_chars(s):
    count = 0

    for char in s:
        if char in chinese_punctuation:
            count += 1
        elif '\u4e00' <= char <= '\u9fff' or \
           '\u3000' <= char <= '\u303f' or \
           '\u3400' <= char <= '\u4dbf' or \
           '\u20000' <= char <= '\u2a6df' or \
           '\u2a700' <= char <= '\u2b73f' or \
           '\u2b740' <= char <= '\u2b81f' or \
           '\u2b820' <= char <= '\u2ceaf' or \
           '\uf900' <= char <= '\ufaff' or \
           '\u31c0' <= char <= '\u31ef' or \
           '\u2f00' <= char <= '\u2fdf' or \
           '\u31a0' <= char <= '\u31bf' or \
           '\uac00' <= char <= '\ud7af':
            count += 1
    return count


def array_to_hex_string(arr):
    hex_strings = [format(num, '02x') for num in arr]  # 02x 表示至少两位，不足则前面补0
    return ''.join(hex_strings)


def is_string(obj):
    return isinstance(obj, str)
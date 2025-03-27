#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02


def truncate(s, max_length=32):
    """截断过长的字符串，并在尾部显示..."""
    if len(s) > max_length:
        return s[:max_length] + '...'
    return s


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

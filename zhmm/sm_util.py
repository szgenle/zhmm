#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02
from gmssl import sm3, sm4, func

from zhmm.utils import array

block_len = 64
iPad = bytearray([0x36] * block_len)
oPad = bytearray([0x5c] * block_len)
iv = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x27\x00\x00\x00\x00\x03'  # bytes类型


def hash_by_sm3(input_bytes, key='9gx^1-z:ixYWe(@JAJKFu1*k@913^ka1'):
    # print("input_bytes", input_bytes)
    # input_data = gl_util.string_to_hex_array(input_data)
    key_hash = sm3.sm3_hash(array.string_to_hex_array(key))
    key_array = array.hex_to_array(key_hash)

    # if len(key_array) > block_len:
    #     print("len(key_array) > block_len")
    #     key_array = sm3.sm3_hash(key_array)

    while len(key_array) < block_len:
        key_array.append(0)

    ipad_key = func.xor(key_array, iPad)
    opad_key = func.xor(key_array, oPad)
    # print("ipad_key", ipad_key)

    hash_ = sm3.sm3_hash(ipad_key + input_bytes)
    input_bytes = opad_key + array.hex_to_array(hash_)
    return sm3.sm3_hash(input_bytes)


def decrypt_by_sm4(encrypt_value, key):
    encrypt_value = array.hex_to_array(encrypt_value)
    crypt_sm4 = sm4.CryptSM4()
    key = array.hex_to_array(key)
    crypt_sm4.set_key(key, sm4.SM4_DECRYPT)
    decrypt_value = crypt_sm4.crypt_cbc(iv, encrypt_value)  # bytes类型
    # print(decrypt_value)
    return decrypt_value


def encrypt_by_sm4(encrypt_bytes, key):
    # encrypt_value = gl_util.string_to_hex_array(encrypt_value)
    crypt_sm4 = sm4.CryptSM4()
    key = array.hex_to_array(key)
    crypt_sm4.set_key(key, sm4.SM4_ENCRYPT)
    decrypt_value = crypt_sm4.crypt_cbc(iv, encrypt_bytes)  # bytes类型
    # print(decrypt_value)
    return decrypt_value

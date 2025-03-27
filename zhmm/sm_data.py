#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02
import json
from typing import TypedDict, Optional

from zhmm import sm_util
from zhmm.utils import array_util, date_util, string_util


class ZhmmDict(TypedDict):
    id: Optional[int | None]
    role: Optional[str]
    userID: str
    pwd: str
    phone: Optional[str]
    email: Optional[str]
    url: str
    desc: str
    utime: Optional[int]


class ZhmmDataDict(TypedDict):
    data: list[ZhmmDict]


class SmData:
    pwd = ''
    openId = ''

    pwdHash = ''
    encryptHash = ''
    suffixHash = ''

    mm: ZhmmDataDict = {
        'data': []
    }

    def __init__(self):
        return

    def init(self, open_id: str, pwd: str):
        self.openId = open_id
        self.pwd = pwd

        self.pwdHash = sm_util.hash_by_sm3(array_util.string_to_hex_array(self.pwd), self.openId)
        self.encryptHash = self.pwdHash[0:32]
        self.suffixHash = self.pwdHash[32:64]

    def get_encrypt_mmdata(self, mm_data):
        if not mm_data:
            return

        mm_data_len = len(mm_data)
        if mm_data_len <= 64:
            return

        end_index = mm_data_len - 64
        suffix = mm_data[end_index:mm_data_len]
        mm_data = mm_data[0:end_index]

        hash_en_data = sm_util.hash_by_sm3(array_util.string_to_hex_array(mm_data), self.suffixHash)
        if hash_en_data == suffix:
            return mm_data

    def decrypt(self, encrypt_data):
        encrypt_mmdata = self.get_encrypt_mmdata(encrypt_data)
        if not encrypt_mmdata:
            print("EncryptDataVerifyFail")
            return

        decrypt_data = sm_util.decrypt_by_sm4(encrypt_mmdata, self.encryptHash)  # 解密，cbc 模式
        return {'res': decrypt_data.decode()}

    def encrypt(self, data):
        # print('data', data)
        encrypt_data = sm_util.encrypt_by_sm4(data.encode('utf-8'), self.encryptHash)
        # print('encrypt_data', encrypt_data)

        list_data = string_util.array_to_hex_string(encrypt_data)
        suffix = sm_util.hash_by_sm3(array_util.string_to_hex_array(list_data), self.suffixHash)
        # print('suffix', suffix)
        return list_data + suffix
        # print(suffix)
        # return encrypt_data.decode() + suffix

    def set_mm(self, user_mm_data: ZhmmDataDict):
        self.mm = user_mm_data

    def search(self, words: str) -> list[ZhmmDict] | None:
        if not self.mm or not self.mm['data']:
            return None

        find_data: list[ZhmmDict] = []
        arr_words = words.split()
        for word in arr_words:
            for data in self.mm['data']:
                if 'url' in data and word in data['url']:
                    find_data.append(data)
                elif 'desc' in data and word in data['desc']:
                    find_data.append(data)
                elif 'userID' in data and word in data['userID']:
                    find_data.append(data)
                elif 'phone' in data and data['phone'] and word in data['phone']:
                    find_data.append(data)
                elif 'email' in data and data['email'] and word in data['email']:
                    find_data.append(data)
        return find_data

    def add(self, info: ZhmmDict, file_path: str) -> bool:
        self.mm['data'].append(info)
        if 'role' not in info:
            info['role'] = '个人'
        if 'id' not in info:
            info['id'] = date_util.timestamp_int()
        if 'utime' not in info:
            info['utime'] = date_util.timestamp_int()
        return self.save(file_path)

    def save(self, file_path: str) -> bool:
        data = self.encrypt(json.dumps(self.mm))
        data_size = len(data)
        with open(file_path, 'w') as file:
            write_size = file.write(data)
            return data_size == write_size

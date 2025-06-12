#!/usr/bin/env python3
# coding=utf-8

from cryptography.fernet import Fernet  # 新增加密库导入

import os
import json
from pathlib import Path
from zhmm.utils import file_util


class AppConfig:

    save_file_name: str = "save"
    my_encryption_key: str = None

    def __init__(self):
        pass

    def get_lock_time(self):
        return 10

    def save_lock_time(self, v):
        return
       
    def get(self, key, default_value=None):
        return self.config.get(key, default_value)

    def set(self, key, value):
        self.config[key] = value

    def load_config(self):
        cfg_Path = file_util.get_full_path(self.save_file_name)
        # 检查配置文件是否存在
        if not cfg_Path.exists():
            self.config = {}
            return
        # 读取加密内容并解密
        with open(cfg_Path.as_posix(), 'rb') as f:
            encrypted_data = f.read()
        # 获取加密密钥（示例使用QSettings存储）
        key = self.my_encryption_key
        if key is None:
            decrypted_data = encrypted_data
        else:
            cipher_suite = Fernet(key)
            try:
                decrypted_data = cipher_suite.decrypt(encrypted_data).decode()
            except Exception as e:
                print("错误: 配置文件解密失败，请检查密钥或配置文件是否损坏")
                self.config = {}
                return
        # 解析解密后的JSON
        self.config = json.loads(decrypted_data)
        if self.config:
            self.api_key = self.config.get('api_key')
            self.work_dir = self.config.get('work_dir', os.getcwd())

    def save_config(self):
        cfg_Path = file_util.get_full_path(self.save_file_name)
        cfg_Path.parent.mkdir(parents=True, exist_ok=True)
        # 获取加密密钥
        key = self.my_encryption_key
        if key:
            cipher_suite = Fernet(key)
            # 加密配置数据
            cfg_json = json.dumps(self.config).encode()
            encrypted_data = cipher_suite.encrypt(cfg_json)
            file_util.set_file_bytes(str(cfg_Path), encrypted_data)
        else:
            encrypted_data = json.dumps(self.config)
            file_util.set_file_content(str(cfg_Path), encrypted_data)



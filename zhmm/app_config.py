#!/usr/bin/env python3
# coding=utf-8

from cryptography.fernet import Fernet  # 新增加密库导入

import os
import json
from pathlib import Path
from zhmm.utils import file_util
from zhmm.cloud.cloud_cos import CloudBase
from zhmm import setting

class AppConfig:

    save_file_name: str = "save"
    my_encryption_key: str = None

    cloud: CloudBase = None

    def __init__(self):
        pass

    def init(self, file_name, password):
        self.save_file_name = file_name
        self.my_encryption_key = setting.generate_key_from_string(password)
        self.load_config()

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
            return True
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

        # 解析解密后的JSON
        self.config = json.loads(decrypted_data)
        self.init_cloud()

    def init_cloud(self):
        platform = self.get('cloud_platform', '')
        if platform == 'cos':
            from zhmm.cloud.cloud_cos import CloudCos
            cloud = CloudCos()
            if cloud.init(self.config):
                self.cloud = cloud
        elif platform == 'oss':
            from zhmm.cloud.cloud_oss import CloudOss
            self.cloud = CloudOss(self.config)
        else:
            self.cloud = None

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
    
    def reset_sync_cloud(self, cloud_type: str):
        print("重置同步云盘", cloud_type)
        self.set('cloud_platform', cloud_type)
        self.save_config()
        self.init_cloud()



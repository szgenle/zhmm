#!/usr/bin/env python3
# coding=utf-8

import json
import hashlib

from cryptography.fernet import Fernet  # 新增加密库导入
from zhmm.utils.log import logger

from zhmm import setting
from zhmm.cloud.cloud_cos import CloudBase
from zhmm.utils import date_util, file_util


class AppConfig:
    cfg_file_name: str = "save"
    my_encryption_key: str
    _password_input: str | None

    cloud: CloudBase | None

    def __init__(self):
        self.cloud = None
        self._password_input = None

    def init(self, file_name, password):
        self.cfg_file_name = file_name
        self._password_input = password
        self.my_encryption_key = setting.generate_key_from_string(password)
        return self.load_config()

    def get_lock_time(self):
        return setting.get_lock_time()

    def save_lock_time(self, v):
        setting.save_lock_time(v)

    def get_theme(self):
        """获取主题设置"""
        return setting.get_theme()

    def save_theme(self, theme):
        """保存主题设置"""
        setting.save_theme(theme)

    def get(self, key, default_value=None):
        return self.config.get(key, default_value)

    def set(self, key, value):
        self.config[key] = value

    def load_config(self):
        cfg_Path = file_util.get_full_path(self.cfg_file_name)
        # 检查配置文件是否存在
        if not cfg_Path.exists():
            self.config = {}
            return True
        # 读取加密内容并解密
        with open(cfg_Path.as_posix(), "rb") as f:
            encrypted_data = f.read()
        # 获取加密密钥（示例使用QSettings存储）
        key = self.my_encryption_key

        decrypted_data = None
        if key is None:
            decrypted_data = encrypted_data
        else:
            cipher_suite = Fernet(key)
            try:
                decrypted_data = cipher_suite.decrypt(encrypted_data).decode()
                logger.info("配置解密方式: 新算法(PBKDF2+盐)成功")
            except Exception:
                # 回退1：旧算法 + md5(密码)
                try:
                    pwd = (self._password_input or "")
                    pwd_md5 = hashlib.md5(pwd.encode("utf-8")).hexdigest()
                    legacy_key = setting.legacy_generate_key_from_string(pwd_md5)
                    legacy_cipher = Fernet(legacy_key)
                    decrypted_data = legacy_cipher.decrypt(encrypted_data).decode()
                    logger.warning("配置解密方式: 旧算法(md5(密码)→SHA256)成功，已迁移到新算法")
                    self.config = json.loads(decrypted_data)
                    self.init_cloud()
                    # 用新算法重写保存
                    self.save_config()
                    return True
                except Exception:
                    # 回退2：旧算法 + 原始密码
                    try:
                        legacy_key2 = setting.legacy_generate_key_from_string(self._password_input or "")
                        legacy_cipher2 = Fernet(legacy_key2)
                        decrypted_data = legacy_cipher2.decrypt(encrypted_data).decode()
                        logger.warning("配置解密方式: 旧算法(原始密码→SHA256)成功，已迁移到新算法")
                        self.config = json.loads(decrypted_data)
                        self.init_cloud()
                        # 用新算法重写保存
                        self.save_config()
                        return True
                    except Exception:
                        # 回退3：尝试当作纯文本JSON读取
                        try:
                            decrypted_text = encrypted_data.decode("utf-8")
                            self.config = json.loads(decrypted_text)
                            logger.warning("配置解析方式: 纯文本JSON成功，已迁移到新算法")
                            self.init_cloud()
                            # 用新算法重写保存
                            self.save_config()
                            return True
                        except Exception:
                            # 放宽兜底：使用空配置继续，避免阻塞
                            logger.error("配置解密失败，采用空配置并重写为新算法")
                            self.config = {}
                            self.init_cloud()
                            self.save_config()
                            return True

        if decrypted_data is None:
            return False

        # 解析解密后的JSON
        self.config = json.loads(decrypted_data)
        self.init_cloud()
        return True

    def init_cloud(self):
        platform = self.get("cloud_platform", "")
        if platform == "cos":
            from zhmm.cloud.cloud_cos import CloudCos

            cloud = CloudCos()
            if cloud.init(self.config):
                self.cloud = cloud
        elif platform == "oss":
            from zhmm.cloud.cloud_oss import CloudOss

            self.cloud = CloudOss(self.config)

    def save_config(self):
        cfg_Path = file_util.get_full_path(self.cfg_file_name)
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
        self.set("cloud_platform", cloud_type)
        self.save_config()
        self.init_cloud()

    def sync_cloud_file(self, file_path):
        if not self.cloud:
            return False
        cloud_ver = self.cloud.get_file_content(f'zhmm/{self.cfg_file_name}.ver')
        local_ver = self.get('zhmm_ver')
        if local_ver and file_util.get_file_content(file_path) is None:
            local_ver = None
            self.set('zhmm_ver', local_ver)
        if cloud_ver:
            if not local_ver or (cloud_ver > local_ver):
                data = self.cloud.get_file_content(f'zhmm/{self.cfg_file_name}.gl')
                if data:
                    file_util.set_file_content(file_path, data)
                    self.set('zhmm_ver', cloud_ver)
                    return True
        return False

    def upload_cloud(self, file_path):
        if not self.cloud:
            return False
        data = file_util.get_file_content(file_path)
        if not data:
            return False
        if self.cloud.set_file_content(f'zhmm/{self.cfg_file_name}.gl', data) is None:
            return False
        cloud_ver = date_util.time_now()
        if self.cloud.set_file_content(f'zhmm/{self.cfg_file_name}.ver', cloud_ver):
            self.set('zhmm_ver', cloud_ver)
            self.save_config()
            return True
        pass

#!/usr/bin/env python3

import hashlib
import json

from cryptography.fernet import Fernet

from zhmm.config.settings import AppSetting
from zhmm.utils import file_util


class AppConfig:
    cfg_file_name: str = "save"
    my_encryption_key: str
    _password_input: str | None

    setting: AppSetting

    def __init__(self, setting: AppSetting):
        self.setting = setting
        self._password_input = None

    def init(self, file_name, password):
        self.cfg_file_name = file_name
        self._password_input = password
        self.my_encryption_key = self.setting.generate_key_from_string(password)
        return self.load_config()

    def get_lock_time(self):
        return self.setting.get_lock_time()

    def save_lock_time(self, v):
        self.setting.save_lock_time(v)

    def get_theme(self):
        """获取主题设置"""
        return self.setting.get_theme()

    def save_theme(self, theme):
        """保存主题设置"""
        self.setting.save_theme(theme)

    def get_auto_backup_enabled(self):
        """获取自动备份启用状态"""
        return self.setting.get_auto_backup_enabled()

    def save_auto_backup_enabled(self, enabled):
        """保存自动备份启用状态"""
        self.setting.save_auto_backup_enabled(enabled)

    def get_backup_interval(self):
        """获取备份间隔（分钟）"""
        return self.setting.get_backup_interval()

    def save_backup_interval(self, minutes):
        """保存备份间隔"""
        self.setting.save_backup_interval(minutes)

    def get_backup_keep_count(self):
        """获取备份保留数量"""
        return self.setting.get_backup_keep_count()

    def save_backup_keep_count(self, count):
        """保存备份保留数量"""
        self.setting.save_backup_keep_count(count)

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
                print("配置解密方式: 新算法(PBKDF2+盐)成功")
            except Exception:
                # 回退1：旧算法 + md5(密码)
                try:
                    pwd = (self._password_input or "")
                    pwd_md5 = hashlib.md5(pwd.encode("utf-8")).hexdigest()
                    legacy_key = self.setting.legacy_generate_key_from_string(pwd_md5)
                    legacy_cipher = Fernet(legacy_key)
                    decrypted_data = legacy_cipher.decrypt(encrypted_data).decode()
                    print("配置解密方式: 旧算法(md5(密码)→SHA256)成功，已迁移到新算法")
                    self.config = json.loads(decrypted_data)
                    # 用新算法重写保存
                    self.save_config()
                    return True
                except Exception:
                    # 回退2：旧算法 + 原始密码
                    try:
                        legacy_key2 = self.setting.legacy_generate_key_from_string(self._password_input or "")
                        legacy_cipher2 = Fernet(legacy_key2)
                        decrypted_data = legacy_cipher2.decrypt(encrypted_data).decode()
                        print("配置解密方式: 旧算法(原始密码→SHA256)成功，已迁移到新算法")
                        self.config = json.loads(decrypted_data)
                        # 用新算法重写保存
                        self.save_config()
                        return True
                    except Exception:
                        # 回退3：尝试当作纯文本JSON读取
                        try:
                            decrypted_text = encrypted_data.decode("utf-8")
                            self.config = json.loads(decrypted_text)
                            print("配置解析方式: 纯文本JSON成功，已迁移到新算法")
                            # 用新算法重写保存
                            self.save_config()
                            return True
                        except Exception:
                            # 放宽兜底：使用空配置继续，避免阻塞
                            print("配置解密失败，采用空配置并重写为新算法")
                            self.config = {}
                            self.save_config()
                            return True

        if decrypted_data is None:
            return False

        # 解析解密后的JSON
        self.config = json.loads(decrypted_data)
        return True

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

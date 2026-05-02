"""QSettings 封装：主题、自动备份、自动锁定、记住密码等本地偏好。"""

from __future__ import annotations

import base64
import hashlib
import os
from hashlib import sha256

from cryptography.fernet import Fernet
from PyQt6.QtCore import QSettings


class AppSetting(QSettings):
    def __init__(self) -> None:
        super().__init__("szgenle", "zhmm")

    def generate_key(self) -> None:
        # 生成并打印符合要求的密钥（32字节 URL安全 Base64编码）
        # 生成 32 字节 URL-safe Base64 编码的密钥（Fernet 标准格式）
        key = Fernet.generate_key()
        print(key.decode())  # 保存这个字符串到配置中

    # 新增：获取或生成加密盐（URL安全Base64存储）
    def _get_or_create_encryption_salt(self) -> bytes:
        salt_str: str = self.value("encryption_salt", "", type=str)
        if not salt_str:
            raw = os.urandom(16)
            salt_str = base64.urlsafe_b64encode(raw).decode()
            self.setValue("encryption_salt", salt_str)
            self.sync()
        return base64.urlsafe_b64decode(salt_str.encode())

    # 新版密钥派生：PBKDF2-HMAC-SHA256 + 盐，返回Fernet要求的URL安全Base64字符串
    def generate_key_from_string(self, input_str: str) -> str:
        input_bytes = input_str.encode()
        salt = self._get_or_create_encryption_salt()
        derived = hashlib.pbkdf2_hmac("sha256", input_bytes, salt, 200_000, dklen=32)
        return base64.urlsafe_b64encode(derived).decode()

    # 旧版兼容：SHA256摘要 + URL安全Base64（保留等号）
    def legacy_generate_key_from_string(self, input_str: str) -> str:
        digest = sha256(input_str.encode()).digest()
        return base64.urlsafe_b64encode(digest).decode()

    @property
    def remember_password(self) -> bool:
        value: bool = self.value("remember_password", False, type=bool)
        return value

    def save_remember_password(self, value: bool) -> None:
        self.setValue("remember_password", value)
        if not value:
            self.remove("encrypted_password")

    def get_lock_time(self) -> int:
        """获取自动锁定时间（分钟）"""
        value: int = self.value("lock_time", 10, type=int)
        return value

    def save_lock_time(self, minutes: int) -> None:
        """保存自动锁定时间"""
        self.setValue("lock_time", minutes)
        self.sync()

    def get_theme(self) -> str:
        """获取主题设置，默认为浅色主题
        返回值: 'light', 'dark', 'auto'
        """
        value: str = self.value("theme", "light", type=str)
        return value

    def save_theme(self, theme: str) -> None:
        """保存主题设置
        参数:
            theme: 'light', 'dark', 'auto'
        """
        self.setValue("theme", theme)
        self.sync()

    def get_auto_backup_enabled(self) -> bool:
        """获取自动备份是否启用"""
        value: bool = self.value("auto_backup_enabled", True, type=bool)
        return value

    def save_auto_backup_enabled(self, enabled: bool) -> None:
        """保存自动备份启用状态"""
        self.setValue("auto_backup_enabled", enabled)
        self.sync()

    def get_backup_interval(self) -> int:
        """获取备份间隔（分钟），默认30分钟"""
        value: int = self.value("backup_interval", 30, type=int)
        return value

    def save_backup_interval(self, minutes: int) -> None:
        """保存备份间隔"""
        self.setValue("backup_interval", minutes)
        self.sync()

    def get_backup_keep_count(self) -> int:
        """获取备份保留数量，默认10个"""
        value: int = self.value("backup_keep_count", 10, type=int)
        return value

    def save_backup_keep_count(self, count: int) -> None:
        """保存备份保留数量"""
        self.setValue("backup_keep_count", count)
        self.sync()

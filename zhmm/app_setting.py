from cryptography.fernet import Fernet
from PyQt6.QtCore import QSettings


class AppSetting(QSettings):
    def __init__(self):
        super().__init__("szgenle", "zhmm")
        pass

    def generate_key(self):
        # 生成并打印符合要求的密钥（32字节 URL安全 Base64编码）
        key = Fernet.generate_key()  # 例如：b'abcdefgh-ijklmnop_qrstuvwxyz123456'
        print(key.decode())  # 保存这个字符串到配置中

    # 新增：获取或生成加密盐（URL安全Base64存储）
    def _get_or_create_encryption_salt(self) -> bytes:
        import os, base64
        salt_str = self.value("encryption_salt", "", type=str)
        if not salt_str:
            raw = os.urandom(16)
            salt_str = base64.urlsafe_b64encode(raw).decode()
            self.setValue("encryption_salt", salt_str)
            self.sync()
        return base64.urlsafe_b64decode(salt_str.encode())

    # 新版密钥派生：PBKDF2-HMAC-SHA256 + 盐，返回Fernet要求的URL安全Base64字符串
    def generate_key_from_string(self, input_str: str):
        import base64, hashlib
        input_bytes = input_str.encode()
        salt = self._get_or_create_encryption_salt()
        derived = hashlib.pbkdf2_hmac("sha256", input_bytes, salt, 200_000, dklen=32)
        return base64.urlsafe_b64encode(derived).decode()

    # 旧版兼容：SHA256摘要 + URL安全Base64（保留等号）
    def legacy_generate_key_from_string(self, input_str: str):
        import base64
        from hashlib import sha256
        digest = sha256(input_str.encode()).digest()
        return base64.urlsafe_b64encode(digest).decode()

    @property
    def remember_password(self):
        return self.value("remember_password", False, type=bool)

    def save_remember_password(self, value):
        self.setValue("remember_password", value)
        if not value:
            self.remove("encrypted_password")

    def get_lock_time(self):
        """获取自动锁定时间（分钟）"""
        return self.value("lock_time", 10, type=int)

    def save_lock_time(self, minutes):
        """保存自动锁定时间"""
        self.setValue("lock_time", minutes)
        self.sync()

    def get_theme(self):
        """获取主题设置，默认为浅色主题
        返回值: 'light', 'dark', 'auto'
        """
        return self.value("theme", "light", type=str)

    def save_theme(self, theme):
        """保存主题设置
        参数:
            theme: 'light', 'dark', 'auto'
        """
        self.setValue("theme", theme)
        self.sync()

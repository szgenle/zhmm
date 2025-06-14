from cryptography.fernet import Fernet
from PyQt6.QtCore import QSettings


class AppSetting(QSettings):
    def __init__(self):
        super().__init__("szgenle", "zhmm")
        pass

    def get_app_encryption_key(self):
        return "2kheiDwP6OY3pDljvyjQEpI__Og-pDE_s14HfEUK4SE="

    def generate_key(self):
        # 生成并打印符合要求的密钥（32字节 URL安全 Base64编码）
        key = Fernet.generate_key()  # 例如：b'abcdefgh-ijklmnop_qrstuvwxyz123456'
        print(key.decode())  # 保存这个字符串到配置中

    def generate_key_from_string(self, input_str: str):
        """从任意字符串生成符合要求的32字节密钥"""
        import base64

        # 将输入字符串编码为字节
        input_bytes = input_str.encode()
        # 使用SHA-256生成固定长度的摘要（32字节）
        from hashlib import sha256

        digest = sha256(input_bytes).digest()
        # 转换为URL安全的base64编码（替换+/为-_）
        key = base64.urlsafe_b64encode(digest)
        # 返回完整的base64字符串（保留等号）
        return key.decode()

    @property
    def remember_password(self):
        return self.value("remember_password", False, type=bool)

    def save_remember_password(self, value):
        self.setValue("remember_password", value)
        if not value:
            self.remove("encrypted_password")

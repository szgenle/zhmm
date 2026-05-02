"""UI 层 QSettings 薄包装（主题、锁定时间等本地偏好）。"""

from __future__ import annotations

from PyQt6.QtCore import QSettings


class UIConfig:
    def __init__(self) -> None:
        self.settings = QSettings("szgenle", "账号小本本")

    def get_lock_time(self) -> int:
        value: int = self.settings.value("lock_time", 10, type=int)
        return value

    def save_lock_time(self, minutes: int) -> None:
        self.settings.setValue("lock_time", minutes)
        self.settings.sync()

    def get_theme(self) -> str:
        """获取主题设置，默认为浅色主题
        返回值: 'light', 'dark', 'auto'
        """
        value: str = self.settings.value("theme", "light", type=str)
        return value

    def save_theme(self, theme: str) -> None:
        """保存主题设置
        参数:
            theme: 'light', 'dark', 'auto'
        """
        self.settings.setValue("theme", theme)
        self.settings.sync()

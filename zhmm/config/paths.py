from PyQt6.QtCore import QSettings


class UIConfig:
    def __init__(self):
        self.settings = QSettings("szgenle", "账号小本本")

    def get_lock_time(self):
        return self.settings.value("lock_time", 10, type=int)

    def save_lock_time(self, minutes):
        self.settings.setValue("lock_time", minutes)
        self.settings.sync()

    def get_theme(self):
        """获取主题设置，默认为浅色主题
        返回值: 'light', 'dark', 'auto'
        """
        return self.settings.value("theme", "light", type=str)

    def save_theme(self, theme):
        """保存主题设置
        参数:
            theme: 'light', 'dark', 'auto'
        """
        self.settings.setValue("theme", theme)
        self.settings.sync()

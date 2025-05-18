
from PyQt6.QtCore import QSettings


class UIConfig:

    def __init__(self):
        self.settings = QSettings("szgenle", "账号小本本")

    def get_lock_time(self):
        return self.settings.value("lock_time", 10, type=int)

    def save_lock_time(self, minutes):
        self.settings.setValue("lock_time", minutes)
        self.settings.sync()



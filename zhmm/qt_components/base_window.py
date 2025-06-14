from PyQt6.QtGui import QCloseEvent  # 新增导入
from PyQt6.QtWidgets import QMainWindow

from zhmm.ui_config import UIConfig


class BaseWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.config = UIConfig()
        self.init_ui()

    def init_ui(self):
        # 恢复窗口位置和大小
        geometry = self.config.settings.value("geometry")
        if geometry:
            self.setGeometry(geometry)
        else:
            self.setGeometry(100, 100, 1400, 1000)

    def closeEvent(self, event: QCloseEvent):  # 添加类型注解  # type: ignore[override]
        # 保存窗口位置和大小
        self.config.settings.setValue("geometry", self.geometry())
        super().closeEvent(event)


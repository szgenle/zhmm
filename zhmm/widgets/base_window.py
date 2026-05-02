from PyQt6.QtGui import QCloseEvent, QShowEvent  # 新增导入
from PyQt6.QtWidgets import QMainWindow

import zhmm
from zhmm.config.paths import UIConfig
from zhmm.utils.anti_capture import apply_anti_capture


class BaseWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = UIConfig()
        self._anti_capture_applied = False
        self.init_ui()

    def init_ui(self):
        # 恢复窗口位置和大小
        geometry = self.config.settings.value("geometry")
        if geometry:
            self.setGeometry(geometry)
        else:
            self.setGeometry(100, 100, 1400, 1000)

    def showEvent(self, event: QShowEvent):  # type: ignore[override]
        super().showEvent(event)
        # 窗口首次展示时应用防截屏（需等原生窗口创建完毕）
        if self._anti_capture_applied:
            return
        enabled = True
        if zhmm.setting is not None:
            enabled = zhmm.setting.get_anti_screenshot()
        apply_anti_capture(self, enabled=enabled)
        self._anti_capture_applied = True

    def refresh_anti_capture(self, enabled: bool) -> None:
        """设置面板切换开关时实时应用。"""
        apply_anti_capture(self, enabled=enabled)

    def closeEvent(self, event: QCloseEvent):  # 添加类型注解  # type: ignore[override]
        # 保存窗口位置和大小
        self.config.settings.setValue("geometry", self.geometry())
        super().closeEvent(event)

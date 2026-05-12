#!/usr/bin/env python3
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
import os
import sys
from datetime import datetime, timedelta

from PyQt6.QtCore import QEvent, QObject, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QMessageBox

import zhmm
from zhmm.config.constants import ZhmmFileInfo
from zhmm.gui.main_window import MainWindow
from zhmm.gui.welcome_widget import WelcomeWidget
from zhmm.utils.log import logger
from zhmm.widgets.base_window import BaseWindow

# 浏览器填充桥（方案 C POC），通过环境变量 ZHMM_BROWSER_BRIDGE=1 启用
_BROWSER_BRIDGE_ENABLED = os.environ.get("ZHMM_BROWSER_BRIDGE", "") == "1"


class AppWindow(BaseWindow):
    """主窗口"""

    welcome_widget: WelcomeWidget | None = None
    main_widget: MainWindow | None = None

    def __init__(self):
        super().__init__()
        self.setWindowTitle("账号管理器")

        # 创建菜单栏
        self.create_menu_bar()

        # 记录最后活动时间
        self.last_active_time = datetime.now()

        # 安装 QApplication 级事件过滤器跟踪用户键鼠活动（#M）
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        # 创建定时器，每 30s tick 一次，让锁定触发精度接近分钟级
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.timeout.connect(self.check_inactivity)
        self.inactivity_timer.start(30_000)

        # 可选：浏览器填充桥
        self._bridge = None
        if _BROWSER_BRIDGE_ENABLED:
            self._start_browser_bridge()

        # 首次启动时显示欢迎窗口
        QTimer.singleShot(500, self.show_welcome_ui)

    # ------------------------------------------------------------------
    # 浏览器填充桥（POC）
    # ------------------------------------------------------------------
    def _start_browser_bridge(self) -> None:
        try:
            from zhmm.browser_bridge import BrowserBridgeController

            self._bridge = BrowserBridgeController(self)
            self._bridge.set_vault_source(self._current_sm_data)
            port, _token, path = self._bridge.start()
            logger.info(f"浏览器填充桥已启用，端口={port}，凭据文件={path}")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"浏览器填充桥启动失败：{exc}")
            self._bridge = None

    def _current_sm_data(self):
        """返回当前已解锁的 SmData，未登录/已锁时返回 None。"""
        if self.main_widget is None:
            return None
        info = getattr(self.main_widget, "info", None)
        if not info:
            return None
        return info.get("sm_data")

    def closeEvent(self, event):  # type: ignore[override]
        if self._bridge is not None:
            try:
                self._bridge.stop()
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"浏览器填充桥关闭异常：{exc}")
        super().closeEvent(event)

    def setup_welcome_ui(self, show_login_dialog: bool = True):
        """设置欢迎界面"""
        welcome_widget = WelcomeWidget(self)
        if show_login_dialog:
            welcome_widget.file_list.auto_select_last_file()
        welcome_widget.file_list.login_success.connect(lambda info: self.on_login_success(info))
        self.setCentralWidget(welcome_widget)
        return welcome_widget

    def show_welcome_ui(self, show_login_dialog: bool = True):
        """显示欢迎界面"""
        self.hide_welcome_ui()

        self.welcome_widget = self.setup_welcome_ui(show_login_dialog)
        self.setCentralWidget(self.welcome_widget)

        self.hide_data_ui()

    def hide_welcome_ui(self):
        """隐藏欢迎界面"""
        if self.welcome_widget:
            self.welcome_widget.deleteLater()
            del self.welcome_widget
            self.welcome_widget = None

    def hide_data_ui(self):
        """隐藏数据管理界面并清理会话中的明文数据（#M）。"""
        if self.main_widget:
            info = getattr(self.main_widget, "info", None)
            sm_data = info.get("sm_data") if isinstance(info, dict) else None
            if sm_data is not None and hasattr(sm_data, "close"):
                try:
                    sm_data.close()
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"会话清理异常：{exc}")
            self.main_widget.deleteLater()
            del self.main_widget
            self.main_widget = None

    def show_data_ui(self, info: ZhmmFileInfo):
        self.hide_data_ui()
        # 创建数据管理界面
        self.main_widget = MainWindow(info)
        self.setCentralWidget(self.main_widget)
        # 连接返回首页信号
        self.main_widget.return_requested.connect(lambda: self.show_welcome_ui(False))
        # 隐藏欢迎界面
        self.hide_welcome_ui()

    def on_login_success(self, info: ZhmmFileInfo):
        """登录成功后的处理"""
        if not info or not info["sm_data"]:
            return
        # 更新最后活动时间
        self.last_active_time = datetime.now()
        logger.info("登录成功，更新活动时间")
        self.show_data_ui(info)

    def check_inactivity(self):
        """检查非活动时间。

        活动判定依赖 :meth:`eventFilter` 记录的 ``last_active_time``，
        包含鼠标 / 键盘 / 轮 等输入事件。
        """
        if isinstance(self.centralWidget(), WelcomeWidget):
            # 已在登录页，无需锁定
            return
        inactive_duration = datetime.now() - self.last_active_time
        if inactive_duration > timedelta(minutes=zhmm.config.get_lock_time()):
            logger.info(f"检测到非活动时间: {inactive_duration}，触发自动锁定")
            self.show_welcome_ui()

    # ------------------------------------------------------------------
    # 全局输入活动检测（#M）
    # ------------------------------------------------------------------
    _ACTIVITY_EVENT_TYPES = frozenset(
        {
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseMove,
            QEvent.Type.KeyPress,
            QEvent.Type.Wheel,
            QEvent.Type.TouchBegin,
            QEvent.Type.TouchUpdate,
        }
    )

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if event.type() in self._ACTIVITY_EVENT_TYPES:
            self.last_active_time = datetime.now()
        return super().eventFilter(obj, event)

    # def changeEvent(self, event):  # type: ignore
    #     """窗口状态改变事件"""
    #     super().changeEvent(event)
    #     # 当窗口从非活动状态变为活动状态时
    #     if event.type() == event.Type.ActivationChange and self.isActiveWindow():
    #         current_time = datetime.now()
    #         inactive_duration = current_time - self.last_active_time
    #
    #         # 使用配置的锁屏时间检查非活动时间
    #         if inactive_duration > timedelta(minutes=config.get_lock_time()):
    #             logger.info(f"窗口重新激活，非活动时间: {inactive_duration}，显示登录窗口")
    #             self.show_welcome_ui()
    #
    #         # 更新最后活动时间
    #         self.last_active_time = current_time

    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")

        # 关于动作
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def show_about_dialog(self):
        """显示关于对话框"""
        from zhmm import __version__

        about_text = f"""
        <h2>账号管理器</h2>
        <p>版本: {__version__}</p>
        <p>一个用于管理网站、App 账号密码及相关信息的工具。</p>
        <p>支持数据加密存储、手动备份等功能。</p>
        """

        QMessageBox.about(self, "关于", about_text)


def _install_global_excepthook() -> None:
    """拦截所有 slot 未捕获的 Python 异常，避免 PyQt6 默认行为 abort 进程。

    PyQt6 从 6.0 起，signal/slot 里抛出的 Python 异常默认会调 ``qFatal``让进程
    直接崩溃（用户视角“闪退”）。比如曾经的 ``QTimer.singleShot(msec, receiver, slot)``
    三参误用、lambda 参数不匹配等，都会例就独立触发闪退，极难定位。

    改成统一走 logger 记下完整栈，业务上的未捕获异常后续仍可通过日志定位，但不
    再让用户在无提示下丢失进程与会话（包括未落盘的数据修改）。
    """

    def _hook(exc_type, exc_value, exc_tb):
        # KeyboardInterrupt 仍按默认行为处理，方便终端 Ctrl-C 退出。
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.error(
            "GUI 中出现未捕获异常（已拦截以避免进程崩溃）",
            exc_info=(exc_type, exc_value, exc_tb),
        )

    sys.excepthook = _hook


def main() -> None:
    """主函数"""

    _install_global_excepthook()

    app = QApplication(sys.argv)

    # 根据保存的主题设置应用样式
    from zhmm.gui.theme import ThemeManager

    current_theme = zhmm.config.get_theme()
    stylesheet = ThemeManager.get_theme_stylesheet(current_theme)
    app.setStyleSheet(stylesheet)

    window = AppWindow()
    window.show()

    print(len(sys.argv))
    print(sys.argv[0])
    if len(sys.argv) > 1:
        QMessageBox.information(None, "提示", sys.argv[1])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

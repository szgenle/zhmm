#!/usr/bin/env python3
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
import sys
from datetime import datetime, timedelta

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QMessageBox

import zhmm
from zhmm.config.constants import ZhmmFileInfo
from zhmm.gui.main_window import MainWindow
from zhmm.gui.welcome_widget import WelcomeWidget
from zhmm.utils.log import logger
from zhmm.widgets.base_window import BaseWindow


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

        # 创建定时器，使用配置的锁屏时间检查非活动时间
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.timeout.connect(self.check_inactivity)
        self.inactivity_timer.start(zhmm.config.get_lock_time() * 60000)

        # 首次启动时显示欢迎窗口
        QTimer.singleShot(500, self.show_welcome_ui)

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
        """隐藏数据管理界面"""
        if self.main_widget:
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
        """检查非活动时间"""
        if self.isActiveWindow():
            logger.info("isActiveWindow")
            self.last_active_time = datetime.now()
            return

        current_time = datetime.now()
        inactive_duration = current_time - self.last_active_time

        # 使用配置的锁屏时间检查非活动时间
        if inactive_duration > timedelta(minutes=zhmm.config.get_lock_time()) and not isinstance(
            self.centralWidget(), WelcomeWidget
        ):
            logger.info(f"检测到非活动时间: {inactive_duration}，显示登录窗口")
            self.show_welcome_ui()
        else:
            logger.info("check_inactivity .. ")

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
        <p>支持数据加密存储、自动备份、云同步等功能。</p>
        """

        QMessageBox.about(self, "关于", about_text)


def main() -> None:
    """主函数"""

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

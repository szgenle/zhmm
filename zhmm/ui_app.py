#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
import sys
from datetime import datetime, timedelta

from PyQt6.QtCore import QCoreApplication, QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox

QCoreApplication.setApplicationName("zhmm")
QCoreApplication.setOrganizationName("szgenle")  # 替换为您的组织名称

from zhmm import config
from zhmm.qt_components.base_window import BaseWindow
from zhmm.ui.welcome_widget import WelcomeWidget
from zhmm.ui_defined import ZhmmFileInfo
from zhmm.ui_main import MainWindow
from zhmm.utils.log import logger


class AppWindow(BaseWindow):
    """主窗口"""

    welcome_widget: WelcomeWidget | None = None
    main_widget: MainWindow | None = None

    def __init__(self):
        super().__init__()
        self.setWindowTitle("账号管理器")

        # 记录最后活动时间
        self.last_active_time = datetime.now()

        # 创建定时器，使用配置的锁屏时间检查非活动时间
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.timeout.connect(self.check_inactivity)
        self.inactivity_timer.start(config.get_lock_time() * 60000)

        # 首次启动时显示欢迎窗口
        QTimer.singleShot(500, self.show_welcome_ui)

    def setup_welcome_ui(self, show_login_dialog: bool = True):
        """设置欢迎界面"""
        welcome_widget = WelcomeWidget(self)
        if show_login_dialog:
            welcome_widget.file_list.auto_select_last_file()
        welcome_widget.file_list.login_success.connect(
            lambda info: self.on_login_success(info)
        )
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
        # 添加返回按钮信号连接
        self.main_widget.data_manager_widget.return_requested.connect(
            lambda: self.show_welcome_ui(False)
        )  # 新增
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
        if inactive_duration > timedelta(
            minutes=config.get_lock_time()
        ) and not isinstance(self.centralWidget(), WelcomeWidget):
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


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 应用全局样式表
    app.setStyleSheet("""
        QDialog { background-color: #f5f7fa; border-radius: 8px; }
        QLabel#title_label { color: #2c3e50; font-size: 18px; font-weight: bold; }
        QLabel { color: #34495e; font-size: 14px; }
        QLineEdit, QTextEdit, QComboBox {
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            padding: 6px 10px;
            background-color: white;
            selection-background-color: #3498db;
            selection-color: white;
        }
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
            border-color: #3498db;
            outline: none;
        }
        QPushButton {
            border-radius: 4px;
            padding: 6px 12px;
            font-size: 14px;
        }
        QPushButton#confirm_button {
            background-color: #3498db;
            color: white;
            border: none;
        }
        QPushButton#confirm_button:hover { background-color: #2980b9; }
        QPushButton#cancel_button {
            background-color: #ecf0f1;
            color: #34495e;
            border: 1px solid #bdc3c7;
        }
        QPushButton#cancel_button:hover { background-color: #dcdde1; }
        QPushButton#add_role_btn, QPushButton#random_pwd_btn {
            background-color: #3498db;
            color: white;
            border: none;
        }
        QPushButton#add_role_btn:hover, QPushButton#random_pwd_btn:hover {
            background-color: #2980b9;
        }
    """)

    window = AppWindow()
    window.show()

    print(len(sys.argv))
    print(sys.argv[0])
    if len(sys.argv) > 1:
        QMessageBox.information(None, "提示", sys.argv[1])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

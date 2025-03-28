#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
import sys
from datetime import datetime, timedelta

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (QApplication, QMainWindow)

from zhmm.ui.data_manager_widget import DataManagerWidget
from zhmm.ui.login_dialog import LoginDialog, ZhmmFileInfo
from zhmm.ui.welcome_widget import WelcomeWidget
from zhmm.utils.log import logger


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("密码管理器")
        self.resize(800, 600)

        # 记录最后活动时间
        self.last_active_time = datetime.now()

        # 创建定时器，每分钟检查一次非活动时间
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.timeout.connect(self.check_inactivity)
        self.inactivity_timer.start(60000)  # 60000毫秒 = 1分钟

        # 创建欢迎界面
        self.welcome_widget = self.setup_welcome_ui()

        # 首次启动时显示欢迎窗口
        QTimer.singleShot(500, self.show_welcome_ui)

    def setup_welcome_ui(self):
        """设置欢迎界面"""
        welcome_widget = WelcomeWidget(self)
        welcome_widget.file_list.login_success.connect(lambda info: self.on_login_success(info))
        self.setCentralWidget(welcome_widget)
        return welcome_widget

    def show_welcome_ui(self):
        """显示欢迎界面"""
        self.setCentralWidget(self.welcome_widget)

    def on_login_success(self, info: ZhmmFileInfo):
        """登录成功后的处理"""
        if not info['sm_data']:
            return
        # 更新最后活动时间
        self.last_active_time = datetime.now()
        logger.info("登录成功，更新活动时间")
        # 创建数据管理界面
        self.data_manager = DataManagerWidget(info['sm_data'])
        self.setCentralWidget(self.data_manager)
        # 隐藏欢迎界面
        self.welcome_widget.hide()

    def check_inactivity(self):
        """检查非活动时间"""
        current_time = datetime.now()
        inactive_duration = current_time - self.last_active_time

        # 如果非活动时间超过3分钟且窗口当前是活动的，则显示登录窗口
        if inactive_duration > timedelta(minutes=1) and self.isActiveWindow() and not isinstance(self.centralWidget(), WelcomeWidget):
            logger.info(f"检测到非活动时间: {inactive_duration}，显示登录窗口")
            self.show_welcome_ui()

    def changeEvent(self, event):  # type: ignore
        """窗口状态改变事件"""
        super().changeEvent(event)
        # 当窗口从非活动状态变为活动状态时
        if event.type() == event.Type.ActivationChange and self.isActiveWindow():
            current_time = datetime.now()
            inactive_duration = current_time - self.last_active_time

            # 如果非活动时间超过3分钟，显示登录窗口
            if inactive_duration > timedelta(minutes=3):
                logger.info(f"窗口重新激活，非活动时间: {inactive_duration}，显示登录窗口")
                self.show_welcome_ui()

            # 更新最后活动时间
            self.last_active_time = current_time


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("密码管理器")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

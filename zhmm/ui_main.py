#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
import sys
from datetime import datetime, timedelta

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame)

from zhmm.qt_components.dialog import Dialog
from zhmm.ui.login_dialog import LoginDialog
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
        self.setup_welcome_ui()

        # 首次启动时显示登录窗口
        QTimer.singleShot(500, self.show_login_dialog)

    def setup_welcome_ui(self):
        """设置欢迎界面"""
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # 欢迎标题
        welcome_label = QLabel("欢迎使用密码管理器")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        main_layout.addWidget(welcome_label)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)

        # 说明文本
        info_label = QLabel("这是一个安全的密码管理工具，可以帮助您管理各种账号密码。")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)

        # 功能区域（暂时为空，后续可以添加功能按钮）
        feature_layout = QHBoxLayout()
        main_layout.addLayout(feature_layout)

        # 设置中心部件
        self.setCentralWidget(central_widget)

    def show_login_dialog(self):
        """显示登录对话框"""
        logger.info('show_login_dialog')
        login_dialog = LoginDialog(self)
        # login_dialog.login_success.connect(self.on_login_success)
        login_dialog.exec()

    def on_login_success(self):
        """登录成功后的处理"""
        # 更新最后活动时间
        self.last_active_time = datetime.now()
        logger.info("登录成功，更新活动时间")

    def check_inactivity(self):
        """检查非活动时间"""
        current_time = datetime.now()
        inactive_duration = current_time - self.last_active_time

        # 如果非活动时间超过3分钟且窗口当前是活动的，则显示登录窗口
        if inactive_duration > timedelta(minutes=3) and self.isActiveWindow():
            logger.info(f"检测到非活动时间: {inactive_duration}，显示登录窗口")
            self.show_login_dialog()

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
                self.show_login_dialog()

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

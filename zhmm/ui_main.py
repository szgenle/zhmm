#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03

import os
import sys
import time
from datetime import datetime, timedelta

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (QApplication, QMainWindow, QDialog, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QMessageBox, QWidget, QGridLayout, QFrame)

from utils.log import logger
import sm_util
from gl_data import GlData
from utils import array, file_sys

# 全局数据对象
gl_data = GlData()


class LoginDialog(QDialog):
    """登录对话框"""
    login_success = pyqtSignal()  # 登录成功信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("登录验证")
        self.setFixedSize(400, 250)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        # 创建布局
        layout = QVBoxLayout()
        
        # 标题标签
        title_label = QLabel("请输入登录信息")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 添加一些间距
        layout.addSpacing(20)
        
        # 创建表单布局
        form_layout = QGridLayout()
        
        # OpenID输入
        openid_label = QLabel("OpenID:")
        self.openid_input = QLineEdit()
        self.openid_input.setPlaceholderText("请输入微信小程序中显示的OpenId")
        form_layout.addWidget(openid_label, 0, 0)
        form_layout.addWidget(self.openid_input, 0, 1)
        
        # 密码输入
        password_label = QLabel("密码:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("请输入密码")
        form_layout.addWidget(password_label, 1, 0)
        form_layout.addWidget(self.password_input, 1, 1)
        
        layout.addLayout(form_layout)
        
        # 添加一些间距
        layout.addSpacing(20)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 登录按钮
        self.login_button = QPushButton("登录")
        self.login_button.clicked.connect(self.verify_login)
        button_layout.addWidget(self.login_button)
        
        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def verify_login(self):
        """验证登录信息"""
        openid = self.openid_input.text().strip()
        password = self.password_input.text().strip()
        
        if not openid:
            QMessageBox.warning(self, "警告", "OpenID不能为空")
            return
        
        if not password:
            QMessageBox.warning(self, "警告", "密码不能为空")
            return
        
        # 验证逻辑，使用现有的gl_data验证方法
        try:
            # 处理密码，与cmd_ui.py中相同的逻辑
            pwd_suffix = password + 'woie*#jk20kH2^D@U28)'
            pwd = sm_util.hash_by_sm3(array.string_to_hex_array(pwd_suffix))
            gl_data.init(openid, pwd)
            
            # 尝试读取并解密文件
            file_path = 'zhmm.gl'  # 默认文件路径
            data = file_sys.get_file_content(file_path)
            
            if data:
                decrypt_result = gl_data.decrypt(data)
                
                if not decrypt_result or not decrypt_result['res']:
                    QMessageBox.critical(self, "错误", "密码不正确")
                    return
                
                # 登录成功
                logger.info(f"用户 {openid} 登录成功")
                self.login_success.emit()
                self.accept()
            else:
                QMessageBox.critical(self, "错误", f"无法读取文件: {file_path}")
        
        except Exception as e:
            logger.error(f"登录验证出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"登录验证出错: {str(e)}")


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
        login_dialog.login_success.connect(self.on_login_success)
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
    
    def changeEvent(self, event):   # type: ignore
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
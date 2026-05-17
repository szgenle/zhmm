#!/usr/bin/env python3
"""主题管理器 - 管理应用的主题样式"""

import platform
import subprocess
import time

# auto 主题检测结果缓存的 QSettings key 与 TTL。
# 背景：``ThemeManager.get_system_theme()`` 在 macOS 需 ``subprocess defaults read``，
# 在 Windows 需打开注册表；两者都是同步阻塞调用，在冷启动路径上能走 100~300ms。
# 用户并不会频繁切换系统主题，以 24 小时为 TTL 缓存上一次检测结果。
_SYSTEM_THEME_CACHE_KEY = "theme/system_cache_value"
_SYSTEM_THEME_CACHE_AT_KEY = "theme/system_cache_at"
_SYSTEM_THEME_CACHE_TTL_SEC = 24 * 60 * 60


def _read_cached_system_theme() -> str | None:
    """读 QSettings 中 TTL 内的 system theme 缓存值；未命中返回 None。"""
    try:
        from PyQt6.QtCore import QSettings  # noqa: PLC0415

        settings = QSettings()
        value = settings.value(_SYSTEM_THEME_CACHE_KEY)
        ts_raw = settings.value(_SYSTEM_THEME_CACHE_AT_KEY)
        if not value or ts_raw is None:
            return None
        try:
            ts = float(ts_raw)
        except (TypeError, ValueError):
            return None
        if time.time() - ts > _SYSTEM_THEME_CACHE_TTL_SEC:
            return None
        if value in ("light", "dark"):
            return str(value)
        return None
    except Exception:
        return None


def _write_cached_system_theme(value: str) -> None:
    """把本次检测结果写回 QSettings，供下次启动复用。"""
    try:
        from PyQt6.QtCore import QSettings  # noqa: PLC0415

        settings = QSettings()
        settings.setValue(_SYSTEM_THEME_CACHE_KEY, value)
        settings.setValue(_SYSTEM_THEME_CACHE_AT_KEY, time.time())
    except Exception:
        # 缓存写入失败不应影响主题设置
        pass


class ThemeManager:
    """主题管理器"""

    # 浅色主题样式
    LIGHT_THEME = """
        QDialog { background-color: #f5f7fa; border-radius: 8px; }
        QMainWindow { background-color: #ffffff; }
        QWidget { background-color: #ffffff; color: #2c3e50; }
        QLabel#title_label { color: #2c3e50; font-size: 18px; font-weight: bold; background-color: transparent; }
        QLabel { color: #34495e; font-size: 14px; background-color: transparent; }
        QLabel#setting-datasave-title { color: #2c3e50; font-size: 16px; font-weight: bold; margin-top: 10px; background-color: transparent; }

        QLineEdit, QTextEdit, QComboBox, QSpinBox {
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            padding: 6px 10px;
            background-color: white;
            color: #2c3e50;
            selection-background-color: #3498db;
            selection-color: white;
        }
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
            border-color: #3498db;
            outline: none;
        }

        QPushButton {
            border-radius: 4px;
            padding: 6px 12px;
            font-size: 14px;
            background-color: #ecf0f1;
            color: #34495e;
            border: 1px solid #bdc3c7;
        }
        QPushButton:hover { background-color: #dcdde1; }
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

        QTabWidget::pane {
            border: 1px solid #bdc3c7;
            background-color: #ffffff;
        }
        QTabBar::tab {
            background-color: #ecf0f1;
            color: #34495e;
            padding: 8px 16px;
            border: 1px solid #bdc3c7;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background-color: #ffffff;
            color: #2c3e50;
            font-weight: bold;
        }
        QTabBar::tab:hover { background-color: #dcdde1; }

        QTableWidget, QTableView {
            background-color: #ffffff;
            alternate-background-color: #f8f9fa;
            gridline-color: #e0e0e0;
            selection-background-color: #3498db;
            selection-color: white;
            border: 1px solid #bdc3c7;
            color: #2c3e50;
        }
        QHeaderView::section {
            background-color: #ecf0f1;
            color: #2c3e50;
            padding: 8px;
            border: 1px solid #bdc3c7;
            font-weight: bold;
        }

        QCheckBox, QRadioButton {
            color: #34495e;
            spacing: 5px;
            background-color: transparent;
        }
        QCheckBox::indicator, QRadioButton::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid #bdc3c7;
            border-radius: 3px;
            background-color: white;
        }
        QCheckBox::indicator:checked, QRadioButton::indicator:checked {
            background-color: #3498db;
            border-color: #3498db;
        }
        QRadioButton::indicator { border-radius: 9px; }

        QGroupBox {
            border: 1px solid #d0d7de;
            border-radius: 6px;
            margin-top: 14px;
            padding: 14px 10px 10px 10px;
            background-color: #f8f9fa;
            font-weight: bold;
            color: #2c3e50;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 6px;
            background-color: #f8f9fa;
            color: #2c3e50;
        }

        QScrollBar:vertical {
            border: none;
            background-color: #f5f7fa;
            width: 10px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background-color: #bdc3c7;
            min-height: 20px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover { background-color: #95a5a6; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

        /* 标签列表（标签选择弹窗 / 侧边栏筛选）统一风格 */
        QListWidget#tag_picker_list, QListWidget#tag_sidebar_list {
            border: 1px solid #d0d7de;
            border-radius: 6px;
            padding: 2px;
            background-color: #ffffff;
            color: #2c3e50;
        }
        QListWidget#tag_picker_list::item, QListWidget#tag_sidebar_list::item {
            padding: 6px 6px;
            color: #2c3e50;
            border-radius: 3px;
        }
        QListWidget#tag_picker_list::item:hover, QListWidget#tag_sidebar_list::item:hover {
            background-color: #e3f2fd;
            color: #0d47a1;
        }
        QListWidget#tag_picker_list::item:disabled, QListWidget#tag_sidebar_list::item:disabled {
            color: #95a5a6;
        }
    """

    # 深色主题样式
    DARK_THEME = """
        QDialog { background-color: #2c3e50; border-radius: 8px; }
        QMainWindow { background-color: #1e272e; }
        QWidget { background-color: #1e272e; color: #ecf0f1; }
        QLabel#title_label { color: #ecf0f1; font-size: 18px; font-weight: bold; background-color: transparent; }
        QLabel { color: #bdc3c7; font-size: 14px; background-color: transparent; }
        QLabel#setting-datasave-title { color: #ecf0f1; font-size: 16px; font-weight: bold; margin-top: 10px; background-color: transparent; }

        QLineEdit, QTextEdit, QComboBox, QSpinBox {
            border: 1px solid #34495e;
            border-radius: 4px;
            padding: 6px 10px;
            background-color: #2c3e50;
            color: #ecf0f1;
            selection-background-color: #3498db;
            selection-color: white;
        }
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
            border-color: #3498db;
            outline: none;
        }

        QPushButton {
            border-radius: 4px;
            padding: 6px 12px;
            font-size: 14px;
            background-color: #34495e;
            color: #ecf0f1;
            border: 1px solid #2c3e50;
        }
        QPushButton:hover { background-color: #465664; }
        QPushButton#confirm_button {
            background-color: #3498db;
            color: white;
            border: none;
        }
        QPushButton#confirm_button:hover { background-color: #2980b9; }
        QPushButton#cancel_button {
            background-color: #34495e;
            color: #ecf0f1;
            border: 1px solid #2c3e50;
        }
        QPushButton#cancel_button:hover { background-color: #465664; }
        QPushButton#add_role_btn, QPushButton#random_pwd_btn {
            background-color: #3498db;
            color: white;
            border: none;
        }
        QPushButton#add_role_btn:hover, QPushButton#random_pwd_btn:hover {
            background-color: #2980b9;
        }

        QTabWidget::pane {
            border: 1px solid #34495e;
            background-color: #1e272e;
        }
        QTabBar::tab {
            background-color: #34495e;
            color: #bdc3c7;
            padding: 8px 16px;
            border: 1px solid #2c3e50;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background-color: #1e272e;
            color: #ecf0f1;
            font-weight: bold;
        }
        QTabBar::tab:hover { background-color: #465664; }

        QTableWidget, QTableView {
            background-color: #1e272e;
            alternate-background-color: #2c3e50;
            gridline-color: #34495e;
            selection-background-color: #3498db;
            selection-color: white;
            border: 1px solid #34495e;
            color: #ecf0f1;
        }
        QHeaderView::section {
            background-color: #34495e;
            color: #ecf0f1;
            padding: 8px;
            border: 1px solid #2c3e50;
            font-weight: bold;
        }

        QCheckBox, QRadioButton {
            color: #bdc3c7;
            spacing: 5px;
            background-color: transparent;
        }
        QCheckBox::indicator, QRadioButton::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid #34495e;
            border-radius: 3px;
            background-color: #2c3e50;
        }
        QCheckBox::indicator:checked, QRadioButton::indicator:checked {
            background-color: #3498db;
            border-color: #3498db;
        }
        QRadioButton::indicator { border-radius: 9px; }

        QGroupBox {
            border: 1px solid #34495e;
            border-radius: 6px;
            margin-top: 14px;
            padding: 14px 10px 10px 10px;
            background-color: #2c3e50;
            font-weight: bold;
            color: #ecf0f1;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 6px;
            background-color: #2c3e50;
            color: #ecf0f1;
        }

        QScrollBar:vertical {
            border: none;
            background-color: #2c3e50;
            width: 10px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background-color: #34495e;
            min-height: 20px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover { background-color: #465664; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

        /* 标签列表（标签选择弹窗 / 侧边栏筛选）统一风格 */
        QListWidget#tag_picker_list, QListWidget#tag_sidebar_list {
            border: 1px solid #34495e;
            border-radius: 6px;
            padding: 2px;
            background-color: #2c3e50;
            color: #ecf0f1;
        }
        QListWidget#tag_picker_list::item, QListWidget#tag_sidebar_list::item {
            padding: 6px 6px;
            color: #ecf0f1;
            border-radius: 3px;
        }
        QListWidget#tag_picker_list::item:hover, QListWidget#tag_sidebar_list::item:hover {
            background-color: #3d566e;
            color: #ffffff;
        }
        QListWidget#tag_picker_list::item:disabled, QListWidget#tag_sidebar_list::item:disabled {
            color: #7f8c8d;
        }
    """

    @staticmethod
    def get_system_theme():
        """检测系统主题（仅支持 macOS 和 Windows）
        返回: 'light' 或 'dark'

        优先返回 QSettings 中 24 小时内的缓存值；未命中时会同步调用系统接口
        （``defaults read`` / 注册表）获取实时结果，同时写回缓存。
        该缓存仅为减少冷启动上的 100~300ms 同步 IO；用户手动切换系统
        主题后最多 24 小时后下次启动生效。
        """
        cached = _read_cached_system_theme()
        if cached is not None:
            return cached

        system = platform.system()
        detected = "light"

        if system == "Darwin":  # macOS
            try:
                result = subprocess.run(
                    ["defaults", "read", "-g", "AppleInterfaceStyle"], capture_output=True, text=True
                )
                # 如果命令成功且返回 'Dark'，则为深色模式
                if result.returncode == 0 and "Dark" in result.stdout:
                    detected = "dark"
            except Exception:
                detected = "light"

        elif system == "Windows":  # Windows
            try:
                import winreg

                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                # 0 = 深色, 1 = 浅色
                detected = "dark" if value == 0 else "light"
            except Exception:
                detected = "light"

        # 其他系统默认返回浅色（detected 保持 "light"）
        _write_cached_system_theme(detected)
        return detected

    @staticmethod
    def get_theme_stylesheet(theme_mode):
        """根据主题模式获取样式表
        参数:
            theme_mode: 'light', 'dark', 'auto'
        返回:
            样式表字符串
        """
        if theme_mode == "auto":
            # 自动模式：检测系统主题
            system_theme = ThemeManager.get_system_theme()
            return ThemeManager.DARK_THEME if system_theme == "dark" else ThemeManager.LIGHT_THEME
        elif theme_mode == "dark":
            return ThemeManager.DARK_THEME
        else:  # 'light' 或其他默认值
            return ThemeManager.LIGHT_THEME

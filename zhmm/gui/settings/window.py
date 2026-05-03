#!/usr/bin/env python3
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

import zhmm
from zhmm.config import saved_files as saved_files_store
from zhmm.config.constants import ZhmmFileInfo
from zhmm.gui.settings.backup_settings import BackupSettings
from zhmm.gui.settings.import_export_handlers import ImportExportHandlers
from zhmm.gui.settings.rekey_dialog import RekeyDialog
from zhmm.gui.settings.tag_management_dialog import TagManagementDialog
from zhmm.gui.texts import Account as AccountText
from zhmm.gui.texts import Rekey as RekeyText
from zhmm.gui.texts import Tags as TagsText
from zhmm.gui.texts import Tooltip
from zhmm.utils.log import logger

# 统一的按钮尺寸，避免大小不一造成视觉混乱
_BUTTON_MIN_WIDTH = 140
_BUTTON_MIN_HEIGHT = 32


class SettingWindow(QWidget):
    """设置界面组件"""

    imported_xlsx = pyqtSignal()  # 登录成功信号
    # 标签批量变更（重命名 / 删除）后发射，供主窗口刷新密码表与标签侧边栏。
    # 与 imported_xlsx 语义不同：数据结构未新增条目，仅某些条目的 tags 字段被修改。
    tags_changed = pyqtSignal()

    def __init__(self, info: ZhmmFileInfo, parent=None):
        super().__init__(parent)
        self.info = info

        # 初始化功能处理器
        self.import_export_handlers = ImportExportHandlers(self, info)

        self.setup_ui()

    def setup_ui(self):
        """初始化界面"""
        # 外层使用滚动区域，避免窗口较小时内容被压缩
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer_layout.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---------- 账户信息 ----------
        layout.addWidget(self._build_account_info_group())

        # ---------- 常规设置 ----------
        layout.addWidget(self._build_general_group())

        # ---------- 主密码 ----------
        layout.addWidget(self._build_master_password_group())

        # ---------- 数据备份 ----------
        layout.addWidget(self._build_backup_group())

        # ---------- 数据导入导出 ----------
        layout.addWidget(self._build_import_export_group())

        # ---------- 标签管理 ----------
        layout.addWidget(self._build_tag_management_group())

        layout.addStretch()

    # ------------------------------------------------------------------
    # 分组构建
    # ------------------------------------------------------------------
    def _build_account_info_group(self) -> QGroupBox:
        """账户信息：明文展示登录账号并提醒其参与加密。

        登录账号作为 KDF 输入一部分参与密钥派生，若用户遗忘将无法解密已有数据，
        因此需要在设置页持续可见地回显该账号，并附上牢记提示。

        布局采用 QGridLayout：第 0 行放「标签 + 只读输入框 + 复制按钮」，
        第 1 行让提醒文案从第 2 列（即输入框所在列）起跨列展示，这样提醒的
        左边缘会自动对齐到输入框左边缘，而非标签左边缘，视觉上更像是对
        「账号值」的补充说明。
        """
        group = QGroupBox(AccountText.GROUP_TITLE)
        grid = QGridLayout()
        grid.setContentsMargins(4, 8, 4, 8)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        # ---- 第 0 行：账号明文行 ----
        account_label = QLabel(AccountText.LABEL_ACCOUNT)
        self.account_display = QLineEdit(self.info.get("account", ""))
        self.account_display.setReadOnly(True)
        self.account_display.setCursorPosition(0)
        # 背景透明的展示式样式，但保留选中复制能力；
        # 显式设定 color 为 palette(text)，避免深色主题下回退黑色导致看不清
        self.account_display.setStyleSheet(
            "QLineEdit { background: transparent; color: palette(text);"
            " border: 1px solid palette(mid); border-radius: 4px; padding: 4px 6px; }"
        )

        copy_btn = QPushButton(AccountText.BTN_COPY)
        copy_btn.setMinimumHeight(_BUTTON_MIN_HEIGHT)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.clicked.connect(self._copy_account)

        grid.addWidget(account_label, 0, 0)
        grid.addWidget(self.account_display, 0, 1)
        grid.addWidget(copy_btn, 0, 2)

        # ---- 第 1 行：提醒文案，从第 2 列起跨到末列，左边缘对齐输入框 ----
        hint = QLabel(AccountText.HINT)
        hint.setWordWrap(True)
        # 用 placeholder-text 角色（专为「淡化提示文字」设计），在深/浅色主题下都能区分于正文
        hint.setStyleSheet("color: palette(placeholder-text); font-size: 12px;")
        grid.addWidget(hint, 1, 1, 1, 2)

        # 让输入框所在列吸收多余宽度，标签列与按钮列保持内容宽度
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)

        group.setLayout(grid)
        return group

    def _copy_account(self) -> None:
        """复制登录账号到剪贴板，10 秒后自动清空。"""
        account = self.info.get("account", "")
        if not account:
            return
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return
        clipboard.setText(str(account))
        QToolTip.showText(QCursor.pos(), Tooltip.ACCOUNT_COPIED, self)
        QTimer.singleShot(10000, lambda: QApplication.clipboard().clear() if QApplication.clipboard() else None)

    def _build_general_group(self) -> QGroupBox:
        """常规设置：自动锁定时间 + 主题"""
        group = QGroupBox("常规")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        # 自动锁定时间
        self.lock_time_spinbox = QSpinBox()
        self.lock_time_spinbox.setRange(1, 60)
        self.lock_time_spinbox.setValue(zhmm.config.get_lock_time())
        self.lock_time_spinbox.setSuffix(" 分钟")
        self.lock_time_spinbox.setFixedWidth(120)
        self.lock_time_spinbox.valueChanged.connect(zhmm.config.save_lock_time)
        form.addRow("自动锁定时间：", self.lock_time_spinbox)

        # 主题
        self.theme_button_group = QButtonGroup(self)
        self.light_theme_radio = QRadioButton("浅色")
        self.dark_theme_radio = QRadioButton("深色")
        self.auto_theme_radio = QRadioButton("跟随系统")
        for btn in (self.light_theme_radio, self.dark_theme_radio, self.auto_theme_radio):
            self.theme_button_group.addButton(btn)

        theme_row = QHBoxLayout()
        theme_row.setSpacing(16)
        theme_row.addWidget(self.light_theme_radio)
        theme_row.addWidget(self.dark_theme_radio)
        theme_row.addWidget(self.auto_theme_radio)
        theme_row.addStretch()
        theme_row_widget = QWidget()
        theme_row_widget.setLayout(theme_row)
        form.addRow("主题：", theme_row_widget)

        # 加载当前主题
        current_theme = zhmm.config.get_theme()
        if current_theme == "dark":
            self.dark_theme_radio.setChecked(True)
        elif current_theme == "auto":
            self.auto_theme_radio.setChecked(True)
        else:
            self.light_theme_radio.setChecked(True)
        self.theme_button_group.buttonClicked.connect(self.on_theme_changed)

        # 防截屏开关
        self.anti_screenshot_checkbox = QCheckBox("开启防截屏（阻止录屏/截图工具抓取窗口内容）")
        self.anti_screenshot_checkbox.setChecked(zhmm.config.get_anti_screenshot())
        self.anti_screenshot_checkbox.toggled.connect(self.on_anti_screenshot_toggled)
        form.addRow("防截屏：", self.anti_screenshot_checkbox)

        # 密码明文显示时长
        self.reveal_duration_spinbox = QSpinBox()
        self.reveal_duration_spinbox.setRange(3, 120)
        self.reveal_duration_spinbox.setValue(zhmm.config.get_password_reveal_duration())
        self.reveal_duration_spinbox.setSuffix(" 秒")
        self.reveal_duration_spinbox.setFixedWidth(120)
        self.reveal_duration_spinbox.setToolTip("点击表格中的 👁 按钮显示密码后，到达该时长将自动隐藏")
        self.reveal_duration_spinbox.valueChanged.connect(zhmm.config.save_password_reveal_duration)
        form.addRow("密码明文显示时长：", self.reveal_duration_spinbox)

        group.setLayout(form)
        return group

    def _build_backup_group(self) -> QGroupBox:
        """数据备份组"""
        group = QGroupBox("数据备份")
        v = QVBoxLayout()
        v.setContentsMargins(4, 8, 4, 8)
        self.backup_settings_widget = BackupSettings(self.info, self)
        v.addWidget(self.backup_settings_widget)
        group.setLayout(v)
        return group

    def _build_master_password_group(self) -> QGroupBox:
        """主密码分组：更换主密码按钮。"""
        group = QGroupBox("主密码")
        v = QHBoxLayout()
        v.setContentsMargins(4, 8, 4, 8)
        v.setSpacing(10)
        self.rekey_button = self._make_button(RekeyText.TITLE, self.open_rekey_dialog)
        v.addWidget(self.rekey_button)
        v.addStretch()
        group.setLayout(v)
        return group

    def _build_tag_management_group(self) -> QGroupBox:
        """标签管理分组：入口按钮打开 TagManagementDialog。

        标签数据是 PasswordEntry.tags 的并集，没有独立存储，批量重命名 / 删除
        统一走 SmData.rename_tag / delete_tag 并立即落盘。
        """
        group = QGroupBox(TagsText.GROUP_TITLE)
        v = QHBoxLayout()
        v.setContentsMargins(4, 8, 4, 8)
        v.setSpacing(10)
        self.tag_manage_button = self._make_button(TagsText.BTN_OPEN, self.open_tag_management_dialog)
        v.addWidget(self.tag_manage_button)
        v.addStretch()
        group.setLayout(v)
        return group

    def _build_import_export_group(self) -> QGroupBox:
        """数据导入导出组：按钮采用网格布局，等宽整齐"""
        group = QGroupBox("数据导入导出")
        grid = QGridLayout()
        grid.setContentsMargins(4, 8, 4, 8)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        self.import_xlsx_button = self._make_button("导入 xlsx 文件", self.import_xlsx)
        self.download_xlsx_button = self._make_button("下载 xlsx 模版", self.download_xlsx_template)
        self.export_button = self._make_button("导出 xlsx 文件", self.export_passwords)

        grid.addWidget(self.import_xlsx_button, 0, 0)
        grid.addWidget(self.download_xlsx_button, 0, 1)
        grid.addWidget(self.export_button, 0, 2)
        grid.setColumnStretch(3, 1)  # 右侧留白

        group.setLayout(grid)
        return group

    @staticmethod
    def _make_button(text: str, slot) -> QPushButton:
        """创建统一尺寸的按钮"""
        btn = QPushButton(text)
        btn.setMinimumWidth(_BUTTON_MIN_WIDTH)
        btn.setMinimumHeight(_BUTTON_MIN_HEIGHT)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(slot)
        return btn

    # ------------------------------------------------------------------
    # 事件处理
    # ------------------------------------------------------------------
    def export_passwords(self):
        """导出密码列表"""
        self.import_export_handlers.export_passwords()

    def import_xlsx(self):
        """导入xlsx文件"""

        def on_success():
            # 发送信号通知界面刷新
            self.imported_xlsx.emit()

        self.import_export_handlers.import_xlsx(on_success)

    def download_xlsx_template(self):
        """下载xlsx模版文件"""
        self.import_export_handlers.download_xlsx_template()

    def on_theme_changed(self, button):
        """主题切换事件处理"""
        from PyQt6.QtWidgets import QApplication

        from zhmm.gui.theme import ThemeManager

        # 确定选择的主题
        if button == self.light_theme_radio:
            theme = "light"
        elif button == self.dark_theme_radio:
            theme = "dark"
        elif button == self.auto_theme_radio:
            theme = "auto"
        else:
            return

        # 保存主题设置
        zhmm.config.save_theme(theme)

        # 应用主题
        app_instance = QApplication.instance()
        if app_instance and isinstance(app_instance, QApplication):
            stylesheet = ThemeManager.get_theme_stylesheet(theme)
            app_instance.setStyleSheet(stylesheet)

    def on_anti_screenshot_toggled(self, checked: bool) -> None:
        """防截屏开关切换：持久化 + 实时对顶层窗口生效。"""
        from zhmm.utils.anti_capture import apply_anti_capture

        zhmm.config.save_anti_screenshot(checked)
        top = self.window()
        if top is not None:
            apply_anti_capture(top, enabled=checked)

    # ------------------------------------------------------------------
    # 更换主密码
    # ------------------------------------------------------------------
    def open_rekey_dialog(self) -> None:
        """打开「更换主密码」对话框；成功后同步会话与本地配置。"""
        dlg = RekeyDialog(self.info, parent=self)
        dlg.finished_ok.connect(self._on_rekey_success)
        dlg.exec()

    # ------------------------------------------------------------------
    # 标签管理
    # ------------------------------------------------------------------
    def open_tag_management_dialog(self) -> None:
        """打开「标签管理」对话框；若有变更，通知主窗口刷新 UI。"""
        from PyQt6.QtWidgets import QMessageBox

        sm_data = self.info.get("sm_data")
        if not sm_data:
            QMessageBox.warning(self, TagsText.TITLE, "数据管理器未初始化")
            return
        dlg = TagManagementDialog(sm_data, parent=self)
        dlg.exec()
        if dlg.has_changes():
            self.tags_changed.emit()

    def _on_rekey_success(self, new_password: str, backup_path: str) -> None:
        """Re-key 成功后的后续操作：

        1) 会话 hashpw 更新为新密码的 bcrypt 哈希；
        2) saved_files 索引中的 hashpw 写回磁盘（后续自动登录才会用新密码）；
        3) AppConfig 用新密码重新派生 Fernet 密钥并落盘，
           避免下次启动时配置文件解密失败。
        """
        import bcrypt
        from PyQt6.QtWidgets import QMessageBox

        # 1) 更新会话 hashpw
        new_hashpw = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode("utf-8")
        self.info["hashpw"] = new_hashpw

        # 2) 更新 saved_files——仅覆盖 hashpw 字段，其他元数据保持
        file_path = self.info.get("file_path") or ""
        if file_path:
            try:
                saved_files_store.update_entry(file_path, {"hashpw": new_hashpw})
            except Exception as e:  # noqa: BLE001
                logger.warning(f"saved_files hashpw 同步失败: {e}")

        # 3) 更新 AppConfig 的 Fernet 密钥并落盘
        config_synced = True
        try:
            if zhmm.config is not None and zhmm.config.setting is not None:
                zhmm.config.my_encryption_key = zhmm.config.setting.generate_key_from_string(new_password)
                zhmm.config.save_config()
        except Exception as e:  # noqa: BLE001
            config_synced = False
            logger.warning(f"AppConfig 同步失败: {e}")

        # 4) 提示用户
        msg = RekeyText.success_message(backup_path) if backup_path else "主密码已更新。"
        if not config_synced:
            msg = f"{msg}\n\n{RekeyText.FAIL_CONFIG_SYNC}"
        QMessageBox.information(self, RekeyText.SUCCESS_TITLE, msg)

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from zhmm.core import totp as totp_mod
from zhmm.core.errors import ValidationError
from zhmm.gui.password.add_role_dialog import AddRoleDialog
from zhmm.gui.password.random_dialog import RandomPasswordDialog
from zhmm.utils import date_util
from zhmm.utils.log import logger
from zhmm.widgets.combo_box import WideComboBox
from zhmm.widgets.strength_bar import PasswordStrengthBar
from zhmm.widgets.tag_editor import TagEditor, TagPickerDialog


class AddPasswordDialog(QDialog):
    """添加密码对话框"""

    added_role = pyqtSignal(str)  # 增加角色信息

    def __init__(self, parent, roles: list[str], edit_data=None, all_tags: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("添加账号密码")
        # 宽度固定，高度随 TOTP 折叠状态自适应（给一个初始高度方便首屏呈现）
        self.setFixedWidth(640)
        self.resize(640, 640)

        self.roles = roles
        self._all_tags: list[str] = list(all_tags or [])
        self._preview_timer: QTimer | None = None

        # 创建布局
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 20, 30, 20)  # 增加外间距
        layout.setSpacing(15)  # 统一控件间距

        # 标题标签
        title_label = QLabel("请输入账号密码信息")
        title_label.setObjectName("title_label")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFixedHeight(40)
        layout.addWidget(title_label)

        # 创建表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(12)  # 表单控件间距
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        # 类别选择
        self.role_combo = WideComboBox()
        self.role_combo.setFixedHeight(36)  # 增加控件高度
        self.role_combo.setEditable(True)
        self.role_combo.addItems(self.roles)

        # 添加新建类别按钮
        add_role_btn = QPushButton("+")
        add_role_btn.setObjectName("add_role_btn")
        add_role_btn.setFixedSize(36, 36)
        add_role_btn.clicked.connect(self._add_custom_role)

        role_layout = QHBoxLayout()
        role_layout.setSpacing(8)
        role_layout.addWidget(self.role_combo)
        role_layout.addWidget(add_role_btn)
        form_layout.addRow("类别:", role_layout)

        # 账号输入
        self.userid_input = QLineEdit()
        self.userid_input.setMinimumWidth(300)
        self.userid_input.setFixedHeight(30)
        self.userid_input.setPlaceholderText("请输入账号")
        form_layout.addRow("账号:", self.userid_input)

        # 密码输入
        self.password_input = QLineEdit()
        self.password_input.setMinimumWidth(300)
        self.password_input.setFixedHeight(30)
        self.password_input.setPlaceholderText("请输入密码")

        # 添加随机密码按钮
        self.random_pwd_btn = QPushButton("随机密码")
        self.random_pwd_btn.setFixedHeight(30)
        self.random_pwd_btn.clicked.connect(self.show_random_pwd_dialog)

        # 将输入框和按钮放入水平布局
        pwd_layout = QHBoxLayout()
        pwd_layout.addWidget(self.password_input, stretch=4)
        pwd_layout.addWidget(self.random_pwd_btn, stretch=1)

        form_layout.addRow("密码:", pwd_layout)

        # 密码强度条：实时评估 password_input 内容
        self.password_strength_bar = PasswordStrengthBar()
        self.password_input.textChanged.connect(self.password_strength_bar.set_password)
        form_layout.addRow("", self.password_strength_bar)

        # 手机输入
        self.phone_input = QLineEdit()
        self.phone_input.setMinimumWidth(300)
        self.phone_input.setFixedHeight(30)
        self.phone_input.setPlaceholderText("请输入手机号码（可选）")
        form_layout.addRow("手机:", self.phone_input)

        # 邮箱输入
        self.email_input = QLineEdit()
        self.email_input.setMinimumWidth(300)
        self.email_input.setFixedHeight(36)
        self.email_input.setPlaceholderText("请输入邮箱（可选）")
        form_layout.addRow("邮箱:", self.email_input)

        # 网站输入
        self.url_input = QLineEdit()
        self.url_input.setMinimumWidth(300)
        self.url_input.setFixedHeight(30)
        self.url_input.setPlaceholderText("请输入网站地址（可选）")
        form_layout.addRow("网站:", self.url_input)

        # 备注输入
        self.desc_input = QTextEdit()
        self.desc_input.setMinimumWidth(300)
        self.desc_input.setMinimumHeight(120)  # 优化备注框高度
        self.desc_input.setPlaceholderText("请输入备注信息（可选）")
        self.desc_input.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        form_layout.addRow("备注:", self.desc_input)

        # 标签输入（Chip 可视化）+ 「选择…」按钮：从已有标签中批量勾选追加
        self.tag_editor = TagEditor(all_tags=self._all_tags)
        self.tag_editor.setMinimumWidth(300)

        self.tag_pick_btn = QPushButton("选择…")
        self.tag_pick_btn.setObjectName("tag_pick_btn")
        self.tag_pick_btn.setFixedHeight(30)
        self.tag_pick_btn.setToolTip("从当前库已有标签中批量勾选")
        self.tag_pick_btn.clicked.connect(self._open_tag_picker)

        tag_row = QHBoxLayout()
        tag_row.setSpacing(8)
        tag_row.addWidget(self.tag_editor, 1)
        tag_row.addWidget(self.tag_pick_btn)
        form_layout.addRow("标签:", tag_row)

        layout.addLayout(form_layout)

        # TOTP 区域
        self._setup_totp_group(layout)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 确认按钮
        self.confirm_button = QPushButton("确认添加")
        self.confirm_button.setObjectName("confirm_button")
        self.confirm_button.setFixedSize(100, 36)
        button_layout.addWidget(self.confirm_button)

        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.setObjectName("cancel_button")
        cancel_button.setFixedSize(100, 36)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # 如果是编辑模式，填充数据
        if edit_data:
            self._populate_data(edit_data)

    def _add_custom_role(self):
        """打开自绘「新建类别」对话框，确认后将新类别加入下拉。

        对话框内部已做空值 / 重复校验（大小写不敏感），结果回来一定是合法的新类别。
        下拉去重仍以 roles 列表原始值为准。
        """
        dialog = AddRoleDialog(self, self.roles)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        new_role = dialog.role_value()
        if not new_role:
            return
        self.added_role.emit(new_role)
        self.role_combo.addItem(new_role)
        # 新增后自动选中，减少一次手动点击
        idx = self.role_combo.findText(new_role)
        if idx >= 0:
            self.role_combo.setCurrentIndex(idx)

    def _open_tag_picker(self) -> None:
        """弹出「选择标签」对话框，确认后把新勾选的标签追加到编辑器。

        all_tags 优先使用宿主传入的全库标签（频次倒序）；当前编辑框内
        已有的标签会被对话框自动合并到列表中（置灰），保证视觉上“看得到”。
        """
        dlg = TagPickerDialog(
            all_tags=self._all_tags,
            current=self.tag_editor.tags(),
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        picked = dlg.selected_tags()
        if picked:
            self.tag_editor.add_tags(picked)

    def _populate_data(self, data):
        """填充编辑数据"""
        index = self.role_combo.findText(data["role"])
        if index >= 0:
            self.role_combo.setCurrentIndex(index)
        self.userid_input.setText(data["userID"])
        self.password_input.setText(data["pwd"])
        self.phone_input.setText(data.get("phone", ""))
        self.email_input.setText(data.get("email", ""))
        self.url_input.setText(data.get("url", ""))
        self.desc_input.setText(data.get("desc", ""))
        # 标签回填
        self.tag_editor.set_tags(data.get("tags") or [])
        # TOTP 回填：已有 secret 才勾选并展开折叠区
        existing_secret = (data.get("totp_secret") or "").strip()
        self.totp_secret_input.setText(existing_secret)
        algo = (data.get("totp_algo") or "").upper()
        if algo:
            idx = self.totp_algo_combo.findText(algo)
            if idx >= 0:
                self.totp_algo_combo.setCurrentIndex(idx)
        digits = data.get("totp_digits") or totp_mod.DEFAULT_DIGITS
        period = data.get("totp_period") or totp_mod.DEFAULT_PERIOD
        try:
            self.totp_digits_spin.setValue(int(digits))
            self.totp_period_spin.setValue(int(period))
        except (TypeError, ValueError):
            pass
        if existing_secret:
            self.totp_group.setChecked(True)
        self._refresh_totp_preview()

    def show_random_pwd_dialog(self):
        """显示随机密码生成对话框"""
        dialog = RandomPasswordDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.password_input.setText(dialog.get_password())

    def get_password_data(self):
        """获取表单数据"""
        # 未勾选 TOTP 折叠区时，强制视为未启用，丢弃任何残留输入
        totp_enabled = self.totp_group.isChecked()
        secret = self.totp_secret_input.text().strip() if totp_enabled else ""
        algo = self.totp_algo_combo.currentText().strip().upper() if secret else ""
        digits = int(self.totp_digits_spin.value()) if secret else totp_mod.DEFAULT_DIGITS
        period = int(self.totp_period_spin.value()) if secret else totp_mod.DEFAULT_PERIOD
        return {
            "id": date_util.timestamp_int(),
            "role": self.role_combo.currentText(),
            "userID": self.userid_input.text().strip(),
            "pwd": self.password_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "email": self.email_input.text().strip(),
            "url": self.url_input.text().strip(),
            "desc": self.desc_input.toPlainText().strip(),
            "utime": date_util.timestamp_int(),
            "totp_secret": secret,
            "totp_algo": algo,
            "totp_digits": digits,
            "totp_period": period,
            "tags": self.tag_editor.tags(),
        }

    # ------------------------------------------------------------------
    # TOTP 区域
    # ------------------------------------------------------------------
    def _setup_totp_group(self, layout: QVBoxLayout) -> None:
        """在对话框下方插入可选的 TOTP 配置区。

        设计：默认未启用 = 仅展示一个单独的勾选框，
        不在下方留任何空的“内容框”（此前用 QGroupBox+setCheckable
        会残留边框和 padding）。勾选后再展开 secret / 参数 / 预览。
        """
        self.totp_checkbox = QCheckBox("启用二次验证 TOTP")
        self.totp_checkbox.setChecked(False)
        # 保留 totp_group 别名以兼容可能的外部引用，且让现有
        # self.totp_group.isChecked() 等调用无需更改
        self.totp_group = self.totp_checkbox

        # 将所有表单控件放进 inner widget，默认隐藏
        inner = QWidget()
        self._totp_inner = inner
        g_layout = QFormLayout()
        g_layout.setContentsMargins(18, 8, 0, 0)  # 左边略缩进，视觉上隐含属于上方勾选框
        g_layout.setSpacing(10)

        self.totp_secret_input = QLineEdit()
        self.totp_secret_input.setPlaceholderText("粘贴 Base32 secret 或 otpauth:// URI")
        self.totp_secret_input.textChanged.connect(self._on_totp_secret_changed)
        g_layout.addRow("Secret:", self.totp_secret_input)

        algo_row = QHBoxLayout()
        self.totp_algo_combo = QComboBox()
        self.totp_algo_combo.addItems(list(totp_mod.SUPPORTED_ALGOS))
        self.totp_algo_combo.setCurrentText(totp_mod.DEFAULT_ALGO)
        self.totp_algo_combo.currentIndexChanged.connect(self._refresh_totp_preview)
        self.totp_digits_spin = QSpinBox()
        self.totp_digits_spin.setRange(6, 10)
        self.totp_digits_spin.setValue(totp_mod.DEFAULT_DIGITS)
        self.totp_digits_spin.valueChanged.connect(self._refresh_totp_preview)
        self.totp_period_spin = QSpinBox()
        self.totp_period_spin.setRange(15, 300)
        self.totp_period_spin.setValue(totp_mod.DEFAULT_PERIOD)
        self.totp_period_spin.setSuffix(" s")
        self.totp_period_spin.valueChanged.connect(self._refresh_totp_preview)
        algo_row.addWidget(QLabel("算法:"))
        algo_row.addWidget(self.totp_algo_combo)
        algo_row.addSpacing(12)
        algo_row.addWidget(QLabel("位数:"))
        algo_row.addWidget(self.totp_digits_spin)
        algo_row.addSpacing(12)
        algo_row.addWidget(QLabel("周期:"))
        algo_row.addWidget(self.totp_period_spin)
        algo_row.addStretch(1)
        g_layout.addRow("参数:", algo_row)

        self.totp_preview_label = QLabel("—")
        self.totp_preview_label.setStyleSheet("font-family: Menlo, monospace; font-size: 16px; font-weight: bold;")
        g_layout.addRow("预览:", self.totp_preview_label)

        inner.setLayout(g_layout)
        inner.setVisible(False)  # 默认折叠

        # 直接将勾选框 + inner 交给外层 layout，不再套 QGroupBox
        layout.addWidget(self.totp_checkbox)
        layout.addWidget(inner)

        # 勾选/取消勾选时切换内部可见性
        self.totp_checkbox.toggled.connect(self._on_totp_group_toggled)

        # 1 秒刷新预览（仅在展开时才有意义；_refresh_totp_preview 内部会判断）
        self._preview_timer = QTimer(self)
        self._preview_timer.setInterval(1000)
        self._preview_timer.timeout.connect(self._refresh_totp_preview)
        self._preview_timer.start()
        # 初次绘制
        self._refresh_totp_preview()

    def _on_totp_group_toggled(self, checked: bool) -> None:
        """勾选框 toggled：展开/折叠内部控件。"""
        if hasattr(self, "_totp_inner"):
            self._totp_inner.setVisible(checked)
        if checked:
            self._refresh_totp_preview()
        # 让对话框按需重新计算布局尺寸
        self.adjustSize()

    def _on_totp_secret_changed(self, text: str) -> None:
        """检测到 otpauth:// URI 时自动解析并回填各字段。"""
        s = text.strip()
        if s.lower().startswith("otpauth://"):
            try:
                params = totp_mod.parse_otpauth_uri(s)
            except ValidationError as ex:
                logger.debug(f"otpauth 解析失败: {ex}")
                self._refresh_totp_preview()
                return
            # 回填：避免触发 textChanged 递归，先 block
            self.totp_secret_input.blockSignals(True)
            try:
                self.totp_secret_input.setText(params.get("secret", ""))
            finally:
                self.totp_secret_input.blockSignals(False)
            algo = params.get("algo") or totp_mod.DEFAULT_ALGO
            idx = self.totp_algo_combo.findText(algo)
            if idx >= 0:
                self.totp_algo_combo.setCurrentIndex(idx)
            self.totp_digits_spin.setValue(int(params.get("digits") or totp_mod.DEFAULT_DIGITS))
            self.totp_period_spin.setValue(int(params.get("period") or totp_mod.DEFAULT_PERIOD))
        self._refresh_totp_preview()

    def _refresh_totp_preview(self) -> None:
        """根据当前表单值实时刷新预览文案。"""
        if not hasattr(self, "totp_preview_label"):
            return
        # 折叠状态下无需计算，直接跳过
        if hasattr(self, "totp_group") and not self.totp_group.isChecked():
            return
        secret = self.totp_secret_input.text().strip()
        if not secret:
            self.totp_preview_label.setText("—")
            self.totp_preview_label.setStyleSheet(
                "font-family: Menlo, monospace; font-size: 16px; font-weight: bold; color: #888;"
            )
            return
        algo = self.totp_algo_combo.currentText().strip().upper() or totp_mod.DEFAULT_ALGO
        digits = int(self.totp_digits_spin.value())
        period = int(self.totp_period_spin.value())
        try:
            code = totp_mod.generate(secret, algo=algo, digits=digits, period=period)
            left = totp_mod.remaining_seconds(period)
            self.totp_preview_label.setText(f"{code}    剩余 {left}s")
            self.totp_preview_label.setStyleSheet(
                "font-family: Menlo, monospace; font-size: 16px; font-weight: bold; color: #2e7d32;"
            )
        except ValidationError as ex:
            self.totp_preview_label.setText(f"⚠️ {ex}")
            self.totp_preview_label.setStyleSheet("font-family: Menlo, monospace; font-size: 13px; color: #c62828;")

    def closeEvent(self, event):  # type: ignore[override]
        if self._preview_timer is not None:
            self._preview_timer.stop()
        super().closeEvent(event)

"""标签 Chip 编辑器 widget。

一个紧凑的「chip + 尾部输入框」组合控件，用于编辑 `PasswordEntry.tags`。

交互约定：
- 回车 / 空格 / 分号 提交当前输入为一个新 chip
- 输入框为空时 Backspace 删除最后一个 chip
- 失焦不自动提交（避免误入空白）
- 下拉联想来自宿主提供的 `all_tags`（QCompleter）
- 归一化、去重、长度截断统一走 :func:`zhmm.core.models.normalize_tags`

接入：

```python
from zhmm.widgets.tag_editor import TagEditor

editor = TagEditor(all_tags=self._collect_all_tags())
editor.set_tags(entry.get("tags") or [])
layout.addRow("标签:", editor)
...
entry["tags"] = editor.tags()
```

样式通过代码内联 QSS 控制 chip 外观，不依赖全局主题文件。颜色取自项目
现有蓝色系（与 add_role_btn 等控件同族），在深色 / 浅色背景下都能读清。
"""

from __future__ import annotations

from PyQt6.QtCore import QStringListModel, Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from zhmm.core.models import TAG_MAX_LEN, TAGS_MAX_COUNT, normalize_tags


class TagChip(QFrame):
    """单个 chip：文本 + 删除按钮。

    以 `removed(str)` 信号对外通知删除意图，宿主负责实际从列表移除。
    """

    removed = pyqtSignal(str)

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = text
        self.setObjectName("tag_chip")
        # 外观：浅蓝底 + 深蓝字，圆角 pill
        self.setStyleSheet(
            "QFrame#tag_chip {"
            "  background: #e3f2fd;"
            "  border: 1px solid #90caf9;"
            "  border-radius: 11px;"
            "}"
            "QLabel#tag_chip_label { color: #0d47a1; padding: 0 2px; }"
            "QPushButton#tag_chip_x {"
            "  background: transparent;"
            "  border: none;"
            "  color: #546e7a;"
            "  font-weight: bold;"
            "  padding: 0;"
            "}"
            "QPushButton#tag_chip_x:hover { color: #c62828; }"
        )
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 4, 2)
        layout.setSpacing(4)

        label = QLabel(f"#{text}")
        label.setObjectName("tag_chip_label")
        layout.addWidget(label)

        btn = QPushButton("×")
        btn.setObjectName("tag_chip_x")
        btn.setFixedSize(16, 16)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip("移除该标签")
        btn.clicked.connect(self._emit_removed)
        layout.addWidget(btn)

    def text(self) -> str:
        return self._text

    def _emit_removed(self) -> None:
        self.removed.emit(self._text)


class _TagLineEdit(QLineEdit):
    """捕获 Backspace/Enter/分号 的专用 QLineEdit。

    将按键意图以信号形式暴露给上层 `TagEditor`，保持职责清晰。
    """

    commit_requested = pyqtSignal()
    backspace_on_empty = pyqtSignal()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (Qt 签名)
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # 回车仅用于提交 chip，不应让对话框 accept
            self.commit_requested.emit()
            event.accept()
            return
        if key == Qt.Key.Key_Backspace and not self.text():
            self.backspace_on_empty.emit()
            event.accept()
            return
        # 分号当作分隔符：逐段提交
        if event.text() == ";":
            self.commit_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class TagEditor(QWidget):
    """标签 chip 编辑器。

    - `tags() -> list[str]` 获取当前标签列表（已归一化）
    - `set_tags(list[str])` 重置标签
    - `set_suggestions(list[str])` 更新联想源
    - 输入空格或分号或回车 → 提交当前输入为新 chip
    """

    tags_changed = pyqtSignal(list)

    def __init__(self, all_tags: list[str] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tags: list[str] = []
        self._chips: list[TagChip] = []

        self.setMinimumHeight(36)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(4, 2, 4, 2)
        self._layout.setSpacing(4)

        self._input = _TagLineEdit()
        self._input.setPlaceholderText("输入标签后按回车/空格/分号添加")
        self._input.setFrame(False)
        self._input.setMaxLength(TAG_MAX_LEN)
        self._input.setMinimumWidth(120)
        self._input.textChanged.connect(self._on_text_changed)
        self._input.commit_requested.connect(self._commit_current)
        self._input.backspace_on_empty.connect(self._pop_last)
        self._layout.addWidget(self._input, 1)

        # QCompleter 提供联想（显式 QStringListModel，避免隐式模型不可变）
        self._suggestion_model = QStringListModel([], self)
        self._completer = QCompleter(self)
        self._completer.setModel(self._suggestion_model)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.activated.connect(self._on_completer_activated)
        self._input.setCompleter(self._completer)

        self.set_suggestions(all_tags or [])

    # ------------------------------------------------------------------
    # 对外 API
    # ------------------------------------------------------------------
    def tags(self) -> list[str]:
        """返回当前标签（不含输入框里未提交的半成品）。"""
        return list(self._tags)

    def set_tags(self, tags: list[str] | None) -> None:
        """重置标签列表（自动归一化）。"""
        self._clear_chips()
        for t in normalize_tags(tags):
            self._append_tag(t, silent=True)
        self.tags_changed.emit(self.tags())

    def set_suggestions(self, all_tags: list[str]) -> None:
        """更新联想源；当前已选标签会从建议中剔除。"""
        self._all_tags = list(normalize_tags(all_tags))
        self._refresh_completer_model()

    def add_tags(self, tags: list[str] | None) -> None:
        """批量追加标签（供「选择…」对话框等外部批量源调用）。

        - 重复 / 超空 / 超长 / 超上限的项目由 `normalize_tags` 与 `_append_tag` 静默处理。
        - 统一以一次 `tags_changed` 信号告知外部（而不是逐条），避免下游重复刷新。
        """
        cleaned = normalize_tags(tags)
        if not cleaned:
            return
        before = list(self._tags)
        for t in cleaned:
            self._append_tag(t, silent=True)
        if self._tags != before:
            self.tags_changed.emit(self.tags())

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    def _on_text_changed(self, text: str) -> None:
        # 用户把分隔符粘进来：按 ; 或空格拆分并提交全部
        if any(sep in text for sep in (";", " ")):
            parts = [p for p in text.replace(";", " ").split(" ") if p]
            # 最后一段保留在输入框里（可能还没敲完），其余全部提交
            if text.endswith(" ") or text.endswith(";"):
                commit_parts = parts
                remainder = ""
            else:
                commit_parts = parts[:-1]
                remainder = parts[-1] if parts else ""
            if commit_parts:
                for p in commit_parts:
                    self._append_tag(p)
            # 避免递归调用
            self._input.blockSignals(True)
            self._input.setText(remainder)
            self._input.blockSignals(False)

    def _commit_current(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._append_tag(text)
        self._input.clear()

    def _pop_last(self) -> None:
        if not self._tags:
            return
        last = self._tags[-1]
        self._remove_tag(last)

    def _append_tag(self, raw: str, silent: bool = False) -> None:
        cleaned = normalize_tags([raw])
        if not cleaned:
            return
        tag = cleaned[0]
        if tag in self._tags:
            return
        if len(self._tags) >= TAGS_MAX_COUNT:
            return
        self._tags.append(tag)
        chip = TagChip(tag, self)
        chip.removed.connect(self._remove_tag)
        self._chips.append(chip)
        # 插到输入框前面
        self._layout.insertWidget(self._layout.count() - 1, chip)
        self._refresh_completer_model()
        if not silent:
            self.tags_changed.emit(self.tags())

    def _remove_tag(self, tag: str) -> None:
        if tag not in self._tags:
            return
        idx = self._tags.index(tag)
        self._tags.pop(idx)
        chip = self._chips.pop(idx)
        self._layout.removeWidget(chip)
        chip.setParent(None)
        chip.deleteLater()
        self._refresh_completer_model()
        self.tags_changed.emit(self.tags())

    def _clear_chips(self) -> None:
        while self._chips:
            chip = self._chips.pop()
            self._layout.removeWidget(chip)
            chip.setParent(None)
            chip.deleteLater()
        self._tags.clear()

    def _refresh_completer_model(self) -> None:
        remaining = [t for t in self._all_tags if t not in self._tags]
        self._suggestion_model.setStringList(remaining)

    def _on_completer_activated(self, text: str) -> None:
        if not text:
            return
        self._append_tag(text)
        # QCompleter 会把选中文本塞回输入框，清掉防止重复提交
        self._input.blockSignals(True)
        self._input.clear()
        self._input.blockSignals(False)


class RowToggleListWidget(QListWidget):
    """点击整行即切换勾选状态的 QListWidget。

    默认 QListWidget 仅在点击复选框图标时切换勾选，行其他区域只触发
    itemClicked。此处通过重写 mousePressEvent 统一接管：无论点击行内
    的哪个位置（包括复选框），都切换一次勾选，避免「点击复选框翻一次、
    再由信号翻一次」的双重切换问题。

    被禁用的 item（置灰的已绑定标签）跳过，不响应点击。

    通用组件：供任意需要「点整行切换 check 态」的场景复用（标签选择弹窗、
    标签筛选侧边栏等）。
    """

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt 签名)
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if item is not None:
                flags = item.flags()
                if (flags & Qt.ItemFlag.ItemIsEnabled) and (flags & Qt.ItemFlag.ItemIsUserCheckable):
                    new_state = (
                        Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked
                    )
                    item.setCheckState(new_state)
                    event.accept()
                    return
        super().mousePressEvent(event)


class TagPickerDialog(QDialog):
    """从当前库已有标签中批量勾选的模态对话框。

    使用场景：编辑密码条目时，点击「选择…」按钮弹出本对话框，
    列出库中全部标签供勾选，确认后由宿主把新勾选的标签追加到 `TagEditor` 里。

    设计要点：
    - 已在编辑器中存在的标签默认勾选并置灰：给用户反馈「这些已绑定」，
      避免误以为可以把它们取消。取消勾选不会删除已有标签（宿主仅追加，不替换）。
    - 顶部提供「全选 / 全清」快捷，适合标签不多的库快速批量选择。
    - 空库时显示占位文案，而不是一个空列表。
    """

    def __init__(
        self,
        all_tags: list[str] | None,
        current: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("选择标签")
        self.setModal(True)
        self.resize(320, 360)

        self._current = set(normalize_tags(current))
        ordered = normalize_tags(all_tags)
        # 确保当前已有标签也出现在列表里（即使本轮还未被归入 all_tags）
        for t in self._current:
            if t not in ordered:
                ordered.append(t)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        tip = QLabel("勾选要追加的标签，已绑定的默认置灰且不可取消。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #666;")
        root.addWidget(tip)

        # 顶部快捷：全选 / 全清
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self._btn_select_all = QPushButton("全选")
        self._btn_select_all.setFlat(True)
        self._btn_select_all.clicked.connect(self._select_all)
        self._btn_clear_all = QPushButton("全清")
        self._btn_clear_all.setFlat(True)
        self._btn_clear_all.clicked.connect(self._clear_all)
        toolbar.addWidget(self._btn_select_all)
        toolbar.addWidget(self._btn_clear_all)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        self._list = RowToggleListWidget()
        self._list.setObjectName("tag_picker_list")
        self._list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._list.setCursor(Qt.CursorShape.PointingHandCursor)
        # 具体颜色（边框 / 背景 / hover / 置灰）由主题统一定义，避免硬编码导致深色失配
        self._list.setToolTip("点击任意位置切换勾选")
        root.addWidget(self._list, 1)

        if ordered:
            for tag in ordered:
                item = QListWidgetItem(f"#{tag}")
                item.setData(Qt.ItemDataRole.UserRole, tag)
                flags = item.flags() | Qt.ItemFlag.ItemIsUserCheckable
                if tag in self._current:
                    # 已绑定标签：默认勾选 + 置灰不可取消
                    item.setCheckState(Qt.CheckState.Checked)
                    flags &= ~Qt.ItemFlag.ItemIsEnabled
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
                item.setFlags(flags)
                self._list.addItem(item)
        else:
            empty = QLabel("当前库暂无已有标签。\n你可以先在编辑框里手动输入标签。")
            empty.setWordWrap(True)
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #888;")
            root.addWidget(empty)
            self._list.setVisible(False)
            self._btn_select_all.setEnabled(False)
            self._btn_clear_all.setEnabled(False)

        # 标准按钮栏（确定 / 取消）
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = btn_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText("确定添加")
        cancel_btn = btn_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn is not None:
            cancel_btn.setText("取消")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)

    # ------------------------------------------------------------------
    # 对外 API
    # ------------------------------------------------------------------
    def selected_tags(self) -> list[str]:
        """返回本次「新勾选」的标签（不含之前已绑定的那些）。

        宿主直接把这个列表逐个 `_append_tag()` 到 `TagEditor` 即可，
        重复和归一化都由 `TagEditor` 内部统一处理。
        """
        out: list[str] = []
        for i in range(self._list.count()):
            it = self._list.item(i)
            if it is None:
                continue
            tag = it.data(Qt.ItemDataRole.UserRole)
            if not isinstance(tag, str) or not tag:
                continue
            # 跳过已绑定（灰色项）
            if tag in self._current:
                continue
            if it.checkState() == Qt.CheckState.Checked:
                out.append(tag)
        return out

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    def _select_all(self) -> None:
        for i in range(self._list.count()):
            it = self._list.item(i)
            if it is None:
                continue
            # 已绑定项不可操作，略过
            if not (it.flags() & Qt.ItemFlag.ItemIsEnabled):
                continue
            it.setCheckState(Qt.CheckState.Checked)

    def _clear_all(self) -> None:
        for i in range(self._list.count()):
            it = self._list.item(i)
            if it is None:
                continue
            if not (it.flags() & Qt.ItemFlag.ItemIsEnabled):
                continue
            it.setCheckState(Qt.CheckState.Unchecked)


__all__ = ["RowToggleListWidget", "TagChip", "TagEditor", "TagPickerDialog"]

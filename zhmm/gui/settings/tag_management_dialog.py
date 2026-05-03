#!/usr/bin/env python3
"""标签管理对话框。

从设置页的「标签管理」按钮打开，集中展示当前库所有已使用的标签及其使用次数，
允许对任一标签执行 **重命名** 或 **删除** 操作。所有变更会立即同步到每条关联
记录并加密落盘。

## 设计要点

- **直接作用于 SmData**：标签数据是 `PasswordEntry.tags` 的并集，没有独立
  存储，操作委托给 :class:`SmData` 的 `rename_tag` / `delete_tag`，落盘使用
  现有的 `SmData.save()`，复用已有的加密与原子写入路径。
- **失败回滚**：写盘失败时把内存中 `mm` 恢复到操作前的快照（深拷贝），避免
  内存-文件状态不一致。
- **合并语义**：重命名到一个已存在的标签时弹出合并确认，依赖
  `normalize_tags` 内部的去重保证条目的 tags 不会出现重复。
- **变更通知**：对话框有任何成功变更则关闭时通过 `accepted` 状态告诉宿主，
  由 :class:`SettingWindow` 发射 `tags_changed` 信号，主窗口侧边栏 / 表格
  随之刷新。
"""

from __future__ import annotations

import copy

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from zhmm.core.models import TAG_MAX_LEN, normalize_tags
from zhmm.data.sm_data_manager import SmData
from zhmm.gui.texts import Tags as TagsText
from zhmm.utils.log import logger


class TagManagementDialog(QDialog):
    """标签管理对话框：列出所有标签，支持重命名与删除。"""

    def __init__(self, sm_data: SmData, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sm_data = sm_data
        self._changed = False  # 是否发生过成功变更（决定宿主是否需要刷新 UI）

        self.setWindowTitle(TagsText.TITLE)
        self.setModal(True)
        self.resize(360, 420)

        self._setup_ui()
        self._reload_list()

    # ------------------------------------------------------------------
    # 对外 API
    # ------------------------------------------------------------------
    def has_changes(self) -> bool:
        """本次会话是否发生了任何成功的标签变更（宿主据此决定是否刷新）。"""
        return self._changed

    # ------------------------------------------------------------------
    # UI 布局
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        hint = QLabel(TagsText.HINT)
        hint.setWordWrap(True)
        hint.setStyleSheet("color: palette(placeholder-text); font-size: 12px;")
        root.addWidget(hint)

        self._list = QListWidget()
        # 复用标签列表的统一主题样式（浅/深色边框、hover、disabled 置灰）
        self._list.setObjectName("tag_picker_list")
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.setCursor(Qt.CursorShape.PointingHandCursor)
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        self._list.itemDoubleClicked.connect(lambda _i: self._on_rename())
        root.addWidget(self._list, 1)

        self._empty_hint = QLabel(TagsText.EMPTY)
        self._empty_hint.setWordWrap(True)
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_hint.setStyleSheet("color: #888;")
        self._empty_hint.setVisible(False)
        root.addWidget(self._empty_hint)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self._btn_rename = QPushButton(TagsText.BTN_RENAME)
        self._btn_rename.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_rename.setEnabled(False)
        self._btn_rename.clicked.connect(self._on_rename)
        button_row.addWidget(self._btn_rename)

        self._btn_delete = QPushButton(TagsText.BTN_DELETE)
        self._btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_delete.setEnabled(False)
        self._btn_delete.clicked.connect(self._on_delete)
        button_row.addWidget(self._btn_delete)

        button_row.addStretch(1)

        close_btn = QPushButton(TagsText.BTN_CLOSE)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        button_row.addWidget(close_btn)

        root.addLayout(button_row)

    # ------------------------------------------------------------------
    # 列表刷新与选中状态
    # ------------------------------------------------------------------
    def _reload_list(self) -> None:
        """根据最新 SmData 重建列表（保持选中项若仍存在）。"""
        prev = self._current_tag()
        counts = self._sm_data.collect_tag_counts()
        # 频次倒序 + 字母序稳定
        ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

        self._list.blockSignals(True)
        try:
            self._list.clear()
            for tag, count in ordered:
                item = QListWidgetItem(f"#{tag}  ({count})")
                item.setData(Qt.ItemDataRole.UserRole, tag)
                self._list.addItem(item)
                if tag == prev:
                    item.setSelected(True)
                    self._list.setCurrentItem(item)
        finally:
            self._list.blockSignals(False)

        has_any = bool(ordered)
        self._list.setVisible(has_any)
        self._empty_hint.setVisible(not has_any)
        self._on_selection_changed()

    def _current_tag(self) -> str | None:
        item = self._list.currentItem()
        if item is None:
            return None
        tag = item.data(Qt.ItemDataRole.UserRole)
        return tag if isinstance(tag, str) and tag else None

    def _on_selection_changed(self) -> None:
        has = self._current_tag() is not None
        self._btn_rename.setEnabled(has)
        self._btn_delete.setEnabled(has)

    # ------------------------------------------------------------------
    # 操作
    # ------------------------------------------------------------------
    def _on_rename(self) -> None:
        old = self._current_tag()
        if not old:
            return

        new_text, ok = QInputDialog.getText(
            self,
            TagsText.INPUT_TITLE,
            TagsText.INPUT_LABEL,
            QLineEdit.EchoMode.Normal,
            old,
        )
        if not ok:
            return

        cleaned = normalize_tags([new_text])
        if not cleaned:
            QMessageBox.warning(self, TagsText.INPUT_TITLE, TagsText.ERR_EMPTY)
            return
        new_tag = cleaned[0]
        if new_tag == old:
            QMessageBox.information(self, TagsText.INPUT_TITLE, TagsText.ERR_SAME)
            return
        # 超出长度由 normalize_tags 截断，UI 仍提示用户最终生效的标签
        if len(new_text.strip()) > TAG_MAX_LEN and new_tag != new_text.strip():
            QMessageBox.information(
                self,
                TagsText.INPUT_TITLE,
                f"标签名已截断到 {TAG_MAX_LEN} 字符：“#{new_tag}”",
            )

        # 合并确认：目标标签已存在
        existing = set(self._sm_data.collect_tag_counts().keys())
        if new_tag in existing:
            reply = QMessageBox.question(
                self,
                TagsText.INPUT_TITLE,
                TagsText.confirm_merge(old, new_tag),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        affected = self._apply_with_rollback(lambda: self._sm_data.rename_tag(old, new_tag))
        if affected is None:
            return  # 保存失败，已回滚并提示
        if affected > 0:
            self._changed = True
            QMessageBox.information(
                self,
                TagsText.INPUT_TITLE,
                TagsText.success_renamed(old, new_tag, affected),
            )
        self._reload_list()
        # 选中重命名后的结果，方便连续操作
        self._select_tag(new_tag)

    def _on_delete(self) -> None:
        tag = self._current_tag()
        if not tag:
            return
        count = self._sm_data.collect_tag_counts().get(tag, 0)

        reply = QMessageBox.question(
            self,
            TagsText.TITLE,
            TagsText.confirm_delete(tag, count),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        affected = self._apply_with_rollback(lambda: self._sm_data.delete_tag(tag))
        if affected is None:
            return
        if affected > 0:
            self._changed = True
            QMessageBox.information(
                self,
                TagsText.TITLE,
                TagsText.success_deleted(tag, affected),
            )
        self._reload_list()

    # ------------------------------------------------------------------
    # 内部：带回滚的保存
    # ------------------------------------------------------------------
    def _apply_with_rollback(self, op) -> int | None:
        """执行 op 并立即落盘；任一阶段失败则把 mm 恢复到操作前快照。

        Returns:
            受影响的条目数；保存失败返回 None（调用方应停止后续 UI 动作）。
        """
        snapshot = copy.deepcopy(self._sm_data.mm)
        try:
            affected = int(op())
        except Exception as e:  # noqa: BLE001 — 任意异常都视为失败回滚
            logger.exception("标签操作执行失败: %s", e)
            self._sm_data.mm = snapshot  # type: ignore[assignment]
            QMessageBox.critical(self, TagsText.TITLE, f"操作失败：{e}")
            return None

        if affected <= 0:
            # 归一化后无变化，无需落盘；保留 mm 原状也可避免多余 I/O
            self._sm_data.mm = snapshot  # type: ignore[assignment]
            return 0

        if not self._sm_data.save():
            self._sm_data.mm = snapshot  # type: ignore[assignment]
            QMessageBox.critical(self, TagsText.TITLE, TagsText.ERR_SAVE_FAILED)
            return None

        return affected

    def _select_tag(self, tag: str) -> None:
        for i in range(self._list.count()):
            it = self._list.item(i)
            if it is None:
                continue
            if it.data(Qt.ItemDataRole.UserRole) == tag:
                self._list.setCurrentItem(it)
                return

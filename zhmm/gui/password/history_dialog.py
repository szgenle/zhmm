#!/usr/bin/env python3
"""密码历史版本查看对话框。

展示同条目的 history 列表（最新在前），支持：
- 单条明文切换（掩码 ↔ 明文）
- 单条复制到剪贴板（10 秒后自动清空）
- 单条恢复为当前密码（双重确认）

历史数据来源于 ``PasswordEntry.history`` / ``ZhmmDict['history']``，
仅存在于 ``.zmb`` 内，不参与 Excel 导入导出。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolTip,
    QVBoxLayout,
)

from zhmm.gui.clipboard_util import copy_sensitive

# 掩码占位：与表格 reveal 列保持一致的视觉风格
_MASK = "••••••••••••"


def _fmt_time(ts: Any) -> str:
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, OSError):
        return "-"


class PasswordHistoryDialog(QDialog):
    """查看并操作同条目密码历史版本。"""

    # 列索引（保持常量化，减少魔法数）
    COL_TIME = 0
    COL_PWD = 1
    COL_ACTIONS = 2

    def __init__(self, parent, user_id: str, history: list[dict]) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"密码历史 · {user_id or '未命名'}")
        self.setMinimumSize(560, 320)
        # 原始历史列表的浅拷贝；回滚操作由外层处理，这里只负责展示
        self._history: list[dict] = [dict(h) for h in history if isinstance(h, dict)]
        # 被选中要回滚的历史下标；调用方 exec() 后读取
        self.selected_index: int = -1
        # 行级明文切换状态：{row_index: bool}
        self._revealed: dict[int, bool] = {}
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        hint = QLabel(
            "以下为该条目的历史密码版本（最新在前，最多 5 条）。\n" "仅随加密数据库存储，不参与 Excel 导入导出。"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._table = QTableWidget(len(self._history), 3)
        self._table.setHorizontalHeaderLabels(["被替换时间", "密码", "操作"])
        self._table.verticalHeader().setVisible(False)  # type: ignore[union-attr]
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        header = self._table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(self.COL_TIME, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(self.COL_PWD, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(self.COL_ACTIONS, QHeaderView.ResizeMode.ResizeToContents)

        for row, item in enumerate(self._history):
            self._fill_row(row, item)

        layout.addWidget(self._table)

        # 底部关闭按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _fill_row(self, row: int, item: dict) -> None:
        time_cell = QTableWidgetItem(_fmt_time(item.get("utime")))
        time_cell.setFlags(time_cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(row, self.COL_TIME, time_cell)

        pwd_cell = QTableWidgetItem(_MASK)
        pwd_cell.setFlags(pwd_cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
        pwd_cell.setToolTip("点击右侧「显示」按钮查看明文")
        self._table.setItem(row, self.COL_PWD, pwd_cell)

        # 操作列：显示/隐藏、复制、恢复
        actions = self._make_action_cell(row)
        self._table.setCellWidget(row, self.COL_ACTIONS, actions)

    def _make_action_cell(self, row: int):
        from PyQt6.QtWidgets import QWidget

        holder = QWidget(self._table)
        h = QHBoxLayout(holder)
        h.setContentsMargins(4, 0, 4, 0)
        h.setSpacing(6)

        reveal_btn = QPushButton("显示")
        reveal_btn.setFixedWidth(52)
        reveal_btn.clicked.connect(lambda _=False, r=row, b=reveal_btn: self._toggle_reveal(r, b))
        h.addWidget(reveal_btn)

        copy_btn = QPushButton("复制")
        copy_btn.setFixedWidth(52)
        copy_btn.clicked.connect(lambda _=False, r=row: self._copy_pwd(r))
        h.addWidget(copy_btn)

        restore_btn = QPushButton("恢复")
        restore_btn.setFixedWidth(52)
        restore_btn.setToolTip("把该旧密码恢复为当前密码；当前密码会压回历史栈顶")
        restore_btn.clicked.connect(lambda _=False, r=row: self._request_rollback(r))
        h.addWidget(restore_btn)

        return holder

    # ------------------------------------------------------------------
    # 行为
    # ------------------------------------------------------------------
    def _toggle_reveal(self, row: int, btn: QPushButton) -> None:
        if not (0 <= row < len(self._history)):
            return
        cell = self._table.item(row, self.COL_PWD)
        if cell is None:
            return
        revealed = not self._revealed.get(row, False)
        self._revealed[row] = revealed
        if revealed:
            cell.setText(str(self._history[row].get("pwd") or ""))
            btn.setText("隐藏")
        else:
            cell.setText(_MASK)
            btn.setText("显示")

    def _copy_pwd(self, row: int) -> None:
        if not (0 <= row < len(self._history)):
            return
        pwd = str(self._history[row].get("pwd") or "")
        if not pwd:
            return
        # 写入剪贴板 + 10s 带竞态保护的自动清空（与主窗口密码复制一致）
        copy_sensitive(pwd)
        QToolTip.showText(QCursor.pos(), "✅ 已复制历史密码到剪贴板（10 秒后自动清空）", self)

    def _request_rollback(self, row: int) -> None:
        if not (0 <= row < len(self._history)):
            return
        reply = QMessageBox.question(
            self,
            "确认恢复",
            "将该历史密码恢复为当前密码？\n当前密码会被压回历史栈顶，可再次回滚。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.selected_index = row
        self.accept()

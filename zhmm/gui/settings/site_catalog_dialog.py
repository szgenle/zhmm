#!/usr/bin/env python3
"""网站词典查看对话框（只读）。

数据管理 Tab 新增的「网站词典」分组通过本对话框展示随包发行的离线词典：
``domain / host → (中文名, 建议标签)``。

## 设计要点

- **只读**：当前版本仅展示，不提供增删改；词典 JSON 由项目维护 / PR 扩充。
- **搜索防抖**：搜索框走 250ms 防抖，避免大列表每敲一键重建控件；复用项目
  已在其他搜索场景沉淀的防抖范式（见记忆「PyQt6 QLineEdit 搜索框防抖」）。
- **三列表格**：``域名 / 中文名 / 建议标签``；表格只读、整行选中、支持
  「点击任意单元格 → 复制对应文本」的轻交互（未来可扩）。
- **没有任何写盘路径**：与 TagManagementDialog 的行为严格区分，避免用户
  把「词典中的标签」误当成「条目里的标签」来管理。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from zhmm.core.site_catalog import all_entries
from zhmm.gui.texts import SiteCatalog as Texts

# 搜索防抖窗口（毫秒）
_SEARCH_DEBOUNCE_MS = 250


class SiteCatalogViewerDialog(QDialog):
    """只读查看内置网站词典。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(Texts.TITLE)
        self.setModal(True)
        self.resize(620, 480)

        # 全量条目（词典加载失败时为空列表，UI 自动切空态）
        self._all: list[dict[str, object]] = list(all_entries())

        # 搜索防抖定时器
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(_SEARCH_DEBOUNCE_MS)
        self._search_timer.timeout.connect(self._apply_filter)

        self._setup_ui()
        self._apply_filter()  # 初次渲染

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        hint = QLabel(Texts.HINT)
        hint.setWordWrap(True)
        hint.setStyleSheet("color: palette(placeholder-text); font-size: 12px;")
        root.addWidget(hint)

        # 搜索 + 计数
        top = QHBoxLayout()
        top.setSpacing(8)
        self._search = QLineEdit()
        self._search.setPlaceholderText(Texts.SEARCH_PLACEHOLDER)
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_search_changed)
        top.addWidget(self._search, 1)

        self._count_label = QLabel("")
        self._count_label.setStyleSheet("color: palette(placeholder-text); font-size: 12px;")
        top.addWidget(self._count_label)
        root.addLayout(top)

        # 表格
        self._table = QTableWidget(0, 3, self)
        self._table.setHorizontalHeaderLabels([Texts.COL_HOST, Texts.COL_NAME, Texts.COL_TAGS])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setWordWrap(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self._table, 1)

        # 空态占位
        self._empty_label = QLabel("")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("color: palette(placeholder-text);")
        self._empty_label.setVisible(False)
        root.addWidget(self._empty_label)

        # 关闭按钮（标准按钮栏，文字替换为中文）
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn = btn_box.button(QDialogButtonBox.StandardButton.Close)
        if close_btn is not None:
            close_btn.setText(Texts.BTN_CLOSE)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)

    # ------------------------------------------------------------------
    # 搜索 / 过滤
    # ------------------------------------------------------------------
    def _on_search_changed(self, _text: str) -> None:
        """每次键入重置防抖定时器，到点才真正 filter。"""
        self._search_timer.start()

    def _apply_filter(self) -> None:
        keyword = self._search.text().strip().lower()
        shown = [e for e in self._all if _match(e, keyword)] if keyword else list(self._all)
        self._render_rows(shown)
        self._count_label.setText(Texts.count_summary(total=len(self._all), shown=len(shown)))

        # 空态处理：词典本身为空 / 词典非空但搜索无命中
        if not self._all:
            self._empty_label.setText(Texts.EMPTY)
            self._empty_label.setVisible(True)
            self._table.setVisible(False)
        elif not shown:
            self._empty_label.setText(Texts.NO_MATCH)
            self._empty_label.setVisible(True)
            self._table.setVisible(True)
        else:
            self._empty_label.setVisible(False)
            self._table.setVisible(True)

    def _render_rows(self, rows: list[dict[str, object]]) -> None:
        self._table.setRowCount(len(rows))
        for r, entry in enumerate(rows):
            host = str(entry.get("host", ""))
            name = str(entry.get("name", ""))
            tags_val = entry.get("tags") or []
            tags_text = "、".join(str(t) for t in tags_val) if isinstance(tags_val, list) else ""
            self._set_cell(r, 0, host)
            self._set_cell(r, 1, name)
            self._set_cell(r, 2, tags_text)

    def _set_cell(self, row: int, col: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self._table.setItem(row, col, item)


def _match(entry: dict[str, object], keyword: str) -> bool:
    """大小写不敏感地匹配 host / name / 任一 tag。"""
    host = str(entry.get("host", "")).lower()
    name = str(entry.get("name", "")).lower()
    if keyword in host or keyword in name:
        return True
    tags_val = entry.get("tags") or []
    if isinstance(tags_val, list):
        for t in tags_val:
            if isinstance(t, str) and keyword in t.lower():
                return True
    return False


__all__ = ["SiteCatalogViewerDialog"]

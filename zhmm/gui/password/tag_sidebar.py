"""左侧标签筛选侧边栏。

呈现当前密库所有已出现过的标签及每个标签下的条目数量，支持多选 AND 语义筛选。

外部接口：
- `TagSidebar.rebuild(entries)`：根据最新 `sm_data.mm["data"]` 重建列表（导入/增删/编辑后调用）
- `TagSidebar.selected_tags() -> list[str]`：读取当前选中标签
- `TagSidebar.tags_selection_changed`：选择变化时发射 `list[str]`
- `TagSidebar.clear_selection()`：清空选中并发信号

设计考虑：
- 使用 `QListWidget` 配合 `CheckState`，无需自绘；多选即勾选多项。
- 标签顺序按条目出现频次倒序 + 字母序稳定，便于用户快速找到常用标签。
- 顶部独立 `全部` 项：勾选即清空所有标签选择，作为 “重置筛选” 捷径。
- 侧边栏本身不写回数据，只负责收集用户意图并 emit 信号，
  由 `PasswordWindow` 把信号接到 `CustomProxyModel.set_selected_tags()` 上。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class TagSidebar(QWidget):
    """左侧「标签」侧边栏：多选 AND 筛选。"""

    tags_selection_changed = pyqtSignal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("tag_sidebar")
        self._suppress_signal = False

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 4, 8)
        root.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(4)
        title = QLabel("标签")
        title.setStyleSheet("font-weight: bold;")
        header.addWidget(title)
        header.addStretch(1)
        self._clear_btn = QPushButton("清空")
        self._clear_btn.setFlat(True)
        self._clear_btn.setToolTip("清空当前标签筛选")
        self._clear_btn.clicked.connect(self.clear_selection)
        header.addWidget(self._clear_btn)
        root.addLayout(header)

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # 紧凑外观，不用 setAlternatingRowColors 以免与主题冲突
        self._list.setStyleSheet(
            "QListWidget { border: 1px solid #d0d7de; border-radius: 6px; padding: 2px; }"
            "QListWidget::item { padding: 4px 6px; }"
            "QListWidget::item:hover { background: #eef3f8; }"
        )
        self._list.itemChanged.connect(self._on_item_changed)
        root.addWidget(self._list, 1)

        self._empty_hint = QLabel("当前暂无标签。\n编辑条目时添加标签即可在此筛选。")
        self._empty_hint.setWordWrap(True)
        self._empty_hint.setStyleSheet("color: #888;")
        self._empty_hint.setVisible(False)
        root.addWidget(self._empty_hint)

        # 初始空态
        self.rebuild([])

    # ------------------------------------------------------------------
    # 对外 API
    # ------------------------------------------------------------------
    def rebuild(self, entries: Iterable[dict]) -> None:
        """根据条目列表重建标签项。

        会尽量保留用户已选中的标签状态：若重建后标签仍存在，仍保持勾选。
        """
        prev_selected = set(self.selected_tags())

        counter: Counter[str] = Counter()
        for item in entries or []:
            tags = item.get("tags") if isinstance(item, dict) else None
            if not isinstance(tags, list):
                continue
            for t in tags:
                if isinstance(t, str) and t:
                    counter[t] += 1

        # 按频次倒序 + 字母序稳定
        ordered = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))

        self._suppress_signal = True
        try:
            self._list.clear()
            for tag, count in ordered:
                it = QListWidgetItem(f"#{tag}  ({count})")
                it.setData(Qt.ItemDataRole.UserRole, tag)
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                checked = tag in prev_selected
                it.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
                self._list.addItem(it)
        finally:
            self._suppress_signal = False

        has_tags = bool(ordered)
        self._list.setVisible(has_tags)
        self._empty_hint.setVisible(not has_tags)

        # 若上次选中的标签本次已不存在，需通知外部刷新
        new_selected = set(self.selected_tags())
        if new_selected != prev_selected:
            self.tags_selection_changed.emit(self.selected_tags())

    def selected_tags(self) -> list[str]:
        """返回当前被勾选的标签列表（保持列表显示顺序）。"""
        out: list[str] = []
        for i in range(self._list.count()):
            it = self._list.item(i)
            if it is None:
                continue
            if it.checkState() == Qt.CheckState.Checked:
                tag = it.data(Qt.ItemDataRole.UserRole)
                if isinstance(tag, str) and tag:
                    out.append(tag)
        return out

    def clear_selection(self) -> None:
        """清空所有勾选；会触发一次 `tags_selection_changed`。"""
        changed = False
        self._suppress_signal = True
        try:
            for i in range(self._list.count()):
                it = self._list.item(i)
                if it is None:
                    continue
                if it.checkState() == Qt.CheckState.Checked:
                    it.setCheckState(Qt.CheckState.Unchecked)
                    changed = True
        finally:
            self._suppress_signal = False
        if changed:
            self.tags_selection_changed.emit([])

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    def _on_item_changed(self, _item: QListWidgetItem) -> None:
        if self._suppress_signal:
            return
        self.tags_selection_changed.emit(self.selected_tags())


__all__ = ["TagSidebar"]

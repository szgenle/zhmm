"""自适应弹出宽度的 QComboBox。

默认 `QComboBox` 的弹出列表宽度跟随主按钮宽度，一旦某个 item 文字较长
就会被截断。`WideComboBox` 在 `showPopup()` 时根据最长 item 文本动态放宽
弹出 view 的宽度，不影响主按钮自身的布局宽度。
"""

from __future__ import annotations

from PyQt6.QtWidgets import QComboBox, QStyle


class WideComboBox(QComboBox):
    """下拉弹出列表宽度随最长项自适应的 QComboBox。"""

    def showPopup(self) -> None:  # type: ignore[override]
        view = self.view()
        if view is not None and self.count() > 0:
            fm = view.fontMetrics()
            max_text_w = 0
            for i in range(self.count()):
                w = fm.horizontalAdvance(self.itemText(i))
                if w > max_text_w:
                    max_text_w = w
            # 预留内边距 + 可能出现的垂直滚动条宽度
            style = self.style()
            sb_extent = style.pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent) if style else 16
            target = max(self.width(), max_text_w + sb_extent + 24)
            view.setMinimumWidth(target)
        super().showPopup()

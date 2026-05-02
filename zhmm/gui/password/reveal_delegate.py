"""密码表格「显示」列自定义委托：根据当前 reveal 状态绘制 SVG 眼睛图标。"""

from __future__ import annotations

from PyQt6.QtCore import QModelIndex, QSortFilterProxyModel
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem

from zhmm.gui.password.table_models import PasswordTableModel
from zhmm.widgets.eye_icon import EYE_CLOSED_SVG, EYE_OPEN_SVG, svg_to_pixmap


class RevealColumnDelegate(QStyledItemDelegate):
    """在「显示」列居中绘制睁眼/闭眼 SVG 图标。"""

    def __init__(self, parent=None, icon_size: int = 18):
        super().__init__(parent)
        self._icon_size = icon_size
        self._pixmap_open = svg_to_pixmap(EYE_OPEN_SVG, icon_size)
        self._pixmap_closed = svg_to_pixmap(EYE_CLOSED_SVG, icon_size)

    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex) -> None:  # type: ignore[override]
        super().initStyleOption(option, index)
        # 不显示任何文本（model 即使返回了 emoji 占位也会被这里清空）
        option.text = ""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:  # type: ignore[override]
        # 让 super 绘制背景（选中态、交替行色等），文本已在 initStyleOption 清空
        super().paint(painter, option, index)

        revealed = self._is_revealed(index)
        pixmap = self._pixmap_open if revealed else self._pixmap_closed
        rect = option.rect
        x = rect.x() + (rect.width() - pixmap.width()) // 2
        y = rect.y() + (rect.height() - pixmap.height()) // 2

        painter.save()
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.drawPixmap(x, y, pixmap)
        finally:
            painter.restore()

    @staticmethod
    def _is_revealed(index: QModelIndex) -> bool:
        """从 proxy/source model 中查询当前行是否处于明文显示状态。"""
        model = index.model()
        if isinstance(model, QSortFilterProxyModel):
            source_index = model.mapToSource(index)
            source_model = model.sourceModel()
        else:
            source_index = index
            source_model = model
        if isinstance(source_model, PasswordTableModel):
            return source_model.is_revealed(source_index.row())
        return False

    def helpEvent(self, event, view, option, index):  # type: ignore[override]
        # 给「显示」列单元格统一加 ToolTip
        from PyQt6.QtCore import QEvent
        from PyQt6.QtWidgets import QToolTip

        if event is not None and event.type() == QEvent.Type.ToolTip:
            QToolTip.showText(event.globalPos(), "点击显示/隐藏密码", view)
            return True
        return super().helpEvent(event, view, option, index)

    @staticmethod
    def hint_column_width(icon_size: int = 18, padding: int = 12) -> int:
        """建议的「显示」列宽度（图标尺寸 + 两侧留白）。"""
        return icon_size + padding * 2

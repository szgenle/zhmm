"""共享的「眼睛」SVG 图标资源。

登录界面输入框、密码表格「显示」列等场景都使用同一套图标，避免重复维护。
"""

from __future__ import annotations

from PyQt6.QtCore import QByteArray, QSize, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

# 睁眼图标（Feather Icons 风格，适用于「当前显示密码，点击可隐藏」）
EYE_OPEN_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    b'stroke="#333333" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    b'<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"/>'
    b'<circle cx="12" cy="12" r="3"/>'
    b"</svg>"
)

# 闭眼图标（带斜线，适用于「当前隐藏密码，点击可显示」）
EYE_CLOSED_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    b'stroke="#333333" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    b'<path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a19.62 19.62 0 0 1 5.06-5.94"/>'
    b'<path d="M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a19.4 19.4 0 0 1-2.17 3.19"/>'
    b'<path d="M9.88 9.88a3 3 0 0 0 4.24 4.24"/>'
    b'<line x1="1" y1="1" x2="23" y2="23"/>'
    b"</svg>"
)


def svg_to_pixmap(svg_data: bytes, size: int = 20) -> QPixmap:
    """将内联 SVG 字节串渲染为 QPixmap（透明背景）。"""
    renderer = QSvgRenderer(QByteArray(svg_data))
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    return pixmap


def svg_to_icon(svg_data: bytes, size: int = 20) -> QIcon:
    """将内联 SVG 字节串渲染为 QIcon。"""
    return QIcon(svg_to_pixmap(svg_data, size))

"""跨平台防截屏工具。

原理：
- macOS: 将 NSWindow.sharingType 设为 NSWindowSharingNone(0)，屏幕录制 / 截图 /
  屏幕共享抓取到的是黑色区域。通过 ctypes + libobjc 直接调用，避免引入 pyobjc。
- Windows: 调用 user32.SetWindowDisplayAffinity，参数 WDA_EXCLUDEFROMCAPTURE
  (0x11，Win10 2004+) 优先；失败时回退 WDA_MONITOR (0x01)。
- Linux: 无可靠系统 API，仅记录日志。

注意：任何防截屏方案都无法防御摄像头翻拍、虚拟机/外接采集卡等外部途径。
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import c_char_p, c_ulong, c_void_p
from typing import TYPE_CHECKING

from zhmm.utils.log import logger

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

# macOS NSWindow sharingType 常量
_NS_WINDOW_SHARING_NONE = 0

# Windows SetWindowDisplayAffinity 常量
_WDA_NONE = 0x00000000
_WDA_MONITOR = 0x00000001
_WDA_EXCLUDE_FROM_CAPTURE = 0x00000011  # Win10 2004+


def _apply_macos(widget: QWidget) -> bool:
    """在 macOS 上启用防截屏。"""
    try:
        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.dylib")
    except OSError as e:
        logger.warning(f"[anti-capture] 加载 libobjc 失败: {e}")
        return False

    # 配置 selector 注册函数
    objc.sel_registerName.restype = c_void_p
    objc.sel_registerName.argtypes = [c_char_p]

    # winId() 在 macOS 返回 NSView 指针；先取其所属的 NSWindow
    ns_view = c_void_p(int(widget.winId()))
    if not ns_view.value:
        logger.warning("[anti-capture] winId() 返回空指针，跳过")
        return False

    # [nsview window]
    msg_send_obj = objc.objc_msgSend
    msg_send_obj.restype = c_void_p
    msg_send_obj.argtypes = [c_void_p, c_void_p]
    sel_window = objc.sel_registerName(b"window")
    ns_window = msg_send_obj(ns_view, sel_window)
    if not ns_window:
        logger.warning("[anti-capture] 未取到 NSWindow，跳过")
        return False

    # [nswindow setSharingType:NSWindowSharingNone]
    msg_send_void_ulong = ctypes.CFUNCTYPE(None, c_void_p, c_void_p, c_ulong)(
        ("objc_msgSend", objc),
    )
    sel_set_sharing = objc.sel_registerName(b"setSharingType:")
    msg_send_void_ulong(c_void_p(ns_window), c_void_p(sel_set_sharing), _NS_WINDOW_SHARING_NONE)
    logger.info("[anti-capture] macOS NSWindowSharingNone 已启用")
    return True


def _apply_windows(widget: QWidget) -> bool:
    """在 Windows 上启用防截屏。"""
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    except (AttributeError, OSError) as e:
        logger.warning(f"[anti-capture] 加载 user32 失败: {e}")
        return False

    hwnd = int(widget.winId())
    if not hwnd:
        logger.warning("[anti-capture] winId() 返回空句柄，跳过")
        return False

    set_affinity = user32.SetWindowDisplayAffinity
    set_affinity.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    set_affinity.restype = ctypes.c_int

    # 优先完全排除截获（Win10 2004+）
    if set_affinity(hwnd, _WDA_EXCLUDE_FROM_CAPTURE):
        logger.info("[anti-capture] Windows WDA_EXCLUDEFROMCAPTURE 已启用")
        return True
    # 回退到显示器级保护
    if set_affinity(hwnd, _WDA_MONITOR):
        logger.info("[anti-capture] Windows WDA_MONITOR 已启用（回退）")
        return True
    logger.warning("[anti-capture] SetWindowDisplayAffinity 调用失败")
    return False


def _disable_macos(widget: QWidget) -> bool:
    """在 macOS 上关闭防截屏（恢复默认 ReadOnly 共享）。"""
    try:
        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.dylib")
    except OSError:
        return False
    objc.sel_registerName.restype = c_void_p
    objc.sel_registerName.argtypes = [c_char_p]
    ns_view = c_void_p(int(widget.winId()))
    if not ns_view.value:
        return False
    msg_send_obj = objc.objc_msgSend
    msg_send_obj.restype = c_void_p
    msg_send_obj.argtypes = [c_void_p, c_void_p]
    ns_window = msg_send_obj(ns_view, objc.sel_registerName(b"window"))
    if not ns_window:
        return False
    msg_send_void_ulong = ctypes.CFUNCTYPE(None, c_void_p, c_void_p, c_ulong)(
        ("objc_msgSend", objc),
    )
    # NSWindowSharingReadOnly = 1
    msg_send_void_ulong(c_void_p(ns_window), c_void_p(objc.sel_registerName(b"setSharingType:")), 1)
    return True


def _disable_windows(widget: QWidget) -> bool:
    """在 Windows 上关闭防截屏。"""
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return False
    hwnd = int(widget.winId())
    if not hwnd:
        return False
    set_affinity = user32.SetWindowDisplayAffinity
    set_affinity.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    set_affinity.restype = ctypes.c_int
    return bool(set_affinity(hwnd, _WDA_NONE))


def apply_anti_capture(widget: QWidget, enabled: bool = True) -> bool:
    """对指定顶层窗口应用 / 撤销防截屏保护。

    参数:
        widget: 必须是已经创建原生窗口（show() 之后）的顶层 QWidget。
        enabled: True 启用保护；False 恢复系统默认行为。
    返回:
        是否成功生效。
    """
    platform = sys.platform
    try:
        if platform == "darwin":
            return _apply_macos(widget) if enabled else _disable_macos(widget)
        if platform.startswith("win"):
            return _apply_windows(widget) if enabled else _disable_windows(widget)
        logger.info(f"[anti-capture] 平台 {platform} 不支持防截屏，跳过")
        return False
    except Exception as e:  # pragma: no cover - 运行时兜底
        logger.warning(f"[anti-capture] 应用失败: {e}")
        return False

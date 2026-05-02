"""简易 PyQt 网络请求封装（SSE 友好）。"""

from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import QObject, QUrl, pyqtSlot
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


class SsNetwork(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.manager = QNetworkAccessManager(self)
        self.manager.finished.connect(self.on_finished)
        # 存储 QNetworkReply 对象及其回调函数
        self.callbacks: dict[QNetworkReply, dict[str, Any]] = {}

    def request(
        self,
        url: str,
        post_data: Any,
        callback: Callable[..., Any],
        method: str = "POST",
        stream: bool = False,
    ) -> None:
        # 创建网络请求
        request = QNetworkRequest(QUrl(url))
        self.set_header(request)

        # 发送 POST 请求
        if method == "POST":
            reply = self.manager.post(request, post_data)
        else:
            reply = self.manager.get(request, post_data)

        if reply is None:
            return

        self.callbacks[reply] = {"callback": callback, "stream": stream, "buffer": b""}

        # 如果是流式请求，连接readyRead信号
        if stream:
            reply.readyRead.connect(lambda r=reply: self.on_stream_ready(r))

    def set_header(self, request: QNetworkRequest) -> None:
        pass

    @pyqtSlot(QNetworkReply)
    def on_finished(self, reply: QNetworkReply) -> None:
        if reply not in self.callbacks:
            return
        # """处理网络响应"""
        entry = self.callbacks[reply]

        try:
            # 处理流式请求的残留数据
            if entry["stream"] and entry["buffer"]:
                self.on_stream_ready(reply)
                return

            if reply.error() == QNetworkReply.NetworkError.NoError:
                # 调用回调函数
                self.on_response(reply)
            else:
                # 调用回调函数，传递错误信息
                self.on_response_error(reply)
        except Exception as e:
            print(e)
        finally:
            # 释放 reply 对象并从字典中移除
            del self.callbacks[reply]
            reply.deleteLater()

    def on_response(self, reply: QNetworkReply) -> None:
        pass

    def on_response_error(self, reply: QNetworkReply) -> None:
        pass

    def on_stream_ready(self, reply: QNetworkReply) -> None:
        if reply not in self.callbacks:
            return

        entry = self.callbacks[reply]

        # 读取所有可用数据
        data = reply.readAll().data()
        entry["buffer"] += data

        # 处理SSE格式（data: {...}\n\n）
        while True:
            head, sep, tail = entry["buffer"].partition(b"\n\n")
            if not sep:
                break

            # 处理单个事件
            event_data = head
            entry["buffer"] = tail

            if event_data.startswith(b"data: "):
                payload = event_data[6:].strip()
                self.handle_stream_chunk(reply, payload)

    def handle_stream_chunk(self, reply: QNetworkReply, payload: bytes) -> None:
        print("handle_stream_chunk")

    def handle_stream_end(self, reply: QNetworkReply) -> None:
        print("handle_stream_end")

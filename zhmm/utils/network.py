# -*- coding: utf-8 -*-
from PyQt6.QtCore import QObject, QUrl, pyqtSlot
from PyQt6.QtNetwork import (QNetworkAccessManager, QNetworkReply,
                             QNetworkRequest)


class SsNetwork(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = QNetworkAccessManager(self)
        self.manager.finished.connect(self.on_finished)
        self.callbacks = {}  # 存储 QNetworkReply 对象及其回调函数

    def request(self, url: str, post_data, callback, method="POST", stream=False):
        # 创建网络请求
        request = QNetworkRequest(QUrl(url))
        self.set_header(request)

        # 发送 POST 请求
        if method == "POST":
            reply = self.manager.post(request, post_data)
        else:
            reply = self.manager.get(request, post_data)

        self.callbacks[reply] = {"callback": callback, "stream": stream, "buffer": b""}

        # 如果是流式请求，连接readyRead信号
        if stream and reply:
            reply.readyRead.connect(lambda r=reply: self.on_stream_ready(r))

    def set_header(self, request: QNetworkRequest):
        pass

    @pyqtSlot(QNetworkReply)
    def on_finished(self, reply):
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

    def on_response(self, reply):
        pass

    def on_response_error(self, reply):
        pass

    def on_stream_ready(self, reply):
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

    def handle_stream_chunk(self, reply, payload):
        print("handle_stream_chunk")

    def handle_stream_end(self, reply):
        print("handle_stream_end")

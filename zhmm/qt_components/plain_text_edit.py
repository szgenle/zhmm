from PyQt6.QtCore import QMimeData, Qt
from PyQt6.QtWidgets import QApplication, QTextEdit


class PlainTextEdit(QTextEdit):
    on_ok = None

    def __init__(self):
        super().__init__()
        self.setPlaceholderText("輸入消息...（支持多行，Ctrl+Enter發送）(发送后消息会自动复制到剪切板)")
        self.setMaximumHeight(50)  # 限制最大高度
        self.installEventFilter(self)  # 关键代码

    def insertFromMimeData(self, source: QMimeData | None):
        if source and source.hasText():
            # 获取纯文本内容
            plain_text = source.text()
            # 插入纯文本
            self.insertPlainText(plain_text)

    def keyPressEvent(self, e):
        # 捕获键盘事件
        if (
            e
            and e.key() == Qt.Key.Key_Return
            and e.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            # 如果按下 Ctrl+Enter，调用 on_ok 方法
            if self.on_ok:
                self.on_ok()
            pass
        else:
            # 否则调用父类的 keyPressEvent
            super().keyPressEvent(e)

    def set_on_ok_callback(self, cb):
        self.on_ok = cb


if __name__ == "__main__":
    app = QApplication([])

    text_edit = PlainTextEdit()
    text_edit.show()

    app.exec()

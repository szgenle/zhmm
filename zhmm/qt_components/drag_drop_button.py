from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import pyqtSignal


class DragDropButton(QPushButton):
    dragDropEvent = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            # self.setText(f"File: {file_path}")
            # 你可以在这里处理文件路径，例如读取文件内容等
            print(f"File dropped: {file_path}")
            self.dragDropEvent.emit(file_path)

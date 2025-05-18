
from PyQt6.QtWidgets import QFileDialog


class UiDataExporter:

    @staticmethod
    def export_to_file(data):
        """执行导出操作"""
        # 弹出文件保存对话框
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "保存账号文件",
            "zhmm.xlsx",  # 默认文件名
            "GL Files (*.xlsx);;All Files (*)"  # 文件过滤器
        )
        if file_path:
            return DataExporter.export_xlsx(file_path, data)

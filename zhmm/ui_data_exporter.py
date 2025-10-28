from PyQt6.QtWidgets import QFileDialog, QMessageBox

from zhmm.data_exporter import DataExporter


class UiDataExporter:
    @staticmethod
    def export_to_file(data):
        """执行导出操作"""
        # 弹出文件保存对话框
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "保存账号文件",
            "zhmm.xlsx",  # 默认文件名
            "GL Files (*.xlsx);;All Files (*)",  # 文件过滤器
        )
        if file_path:
            result = DataExporter.export_xlsx(file_path, data)
            if result:
                QMessageBox.information(
                    None,
                    "导出成功",
                    f"已成功导出 {len(data)} 条数据到:\n{file_path}"
                )
            else:
                QMessageBox.warning(
                    None,
                    "导出失败",
                    "数据导出失败,请检查文件路径和权限"
                )
            return result

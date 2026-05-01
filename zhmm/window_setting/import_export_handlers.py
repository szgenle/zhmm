#!/usr/bin/env python3
# coding=utf-8
"""数据导入导出功能处理器"""
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget

from zhmm.ui_data_exporter import UiDataExporter
from zhmm.ui_defined import ZhmmFileInfo


class ImportExportHandlers:
    """处理数据导入导出相关操作"""

    def __init__(self, parent: QWidget, info: ZhmmFileInfo):
        self.parent = parent
        self.info = info

    def export_passwords(self):
        """导出密码列表"""
        sm_data = self.info["sm_data"]
        if sm_data:
            UiDataExporter.export_to_file(sm_data.mm["data"])

    def import_xlsx(self, on_success_callback=None):
        """导入xlsx文件

        Args:
            on_success_callback: 导入成功后的回调函数
        """
        from zhmm.data_exporter import DataImporter

        file_path, _ = QFileDialog.getOpenFileName(
            self.parent, "选择xlsx文件", "", "Excel文件 (*.xlsx)"
        )

        if not file_path:
            return

        try:
            imported_data = DataImporter.import_from_file(file_path)
            if not imported_data:
                QMessageBox.warning(
                    self.parent,
                    "导入失败",
                    "无法读取xlsx文件，请检查文件格式是否正确。\n\n" +
                    "文件应包含以下列：\nID、类别、账号、密码、手机、邮箱、网站、备注、更新时间"
                )
                return

            sm_data = self.info["sm_data"]
            if not sm_data:
                QMessageBox.warning(self.parent, "导入失败", "数据管理器未初始化")
                return

            # 合并导入的数据
            append_times, update_times = sm_data.merge(imported_data)  # type: ignore

            # 显示导入结果
            if append_times == 0 and update_times == 0:
                QMessageBox.information(
                    self.parent,
                    "导入完成",
                    "导入完成，但没有新增或更新任何数据。\n\n" +
                    "可能所有数据都已存在且一致。"
                )
            else:
                QMessageBox.information(
                    self.parent,
                    "导入成功",
                    f"成功导入数据！\n\n" +
                    f"新增: {append_times} 条\n" +
                    f"更新: {update_times} 条\n\n" +
                    f"总计处理: {append_times + update_times} 条数据"
                )
                # 调用成功回调
                if on_success_callback:
                    on_success_callback()

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            QMessageBox.critical(
                self.parent,
                "导入失败",
                f"导入xlsx文件时发生错误：\n\n{str(e)}\n\n" +
                f"请检查：\n" +
                f"1. 是否安装了 openpyxl 库\n" +
                f"2. 文件格式是否正确\n" +
                f"3. 文件是否被其他程序占用"
            )
            print(error_detail)

    def download_xlsx_template(self):
        """下载xlsx模版文件（动态生成）"""
        from openpyxl import Workbook

        save_path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "保存xlsx模版",
            "zhmm模版.xlsx",
            "Excel文件 (*.xlsx)"
        )
        if not save_path:
            return

        try:
            wb = Workbook()
            ws = wb.active
            if ws is None:
                raise ValueError("工作表不存在")
            ws.title = "密码模版"
            headers = ["ID", "类别", "账号", "密码", "手机", "邮箱", "网站", "备注", "更新时间"]
            ws.append(headers)
            wb.save(save_path)
            QMessageBox.information(self.parent, "下载成功", f"模版文件已成功保存到：\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self.parent, "下载失败", f"保存模版文件时发生错误：\n\n{str(e)}")

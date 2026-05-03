#!/usr/bin/env python3
"""数据导入导出 UI 处理器。

业务逻辑已迁移到 [zhmm.core.export_service.ExportService]，本模块仅负责
QFileDialog / QMessageBox 交互。
"""

from __future__ import annotations

from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget

from zhmm.config.constants import ZhmmFileInfo
from zhmm.core.errors import StorageError, ValidationError
from zhmm.core.export_service import ExportService
from zhmm.core.models import PasswordEntry


class ImportExportHandlers:
    """处理数据导入导出相关操作。"""

    def __init__(self, parent: QWidget, info: ZhmmFileInfo):
        self.parent = parent
        self.info = info

    def export_passwords(self):
        """导出密码列表到 xlsx。"""
        sm_data = self.info.get("sm_data")
        if not sm_data:
            QMessageBox.warning(self.parent, "导出失败", "数据管理器未初始化")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "保存账号文件",
            "zhmm.xlsx",
            "Excel 文件 (*.xlsx);;所有文件 (*)",
        )
        if not file_path:
            return

        try:
            entries = [PasswordEntry.from_dict(item) for item in sm_data.mm["data"]]
            ExportService.export_xlsx(file_path, entries)
        except StorageError as e:
            QMessageBox.warning(self.parent, "导出失败", f"数据导出失败：{e}")
            return
        QMessageBox.information(
            self.parent,
            "导出成功",
            f"已成功导出 {len(entries)} 条数据到:\n{file_path}",
        )

    def import_xlsx(self, on_success_callback=None):
        """导入 xlsx 文件，并合并到当前库。"""
        sm_data = self.info.get("sm_data")
        if not sm_data:
            QMessageBox.warning(self.parent, "导入失败", "数据管理器未初始化")
            return

        file_path, _ = QFileDialog.getOpenFileName(self.parent, "选择xlsx文件", "", "Excel文件 (*.xlsx)")
        if not file_path:
            return

        try:
            entries = ExportService.import_xlsx(file_path)
        except (StorageError, ValidationError) as e:
            QMessageBox.warning(
                self.parent,
                "导入失败",
                f"无法读取 xlsx 文件：{e}\n\n"
                "文件应包含以下列：\nID、类别、账号、密码、手机、邮箱、网站、备注、更新时间\n"
                "（可选列：标签，多个标签用分号 ; 分隔）",
            )
            return
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "导入失败",
                f"导入 xlsx 文件时发生错误：\n\n{e!s}",
            )
            return

        if not entries:
            QMessageBox.warning(self.parent, "导入失败", "xlsx 文件无有效数据")
            return

        imported_dicts = [e.to_dict() for e in entries]
        append_times, update_times = sm_data.merge(imported_dicts)  # type: ignore

        if append_times == 0 and update_times == 0:
            QMessageBox.information(
                self.parent,
                "导入完成",
                "导入完成，但没有新增或更新任何数据。\n\n可能所有数据都已存在且一致。",
            )
            return

        QMessageBox.information(
            self.parent,
            "导入成功",
            f"成功导入数据！\n\n"
            f"新增: {append_times} 条\n"
            f"更新: {update_times} 条\n\n"
            f"总计处理: {append_times + update_times} 条数据",
        )
        if on_success_callback:
            on_success_callback()

    def download_xlsx_template(self):
        """下载 xlsx 模版文件（动态生成）。"""
        from openpyxl import Workbook

        save_path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "保存xlsx模版",
            "zhmm模版.xlsx",
            "Excel文件 (*.xlsx)",
        )
        if not save_path:
            return

        try:
            wb = Workbook()
            ws = wb.active
            if ws is None:
                raise ValueError("工作表不存在")
            ws.title = "密码模版"
            headers = [
                "ID",
                "类别",
                "账号",
                "密码",
                "手机",
                "邮箱",
                "网站",
                "备注",
                "更新时间",
                "标签",
            ]
            ws.append(headers)
            # 标签多值用分号 ; 分隔，详见导入失败提示
            # （不放示例行：避免用户忘删后被当成空条目导入）
            wb.save(save_path)
        except Exception as e:
            QMessageBox.critical(self.parent, "下载失败", f"保存模版文件时发生错误：\n\n{e!s}")
            return
        QMessageBox.information(self.parent, "下载成功", f"模版文件已成功保存到：\n{save_path}")

import pandas as pd  # 添加pandas库导入
from PyQt6.QtWidgets import QFileDialog

from zhmm.sm_data import ZhmmDict


class DataImporter:
    @staticmethod
    def import_from_file(xlsx_file_path: str) -> list[ZhmmDict] | None:
        """
        从文件导入数据
        检查文件格式
        检查文件内容
        导入数据
        返回导入结果
        """
        cn_heads = ['ID', '类别', '账号', '密码', '手机', '邮箱', '网站', '备注', '更新时间']
        en_heads = ['id', 'role', 'userID', 'pwd', 'phone', 'email', 'url', 'desc', 'utime']
        
        try:
            df = pd.read_excel(xlsx_file_path)
            
            # 检查列名是否匹配
            if not all(col in df.columns for col in cn_heads):
                print("Excel文件列名不匹配")
                return None
                
            data: list[ZhmmDict] = []
            for _, row in df.iterrows():
                item = {}
                for i, cn_col in enumerate(cn_heads):
                    cell_value = row[cn_col]
                    if isinstance(cell_value, pd.Series):
                        value = '' if cell_value.isna().all() else str(cell_value.iloc[0])
                    else:
                        value = '' if pd.isna(cell_value) else str(cell_value)
                    # 还原特殊字符
                    value = value.replace('[r]', '\r').replace('[n]', '\n')
                    item[en_heads[i]] = value
                data.append(item)           # type: ignore
                
            print(f"成功从 {xlsx_file_path} 导入 {len(data)} 条数据")
            return data
            
        except Exception as e:
            print(f"导入Excel文件失败: {str(e)}")
            return None


class DataExporter:
    """数据导出工具类"""
    @staticmethod
    def export_xlsx(file_path, data):
        """导出xlsx文件"""
        cn_heads = ['ID', '类别', '账号', '密码', '手机', '邮箱', '网站', '备注', '更新时间']
        en_heads = ['id', 'role', 'userID', 'pwd', 'phone', 'email', 'url', 'desc', 'utime']

        df = pd.DataFrame(data=None, columns=pd.Index(cn_heads))
        try:
            for item in data:
                row_data = {}
                for i, key in enumerate(en_heads):
                    value = str(item[key]) if key in item else ''
                    value = value.replace('\r', '[r]').replace('\n', '[n]')
                    row_data[cn_heads[i]] = value
                df = pd.concat([df, pd.DataFrame([row_data])], ignore_index=True)

            df.to_excel(file_path, index=False, engine='xlsxwriter')
            print(f"数据已成功导出到: {file_path}")
            return True
        except Exception as e:
            print(f"导出Excel文件失败: {str(e)}")
            try:
                csv_path = file_path.replace('.xlsx', '.csv')
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                print(f"已改为CSV格式导出到: {csv_path}")
                return True
            except Exception as csv_e:
                print(f"CSV导出也失败: {str(csv_e)}")
            return False

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

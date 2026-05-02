from typing import Any

from zhmm.utils import string_util


class TablePrinter:
    @staticmethod
    def print_list(data: list[list[Any]]) -> None:
        # 获取列的最大宽度（可选，用于对齐）
        def str_len(item: Any) -> int:
            cnt = string_util.count_unicode_chars(str(item))
            return len(str(item)) + cnt if cnt else len(str(item))

        max_widths = [max(str_len(item) for item in col) for col in zip(*data, strict=False)]

        def item_width(item: Any, width: int) -> int:
            cnt = string_util.count_unicode_chars(str(item))
            if cnt > 0:
                dc = width - len(str(item))
                dc = min(dc, cnt) if dc > 0 else 0
                return width - dc
            return width

        # 打印表头
        for item, width in zip(data[0], max_widths, strict=False):
            w = item_width(item, width)
            print(f"{item:^{w}}", end="|")
        print()

        # 打印表格内容
        for row in data[1:]:
            for item, width in zip(row, max_widths, strict=False):
                w = item_width(item, width)
                print(f"{item:<{w}}", end="|")
            print()

    @staticmethod
    def print_info(
        infos: list[dict[str, Any]],
        required_fields: list[str],
        cn_headers: list[str] | None = None,
    ) -> None:
        """
        通用信息表格打印方法

        参数：
        infos -- 字典列表，每个字典代表一条数据记录
        required_fields -- 需要展示的英文字段名列表
        cn_headers -- 可选的中文表头列表，默认为None时使用required_fields直接展示
        """

        arrs: list[list[Any]] = []
        if cn_headers:
            arrs.append(list(cn_headers))

        for info in infos:
            values: list[str] = []
            for field in required_fields:
                # 统一使用字段映射获取值
                value = info.get(field, "")
                if not isinstance(value, str):
                    value = str(value)
                values.append(value)
            arrs.append(values)

        TablePrinter.print_list(arrs)

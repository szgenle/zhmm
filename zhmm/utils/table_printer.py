from zhmm.utils import string_util

class TablePrinter:
    @staticmethod
    def print_list(data):
        # 获取列的最大宽度（可选，用于对齐）
        def str_len(item):
            cnt = string_util.count_unicode_chars(item)
            return len(str(item)) + cnt if cnt else len(str(item))

        max_widths = [max(str_len(item) for item in col) for col in zip(*data)]

        def item_width(item, width):
            cnt = string_util.count_unicode_chars(item)
            if cnt > 0:
                dc = width - len(item)
                dc = min(dc, cnt) if dc > 0 else 0
                return width - dc
            return width

        # 打印表头
        for item, width in zip(data[0], max_widths):
            w = item_width(item, width)
            print(f"{item:^{w}}", end='|')
        print()

        # 打印表格内容
        for row in data[1:]:
            for item, width in zip(row, max_widths):
                w = item_width(item, width)
                print(f"{item:<{w}}", end='|')
            print()
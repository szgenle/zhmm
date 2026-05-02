from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QDialog


class Dialog(QDialog):
    def __init__(self, geometry=None):
        super().__init__()
        self._geometry = geometry

    def setGeometry(self, *__args):  # type: ignore[override]
        # 假设 geometry 是从配置文件中读取的字符串，格式为 "x,y,width,height"
        if self._geometry:
            geometry = self._geometry

            # 解析 geometry
            if isinstance(geometry, str):
                # 将字符串解析为四个整数（仅需 x/y）
                x, y, _w, _h = map(int, geometry.split(","))
            else:
                # 如果 geometry 是 QRect 对象，只取偏移需要的 x/y
                x, y = geometry.x(), geometry.y()

            # 解析 *__args
            if len(__args) == 1 and isinstance(__args[0], QRect):
                # 如果传入的是 QRect 对象
                args_rect = __args[0]
                args_x, args_y, args_width, args_height = (
                    args_rect.x(),
                    args_rect.y(),
                    args_rect.width(),
                    args_rect.height(),
                )
            elif len(__args) == 4:
                # 如果传入的是四个整数
                args_x, args_y, args_width, args_height = __args
            else:
                raise ValueError("Invalid arguments for setGeometry")

            # 相加
            new_x = x + args_x
            new_y = y + args_y

            # 调用父类的 setGeometry
            super().setGeometry(new_x, new_y, args_width, args_height)
        else:
            super().setGeometry(*__args)

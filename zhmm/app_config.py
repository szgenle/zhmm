#
from PyQt6.QtCore import QSettings

from zhmm.utils import file_util


class AppConfig:

    def __init__(self):
        self.settings = QSettings("szgenle", "密码本")



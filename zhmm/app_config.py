#
import configparser
import os
from pathlib import Path


class AppConfig:

    def __init__(self):
        self.settings = configparser.ConfigParser()
        self.config_dir = os.path.join(str(Path.home()), '.config', 'szgenle')
        self.config_file = os.path.join(self.config_dir, 'zhmm.ini')
        
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 如果配置文件存在，则读取它
        if os.path.exists(self.config_file):
            self.settings.read(self.config_file)
            
        # 确保有默认部分
        if 'DEFAULT' not in self.settings:
            self.settings['DEFAULT'] = {}

    def get_lock_time(self):
        try:
            return self.settings.getint('DEFAULT', 'lock_time', fallback=10)
        except (ValueError, configparser.Error):
            return 10

    def save_lock_time(self, minutes):
        if 'DEFAULT' not in self.settings:
            self.settings['DEFAULT'] = {}
        self.settings['DEFAULT']['lock_time'] = str(minutes)
        self.sync()
        
    def sync(self):
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        # 写入配置文件
        with open(self.config_file, 'w') as f:
            self.settings.write(f)



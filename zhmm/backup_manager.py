#!/usr/bin/env python3
# coding=utf-8
"""
本地备份管理模块
提供自动备份、备份清理、备份恢复等功能
"""
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from zhmm.utils.log import logger


class BackupManager:
    """本地备份管理器"""

    def __init__(self, backup_dir: Optional[str] = None):
        """
        初始化备份管理器

        Args:
            backup_dir: 备份目录路径，如为None则使用默认目录
        """
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            from zhmm.utils import file_util
            self.backup_dir = file_util.get_full_path(".backups")

        # 确保备份目录存在
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, file_path: str, prefix: str = "backup", config_file: Optional[str] = None) -> Optional[str]:
        """
        创建备份文件（同时备份数据文件和配置文件）

        Args:
            file_path: 要备份的数据文件路径
            prefix: 备份文件名前缀
            config_file: 配置文件路径，如果提供则一起备份

        Returns:
            备份文件路径，失败返回None
        """
        try:
            source_path = Path(file_path)
            if not source_path.exists():
                logger.warning(f"备份失败：源文件不存在 {file_path}")
                return None

            # 生成备份文件名：prefix_原文件名_时间戳.gl
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_name = source_path.stem  # 不含扩展名的文件名
            backup_name = f"{prefix}_{original_name}_{timestamp}.gl"
            backup_path = self.backup_dir / backup_name

            # 复制数据文件
            shutil.copy2(source_path, backup_path)
            logger.info(f"数据文件备份成功：{backup_path}")

            # 如果提供了配置文件，也一起备份
            if config_file:
                config_source = Path(config_file)
                if config_source.exists():
                    config_backup_name = f"{prefix}_{original_name}_{timestamp}.config"
                    config_backup_path = self.backup_dir / config_backup_name
                    shutil.copy2(config_source, config_backup_path)
                    logger.info(f"配置文件备份成功：{config_backup_path}")
                else:
                    logger.warning(f"配置文件不存在，跳过备份：{config_file}")

            return str(backup_path)

        except Exception as e:
            logger.error(f"创建备份失败：{e}")
            return None

    def get_backup_list(self, prefix: str = "backup", pattern: str = "*.gl") -> List[Path]:
        """
        获取备份文件列表（按时间倒序）

        Args:
            prefix: 备份文件名前缀
            pattern: 文件匹配模式

        Returns:
            备份文件路径列表
        """
        try:
            # 查找所有符合条件的备份文件
            backups = [
                f for f in self.backup_dir.glob(pattern)
                if f.is_file() and f.name.startswith(prefix)
            ]
            # 按修改时间倒序排列
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return backups
        except Exception as e:
            logger.error(f"获取备份列表失败：{e}")
            return []

    def cleanup_old_backups(self, keep_count: int, prefix: str = "backup") -> int:
        """
        清理旧备份，保留最新的N个

        Args:
            keep_count: 保留的备份数量
            prefix: 备份文件名前缀

        Returns:
            删除的备份数量
        """
        try:
            backups = self.get_backup_list(prefix)
            if len(backups) <= keep_count:
                return 0

            # 删除超出保留数量的旧备份
            deleted_count = 0
            for backup in backups[keep_count:]:
                try:
                    backup.unlink()
                    logger.info(f"删除旧备份：{backup}")
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"删除备份失败 {backup}：{e}")

            return deleted_count

        except Exception as e:
            logger.error(f"清理旧备份失败：{e}")
            return 0

    def restore_backup(self, backup_path: str, target_path: str, restore_config: bool = True) -> bool:
        """
        恢复备份文件（同时恢复配置文件如果存在）

        Args:
            backup_path: 备份文件路径
            target_path: 恢复目标路径
            restore_config: 是否同时恢复配置文件

        Returns:
            成功返回True，失败返回False
        """
        try:
            backup = Path(backup_path)
            target = Path(target_path)

            if not backup.exists():
                logger.error(f"备份文件不存在：{backup_path}")
                return False

            # 如果目标文件存在，先备份当前文件
            if target.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safety_backup = target.parent / f"{target.stem}_before_restore_{timestamp}{target.suffix}"
                shutil.copy2(target, safety_backup)
                logger.info(f"当前数据文件已备份到：{safety_backup}")

            # 恢复数据备份
            shutil.copy2(backup, target)
            logger.info(f"数据备份恢复成功：{backup_path} -> {target_path}")

            # 尝试恢复配置文件（如果存在）
            if restore_config:
                config_backup = backup.parent / backup.name.replace(".gl", ".config")
                if config_backup.exists():
                    # 获取配置文件目标路径
                    from zhmm.utils import file_util
                    config_target = file_util.get_full_path(target.stem)

                    # 备份当前配置文件
                    if config_target.exists():
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        config_safety_backup = config_target.parent / f"{config_target.stem}_before_restore_{timestamp}"
                        shutil.copy2(config_target, config_safety_backup)
                        logger.info(f"当前配置文件已备份到：{config_safety_backup}")

                    # 恢复配置备份
                    shutil.copy2(config_backup, config_target)
                    logger.info(f"配置备份恢复成功：{config_backup} -> {config_target}")
                else:
                    logger.info("未找到对应的配置备份文件")

            return True

        except Exception as e:
            logger.error(f"恢复备份失败：{e}")
            return False

    def get_backup_size(self) -> int:
        """
        获取备份目录总大小（字节）

        Returns:
            备份目录总大小
        """
        try:
            total_size = 0
            for file in self.backup_dir.glob("*"):
                if file.is_file() and (file.suffix == ".gl" or file.suffix == ".config"):
                    total_size += file.stat().st_size
            return total_size
        except Exception as e:
            logger.error(f"获取备份大小失败：{e}")
            return 0

    def format_size(self, size_bytes: int) -> str:
        """
        格式化文件大小

        Args:
            size_bytes: 字节数

        Returns:
            格式化后的大小字符串（如 "1.5 MB"）
        """
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

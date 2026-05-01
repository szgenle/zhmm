"""本地备份服务：数据文件（.gl）+ 可选配置文件一起备份。

相比老 `BackupManager`：
- 不依赖 PyQt6 (file_util.get_full_path)，目录由调用方注入
- 所有路径统一用 `pathlib.Path`
- 失败抛 `StorageError`，不再返回 None 遮蔽错误
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from zhmm.core.errors import StorageError

DATA_SUFFIX = ".gl"
CONFIG_SUFFIX = ".config"


class BackupService:
    """在指定目录下管理备份文件。"""

    def __init__(self, backup_dir: str | Path) -> None:
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    # ---------- 创建 ----------

    def create(
        self,
        data_file: str | Path,
        prefix: str = "backup",
        config_file: str | Path | None = None,
        now: datetime | None = None,
    ) -> Path:
        """创建一次备份；返回数据备份文件路径。

        Raises:
            StorageError: 源数据文件不存在或复制失败
        """
        src = Path(data_file)
        if not src.exists():
            raise StorageError(f"source not found: {src}")
        ts = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
        stem = src.stem
        data_dst = self.backup_dir / f"{prefix}_{stem}_{ts}{DATA_SUFFIX}"
        try:
            shutil.copy2(src, data_dst)
        except OSError as e:
            raise StorageError(f"copy failed: {src} -> {data_dst}: {e}") from e

        if config_file:
            cfg_src = Path(config_file)
            if cfg_src.exists():
                cfg_dst = self.backup_dir / f"{prefix}_{stem}_{ts}{CONFIG_SUFFIX}"
                try:
                    shutil.copy2(cfg_src, cfg_dst)
                except OSError as e:
                    raise StorageError(
                        f"copy failed: {cfg_src} -> {cfg_dst}: {e}"
                    ) from e
        return data_dst

    # ---------- 查询 ----------

    def list(self, prefix: str = "backup", pattern: str = "*" + DATA_SUFFIX) -> list[Path]:
        """列出所有符合 prefix+pattern 的备份，按修改时间倒序。"""
        items = [
            p
            for p in self.backup_dir.glob(pattern)
            if p.is_file() and p.name.startswith(prefix)
        ]
        items.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return items

    def total_size(self) -> int:
        """统计备份目录中数据+配置文件的总字节数。"""
        total = 0
        for p in self.backup_dir.iterdir():
            if p.is_file() and p.suffix in (DATA_SUFFIX, CONFIG_SUFFIX):
                total += p.stat().st_size
        return total

    # ---------- 清理 ----------

    def cleanup(self, keep: int, prefix: str = "backup") -> int:
        """保留最新的 keep 个，其余删除；返回实际删除数量。"""
        if keep < 0:
            raise ValueError("keep must be non-negative")
        items = self.list(prefix=prefix)
        if len(items) <= keep:
            return 0
        removed = 0
        for p in items[keep:]:
            try:
                p.unlink()
                removed += 1
                # 同时删除同名 config 备份
                cfg = p.with_suffix(CONFIG_SUFFIX)
                if cfg.exists():
                    cfg.unlink()
            except OSError:
                continue
        return removed

    # ---------- 恢复 ----------

    def restore(
        self,
        backup_path: str | Path,
        target_path: str | Path,
        config_target: str | Path | None = None,
        now: datetime | None = None,
    ) -> None:
        """恢复备份到目标位置。

        行为：
        - 若目标已存在，先在其同目录下写一份 `<stem>_before_restore_<ts><suffix>` 作保险
        - 若备份同名 `.config` 也存在且提供了 `config_target`，一并恢复

        Raises:
            StorageError: 备份不存在或恢复失败
        """
        src = Path(backup_path)
        dst = Path(target_path)
        if not src.exists():
            raise StorageError(f"backup not found: {src}")
        ts = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")

        try:
            if dst.exists():
                safety = dst.parent / f"{dst.stem}_before_restore_{ts}{dst.suffix}"
                shutil.copy2(dst, safety)
            shutil.copy2(src, dst)
        except OSError as e:
            raise StorageError(f"restore failed: {src} -> {dst}: {e}") from e

        if config_target:
            cfg_backup = src.with_suffix(CONFIG_SUFFIX)
            if cfg_backup.exists():
                cfg_dst = Path(config_target)
                try:
                    if cfg_dst.exists():
                        cfg_safety = (
                            cfg_dst.parent
                            / f"{cfg_dst.stem}_before_restore_{ts}{cfg_dst.suffix}"
                        )
                        shutil.copy2(cfg_dst, cfg_safety)
                    shutil.copy2(cfg_backup, cfg_dst)
                except OSError as e:
                    raise StorageError(
                        f"config restore failed: {cfg_backup} -> {cfg_dst}: {e}"
                    ) from e

    # ---------- 工具 ----------

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """把字节数格式化为 B/KB/MB/GB/TB。"""
        size = float(size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

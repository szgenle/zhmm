"""Tests for :mod:`zhmm.core.backup_service`."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from zhmm.core.backup_service import BackupService
from zhmm.core.errors import StorageError


@pytest.fixture
def svc(tmp_path: Path) -> BackupService:
    return BackupService(tmp_path / "backups")


@pytest.fixture
def data_file(tmp_path: Path) -> Path:
    f = tmp_path / "mm.zmb"
    f.write_bytes(b"encrypted-payload")
    return f


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    f = tmp_path / "mm"
    f.write_text("config=1")
    return f


class TestCreate:
    def test_creates_data_backup(self, svc, data_file):
        now = datetime(2025, 1, 2, 3, 4, 5)
        path = svc.create(data_file, now=now)
        assert path.name == "backup_mm_20250102_030405.zmb"
        assert path.read_bytes() == b"encrypted-payload"

    def test_creates_with_config(self, svc, data_file, config_file):
        now = datetime(2025, 1, 2, 3, 4, 5)
        svc.create(data_file, config_file=config_file, now=now)
        cfg = svc.backup_dir / "backup_mm_20250102_030405.config"
        assert cfg.exists()

    def test_missing_source_raises(self, svc, tmp_path):
        with pytest.raises(StorageError):
            svc.create(tmp_path / "missing.zmb")


class TestListAndSize:
    def test_list_sorted_by_mtime_desc(self, svc, data_file):
        import os
        import time

        p1 = svc.create(data_file, now=datetime(2025, 1, 1))
        time.sleep(0.01)
        p2 = svc.create(data_file, now=datetime(2025, 1, 2))
        # mtime 受文件系统影响，这里显式调整
        os.utime(p1, (1000, 1000))
        os.utime(p2, (2000, 2000))
        lst = svc.list()
        assert lst[0] == p2 and lst[1] == p1

    def test_list_filters_prefix(self, svc, data_file):
        svc.create(data_file, prefix="snapshot", now=datetime(2025, 1, 1))
        svc.create(data_file, prefix="backup", now=datetime(2025, 1, 2))
        assert len(svc.list(prefix="snapshot")) == 1
        assert len(svc.list(prefix="backup")) == 1

    def test_total_size(self, svc, data_file, config_file):
        svc.create(data_file, config_file=config_file, now=datetime(2025, 1, 1))
        total = svc.total_size()
        assert total == len(b"encrypted-payload") + len(b"config=1")


class TestCleanup:
    def test_keep_n(self, svc, data_file):
        for i in range(5):
            svc.create(data_file, now=datetime(2025, 1, 1 + i))
        removed = svc.cleanup(keep=2)
        assert removed == 3
        assert len(svc.list()) == 2

    def test_keep_zero(self, svc, data_file):
        svc.create(data_file, now=datetime(2025, 1, 1))
        svc.create(data_file, now=datetime(2025, 1, 2))
        removed = svc.cleanup(keep=0)
        assert removed == 2
        assert svc.list() == []

    def test_negative_keep_raises(self, svc):
        with pytest.raises(ValueError):
            svc.cleanup(keep=-1)

    def test_cleanup_deletes_config_pair(self, svc, data_file, config_file):
        svc.create(data_file, config_file=config_file, now=datetime(2025, 1, 1))
        svc.create(data_file, config_file=config_file, now=datetime(2025, 1, 2))
        svc.cleanup(keep=1)
        # 被清除那一批的 config 也应消失
        remaining_configs = list(svc.backup_dir.glob("*.config"))
        assert len(remaining_configs) == 1


class TestRestore:
    def test_restore_creates_safety_backup(self, svc, data_file, tmp_path):
        b = svc.create(data_file, now=datetime(2025, 1, 1))
        target = tmp_path / "mm.zmb"
        assert target.exists()
        svc.restore(b, target, now=datetime(2025, 6, 6, 6, 6, 6))
        safety = tmp_path / "mm_before_restore_20250606_060606.zmb"
        assert safety.exists()

    def test_restore_missing_backup_raises(self, svc, tmp_path):
        with pytest.raises(StorageError):
            svc.restore(tmp_path / "nope.zmb", tmp_path / "mm.zmb")


class TestFormatSize:
    @pytest.mark.parametrize(
        "size,expected",
        [
            (0, "0.0 B"),
            (512, "512.0 B"),
            (2048, "2.0 KB"),
            (5 * 1024 * 1024, "5.0 MB"),
            (3 * 1024 * 1024 * 1024, "3.0 GB"),
        ],
    )
    def test_format(self, size, expected):
        assert BackupService.format_size(size) == expected

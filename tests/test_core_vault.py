"""Tests for :mod:`zhmm.core.vault` - 端到端文件加解密。"""

from __future__ import annotations

from pathlib import Path

import pytest

from zhmm.core.errors import CryptoError, StorageError
from zhmm.core.models import PasswordEntry, Vault
from zhmm.core.vault import VaultFile


@pytest.fixture
def sample_vault() -> Vault:
    return Vault.from_dict({
        "data": [
            {"id": 1, "role": "工作", "userID": "alice", "pwd": "s3cret!@#$%", "utime": 100},
            {"id": 2, "role": "个人", "userID": "bob",   "pwd": "另一个密码", "utime": 200},
        ],
        "roles": ["个人", "工作"],
        "utime": 500,
    })


class TestRoundtrip:
    def test_save_then_load(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "mm.gl"
        VaultFile.save(f, "correct-horse", sample_vault)
        loaded = VaultFile.load(f, "correct-horse")
        assert loaded.to_dict() == sample_vault.to_dict()

    def test_empty_vault(self, tmp_path: Path):
        f = tmp_path / "empty.gl"
        VaultFile.save(f, "pw", Vault.empty())
        loaded = VaultFile.load(f, "pw")
        assert loaded.entries == []

    def test_unicode_password(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "u.gl"
        VaultFile.save(f, "密码🔒包含emoji", sample_vault)
        loaded = VaultFile.load(f, "密码🔒包含emoji")
        assert len(loaded.entries) == 2


class TestErrors:
    def test_wrong_password_raises_crypto(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "mm.gl"
        VaultFile.save(f, "right", sample_vault)
        with pytest.raises(CryptoError):
            VaultFile.load(f, "wrong")

    def test_missing_file_raises_storage(self, tmp_path: Path):
        with pytest.raises(StorageError):
            VaultFile.load(tmp_path / "nope.gl", "pw")

    def test_corrupted_file_raises_crypto(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "mm.gl"
        VaultFile.save(f, "pw", sample_vault)
        data = bytearray(f.read_bytes())
        # 翻转 ct 最后一个字节（在 tag 之前）—— HMAC 必然失败
        data[-40] ^= 0xFF
        f.write_bytes(data)
        with pytest.raises(CryptoError):
            VaultFile.load(f, "pw")


class TestAtomicity:
    def test_no_temp_file_leftover(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "mm.gl"
        VaultFile.save(f, "pw", sample_vault)
        leftover = [p for p in tmp_path.iterdir() if p.name.startswith(".")]
        assert leftover == []

    def test_overwrite_existing(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "mm.gl"
        VaultFile.save(f, "pw", sample_vault)
        empty = Vault.empty()
        empty.entries.append(PasswordEntry(id=9, userID="new"))
        VaultFile.save(f, "pw", empty)
        loaded = VaultFile.load(f, "pw")
        assert len(loaded.entries) == 1 and loaded.entries[0].id == 9

    def test_creates_parent_dir(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "nested" / "sub" / "mm.gl"
        VaultFile.save(f, "pw", sample_vault)
        assert f.exists()

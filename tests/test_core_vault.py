"""Tests for :mod:`zhmm.core.vault` - 端到端文件加解密。"""

from __future__ import annotations

from pathlib import Path

import pytest

from zhmm.core.errors import CryptoError, StorageError
from zhmm.core.models import PasswordEntry, Vault
from zhmm.core.vault import VaultFile


@pytest.fixture
def sample_vault() -> Vault:
    return Vault.from_dict(
        {
            "data": [
                {"id": 1, "role": "工作", "userID": "alice", "pwd": "s3cret!@#$%", "utime": 100},
                {"id": 2, "role": "个人", "userID": "bob", "pwd": "另一个密码", "utime": 200},
            ],
            "roles": ["个人", "工作"],
            "utime": 500,
        }
    )


class TestRoundtrip:
    def test_save_then_load(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "mm.zmb"
        VaultFile.save(f, "alice", "correct-horse", sample_vault)
        loaded = VaultFile.load(f, "alice", "correct-horse")
        assert loaded.to_dict() == sample_vault.to_dict()

    def test_empty_vault(self, tmp_path: Path):
        f = tmp_path / "empty.zmb"
        VaultFile.save(f, "acc", "pw", Vault.empty())
        loaded = VaultFile.load(f, "acc", "pw")
        assert loaded.entries == []

    def test_unicode_account_and_password(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "u.zmb"
        VaultFile.save(f, "账号🙂", "密码🔒包含emoji", sample_vault)
        loaded = VaultFile.load(f, "账号🙂", "密码🔒包含emoji")
        assert len(loaded.entries) == 2


class TestErrors:
    def test_wrong_password_raises_crypto(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "mm.zmb"
        VaultFile.save(f, "acc", "right", sample_vault)
        with pytest.raises(CryptoError):
            VaultFile.load(f, "acc", "wrong")

    def test_wrong_account_raises_crypto(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "mm.zmb"
        VaultFile.save(f, "alice", "pw", sample_vault)
        with pytest.raises(CryptoError):
            VaultFile.load(f, "bob", "pw")

    def test_missing_file_raises_storage(self, tmp_path: Path):
        with pytest.raises(StorageError):
            VaultFile.load(tmp_path / "nope.zmb", "acc", "pw")

    def test_corrupted_file_raises_crypto(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "mm.zmb"
        VaultFile.save(f, "acc", "pw", sample_vault)
        data = bytearray(f.read_bytes())
        # 翻转 ct 最后一个字节（在 tag 之前）—— HMAC 必然失败
        data[-40] ^= 0xFF
        f.write_bytes(data)
        with pytest.raises(CryptoError):
            VaultFile.load(f, "acc", "pw")


class TestAtomicity:
    def test_no_temp_file_leftover(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "mm.zmb"
        VaultFile.save(f, "acc", "pw", sample_vault)
        leftover = [p for p in tmp_path.iterdir() if p.name.startswith(".")]
        assert leftover == []

    def test_overwrite_existing(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "mm.zmb"
        VaultFile.save(f, "acc", "pw", sample_vault)
        empty = Vault.empty()
        empty.entries.append(PasswordEntry(id=9, userID="new"))
        VaultFile.save(f, "acc", "pw", empty)
        loaded = VaultFile.load(f, "acc", "pw")
        assert len(loaded.entries) == 1 and loaded.entries[0].id == 9

    def test_creates_parent_dir(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "nested" / "sub" / "mm.zmb"
        VaultFile.save(f, "acc", "pw", sample_vault)
        assert f.exists()


class TestRekey:
    """主密码更换：原地重新派生密钥并重写密文。"""

    def test_rekey_then_load_with_new_pw(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "mm.zmb"
        VaultFile.save(f, "alice", "old-pw", sample_vault)
        VaultFile.rekey(f, "alice", "old-pw", "new-pw")
        loaded = VaultFile.load(f, "alice", "new-pw")
        assert loaded.to_dict() == sample_vault.to_dict()

    def test_rekey_old_pw_rejected(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "mm.zmb"
        VaultFile.save(f, "alice", "old-pw", sample_vault)
        VaultFile.rekey(f, "alice", "old-pw", "new-pw")
        with pytest.raises(CryptoError):
            VaultFile.load(f, "alice", "old-pw")

    def test_rekey_wrong_old_pw_raises_and_file_untouched(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "mm.zmb"
        VaultFile.save(f, "alice", "right", sample_vault)
        before = f.read_bytes()
        with pytest.raises(CryptoError):
            VaultFile.rekey(f, "alice", "wrong", "new-pw")
        after = f.read_bytes()
        assert before == after
        # 旧密码仍可用
        loaded = VaultFile.load(f, "alice", "right")
        assert loaded.to_dict() == sample_vault.to_dict()

    def test_rekey_is_atomic_no_tmp_leftover(self, tmp_path: Path, sample_vault: Vault):
        f = tmp_path / "mm.zmb"
        VaultFile.save(f, "alice", "old-pw", sample_vault)
        VaultFile.rekey(f, "alice", "old-pw", "new-pw")
        leftover = [p for p in tmp_path.iterdir() if p.name.startswith(".")]
        assert leftover == []

    def test_rekey_missing_file_raises_storage(self, tmp_path: Path):
        with pytest.raises(StorageError):
            VaultFile.rekey(tmp_path / "nope.zmb", "acc", "old", "new")

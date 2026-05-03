"""Tests for :mod:`zhmm.core.password_service`."""

from __future__ import annotations

import pytest

from zhmm.core.models import PasswordEntry
from zhmm.core.password_service import PasswordService


class FakeClock:
    def __init__(self, start: int = 1000):
        self.t = start

    def __call__(self) -> int:
        return self.t

    def tick(self, n: int = 1):
        self.t += n


@pytest.fixture
def svc():
    clock = FakeClock(1000)
    service = PasswordService(clock=clock)
    service._fake_clock = clock  # type: ignore[attr-defined]
    return service


class TestAdd:
    def test_add_autofills(self, svc):
        e = svc.add(PasswordEntry(userID="a", pwd="b"))
        assert e.id == 1000 and e.utime == 1000 and e.role == "个人"
        assert svc.vault.utime == 1000

    def test_add_custom_role_pushed_to_roles(self, svc):
        svc.add(PasswordEntry(role="游戏", userID="a", pwd="b"))
        assert "游戏" in svc.vault.roles

    def test_add_preserves_provided_id(self, svc):
        e = svc.add(PasswordEntry(id=42, userID="u", pwd="p"))
        assert e.id == 42


class TestDelete:
    def test_delete_existing(self, svc):
        svc.add(PasswordEntry(id=1, userID="a", pwd="x"))
        svc.add(PasswordEntry(id=2, userID="b", pwd="y"))
        assert svc.delete(1) is True
        assert len(svc.vault.entries) == 1
        assert svc.vault.entries[0].id == 2

    def test_delete_missing(self, svc):
        svc.add(PasswordEntry(id=1, userID="a", pwd="x"))
        assert svc.delete(999) is False


class TestUpdate:
    def test_update_fields(self, svc):
        svc.add(PasswordEntry(id=1, userID="a", pwd="x"))
        svc._fake_clock.tick(5)
        res = svc.update(1, pwd="NEW")
        assert res is not None
        assert res.pwd == "NEW"
        assert res.utime == 1005

    def test_update_missing(self, svc):
        assert svc.update(999, pwd="x") is None

    def test_update_adds_new_role(self, svc):
        svc.add(PasswordEntry(id=1, userID="a", pwd="x"))
        svc.update(1, role="临时")
        assert "临时" in svc.vault.roles


class TestSearch:
    def _seed(self, svc):
        svc.add(PasswordEntry(id=1, userID="alice", url="github.com", desc="code"))
        svc.add(PasswordEntry(id=2, userID="bob", url="bank.com", desc="finance"))
        svc.add(PasswordEntry(id=3, userID="carol", email="c@example.com", desc="mail"))

    def test_search_single_word_case_insensitive(self, svc):
        self._seed(svc)
        results = svc.search("GITHUB")
        assert [e.id for e in results] == [1]

    def test_search_multiple_words_or(self, svc):
        self._seed(svc)
        results = svc.search("bank example")
        assert sorted(e.id for e in results) == [2, 3]

    def test_search_empty_returns_empty(self, svc):
        self._seed(svc)
        assert svc.search("") == []
        assert svc.search("   ") == []

    def test_search_no_match(self, svc):
        self._seed(svc)
        assert svc.search("nothing-here") == []

    def test_search_dedup(self, svc):
        # 同一条目命中多个关键字应只出现一次
        svc.add(PasswordEntry(id=1, userID="alice", url="bank.com", desc="bank"))
        results = svc.search("bank alice")
        assert len(results) == 1

    def test_search_matches_tag(self, svc):
        # 标签文本也应进入搜索范围
        svc.add(PasswordEntry(id=1, userID="alice", tags=["work", "prod"]))
        svc.add(PasswordEntry(id=2, userID="bob", tags=["personal"]))
        results = svc.search("prod")
        assert [e.id for e in results] == [1]
        results = svc.search("PERSONAL")
        assert [e.id for e in results] == [2]


class TestFixMissingIds:
    def test_fills_missing(self, svc):
        svc.vault.entries.append(PasswordEntry(id=0, userID="a"))
        svc.vault.entries.append(PasswordEntry(id=0, userID="b"))
        fixed = svc.fix_missing_ids()
        assert fixed == 2
        ids = [e.id for e in svc.vault.entries]
        assert ids == [1000, 1001]
        assert all(e.utime == 1000 for e in svc.vault.entries)

    def test_noop_when_complete(self, svc):
        svc.vault.entries.append(PasswordEntry(id=5, userID="a", utime=9))
        assert svc.fix_missing_ids() == 0


class TestMerge:
    def test_append_new(self, svc):
        svc.add(PasswordEntry(id=1, userID="a", pwd="x", utime=10))
        a, u = svc.merge([PasswordEntry(id=2, userID="b", pwd="y", utime=20)])
        assert (a, u) == (1, 0)
        assert len(svc.vault.entries) == 2

    def test_update_newer(self, svc):
        svc.add(PasswordEntry(id=1, userID="a", pwd="x", utime=10))
        a, u = svc.merge([PasswordEntry(id=1, userID="a", pwd="NEW", utime=20)])
        assert (a, u) == (0, 1)
        assert svc.get(1).pwd == "NEW"

    def test_skip_older(self, svc):
        svc.add(PasswordEntry(id=1, userID="a", pwd="x", utime=100))
        a, u = svc.merge([PasswordEntry(id=1, userID="a", pwd="old", utime=10)])
        assert (a, u) == (0, 0)
        assert svc.get(1).pwd == "x"

    def test_skip_identical(self, svc):
        svc.add(PasswordEntry(id=1, userID="a", pwd="x", utime=10, role="个人"))
        dup = PasswordEntry(id=1, userID="a", pwd="x", utime=10, role="个人")
        a, u = svc.merge([dup])
        assert (a, u) == (0, 0)

    def test_ignore_no_id(self, svc):
        a, u = svc.merge([PasswordEntry(id=0, userID="a", pwd="x")])
        assert (a, u) == (0, 0)

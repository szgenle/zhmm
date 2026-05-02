"""Tests for :mod:`zhmm.core.models`."""

from __future__ import annotations

from zhmm.core.models import DEFAULT_ROLE, DEFAULT_ROLES, PasswordEntry, Vault


class TestPasswordEntry:
    def test_defaults(self):
        e = PasswordEntry()
        assert e.id == 0
        assert e.role == DEFAULT_ROLE
        assert e.userID == "" and e.pwd == ""

    def test_to_from_dict_roundtrip(self):
        e = PasswordEntry(id=1, role="工作", userID="u", pwd="p", utime=100)
        e2 = PasswordEntry.from_dict(e.to_dict())
        assert e == e2

    def test_from_dict_ignores_unknown_and_none(self):
        e = PasswordEntry.from_dict(
            {
                "id": 1,
                "userID": None,
                "unknown": "xxx",
                "role": "",
            }
        )
        assert e.id == 1
        assert e.userID == ""
        assert e.role == DEFAULT_ROLE  # 空串会回落到默认

    def test_clone(self):
        e = PasswordEntry(id=1, pwd="a")
        e2 = e.clone(pwd="b")
        assert e.pwd == "a"  # 原对象未改
        assert e2.pwd == "b" and e2.id == 1

    def test_totp_fields_default_and_roundtrip(self):
        # 默认值：secret 空串、algo 空串、digits=6、period=30
        e = PasswordEntry()
        assert e.totp_secret == ""
        assert e.totp_algo == ""
        assert e.totp_digits == 6
        assert e.totp_period == 30

        e2 = PasswordEntry(
            id=1,
            userID="u",
            pwd="p",
            totp_secret="JBSWY3DPEHPK3PXP",
            totp_algo="SM3",
            totp_digits=8,
            totp_period=60,
        )
        d = e2.to_dict()
        assert d["totp_secret"] == "JBSWY3DPEHPK3PXP"
        assert d["totp_algo"] == "SM3"
        assert d["totp_digits"] == 8
        assert d["totp_period"] == 60
        assert PasswordEntry.from_dict(d) == e2

    def test_from_dict_missing_totp_uses_defaults(self):
        # 老 JSON 无 TOTP 字段时应回落到默认值
        e = PasswordEntry.from_dict({"id": 1, "userID": "u", "pwd": "p"})
        assert e.totp_secret == ""
        assert e.totp_algo == ""
        assert e.totp_digits == 6
        assert e.totp_period == 30


class TestVault:
    def test_empty(self):
        v = Vault.empty()
        assert v.entries == []
        assert list(v.roles) == list(DEFAULT_ROLES)
        assert v.utime == 0

    def test_from_dict_collects_unknown_roles(self):
        v = Vault.from_dict(
            {
                "data": [
                    {"id": 1, "role": "新类别", "userID": "u", "pwd": "p"},
                ],
                "roles": ["个人"],
                "utime": 123,
            }
        )
        assert "新类别" in v.roles
        assert v.utime == 123
        assert len(v.entries) == 1

    def test_from_dict_empty_roles_defaults(self):
        v = Vault.from_dict({"data": [], "roles": [], "utime": 0})
        assert list(v.roles) == list(DEFAULT_ROLES)

    def test_to_dict_roundtrip(self):
        v = Vault.from_dict(
            {
                "data": [{"id": 1, "role": "工作", "userID": "u", "pwd": "p", "utime": 100}],
                "roles": ["工作"],
                "utime": 200,
            }
        )
        d = v.to_dict()
        v2 = Vault.from_dict(d)
        assert v2.entries == v.entries
        assert v2.roles == v.roles
        assert v2.utime == v.utime

    def test_from_dict_skips_non_dict_entries(self):
        v = Vault.from_dict({"data": [None, "bad", {"id": 1}], "roles": []})
        assert len(v.entries) == 1
        assert v.entries[0].id == 1

    def test_utime_non_numeric_falls_back_to_zero(self):
        v = Vault.from_dict({"data": [], "roles": [], "utime": "not-a-number"})
        assert v.utime == 0

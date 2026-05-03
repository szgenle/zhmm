"""Tests for :mod:`zhmm.core.models`."""

from __future__ import annotations

from zhmm.core.models import (
    DEFAULT_ROLE,
    DEFAULT_ROLES,
    TAG_MAX_LEN,
    TAGS_MAX_COUNT,
    PasswordEntry,
    Vault,
    normalize_tags,
)


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

    # ----------------------------- tags -----------------------------
    def test_tags_default_empty_list(self):
        e = PasswordEntry()
        assert e.tags == []
        # 默认值独立，不应共享列表实例
        assert PasswordEntry().tags is not e.tags

    def test_from_dict_missing_tags_uses_default(self):
        e = PasswordEntry.from_dict({"id": 1, "userID": "u"})
        assert e.tags == []

    def test_from_dict_tags_none_becomes_empty(self):
        e = PasswordEntry.from_dict({"id": 1, "userID": "u", "tags": None})
        assert e.tags == []

    def test_from_dict_tags_non_list_becomes_empty(self):
        # 传入 dict / int 等非法形态，不能报错
        e = PasswordEntry.from_dict({"id": 1, "userID": "u", "tags": {"a": 1}})
        assert e.tags == []

    def test_from_dict_tags_filters_non_str_and_blank(self):
        e = PasswordEntry.from_dict({"id": 1, "userID": "u", "tags": ["work", " ", "", None, 42, "prod"]})
        assert e.tags == ["work", "prod"]

    def test_from_dict_tags_dedup_preserves_order(self):
        e = PasswordEntry.from_dict({"id": 1, "userID": "u", "tags": ["a", "b", "a", " b ", "c"]})
        assert e.tags == ["a", "b", "c"]

    def test_to_from_dict_tags_roundtrip(self):
        e = PasswordEntry(id=1, userID="u", pwd="p", tags=["work", "prod"])
        d = e.to_dict()
        assert d["tags"] == ["work", "prod"]
        assert PasswordEntry.from_dict(d) == e

    def test_from_dict_tags_truncates_long_tag(self):
        long_tag = "x" * (TAG_MAX_LEN + 5)
        e = PasswordEntry.from_dict({"id": 1, "userID": "u", "tags": [long_tag]})
        assert e.tags == ["x" * TAG_MAX_LEN]

    def test_from_dict_tags_caps_count(self):
        tags = [f"t{i}" for i in range(TAGS_MAX_COUNT + 5)]
        e = PasswordEntry.from_dict({"id": 1, "userID": "u", "tags": tags})
        assert len(e.tags) == TAGS_MAX_COUNT
        assert e.tags[0] == "t0" and e.tags[-1] == f"t{TAGS_MAX_COUNT - 1}"


class TestNormalizeTags:
    def test_none_empty(self):
        assert normalize_tags(None) == []
        assert normalize_tags([]) == []
        assert normalize_tags("") == []

    def test_string_semicolon_split(self):
        # 兼容 Excel 场景：单元格直接进来的字符串按 ; 拆分
        assert normalize_tags("a;b; c ") == ["a", "b", "c"]
        assert normalize_tags(" ; ; ") == []

    def test_tuple_input(self):
        assert normalize_tags(("a", "b")) == ["a", "b"]

    def test_unsupported_type(self):
        assert normalize_tags(123) == []
        assert normalize_tags({"a": 1}) == []


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

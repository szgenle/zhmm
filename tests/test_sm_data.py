"""Tests for :class:`zhmm.data.sm_data_manager.SmData`.

覆盖：
- #J 搜索增强：全/半角统一、role 纳入默认字段、mode=any/all 语义
- #M 会话擦除：close() 清空已解密条目与账号/密码引用
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from zhmm.data.sm_data_manager import SmData, _normalize_search_text
from zhmm.data.sm_data_types import ZhmmDataDict, ZhmmDict


def _make_sm(items: list[dict[str, Any]]) -> SmData:
    sm = SmData()
    # 直接通过 set_mm 注入，避免走加密/文件 IO
    mm: ZhmmDataDict = {
        "data": cast("list[ZhmmDict]", items),
        "roles": ["个人", "工作"],
        "utime": 0,
    }
    sm.set_mm(mm)
    return sm


class TestNormalizeSearchText:
    def test_fullwidth_digits_normalized(self):
        # 全角数字 "１２３" -> "123"
        assert _normalize_search_text("１２３") == "123"

    def test_fullwidth_space_normalized(self):
        assert _normalize_search_text("hello\u3000world") == "hello world"

    def test_lowercased(self):
        assert _normalize_search_text("GitHub") == "github"

    def test_empty_returns_empty(self):
        assert _normalize_search_text("") == ""


class TestSearch:
    def test_search_matches_role_field(self):
        # 之前漏掉的 role（类别）现在应能匹配
        sm = _make_sm(
            [
                {"id": 1, "role": "工作", "userID": "a", "pwd": "", "url": "", "desc": ""},
                {"id": 2, "role": "个人", "userID": "b", "pwd": "", "url": "", "desc": ""},
            ]
        )
        hits = sm.search("工作") or []
        assert len(hits) == 1
        assert hits[0]["id"] == 1

    def test_search_fullwidth_query_matches_halfwidth_field(self):
        sm = _make_sm(
            [
                {"id": 1, "role": "个人", "userID": "user123", "pwd": "", "url": "", "desc": ""},
            ]
        )
        # 全角 "１２３" 的查询应能命中半角 "user123"
        hits = sm.search("１２３") or []
        assert len(hits) == 1

    def test_search_case_insensitive(self):
        sm = _make_sm([{"id": 1, "role": "个人", "userID": "", "pwd": "", "url": "GitHub.com", "desc": ""}])
        assert len(sm.search("github") or []) == 1
        assert len(sm.search("GITHUB") or []) == 1

    def test_search_mode_all_requires_all_tokens(self):
        sm = _make_sm(
            [
                {"id": 1, "role": "个人", "userID": "alice", "pwd": "", "url": "example.com", "desc": "blog"},
                {"id": 2, "role": "工作", "userID": "alice", "pwd": "", "url": "corp.net", "desc": ""},
            ]
        )
        # any: alice 或 example 任一命中
        assert len(sm.search("alice example", mode="any") or []) == 2
        # all: 必须同时包含 alice 和 example
        hits = sm.search("alice example", mode="all") or []
        assert len(hits) == 1
        assert hits[0]["id"] == 1

    def test_search_tags_field(self):
        sm = _make_sm(
            [
                {
                    "id": 1,
                    "role": "个人",
                    "userID": "",
                    "pwd": "",
                    "url": "",
                    "desc": "",
                    "tags": ["社交", "重要"],
                }
            ]
        )
        assert len(sm.search("重要") or []) == 1

    def test_search_pwd_never_matched(self):
        # 即使密码里包含关键字也不应被搜索到
        sm = _make_sm([{"id": 1, "role": "个人", "userID": "a", "pwd": "secret_keyword", "url": "", "desc": ""}])
        assert sm.search("secret_keyword") is None

    def test_search_empty_query_returns_none(self):
        sm = _make_sm([{"id": 1, "role": "个人", "userID": "a", "pwd": "", "url": "u", "desc": "d"}])
        assert sm.search("") is None
        assert sm.search("   ") is None

    def test_search_invalid_mode_raises(self):
        sm = _make_sm([{"id": 1, "role": "个人", "userID": "a", "pwd": "", "url": "", "desc": ""}])
        with pytest.raises(ValueError):
            sm.search("a", mode="weird")  # type: ignore[arg-type]


class TestClose:
    def test_close_clears_data_and_credentials(self):
        sm = SmData()
        sm.init("alice", "pw")
        sm.set_mm(
            {
                "data": [{"id": 1, "role": "个人", "userID": "u", "pwd": "s", "url": "", "desc": ""}],
                "roles": ["个人"],
                "utime": 123,
            }
        )
        assert sm._account == "alice"
        assert sm._password == "pw"
        assert len(sm.mm["data"]) == 1

        sm.close()

        assert sm._account == ""
        assert sm._password == ""
        assert sm.mm["data"] == []
        # roles 会被重置为 DEFAULT_ROLES
        assert isinstance(sm.mm["roles"], list)

    def test_close_is_idempotent(self):
        sm = SmData()
        sm.close()
        sm.close()  # 再次调用不应抛异常
        assert sm._account == ""
        assert sm._password == ""

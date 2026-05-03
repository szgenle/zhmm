"""Tests for zhmm.utils.url_util."""

from __future__ import annotations

import pytest

from zhmm.utils import url_util


class TestExtractHost:
    def test_empty_and_invalid(self):
        assert url_util.extract_host(None) == ""
        assert url_util.extract_host("") == ""
        assert url_util.extract_host("   ") == ""
        assert url_util.extract_host(123) == ""  # type: ignore[arg-type]

    def test_strip_scheme_and_path(self):
        assert url_util.extract_host("https://www.baidu.com/search?q=1") == "baidu.com"
        assert url_util.extract_host("http://GitHub.com/repo") == "github.com"

    def test_no_scheme_auto_prefix(self):
        assert url_util.extract_host("weixin.qq.com") == "weixin.qq.com"
        assert url_util.extract_host("   www.jd.com   ") == "jd.com"

    def test_lowercase(self):
        assert url_util.extract_host("https://ICBC.COM.CN") == "icbc.com.cn"


class TestRegistrableDomain:
    @pytest.mark.parametrize(
        "inp,expected",
        [
            # 普通二级域名
            ("https://www.baidu.com", "baidu.com"),
            ("mail.google.com", "google.com"),
            ("a.b.c.example.org", "example.org"),
            # 中国多级后缀
            ("login.icbc.com.cn", "icbc.com.cn"),
            ("www.beian.gov.cn", "beian.gov.cn"),
            ("portal.tsinghua.edu.cn", "tsinghua.edu.cn"),
            # 日本 / 英国多级后缀
            ("https://foo.co.jp/login", "foo.co.jp"),
            ("news.bbc.co.uk", "bbc.co.uk"),
            # 单标签 / 本地 / IP
            ("localhost", "localhost"),
            ("127.0.0.1", "127.0.0.1"),
            # 空输入
            ("", ""),
            (None, ""),
        ],
    )
    def test_registrable_domain(self, inp, expected):
        assert url_util.registrable_domain(inp) == expected


class TestNormalizeUrl:
    def test_empty(self):
        assert url_util.normalize_url(None) == ""
        assert url_util.normalize_url("") == ""

    def test_auto_scheme(self):
        assert url_util.normalize_url("baidu.com") == "https://baidu.com"

    def test_keep_path_and_query(self):
        assert url_util.normalize_url("http://jd.com/item?id=1") == "http://jd.com/item?id=1"

    def test_strip_default_port(self):
        assert url_util.normalize_url("http://x.com:80/") == "http://x.com/"
        assert url_util.normalize_url("https://x.com:443") == "https://x.com"

    def test_keep_nonstandard_port(self):
        assert url_util.normalize_url("http://x.com:8080/a") == "http://x.com:8080/a"

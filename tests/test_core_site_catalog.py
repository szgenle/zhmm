"""Tests for zhmm.core.site_catalog."""

from __future__ import annotations

import pytest

from zhmm.core import site_catalog


@pytest.fixture(autouse=True)
def _reset_cache():
    # 每个用例使用真实词典 JSON，但清缓存以免用例间污染
    site_catalog.reload_catalog()
    yield
    site_catalog.reload_catalog()


class TestSuggest:
    def test_empty_input_returns_empty(self):
        for x in (None, "", "   "):
            s = site_catalog.suggest(x)
            assert s.is_empty()
            assert s.matched == ""

    def test_host_exact_match(self):
        # mail.qq.com 在词典里是独立条目
        s = site_catalog.suggest("https://mail.qq.com/inbox")
        assert s.matched == "host"
        assert s.name == "QQ 邮箱"
        assert "邮箱" in s.tags

    def test_domain_match_via_subdomain(self):
        # login.icbc.com.cn 应命中根域名 icbc.com.cn
        s = site_catalog.suggest("https://login.icbc.com.cn/perbank")
        assert s.matched == "domain"
        assert s.name == "工商银行"
        assert "银行" in s.tags

    def test_domain_match_plain(self):
        # www.github.com 剔除 www. 后 == github.com（本身在词典），属 host 命中
        s = site_catalog.suggest("https://www.github.com/user/repo")
        assert s.matched == "host"
        assert s.name == "GitHub"
        assert "开发" in s.tags

    def test_domain_match_via_unknown_subdomain(self):
        # 未收录的子域 → 应回落到词典中的根域 jd.com
        s = site_catalog.suggest("https://foo.bar.jd.com/detail")
        assert s.matched == "domain"
        assert s.name == "京东"

    def test_fallback_rule_gov_cn(self):
        # 未收录的 *.gov.cn 应由兜底规则返回「政务」
        s = site_catalog.suggest("https://unknown-agency.gov.cn")
        assert s.matched == "rule"
        assert s.name == ""
        assert "政务" in s.tags

    def test_fallback_rule_edu_cn(self):
        s = site_catalog.suggest("https://xyz.edu.cn")
        assert s.matched == "rule"
        assert "教育" in s.tags

    def test_fallback_rule_keyword_bank(self):
        # 未收录的带 bank 关键字域名 → 金融 / 银行
        s = site_catalog.suggest("https://mybank-unknown.com/login")
        assert s.matched == "rule"
        assert "金融" in s.tags
        assert "银行" in s.tags

    def test_no_match_returns_empty(self):
        # 不太可能命中词典也无关键字的域名
        s = site_catalog.suggest("https://zzz-random-987654321.example")
        assert s.is_empty()

    def test_input_without_scheme(self):
        s = site_catalog.suggest("jd.com")
        assert s.matched == "host"
        assert s.name == "京东"

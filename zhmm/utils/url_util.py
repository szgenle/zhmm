"""URL 规范化与根域名提取工具（纯离线，无网络请求）。

用途：
- 为 GUI 层根据用户输入的网址做「站点建议」：提取可识别的根域名，
  然后交给 ``zhmm.core.site_catalog`` 去匹配本地词典 / 规则。

设计约束：
- 不依赖第三方 ``tldextract`` / ``publicsuffix2`` 等大依赖；
  内置一小组常见的「多级公共后缀」覆盖 90%+ 常用场景（尤其中国站点）。
- 函数均为纯函数，不抛异常：输入异常时统一返回空串 / ``None``。
"""

from __future__ import annotations

from urllib.parse import urlsplit

# 常见多级公共后缀（registrable TLD 的第二段）。
# 仅覆盖可能出现在用户密码条目中的主流场景，避免引入整份 PSL。
# 规则：host 以 ``.<X>.<Y>`` 结尾且 ``<X>.<Y>`` 命中该集合时，把倒数第三段作为主域名。
_MULTI_LEVEL_SUFFIXES: frozenset[str] = frozenset(
    {
        # 中国
        "com.cn",
        "net.cn",
        "org.cn",
        "gov.cn",
        "edu.cn",
        "ac.cn",
        "mil.cn",
        # 香港 / 台湾
        "com.hk",
        "org.hk",
        "gov.hk",
        "edu.hk",
        "com.tw",
        "org.tw",
        "gov.tw",
        "edu.tw",
        # 日本 / 韩国
        "co.jp",
        "or.jp",
        "ne.jp",
        "ac.jp",
        "go.jp",
        "co.kr",
        "or.kr",
        # 英国 / 澳大利亚
        "co.uk",
        "org.uk",
        "ac.uk",
        "gov.uk",
        "com.au",
        "org.au",
        "gov.au",
        "edu.au",
    }
)


def normalize_url(raw: str | None) -> str:
    """规范化用户输入的 URL。

    - ``None`` / 非字符串 / 空白 → 返回空串
    - 自动补全缺失的 ``scheme``（默认 ``https://``）
    - 返回去除尾部 ``#`` 锚与默认端口后的紧凑形式，仅用于内部匹配
    """
    if not isinstance(raw, str):
        return ""
    s = raw.strip()
    if not s:
        return ""
    # 补全 scheme：``baidu.com`` → ``https://baidu.com``
    lower = s.lower()
    if not (lower.startswith("http://") or lower.startswith("https://") or "://" in lower):
        s = "https://" + s
    try:
        parts = urlsplit(s)
    except ValueError:
        return ""
    host = (parts.hostname or "").lower()
    if not host:
        return ""
    # 去除默认端口（80/443）
    netloc = host
    if parts.port and parts.port not in (80, 443):
        netloc = f"{host}:{parts.port}"
    path = parts.path or ""
    if parts.query:
        path = f"{path}?{parts.query}"
    return f"{parts.scheme}://{netloc}{path}" if path else f"{parts.scheme}://{netloc}"


def extract_host(raw: str | None) -> str:
    """从原始输入中提取小写 host（不含端口、不含 www. 前缀）。

    空输入或解析失败返回空串。
    """
    if not isinstance(raw, str):
        return ""
    s = raw.strip()
    if not s:
        return ""
    lower = s.lower()
    if not (lower.startswith("http://") or lower.startswith("https://") or "://" in lower):
        s = "https://" + s
    try:
        parts = urlsplit(s)
    except ValueError:
        return ""
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def registrable_domain(host_or_url: str | None) -> str:
    """提取可识别的「根域名」（registrable domain）。

    例：
    - ``mail.google.com``            → ``google.com``
    - ``www.beian.gov.cn``           → ``beian.gov.cn``
    - ``login.icbc.com.cn``          → ``icbc.com.cn``
    - ``https://foo.co.jp/login``    → ``foo.co.jp``
    - ``localhost``                  → ``localhost``  （无点视为单标签）
    - ``127.0.0.1``                  → ``127.0.0.1``  （IP 原样返回）
    """
    host = extract_host(host_or_url)
    if not host:
        return ""
    # IP 地址或无点的主机名（localhost）原样返回
    if _looks_like_ip(host) or "." not in host:
        return host
    labels = host.split(".")
    # 末两段拼起来看看是否命中多级后缀
    if len(labels) >= 3:
        last_two = ".".join(labels[-2:])
        if last_two in _MULTI_LEVEL_SUFFIXES:
            return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def _looks_like_ip(host: str) -> bool:
    """粗略识别 IPv4 / IPv6：仅用于避免把 IP 当域名切分。"""
    if ":" in host:
        return True  # IPv6
    parts = host.split(".")
    if len(parts) != 4:
        return False
    return all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


__all__ = [
    "extract_host",
    "normalize_url",
    "registrable_domain",
]

"""浏览器填充桥 HTTP 服务（POC）。

- 仅绑定 127.0.0.1，随机端口
- Bearer Token 认证（每次进程启动随机生成）
- `/ping`（GET，无鉴权，仅返回运行状态）
- `/candidates`（POST，鉴权）：按 origin 查询候选条目（不返回密码）
- `/fill`（POST，鉴权）：需桌面端弹窗授权，返回明文用户名/密码/TOTP

注意：响应头不设置 `Access-Control-Allow-Origin`，用户脚本必须通过
`GM_xmlhttpRequest` 绕过 CORS，防止任意网页脚本直接嗅探本地端口。
"""

from __future__ import annotations

import hmac
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from zhmm.browser_bridge.controller import BrowserBridgeController


def _is_safe_origin(origin: str) -> bool:
    """严格 origin 校验：scheme://host[:port]，无 path/query/fragment。"""
    try:
        p = urlparse(origin)
    except ValueError:
        return False
    if p.scheme not in ("http", "https"):
        return False
    if not p.netloc or not p.hostname:
        return False
    if p.path and p.path != "/":
        return False
    return not (p.query or p.fragment)


def _split_entry_urls(entry_url: str) -> list[str]:
    """拆分 vault 条目的 url 字段：支持用空白 / 逗号 / 分号 / 换行 分隔多个 URL。

    应对同一个账号的多个登录入口（如 `cocos.com` + `auth.cocos.com`）。
    单 URL 场景结果与旧逻辑完全一致，对存量数据零破坏。
    """
    if not entry_url:
        return []
    # 按多种常见分隔符切分：空白类 / 逗号 / 分号
    tokens = re.split(r"[\s,;]+", entry_url.strip())
    return [t for t in tokens if t]


def origin_matches(entry_url: str, origin: str) -> bool:
    """按 hostname 精确匹配（大小写不敏感），防止 example.com ↔ exmple.com 混淆。

    支持条目 url 字段写多个 URL（用空格/逗号/分号分隔），任一匹配即命中。
    """
    if not entry_url:
        return False
    try:
        op = urlparse(origin)
    except ValueError:
        return False
    oh = (op.hostname or "").lower()
    if not oh:
        return False
    for raw in _split_entry_urls(entry_url):
        eu = raw if raw.startswith(("http://", "https://")) else "https://" + raw
        try:
            ep = urlparse(eu)
        except ValueError:
            continue
        eh = (ep.hostname or "").lower()
        if eh and eh == oh:
            return True
    return False


class _Handler(BaseHTTPRequestHandler):
    controller: BrowserBridgeController  # 绑定在子类上
    token: str

    # ----- util -----
    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # 有意不设置 Access-Control-Allow-Origin：强制用户脚本走 GM_xmlhttpRequest，
        # 避免任意网站的 fetch() 直接访问本地端口。
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _authed(self) -> bool:
        auth = self.headers.get("Authorization", "")
        expected = f"Bearer {self.token}"
        return hmac.compare_digest(auth, expected)

    def _read_json(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return None
        if length < 0 or length > 64 * 1024:
            return None
        raw = self.rfile.read(length) if length > 0 else b""
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        return data

    # ----- routes -----
    def do_GET(self) -> None:  # noqa: N802 (stdlib name)
        if self.path == "/ping":
            self._send_json(
                200,
                {"app": "zhmm", "version": 1, "unlocked": self.controller.is_unlocked()},
            )
            return
        self._send_json(404, {"error": "not found"})

    def _collect_origins(self, body: dict[str, Any]) -> list[str] | None:
        """收集安全的 origin 列表：主 origin + 可选 frame_origins。

        返回去重后的有序列表；任一不合法则返回 None。
        思路：iframe 场景下脚本会把祖先链（顶层 → 当前）一起发过来，
        服务端不假设具体是哪一个，只要任一匹配 vault 里的 url 即可给出候选；
        信任根仍是「用户在桌面端手工授权」，研判 iframe 是否恶意不是服务端责任。
        """
        main = str(body.get("origin", "")).strip()
        if not _is_safe_origin(main):
            return None
        origins: list[str] = [main]
        raw = body.get("frame_origins")
        if raw is not None:
            if not isinstance(raw, list) or len(raw) > 16:
                return None
            for item in raw:
                if not isinstance(item, str):
                    return None
                o = item.strip()
                if not o:
                    continue
                if not _is_safe_origin(o):
                    return None
                if o not in origins:
                    origins.append(o)
        return origins

    def do_POST(self) -> None:  # noqa: N802
        if not self._authed():
            self._send_json(401, {"error": "unauthorized"})
            return
        body = self._read_json()
        if body is None:
            self._send_json(400, {"error": "bad request"})
            return
        origins = self._collect_origins(body)
        if origins is None:
            self._send_json(400, {"error": "invalid origin"})
            return

        if self.path == "/candidates":
            items = self.controller.list_candidates(origins)
            if items is None:
                self._send_json(423, {"error": "locked"})
                return
            self._send_json(200, {"origin": origins[0], "origins": origins, "candidates": items})
            return

        if self.path == "/fill":
            raw_id = body.get("id")
            try:
                entry_id = int(raw_id)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                self._send_json(400, {"error": "missing id"})
                return
            result = self.controller.fill(origins, entry_id)
            if result is None:
                self._send_json(403, {"error": "denied or not found"})
                return
            self._send_json(200, result)
            return

        self._send_json(404, {"error": "not found"})

    # 不打印访问日志，避免污染 stdout（桌面应用场景）
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return


def start_server(
    controller: BrowserBridgeController,
    host: str = "127.0.0.1",
    port: int = 0,
    token: str = "",
) -> tuple[ThreadingHTTPServer, threading.Thread, int]:
    """启动后台线程内的 HTTP 服务。

    返回 (httpd, thread, actual_port)。调用方负责 `httpd.shutdown()` 优雅停机。
    """
    handler_cls = type(
        "BridgeHandler",
        (_Handler,),
        {"controller": controller, "token": token},
    )
    httpd = ThreadingHTTPServer((host, port), handler_cls)
    actual_port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, name="zhmm-bridge", daemon=True)
    thread.start()
    return httpd, thread, actual_port

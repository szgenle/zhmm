"""浏览器填充桥控制器（生命周期 + 授权 + 数据访问）。

职责：
    - 启停 HTTP 服务（见 :mod:`zhmm.browser_bridge.server`）
    - 把桌面端已解锁的 SmData 暴露给 server（通过 `set_vault_source` 回调）
    - 处理 `/fill` 授权：把请求从 server 线程桥接到 Qt 主线程弹窗
    - 维护 origin → TTL 临时白名单，减少用户频繁点击

安全要点：
    - 服务仅在 vault 已解锁时返回数据，锁屏/未登录一律返回 423
    - 每次 `/fill` 默认需要人工授权，用户可勾选 5 分钟免打扰
    - Token 文件 `~/.zhmm/browser_bridge.json` 以 0600 权限落盘
"""

from __future__ import annotations

import contextlib
import json
import os
import secrets
import stat
import threading
import time
from collections.abc import Callable
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, Qt, pyqtSignal, pyqtSlot

from zhmm.browser_bridge.dialog import ApprovalDialog
from zhmm.browser_bridge.server import origin_matches, start_server
from zhmm.utils.log import logger

# SmData.mm["data"] 元素的 TypedDict 在 sm_data_types 中定义，这里只看需要的字段
VaultSource = Callable[[], Any]  # 返回 SmData 或 None


def _token_file() -> Path:
    return Path.home() / ".zhmm" / "browser_bridge.json"


def _write_token_file(port: int, token: str) -> Path:
    p = _token_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "host": "127.0.0.1",
        "port": port,
        "token": token,
        "pid": os.getpid(),
        "endpoint": f"http://127.0.0.1:{port}",
    }
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with contextlib.suppress(OSError):
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp, p)
    return p


class BrowserBridgeController(QObject):
    """浏览器填充桥控制器（单例，QObject 以便跨线程 signal）。"""

    # payload: dict，由 server 线程填充并阻塞等待 event.set()
    _approval_signal = pyqtSignal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._vault_source: VaultSource | None = None
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._port: int = 0
        self._token: str = ""
        self._token_path: Path | None = None
        self._trust: dict[str, float] = {}  # origin → expire_ts
        self._trust_lock = threading.Lock()
        self._approval_signal.connect(self._on_approval, Qt.ConnectionType.QueuedConnection)  # type: ignore[call-arg,unused-ignore]

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def set_vault_source(self, source: VaultSource | None) -> None:
        """由 GUI 注入的"当前已解锁 vault"访问器。返回 None 表示已锁。"""
        self._vault_source = source

    def start(self, host: str = "127.0.0.1", port: int = 0) -> tuple[int, str, Path]:
        if self._httpd is not None:
            return self._port, self._token, self._token_path or _token_file()
        token = secrets.token_hex(32)
        httpd, thread, actual_port = start_server(self, host=host, port=port, token=token)
        self._httpd = httpd
        self._thread = thread
        self._port = actual_port
        self._token = token
        self._token_path = _write_token_file(actual_port, token)
        logger.info(f"浏览器填充桥已启动：http://{host}:{actual_port}  token file: {self._token_path}")
        return actual_port, token, self._token_path

    def stop(self) -> None:
        if self._httpd is None:
            return
        try:
            self._httpd.shutdown()
            self._httpd.server_close()
        except OSError:
            pass
        self._httpd = None
        self._thread = None
        # 擦除 token 文件（避免残留）
        if self._token_path and self._token_path.exists():
            with contextlib.suppress(OSError):
                self._token_path.unlink()
        self._token = ""
        self._port = 0
        with self._trust_lock:
            self._trust.clear()

    # ------------------------------------------------------------------
    # server 回调（在 server 线程调用，必须线程安全）
    # ------------------------------------------------------------------
    def is_unlocked(self) -> bool:
        return self._vault_source is not None and self._vault_source() is not None

    def list_candidates(self, origins: list[str]) -> list[dict[str, Any]] | None:
        sm = self._current_vault()
        if sm is None:
            return None
        out: list[dict[str, Any]] = []
        for e in sm.mm.get("data", []):
            url = str(e.get("url", "") or "")
            if any(origin_matches(url, o) for o in origins):
                out.append(
                    {
                        "id": int(e.get("id", 0) or 0),
                        "userID": str(e.get("userID", "") or ""),
                        "url": url,
                        "desc": str(e.get("desc", "") or ""),
                        "has_totp": bool(e.get("totp_secret")),
                    }
                )
        return out

    def fill(self, origins: list[str], entry_id: int) -> dict[str, Any] | None:
        sm = self._current_vault()
        if sm is None:
            return None
        entry = next(
            (e for e in sm.mm.get("data", []) if int(e.get("id", 0) or 0) == entry_id),
            None,
        )
        if not entry:
            return None
        url = str(entry.get("url", "") or "")
        # 匹配到的具体 origin 作为授权弹窗展示的主角 + 入白名单的 key
        matched = next((o for o in origins if origin_matches(url, o)), None)
        if matched is None:
            return None
        if not self._request_approval(matched, origins, entry):
            return None
        result: dict[str, Any] = {
            "userID": str(entry.get("userID", "") or ""),
            "pwd": str(entry.get("pwd", "") or ""),
        }
        secret = str(entry.get("totp_secret", "") or "")
        if secret:
            try:
                from zhmm.core.totp import generate as generate_totp

                code = generate_totp(
                    secret,
                    algo=str(entry.get("totp_algo") or "SHA1"),
                    digits=int(entry.get("totp_digits") or 6),
                    period=int(entry.get("totp_period") or 30),
                )
                result["totp"] = code
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"TOTP 生成失败：{exc}")
        return result

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    def _current_vault(self) -> Any:
        if self._vault_source is None:
            return None
        try:
            return self._vault_source()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"vault source 访问失败：{exc}")
            return None

    def _request_approval(self, display_origin: str, all_origins: list[str], entry: dict[str, Any]) -> bool:
        # 命中临时白名单则直接通过（只要任一 origin 在白名单内、未过期）
        now = time.time()
        with self._trust_lock:
            for o in all_origins:
                exp = self._trust.get(o, 0.0)
                if exp > now:
                    return True

        # 跨线程弹窗：signal → 主线程 slot → 阻塞等待 event
        ctx: dict[str, Any] = {
            "origin": display_origin,
            "userID": str(entry.get("userID", "") or ""),
            "url": str(entry.get("url", "") or ""),
            "has_totp": bool(entry.get("totp_secret")),
            "event": threading.Event(),
            "approved": False,
            "trust_ttl": 0,
        }
        self._approval_signal.emit(ctx)
        # 60 秒窗口，用户不响应视作拒绝
        ctx["event"].wait(timeout=60)
        if ctx["approved"] and ctx["trust_ttl"] > 0:
            # 免打扰对所有参与的 origin 生效（覆盖祖先链）
            with self._trust_lock:
                expire = time.time() + float(ctx["trust_ttl"])
                for o in all_origins:
                    self._trust[o] = expire
        return bool(ctx["approved"])

    @pyqtSlot(object)
    def _on_approval(self, ctx: dict[str, Any]) -> None:
        try:
            dlg = ApprovalDialog(
                origin=ctx["origin"],
                entry_user_id=ctx["userID"],
                entry_url=ctx["url"],
                has_totp=ctx["has_totp"],
                parent=None,
            )
            accepted = dlg.exec() == dlg.DialogCode.Accepted
            ctx["approved"] = accepted
            ctx["trust_ttl"] = dlg.trust_ttl() if accepted else 0
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"授权弹窗异常：{exc}")
            ctx["approved"] = False
            ctx["trust_ttl"] = 0
        finally:
            ctx["event"].set()

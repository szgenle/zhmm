"""浏览器填充桥（POC，方案 C）。

.. warning::
    **Experimental / POC — 不提供稳定性承诺。**

    端点、请求/响应格式、Token 文件位置及结构随时可能变更或移除，
    **不保证向后兼容**。一旦正式版本切换到 **KeePassXC-Browser 协议**
    （X25519 + libsodium + Native Messaging），本包将被 deprecated 并最终移除。
    请勿基于它构建长期工作流。

桌面端起一个只绑定 127.0.0.1 的 HTTP 服务，配合 Tampermonkey 用户脚本完成
浏览器侧填充。明文密码只在 `/fill` 授权通过后的单次响应中送达浏览器，桌面端
永不缓存、不后台推送。

开启方式：启动 GUI 前设置环境变量 `ZHMM_BROWSER_BRIDGE=1`。
端点与令牌写入 `~/.zhmm/browser_bridge.json`（0600）。
"""

from __future__ import annotations

from zhmm.browser_bridge.controller import BrowserBridgeController

__all__ = ["BrowserBridgeController"]

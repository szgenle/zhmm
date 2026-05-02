// ==UserScript==
// @name         zhmm 浏览器填充 (POC)
// @namespace    https://github.com/szgenle/zhmm
// @version      0.3.0
// @description  与 zhmm 桌面端通信，从本地密码库填充用户名 / 密码 / TOTP（支持多步登录 / iframe / 祖先 origin 匹配）
// @author       zhmm
// @match        *://*/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_registerMenuCommand
// @grant        GM_notification
// @connect      127.0.0.1
// @connect      localhost
// @run-at       document-idle
// ==/UserScript==

// 注意：
//   v0.2.0 起移除 @noframes，以支持把登录表单放在 iframe 的站点（mail.qq.com 等）。
//   v0.3.0 起在 iframe 里会把祖先 origin 链连同当前 origin 一起上报服务端，
//   vault 里无论登记的是 mail.qq.com 还是 xui.ptlogin2.qq.com 都能匹配到。

/*
 安全说明
 --------
 - 本脚本不缓存密码/TOTP，明文仅在用户在桌面端点击"允许"之后的单次响应中经过浏览器 → 注入 DOM → 立即释放；
 - 脚本必须通过 Tampermonkey/Violentmonkey 的 GM_xmlhttpRequest 访问 127.0.0.1，普通页面 fetch() 会被 CORS 拦截；
 - 端点与 Token 读取自 ~/.zhmm/browser_bridge.json，随桌面端每次启动轮换；请勿把 Token 提交到任何仓库。
*/

(function () {
    'use strict';

    const K_ENDPOINT = 'zhmm_endpoint';
    const K_TOKEN = 'zhmm_token';

    // ------------------------------------------------------------ 配置
    function getEndpoint() { return (GM_getValue(K_ENDPOINT, '') || '').trim(); }
    function getToken() { return (GM_getValue(K_TOKEN, '') || '').trim(); }

    function configure() {
        const ep = prompt(
            'zhmm 桌面端地址（如 http://127.0.0.1:17615，取自 ~/.zhmm/browser_bridge.json 的 endpoint 字段）',
            getEndpoint() || 'http://127.0.0.1:17615',
        );
        if (ep === null) return;
        const token = prompt(
            'zhmm 桌面端 Token（取自 ~/.zhmm/browser_bridge.json 的 token 字段）',
            getToken(),
        );
        if (token === null) return;
        GM_setValue(K_ENDPOINT, ep.trim());
        GM_setValue(K_TOKEN, token.trim());
        GM_notification({ title: 'zhmm', text: '已保存端点与 Token' });
    }

    GM_registerMenuCommand('配置 zhmm 桌面端', configure);

    // ------------------------------------------------------------ 通信
    function apiPost(path, body) {
        return new Promise((resolve, reject) => {
            const endpoint = getEndpoint();
            const token = getToken();
            if (!endpoint || !token) {
                reject({ status: 0, data: { error: '未配置端点或 Token' } });
                return;
            }
            const payload = Object.assign({}, body || {});
            // 主 origin + 祖先链（iframe 场景下有值）
            if (!payload.origin) payload.origin = currentOrigin();
            if (!payload.frame_origins) payload.frame_origins = ancestorOrigins();
            GM_xmlhttpRequest({
                method: 'POST',
                url: endpoint + path,
                headers: {
                    'Authorization': 'Bearer ' + token,
                    'Content-Type': 'application/json',
                },
                data: JSON.stringify(payload),
                timeout: 65000,
                onload: (r) => {
                    let data = {};
                    try { data = JSON.parse(r.responseText || '{}'); } catch (_) { /* ignore */ }
                    if (r.status >= 200 && r.status < 300) resolve(data);
                    else reject({ status: r.status, data });
                },
                onerror: () => reject({ status: 0, data: { error: '连接失败，桌面端可能未运行' } }),
                ontimeout: () => reject({ status: 0, data: { error: '超时（未在桌面端授权？）' } }),
            });
        });
    }

    function currentOrigin() {
        return location.protocol + '//' + location.host;
    }

    // 返回祖先 origin（顶层 → 父 → 当前 之间的那几个；HTML5 规范）。
    // 顶层框架的 ancestorOrigins 为空，iframe 里会拿到包含顶层在内的所有祖先。
    function ancestorOrigins() {
        try {
            const ao = location.ancestorOrigins;
            if (!ao || !ao.length) return [];
            const out = [];
            for (let i = 0; i < ao.length; i++) {
                const v = String(ao[i] || '').trim();
                if (v && /^https?:\/\//.test(v) && out.indexOf(v) === -1) out.push(v);
            }
            return out;
        } catch (_) { return []; }
    }

    // ------------------------------------------------------------ DOM 识别
    function isVisible(el) {
        if (!el) return false;
        if (el.offsetParent !== null) return true;
        // position:fixed 的元素 offsetParent 可能为 null，兜底看 rect
        const r = el.getClientRects();
        return r.length > 0 && (r[0].width > 0 || r[0].height > 0);
    }

    function findVisiblePasswordField() {
        const list = document.querySelectorAll('input[type="password"]');
        for (const el of list) {
            if (el.disabled || el.readOnly) continue;
            if (!isVisible(el)) continue;
            return el;
        }
        return null;
    }

    // 填充时可以接受隐藏字段（某些站点会先把密码框 type=text 再切 password；
    // 但 document.querySelector 只能找到当前属性）
    function findPasswordField() {
        return findVisiblePasswordField() || (function () {
            const list = document.querySelectorAll('input[type="password"]');
            for (const el of list) {
                if (el.disabled || el.readOnly) continue;
                return el;
            }
            return null;
        })();
    }

    function findUsernameField(pwd) {
        if (!pwd) return null;
        const scope = pwd.form || document;
        const candidates = scope.querySelectorAll(
            'input[type="text"],input[type="email"],input[type="tel"],input[type="username"],input:not([type])',
        );
        // 取在 password 之前、最接近的一个可见输入框
        let best = null;
        for (const el of candidates) {
            if (el.disabled || el.readOnly) continue;
            if (el.offsetParent === null) continue;
            // el 必须出现在 pwd 之前
            if (el.compareDocumentPosition(pwd) & Node.DOCUMENT_POSITION_FOLLOWING) {
                best = el;
            }
        }
        return best;
    }

    function findTotpField() {
        const selectors = [
            'input[autocomplete="one-time-code"]',
            'input[name*="otp" i]',
            'input[name*="totp" i]',
            'input[name*="2fa" i]',
            'input[id*="otp" i]',
            'input[id*="totp" i]',
            'input[inputmode="numeric"][maxlength="6"]',
        ];
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el && !el.disabled && !el.readOnly && el.offsetParent !== null) return el;
        }
        return null;
    }

    function setValue(el, value) {
        if (!el) return;
        const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
        setter.call(el, value);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }

    // ------------------------------------------------------------ UI
    function removePicker() {
        const old = document.getElementById('zhmm-picker');
        if (old) old.remove();
    }

    function showPicker(list) {
        removePicker();
        const box = document.createElement('div');
        box.id = 'zhmm-picker';
        box.style.cssText = [
            'position:fixed', 'right:16px', 'bottom:64px', 'z-index:2147483647',
            'background:#fff', 'color:#222', 'border:1px solid #ccc', 'border-radius:8px',
            'padding:8px', 'box-shadow:0 4px 16px rgba(0,0,0,.2)',
            'font:13px/1.4 system-ui,-apple-system,sans-serif',
            'min-width:260px', 'max-width:420px', 'max-height:60vh', 'overflow:auto',
        ].join(';');
        const title = document.createElement('div');
        title.textContent = 'zhmm · 选择账号';
        title.style.cssText = 'font-weight:600;margin:2px 4px 6px;';
        box.appendChild(title);
        list.forEach((item) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            const tags = [];
            if (item.has_totp) tags.push('TOTP');
            if (item.desc) tags.push(item.desc);
            btn.textContent = (item.userID || '(未填用户名)') + (tags.length ? '  — ' + tags.join(' · ') : '');
            btn.style.cssText = [
                'display:block', 'width:100%', 'text-align:left',
                'padding:6px 8px', 'margin:2px 0',
                'border:1px solid #e0e0e0', 'background:#fafafa',
                'border-radius:4px', 'cursor:pointer', 'color:#222',
            ].join(';');
            btn.onclick = () => { removePicker(); doFill(item.id); };
            box.appendChild(btn);
        });
        const close = document.createElement('button');
        close.type = 'button';
        close.textContent = '取消';
        close.style.cssText = [
            'display:block', 'width:100%', 'padding:6px 8px', 'margin-top:6px',
            'border:1px solid #e0e0e0', 'background:#f5f5f5',
            'border-radius:4px', 'cursor:pointer', 'color:#222',
        ].join(';');
        close.onclick = removePicker;
        box.appendChild(close);
        document.body.appendChild(box);
    }

    // ------------------------------------------------------------ 多步登录：记住本会话最近一次选择的条目
    // 仅保存 entry id 和过期时间，不缓存明文密码；每次 /fill 仍需桌面端授权
    // （但用户在桌面端勾选「5 分钟免打扰」后，二次 /fill 不会再弹窗）。
    const PENDING_TTL_MS = 3 * 60 * 1000;

    function pendingKey() { return 'zhmm_pending_' + currentOrigin(); }

    function setPending(entryId) {
        try {
            sessionStorage.setItem(pendingKey(), JSON.stringify({
                id: entryId, expire: Date.now() + PENDING_TTL_MS,
            }));
        } catch (_) { /* 隐身模式等可能抛异常 */ }
    }

    function getPending() {
        try {
            const raw = sessionStorage.getItem(pendingKey());
            if (!raw) return null;
            const obj = JSON.parse(raw);
            if (!obj || obj.expire < Date.now()) {
                sessionStorage.removeItem(pendingKey());
                return null;
            }
            return obj.id;
        } catch (_) { return null; }
    }

    // ------------------------------------------------------------ 页内浮层提示（iframe 里 GM_notification 可能不出或被浏览器屏蔽时的兑底）
    function toast(msg, variant) {
        if (!document.body) return;
        try {
            const id = 'zhmm-toast';
            const old = document.getElementById(id);
            if (old) old.remove();
            const el = document.createElement('div');
            el.id = id;
            const bg = variant === 'error' ? '#d14' : (variant === 'warn' ? '#b80' : '#2b7');
            el.textContent = 'zhmm · ' + msg;
            el.style.cssText = [
                'position:fixed', 'right:16px', 'bottom:60px', 'z-index:2147483647',
                'padding:8px 12px', 'border-radius:6px', 'background:' + bg, 'color:#fff',
                'font:500 12px/1.4 system-ui,-apple-system,sans-serif',
                'box-shadow:0 2px 8px rgba(0,0,0,.25)', 'max-width:320px',
            ].join(';');
            document.body.appendChild(el);
            setTimeout(() => { el.remove(); }, 4000);
        } catch (_) { /* ignore */ }
        // GM_notification 兼兑
        try { GM_notification({ title: 'zhmm', text: msg }); } catch (_) { /* ignore */ }
    }

    async function doFill(entryId, silent) {
        try {
            const res = await apiPost('/fill', { id: entryId });
            const pwd = findPasswordField();
            const user = findUsernameField(pwd);
            let filled = [];
            if (user && res.userID) { setValue(user, res.userID); filled.push('账号'); }
            if (pwd && res.pwd) { setValue(pwd, res.pwd); filled.push('密码'); }
            if (res.totp) {
                const otp = findTotpField();
                if (otp) { setValue(otp, res.totp); filled.push('TOTP'); }
            }
            setPending(entryId);
            if (!silent && filled.length) {
                toast('已填充：' + filled.join(' / '));
            } else if (!silent && !filled.length) {
                toast('未匹配到密码框，请点完后手动粘贴', 'warn');
            }
            return filled.length > 0;
        } catch (err) {
            const msg = (err && err.data && err.data.error) || (err && err.message) || '失败';
            if (!silent) toast('填充失败：' + msg, 'error');
            return false;
        }
    }

    async function openPicker() {
        if (!getEndpoint() || !getToken()) { configure(); return; }
        let data;
        try {
            data = await apiPost('/candidates', {});
        } catch (err) {
            const msg = (err && err.data && err.data.error) || (err && err.message) || '失败';
            toast('查询失败：' + msg, 'error');
            return;
        }
        const list = (data && data.candidates) || [];
        if (list.length === 0) {
            // iframe 里把祖先 origin 也打出来，方便用户对照 vault 里的 url 检查
            const ao = ancestorOrigins();
            const hint = ao.length
                ? ' (已尝试：' + [currentOrigin()].concat(ao).join(', ') + ')'
                : ' (' + currentOrigin() + ')';
            toast('当前域名没有匹配条目' + hint, 'warn');
            return;
        }
        if (list.length === 1) { doFill(list[0].id); return; }
        showPicker(list);
    }

    // 放宽 FAB 挂载条件：可见密码框 / autocomplete 语义字段 / 登录路径关键字 + 文本框
    // 用于 qoder.com 的「账号页 → 密码页」这种多步登录，让账号页也能挂按钮
    function hasLoginHint() {
        if (findVisiblePasswordField()) return true;
        const semantic = document.querySelector(
            'input[autocomplete="username"]:not([disabled]),'
            + 'input[autocomplete="email"]:not([disabled]),'
            + 'input[autocomplete="current-password"]:not([disabled]),'
            + 'input[autocomplete="new-password"]:not([disabled])',
        );
        if (semantic && isVisible(semantic)) return true;
        const path = (location.pathname || '').toLowerCase();
        if (/(^|[\/_-])(login|signin|sign-in|logon|auth|account|passport)([\/_-]|$)/.test(path)) {
            const candidate = document.querySelector(
                'input[type="email"]:not([disabled]),'
                + 'input[type="text"]:not([disabled]),'
                + 'input[type="tel"]:not([disabled])',
            );
            if (candidate && isVisible(candidate)) return true;
        }
        return false;
    }

    function mountFab() {
        if (!hasLoginHint()) return;
        if (!document.body) return;
        if (document.getElementById('zhmm-fab')) return;
        const btn = document.createElement('button');
        btn.id = 'zhmm-fab';
        btn.type = 'button';
        btn.textContent = 'zhmm';
        btn.title = 'zhmm 填充';
        btn.style.cssText = [
            'position:fixed', 'right:16px', 'bottom:16px', 'z-index:2147483647',
            'padding:8px 14px', 'border-radius:20px', 'border:none',
            'background:#2b7', 'color:#fff',
            'font:600 13px system-ui,-apple-system,sans-serif',
            'box-shadow:0 2px 8px rgba(0,0,0,.25)', 'cursor:pointer', 'opacity:.85',
        ].join(';');
        btn.onmouseenter = () => { btn.style.opacity = '1'; };
        btn.onmouseleave = () => { btn.style.opacity = '.85'; };
        btn.onclick = openPicker;
        document.body.appendChild(btn);
    }

    // 多步登录自动复填：看到新密码框且值为空 → 使用会话内记住的 entry 重试一次
    let autoRefillInFlight = false;
    async function tryAutoRefill() {
        if (autoRefillInFlight) return;
        const pending = getPending();
        if (!pending) return;
        const pwd = findVisiblePasswordField();
        if (!pwd || pwd.value) return;
        autoRefillInFlight = true;
        try {
            // silent：若桌面端未授权会超时/403，悄悄失败，用户可手动点按钮
            await doFill(pending, true);
        } finally {
            autoRefillInFlight = false;
        }
    }

    // SPA / 异步渲染：持续观察（节流，避免高频 DOM 抖动压垮 CPU）
    let scheduled = false;
    function schedule() {
        if (scheduled) return;
        scheduled = true;
        setTimeout(() => {
            scheduled = false;
            mountFab();
            tryAutoRefill();
        }, 150);
    }
    const mo = new MutationObserver(schedule);
    mo.observe(document.documentElement, { childList: true, subtree: true });
    mountFab();

    GM_registerMenuCommand('zhmm 手动填充', openPicker);
})();

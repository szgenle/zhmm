# 浏览器填充 POC 使用说明（方案 C）

> ⚠️ **Experimental / POC — 不提供任何稳定性承诺**
>
> - 默认**关闭**，需显式设置 `ZHMM_BROWSER_BRIDGE=1` 才会启动；普通用户零感知。
> - 端点路径、请求/响应格式、Token 文件位置与格式**随时可能变更或移除**，**不保证向后兼容**。
> - 本包（`zhmm.browser_bridge`）与本脚本在正式版本迁移到 **KeePassXC-Browser 协议**（X25519 + libsodium + Native Messaging）后将被 **deprecated 并最终移除**。
> - 保留在仓库里的目的：验证「解密与授权做在桌面端、浏览器侧只当填字员」这一架构与 UX；欢迎体验和反馈，但**不建议依赖它构建任何长期工作流**。

## 架构

```
┌──────────────┐    GM_xhr     ┌──────────────────────┐
│ 浏览器 + 用户脚本 │ ◄─────────► │ zhmm 桌面端 127.0.0.1 │
│  (content.js) │   Bearer Token │  /candidates /fill    │
└──────────────┘               └──────────────────────┘
                                          ↑
                                     Qt 授权弹窗
```

- **桌面端**：解锁 vault 后，在 `127.0.0.1` 起一个 HTTP 服务（随机端口 + 随机 Token）
- **用户脚本**：通过 Tampermonkey 的 `GM_xmlhttpRequest` 访问本地端口（普通 `fetch()` 会被 CORS 拦截，正是我们想要的）
- **授权**：每次 `/fill` 都会弹 Qt 对话框让用户确认；可选勾选"该域名 5 分钟内不再询问"

## 安全边界（先说清楚）

1. Token 每次桌面端启动随机生成，写入 `~/.zhmm/browser_bridge.json`（`0600` 权限），进程退出时删除
2. 桌面端**仅当 vault 已解锁**才返回数据，锁屏 / 未登录一律 `423 Locked`
3. `/candidates` 只返回 `userID / url / desc / has_totp`，**明文密码不会在这个端点出现**
4. `/fill` 按条目 `url` 的 hostname 与请求 `origin` 严格匹配（忽略大小写）——`example.com` 与 `exmple.com` 不互认
5. 授权弹窗**默认聚焦"拒绝"**，避免空格/回车误授权；origin 与条目 URL 并排显示，让用户自行比对钓鱼风险
6. 响应头**不设置 CORS**，防止任意网页脚本直接命中本地端口
7. 桥只在浏览器脚本主动发起请求时响应，**不做任何 push / 长连**

**已知局限（POC 阶段）**：
- 只做 Bearer Token，未对扩展身份做公钥绑定（正式版走 KeePassXC 协议时补齐）
- 用户脚本读 Token 需要手动复制一次（不能自动从文件读，是 Tampermonkey 的沙箱限制）
- 弹窗默认阻塞 60 秒，超时视作拒绝

## 安装步骤

### 1. 桌面端开启桥（opt-in）

**注意**：zhmm 用 Poetry 管理依赖（PyQt6 等），直接用系统 `python` 会报 `ModuleNotFoundError: No module named 'PyQt6'`。选一种：

```bash
# ① 源码调试：Poetry 运行（推荐）
export ZHMM_BROWSER_BRIDGE=1
poetry run python -m zhmm.main

# ② 源码调试：手动激活 venv
source "$(poetry env info --path)/bin/activate"
export ZHMM_BROWSER_BRIDGE=1
python -m zhmm.main

# ③ 打包后的 .app（macOS）
ZHMM_BROWSER_BRIDGE=1 /Applications/zhmm.app/Contents/MacOS/zhmm
```

看到日志：
```
浏览器填充桥已启用，端口=17615，凭据文件=/Users/you/.zhmm/browser_bridge.json
```

查看凭据：
```bash
cat ~/.zhmm/browser_bridge.json
# {
#   "host": "127.0.0.1",
#   "port": 17615,
#   "token": "<64 位十六进制>",
#   "endpoint": "http://127.0.0.1:17615"
# }
```

### 2. 浏览器装 Tampermonkey / Violentmonkey

Chrome / Edge / Firefox 商店都有。

### 3. 装用户脚本

Tampermonkey 的安装触发条件是「访问以 `.user.js` 结尾的 URL」。三种任选一种：

**方式 A：GitHub Raw 链接（最省心）**

在浏览器里打开仓库里该文件的 **raw** 地址，例如：

```
https://raw.githubusercontent.com/<your-org>/zhmm/main/docs/browser_fill/zhmm-fill.user.js
```

Tampermonkey 会自动拦截并弹安装页，点「安装」即可。

**方式 B：本地 HTTP（未推到 GitHub 时）**

```bash
cd docs/browser_fill
python3 -m http.server 8000
# 浏览器访问：http://127.0.0.1:8000/zhmm-fill.user.js
```

同样会触发 Tampermonkey 安装提示。

**方式 C：手动粘贴（最兄弟）**

1. 打开 Tampermonkey 仪表盘→左侧「+」创建新脚本
2. 用编辑器打开 [`zhmm-fill.user.js`](./zhmm-fill.user.js)，全选复制，粘贴进去盖掉默认模板
3. `Ctrl/⌘ + S` 保存

---

安装完成后：

1. **首次访问任意登录页**点击右下角绿色 `zhmm` 按钮，会弹出配置框
2. 把 `browser_bridge.json` 里的 `endpoint` 与 `token` 粘进去（或从 Tampermonkey 菜单「配置 zhmm 桌面端」手动打开）

### 4. 使用

- 登录页出现 `<input type="password">` 时，右下角会显示 `zhmm` 悬浮按钮
- 点按钮 → 桌面端弹出授权框 → 允许后自动填入用户名 / 密码 / TOTP（若有）
- 多条匹配时弹出选择器
- Tampermonkey 菜单里也有「zhmm 手动填充」，不依赖悬浮按钮

## 验证 POC 是否工作

`curl` 自测（把 `<TOKEN>` 替换为凭据文件里的值）：

```bash
# 健康检查（无鉴权）
curl -s http://127.0.0.1:17615/ping
# -> {"app": "zhmm", "version": 1, "unlocked": true}

# 候选查询（需鉴权）
curl -s -X POST http://127.0.0.1:17615/candidates \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"origin":"https://github.com"}'
# -> {"origin": "https://github.com", "candidates": [...]}
```

`/fill` 必须在桌面端授权弹窗里点「允许」才会返回。

## 故障排查

### Q1：登录页分两步（先账号、后密码），第二步密码没被自动填入？

这是「多步登录」场景（qoder.com / Google / 飞书等）。v0.2.0 起已做自动复填：

- 第一步点 `zhmm` 按钮选中账号后，**脚本会把 entry id 记入 `sessionStorage`**（仅 id，不是密码）
- 进入密码页后，脚本通过 MutationObserver 检测到新密码框 → **自动再发一次 `/fill`**
- 为避免桌面端再弹一次授权框，**第一次授权时请在弹窗里勾选「该域名 5 分钟内不再询问」**；之后的自动复填会被临时白名单放行
- 若你没勾选免打扰，自动复填会因超时/拒绝而悄悄失败，**手动点一下右下角 `zhmm` 按钮**即可

会话关闭后缓存自动清除；TTL 3 分钟。

### Q2：某些站点（如 mail.qq.com）右下角没有绿色按钮？

这类站点把登录表单放在 **iframe** 里（mail.qq.com 的登录表单实际在 `xui.ptlogin2.qq.com`）。

- v0.1.0 含 `@noframes`，脚本只在顶层框架运行 → 子框架里没按钮
- **v0.2.0 起已移除 `@noframes`**，脚本会在顶层和每个同源/跨源 iframe 里各运行一份，各自挂 FAB
- 升级后若按钮仍在 iframe 内未出现，可能是：
  1. Tampermonkey 设置里对该子域名禁用了脚本 —— 在 Tampermonkey 仪表盘把该子域名重新启用
  2. 子框架被 `Content-Security-Policy` 阻止注入 —— 目前无解，可用 Tampermonkey 菜单的「zhmm 手动填充」在顶层触发
  3. iframe 里没有可见的 `input[type=password]` —— 可能表单用的是自定义组件，现阶段 POC 不支持

### Q2 补：iframe 里按钮出现了，点击没任何反应 / 提示「没有匹配条目」？

这是 **origin 不匹配**：登录表单所在 iframe 的 origin（例如 `xui.ptlogin2.qq.com`）与 vault 里登记的 URL（例如 `mail.qq.com`）不相等。

- **v0.3.0 已修复**：iframe 里脚本会把 `location.ancestorOrigins`（顶层→父→当前的祖先链）连同当前 origin 一起上报服务端，**任一匹配即给候选**
- 服务端会在授权弹窗里展示**匹配到的具体 origin**，用户可以核对后再点「允许」
- 所以无论你 vault 里对 mail.qq.com 用户登记的是 `mail.qq.com` 还是 `xui.ptlogin2.qq.com`，都能打中
- 若仍提示「没有匹配条目」，浮层 toast 会列出本次尝试的所有 origin，对照 vault 条目的 url 字段补全即可

### Q3：qoder.com / Google / 飞书的「账号页」右下角一直不出按钮？

v0.2.0 严格要求「页面上存在可见密码框」才挂 FAB，导致账号页不挂。**v0.3.0 已放宽**，满足以下任一条就会挂：

1. 页面上有可见 `<input type="password">`
2. 页面上有可见 `input[autocomplete="username" | "email" | "current-password" | "new-password"]`
3. URL 路径包含 `login/signin/sign-in/logon/auth/account/passport` 关键字，且页面上有可见的文本/邮箱/电话输入框

挂按钮后，账号页点击→选择账号→填入用户名，后续密码页的自动复填依旧有效（sessionStorage pending + MutationObserver）。

### Q4：突然出现「当前域名没有匹配条目」，但确定 vault 里明明有？

- 点击后浮层 toast 会显示本次上报的所有 origin（当前 + 祖先链）——对照 vault 里条目的 `url` 字段，看 hostname 是否**完全相等**
- 我们故意不做「父域/子域」模糊匹配，以防 `example.com` 与 `exmple.com` / `mail.example.com` 与 `login.example.com` 被混淆，钓鱼频发的今天宁严勿粗
- 如果 vault 里登记的是 `example.com` 但登录页在 `accounts.example.com`，请把其中一个调整为与页面 hostname 一致（或新增一条单独条目）

### Q4：同一个账号有多个登录入口（如 cocos.com 和 auth.cocos.com），怎么处理？

vault 里对一条账号的 `url` 字段，**支持用空格 / 逗号 / 分号分隔多个 URL**，任一匹配即命中：

```
cocos.com auth.cocos.com
```

或：

```
https://cocos.com, https://auth.cocos.com, https://passport.cocos.com
```

- 这是密码管理器领域的常见做法（KeePassXC 的「额外 URL」/ 1Password 的 "websites" 字段）
- 比「父域/子域模糊匹配」更安全：每个 hostname 是你**显式信任的**，避免 `github.com` ↔ `pages.github.com` 被自动视为同站
- 按 hostname 精确比对，仍然防 `example.com` ↔ `exmple.com` / `evil.example.com.attacker.cn` 混淆

### Q5：vault 里登记的是 `example.com` 但登录页在 `accounts.example.com`，一直匹配不到？

同 Q4：编辑该条目，把 `url` 改为 `example.com accounts.example.com` 即可（无需新增重复条目）。

> 注：我们故意不默认做「父域/子域」模糊匹配，以防钓鱼场景下 `github.com` ↔ `pages.github.com`
> 这类「属同域但不同信任边界」的密码被混淆。多 URL 申明是你的显式授权。

### Q6：怎么确认用的是 v0.3.0？

Tampermonkey 仪表盘 → 找到脚本 → 右侧版本列应显示 `0.3.0`；或打开脚本编辑器查看头部 `@version`。升级方法：

- **方式 A（raw URL）**：Tampermonkey 会定期自动检查更新；或仪表盘 → 脚本 → 设置 → 「立即检查更新」
- **方式 C（手动粘贴）**：重新复制最新内容覆盖保存

> ⚠️ **服务端也需同步升级**：v0.3.0 用户脚本依赖服务端的 `frame_origins` 字段，
> 旧服务端不认该字段会忽略（不会报错，但 iframe 场景下仍然匹配不到）。请一起拉取最新仓库代码重启桌面端。

## 移除

- 关闭桌面端即停止服务并删除凭据文件
- Tampermonkey 里禁用或删除用户脚本
- 删除 `~/.zhmm/browser_bridge.json`（若残留）

## 下一步（正式版方向）

- 替换 HTTP + Bearer Token → KeePassXC-Browser 协议（X25519 + libsodium）
- 扩展身份首次握手时在桌面端展示公钥指纹人工确认（替代当前的"手动复制 Token"）
- 支持 `set-login`（网页端新建账号直接入库）
- 增加"锁定后自动拒绝"的可视化状态

欢迎在 issue 中反馈体验问题。

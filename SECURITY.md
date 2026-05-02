# 安全策略 / Security Policy

`zhmm` 是一款处理用户密码数据的工具，我们非常重视任何安全问题。

---

## 📣 报告安全漏洞 / Reporting a Vulnerability

**请不要在公开 Issue 中披露安全漏洞。**
Please do **not** disclose security vulnerabilities through public GitHub issues.

推荐通过以下任一渠道进行**私下**披露：

1. **GitHub Security Advisory（推荐）**：
   在本仓库 `Security` → `Report a vulnerability` 发起 private advisory
   → <https://github.com/Lioesquieu/zhmm/security/advisories/new>
2. 通过 Release 页面的维护者联系方式直接邮件联系

请在报告中包含：

- 漏洞的描述、影响范围、严重程度评估（若可）
- 复现步骤（建议附带最小化 PoC）
- 受影响的版本
- 你的联系方式（可选，用于后续沟通与致谢）

### 响应时间 / Response Timeline

- **72 小时内** 确认收到报告
- **7 天内** 给出初步分析结论
- **30 天内** 发布修复版本（视严重程度可提前或延后）

修复后，我们会在 [CHANGELOG.md](CHANGELOG.md) 的 `Security` 节记录（默认致谢报告者，除非你希望匿名）。

---

## ✅ 支持的版本 / Supported Versions

| 版本     | 是否接受安全更新 |
|---------|-------------------|
| 最新发行版 | ✅                |
| 其它版本   | ❌（请升级）       |

---

## 🧭 威胁模型说明 / Threat Model

`zhmm` 的设计目标是：

- 保护静态存储的密码数据（`.zmb` 文件）
- 防止攻击者在**没有主密码 + 账号名**的情况下读取密码内容
- 通过 HMAC-SM3 认证标签检测文件篡改

**不在威胁模型内**的场景（用户需自行负责）：

- 运行时内存被 dump（例如你的机器已被 root）
- 剪贴板被其它应用读取
- 键盘被键盘记录器监听
- 主密码被肩窥、暴力破解（弱密码）
- `.zmb` 文件被反复拿到后离线暴力破解（请使用强主密码 + 非通用账号名）

---

## 🔐 加密算法详解 / Encryption Details

### 算法栈

| 环节 | 算法 | 参数 |
|------|------|------|
| 密钥派生 | **Argon2id**（memory-hard） | 默认 `m=64 MiB, t=3, p=1`（16 字节随机盐），输出 32 字节密钥；KDF 口令材料为 `account.utf8 + 0x00 + password.utf8`；参数随密文头部内嵌存储，允许未来调强度而不破坏老文件 |
| 数据加密 | **SM4-CBC** | 16 字节随机 IV，PKCS7 填充（块长 16 字节），前 16 字节派生密钥 |
| 完整性校验 | **HMAC-SM3** | 覆盖 `magic + ver + m_cost + t_cost + p_cost + salt + iv + ciphertext`，生成 32 字节标签，后 16 字节派生密钥 |

> KDF 从 v4 的 PBKDF2-HMAC-SHA256 升级为 Argon2id（2015 PHC 冠军算法，
> memory-hard），显著抬升 GPU/ASIC 离线破解成本。默认 `m=64 MiB`
> 在现代桌面单次派生约 100-500 ms，体感良好；OWASP 2024 的
> 最低基线为 `m=19 MiB, t=2, p=1`，本项目取更保守值。
> 数据加密与完整性保护仍由国密算法（SM4 + SM3）承担。

### 文件格式（v5）

```
magic(4B="ZHMM") | ver(1B=5) | m_cost(4B BE) | t_cost(4B BE) | p_cost(4B BE)
                | salt(16B) | iv(16B) | ciphertext(NB) | tag(32B)
```

- **magic**：固定 4 字节 `ZHMM`，用于文件类型识别
- **ver**：单字节版本号（当前 = 5），便于未来升级
- **m_cost / t_cost / p_cost**：大端无符号 32 位整数，从文件读取的参数优先于默认值，且读取前校验在安全范围内（m ≤ 512 MiB，t ≤ 100，p ≤ 64）以防恶意 blob OOM
- **salt**：每次保存重新生成，确保相同账号+密码产生不同密钥
- **iv**：每次保存重新生成，确保相同明文产生不同密文
- **tag**：覆盖 header（含 Argon2 参数）+ ciphertext，篡改任何字段均会被检测
- **账号名**：作为 KDF 输入的一部分参与密钥派生，**本身不写入文件**；解密时需由调用方重新提供，账号错误将与密码错误产生相同的 HMAC 认证失败。

### 设计理由

1. **为什么让账号参与 KDF**：账号作为应用层常量盐，使不同账号 + 相同弱密码的用户派生出完全不同的密钥，缓解弱口令用户面临的离线字典/彩虹表风险。
2. **为什么选 Argon2id**：Argon2id 是 2015 年 Password Hashing Competition 冠军算法，memory-hard 特性使其在 GPU/ASIC 上的并行加速比 PBKDF2 困难得多；OWASP 2024 Password Storage Cheat Sheet 明确推荐 Argon2id 作为首选 KDF。
3. **为什么头部内嵌 Argon2 参数**：让默认强度未来可调（硬件提升、安全形势演化）无需再次 bump 文件格式版本；老文件仍能用自己原始参数被正确解密。
4. **为什么用 SM4-CBC 而不是 CTR**：CBC 配合 Encrypt-then-MAC 是经典模式，安全性已被充分证明。
5. **为什么需要 HMAC 标签**：单纯 CBC 无法检测篡改，HMAC 提供认证加密保证。
6. **保留国密特色**：SM3 / SM4 是中国国家标准（GB/T 32905、32907），适合需要国密合规的场景。

---

## 🔑 TOTP 2FA 实现说明 / TOTP Implementation

`zhmm` 内置 TOTP（基于时间的一次性密码）动态码能力，用于承担账号「第二因子」：

| 项目 | 说明 |
|------|------|
| 标准算法 | 完整实现 **RFC 6238**（TOTP）+ **RFC 4226**（HOTP 动态截断），支持 `HMAC-SHA1 / SHA256 / SHA512` |
| 国密扩展 | 新增 **HMAC-SM3** 变体（算法名 `SM3`），复用项目现有 SM3 实现，兼容国密合规场景 |
| Secret 来源 | 支持 Base32 手动粘贴（容错空格、大小写、缺失 padding）与 `otpauth://` URI 解析（自动回填 algo / digits / period） |
| 默认参数 | `digits=6, period=30`，与主流认证器（Google Authenticator / Microsoft Authenticator / 1Password）完全互通；`SM3` 为 `zhmm` 私有扩展，其它应用不识别 |
| 刷新节奏 | 表格列每 1 秒重算一次，展示 `当前码 + 剩余秒数`；点击即复制到剪贴板，10 秒后自动清空 |

### TOTP Secret 的存储策略

- **`.zmb` 密库**：TOTP Secret 作为条目字段之一，随整库一起经 **Argon2id → SM4-CBC → HMAC-SM3** 链路加密落盘。**破解 TOTP Secret 的门槛与破解主密码完全等价。**
- **Excel 导出（`.xlsx`）**：**刻意不包含 TOTP Secret 列**。导出文件仅保留 `totp_algo / totp_digits / totp_period` 三列元信息，便于迁移时提示「此条目曾启用 2FA，请重新扫码绑定」。这一设计避免用户把明文 Secret 泄露给云盘 / 协作工具 / 邮箱等不受控通道。
- **CLI `--totp <id>`**：仅输出当前动态码与剩余秒数，**不输出 Secret 本身**。
- **剪贴板**：TOTP 动态码与密码列复制后均 10 秒自动清空；TOTP Secret 不会进入剪贴板。

### 已知边界

1. **TOTP 并非替代主密码**：与主密码同库存储，本质仍是「你拥有的 `.zmb` 文件 + 你记住的主密码」的加强，**不构成独立第二因子**。若追求「物理隔离第二因子」请使用硬件令牌（YubiKey）或手机认证器。
2. **SM3-TOTP 是私有扩展**：其它认证器不识别 `algorithm=SM3`；请勿将此类 Secret 同时录入到第三方应用。
3. **时间漂移**：本地系统时间偏差 > 30 秒会导致动态码失效，TOTP 校验方通常允许 ±1 个 period 的容差。

---

## ⚠️ 已知局限 / Known Limitations

我们开诚布公地列出已知安全局限，欢迎贡献改进：

1. **GUI 主密码在 Qt 事件循环期间驻留内存**：PyQt6 字符串对象不保证被及时清零。
2. **自动锁定的粒度有限**：GUI 支持按「设置 → 常规 → 自动锁定时间」配置的分钟数，窗口失去焦点并超过该时长后会自动回到登录页并释放内存中的明文条目（`main_widget.deleteLater()`）；但判定活动的依据是 `QWidget.isActiveWindow()`，**不监听鼠标 / 键盘输入**——窗口保持前台但长时间无人操作的场景不会触发锁定。敏感场景建议手动退出或缩短该时长。
3. **无多因素认证支持**（主密码之外）。
4. **防截屏仅覆盖系统截图/录屏 API**：默认开启防截屏（macOS `NSWindowSharingNone` / Windows 10 2004+ `WDA_EXCLUDE_FROM_CAPTURE`，可在「设置 → 常规」关闭）仅能让系统级截图/录屏工具抓到黑屏，**无法防御摄像头翻拍、外接采集卡、虚拟机抓屏、内核级屏幕驱动 hook**。Linux 无可靠系统 API，为 no-op。Windows 在部分远程桌面/投屏场景下画面会全黑，属预期行为。

---

## 🛡 使用建议 / Best Practices for Users

- 主密码至少 **16 位**，混合大小写字母、数字、符号
- 账号名避免使用通用字符串（如 `admin`、`root`、`test`），推荐用邮箱、手机号或自定义唯一串，以最大化 KDF 常量盐的熵
- `.zmb` 文件**多地备份**（至少 1 份本地、1 份离线介质）
- 切勿通过聊天软件、邮件传输 `.zmb` 文件或主密码
- 不要在他人设备上运行未经审计的 zhmm 构建
- 打包分发请验证二进制的 SHA256 校验和

---

感谢你帮助让 `zhmm` 变得更安全。🙏

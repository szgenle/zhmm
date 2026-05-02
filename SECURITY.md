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
| 密钥派生 | **PBKDF2-HMAC-SHA256** | 600 000 轮迭代（OWASP 2024 推荐），16 字节随机盐，输出 32 字节密钥；KDF 口令材料为 `account.utf8 + 0x00 + password.utf8` |
| 数据加密 | **SM4-CBC** | 16 字节随机 IV，PKCS7 填充（块长 16 字节），前 16 字节派生密钥 |
| 完整性校验 | **HMAC-SM3** | 覆盖 `magic + ver + salt + iv + ciphertext`，生成 32 字节标签，后 16 字节派生密钥 |

> KDF 选用 SHA256 而非 SM3 是实用折中：gmssl 的 SM3 是纯 Python 实现，
> 用作 PBKDF2 的 PRF 时 600 000 轮需分钟级耗时；改用标准库 `hashlib.pbkdf2_hmac`
> 的 C 实现后，同轮数可在交互级响应时间内完成。
> 数据加密与完整性保护仍由国密算法（SM4 + SM3）承担。

### 文件格式（v4）

```
magic(4B="ZHMM") | ver(1B=4) | salt(16B) | iv(16B) | ciphertext(NB) | tag(32B)
```

- **magic**：固定 4 字节 `ZHMM`，用于文件类型识别
- **ver**：单字节版本号（当前 = 4），便于未来升级
- **salt**：每次保存重新生成，确保相同账号+密码产生不同密钥
- **iv**：每次保存重新生成，确保相同明文产生不同密文
- **tag**：覆盖 header + ciphertext，篡改任何字段均会被检测
- **账号名**：作为 KDF 输入的一部分参与密钥派生，**本身不写入文件**；解密时需由调用方重新提供，账号错误将与密码错误产生相同的 HMAC 认证失败。

### 设计理由

1. **为什么让账号参与 KDF**：账号作为应用层常量盐，使不同账号 + 相同弱密码的用户派生出完全不同的密钥，缓解弱口令用户面临的离线字典/彩虹表风险。
2. **为什么 600 000 轮**：OWASP 2024 Password Storage Cheat Sheet 对 PBKDF2-HMAC-SHA256 的推荐下限。
3. **为什么用 PBKDF2 而不是单次 SM3**：单次哈希无法抵御 GPU/ASIC 暴力破解；60 万轮 PBKDF2 大幅提高攻击成本。
4. **为什么用 SM4-CBC 而不是 CTR**：CBC 配合 Encrypt-then-MAC 是经典模式，安全性已被充分证明。
5. **为什么需要 HMAC 标签**：单纯 CBC 无法检测篡改，HMAC 提供认证加密保证。
6. **保留国密特色**：SM3 / SM4 是中国国家标准（GB/T 32905、32907），适合需要国密合规的场景。

---

## ⚠️ 已知局限 / Known Limitations

我们开诚布公地列出已知安全局限，欢迎贡献改进：

1. **GUI 主密码在 Qt 事件循环期间驻留内存**：PyQt6 字符串对象不保证被及时清零。
2. **未做「锁屏」功能**：GUI 打开后长时间无操作不会自动锁定，敏感使用请手动退出。
3. **无多因素认证支持**（主密码之外）。

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

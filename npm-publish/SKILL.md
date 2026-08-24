---
name: npm-publish
description: 把本地目录/包发布到 **npm 官方源** 的全流程技能：发布前检查（包名占用/登录态/打包内容/registry 源）→ npm pack --dry-run 预览 → 登录 → 带 2FA 发布（交互式网页审批流）→ npm view 验证 → 版本迭代 → 72h 内撤回。当用户要发布 npm 包、预览包内容、登录账号、验证发布、升版重发、撤回 unpublish，或排查镜像/2FA/EOTP/E403 类错误时使用。
---

# npm-publish

> 把本地目录发布为 **npm 包**的全流程技能：检查 → 打包预览 → 登录 → 发布 → 验证 → 版本迭代 → 撤回。覆盖官方源约束与 2FA 网页审批流。

## 管什么 / 不管什么（30 秒边界）

**管**：
- 发布到 npm **官方源**（`https://registry.npmjs.org`）的完整操作序列
- 发布前检查（包名占用 / 登录态 / 打包内容 / registry 源）
- 发布后验证（`npm view` / 临时目录试装）
- 版本迭代（语义化升版重发）与撤回（72h 内 `unpublish`，超期 `deprecate`）
- 账号安全：2FA 策略、令牌不泄露原则

**不管**：
- 不写包的业务代码（假设包已就绪，`package.json` 已可构建）
- 不管私有 registry（Verdaccio / 公司源）、GitHub Packages 等非官方源
- 不管其他语言包管理器（pip / cargo / gem）
- 不管 npm 之外的安装/使用问题

> 框架插件（如需额外 manifest 字段）见 `references/package-checklist.md` 附录，非通用流程不进入主路径。

## 触发词表

| 核心触发词 | 变体（同义 / 口语） | 动作序列 |
|---|---|---|
| 发布 npm 包 | 把 X 发到 npm / 帮我发布 / 发一下 / 上传到 npm | 全流程（§0→5） |
| 检查发布内容 | 包里有什么 / 预览包 / 打包看看 | §2 dry-run |
| 登录 npm | 登 npm 账号 / 我还没登录 / whoami 没输出 | §3 |
| 验证包 | 试试装 / 确认发布成功 / 查一下发上去了没 | §5 |
| 发新版本 | 升版本 / 更新包 / 发 1.0.1 | §6 |
| 撤回包 | 下架 / unpublish / 删掉这个版本 | §7 |
| 管理令牌 | 吊销令牌 / 令牌泄露了 | 硬规则-4 |

## 发布流程

### 0. 前置三查（每次发布前必做）

```bash
node -v; npm -v                          # ① 环境
npm whoami --registry=https://registry.npmjs.org   # ② 登录态（空输出或报错 = 未登录 → §3）
npm view <包名> --registry=https://registry.npmjs.org  # ③ 包名占用（404 = 可用；有输出 = 已被占用/需升版）
npm config get registry                  # ④ 当前源（若不是官方源，发布时必须显式 --registry 覆盖）
```

> `npm view` 查占用时永远显式带 `--registry=https://registry.npmjs.org`，避免镜像同步延迟误判。

### 1. 包就绪检查（改 `package.json` 后必查）

| 字段 | 要求 |
|---|---|
| `name` | 全网唯一（§0 已查）；小写英文 + 连字符，作用域包需 `@scope/name` |
| `version` | 只增不减；npm 拒绝重发同名同版本（E403/E409） |
| `description` | 有；npm 页面展示 |
| `files` | **白名单**（如 `["dist","lib"]`）——只发必要产物，测试/文档/密钥不进包 |
| `license` | 有（如 `MIT`） |
| `private` | 必须不是 `true`（`true` 的包禁止发布） |
| `main` / `exports` / `bin` | 按包类型填写；保持与实际构建产物一致 |

通用最小骨架见 `references/package-checklist.md`。框架/平台的额外字段（如插件 manifest）仅在该框架下需要，通用包跳过。

### 2. 打包预览（发布前最后一道关卡，必跑）

```bash
cd <包目录>
npm pack --dry-run
```

确认：`Tarball Contents` 只含预期文件、无 `node_modules`、无 `.env` / `.npmrc` / 密钥、无多余文档。
**这一步不过关 → 禁止发布。** 详见 `references/pitfalls.md` 坑 5。

### 3. 登录

```bash
npm login --auth-type=web --registry=https://registry.npmjs.org  # 推荐：浏览器授权 + 2FA（npm 10+）
npm whoami --registry=https://registry.npmjs.org                  # 必须输出用户名，否则回到 §0
```

- **首选网页登录**：`--auth-type=web` 会打印浏览器授权链接，完成登录 + 2FA 后 CLI 自动写入令牌（不在终端输密码）。
- 未登录时 `npm publish` 直接报 `ENEEDAUTH`，不会进入 2FA 审批——必须先登录拿到令牌。
- 登录凭证按 registry 隔离：镜像源登录 ≠ 官方源登录。
- 若报 `Public registration is not allowed` → 见 `references/pitfalls.md` 坑 1（镜像源拦截）。

### 4. 发布

```bash
cd <包目录>
npm publish --registry=https://registry.npmjs.org
```

**交互式 2FA 网页审批流（当前推荐）**：在**人可直接操作的交互终端**（有 TTY 的本地 shell）里执行上条命令。账号开启 2FA 时 npm 会打印：

```
Authenticate your account at: https://www.npmjs.com/auth/cli/<uuid>
Press ENTER to open in the browser...
```

按回车 → 浏览器打开授权页 → 完成登录 + 2FA 审批（未绑定认证器 App 时，部分账号可用恢复码填入 2FA 输入框）→ 回终端按回车 → 出现 `+ <包名>@<版本>` 即发布成功。

- 备选：`--otp=<6位码>` 直接携带当前认证器验证码（30 秒轮换，恢复码也可作一次性 OTP）。
- 成功标志：终端输出 `+ <包名>@<版本>`。

> **Agent/自动化铁律**：非交互环境（后台 job、无 TTY、输出被重定向、CI 无人工）下 npm **不发授权 URL、直接报 EOTP**；也不要让用户把 6 位 TOTP 码隔空发进聊天再代跑——30 秒轮换 + 传递时延必过期。正确做法：**把命令交给用户在交互终端自己执行**，Agent 只负责前置检查与事后验证。
>
> **可选增强（Agent 半自动 + 自动弹浏览器，Windows）**：若用户明确授权“你替我开终端，只做需人介入的浏览器认证”，`login` 可后台起 `npm login --auth-type=web` 并轮询 `job_output` 命中 `https://www.npmjs.com/login?next=/login/cli/` 即 `schtasks /it` 弹浏览器；但 `npm publish` 在后台（无 TTY）时完整链接会被打码为 `https://www.npmjs.com/auth/cli/***` 导致轮询永远命中不了，**必须直接用 `schtasks /it` 在用户桌面的交互式 PowerShell 窗口里跑 `npm publish --auth-type=web`**（如 `scripts/publish-auto.ps1` 的 `publish` 段），随后靠 `+ <包>@<版本>` 判成功，二次 `2FA` 自动再弹。详见 `scripts/publish-auto.ps1`（`--PackageDir` 必填，`login` 段后台轮询 1.5s，`publish` 段直接 `schtasks /it` 起交互窗口）。通用流程仍以“人机各司其职”为准，此增强仅为减少“复制链接→手动打开”一步。
>
> **Agent 看到 URL 后的标准动作（必做）**：当 `job_output` 中出现 `https://www.npmjs.com/auth/cli/<uuid>` 或 `https://www.npmjs.com/login?next=/login/cli/<uuid>`，**立即**用以下方式帮用户弹浏览器到可见桌面，不要等待用户手动复制：
> ```powershell
> # 以当前轮询到的 $url 为例（UTF-8，/it 必须）
> $time=(Get-Date).AddMinutes(1).ToString("HH:mm")
> schtasks /create /tn "NpmAuthAuto_$([Guid]::NewGuid().ToString('N').Substring(0,8))" /tr "powershell -Command Start-Process '$url'" /sc once /st $time /it /f | Out-Null
> schtasks /run /tn "NpmAuthAuto_..." | Out-Null
> ```
> 随后继续 `job_output` 轮询，若再次出现新的 `https://.../auth/cli/`（二次 2FA，如 `login` 后紧跟 `publish`），**再次自动弹起**。直到 `job_output` 出现 `+ <包>@<版本>` 即成功，`EOTP` 且无新 URL 则提示用户“请在弹起的 PowerShell 窗口按回车”。
> > **注意**：`npm publish` 在后台 `job`（无 TTY）时，`job_output` 里的 `https://www.npmjs.com/auth/cli/` 会被打码为 `https://www.npmjs.com/auth/cli/***`，**轮询不到完整 `<uuid>`**，此时不要空等 —— `publish` 阶段应如 `scripts/publish-auto.ps1` 那样**直接用 `schtasks /it` 起交互窗口跑 `npm publish --auth-type=web`**，让用户在可见窗口按回车即弹浏览器，Agent 改为轮询 `npm view <包> version --prefer-online` 判成功，而非 `job_output` 的 URL。

**失败分支（先读报错码，再动手）**：

| 报错 | 含义 | 处理 |
|---|---|---|
| `E403 Two-factor authentication ... required` | 需要 2FA | 走上方网页审批流；或 `--otp` 带码 |
| `EOTP`（非交互环境） | 无 TTY 时直接拒绝 | 必须在交互终端执行；检查是否重定向了输出 |
| `E403 cannot publish over previously published version` | 版本重复 | 升 `version` 再发 |
| `E401` / `ENEEDAUTH` | 未登录或令牌失效 | 回 §3 重新登录 |
| `E404` | 包名不存在或 registry 错 | `npm view` 确认；检查 `--registry` |
| `E409` | 版本冲突 | 升 `version` |

> 额外约束：发布命令**不要重定向输出**（`> file` 会让 stdout 非 TTY 而触发 EOTP）；验证查询时建议 `--prefer-online` 跳过本地缓存。

<details>
<summary>Windows 可选：把交互窗口送到用户桌面的思路（非必选）</summary>

部分 Windows 自动化环境中，Agent 直接 `Start-Process` 启动的窗口不在用户可见会话。历史上曾用系统任务计划（`schtasks /it`）将交互式 PowerShell 窗口投递到用户桌面，由用户完成回车与浏览器审批。该做法仅适用于 Windows + 需 Agent 代起窗口的特殊场景，通用流程不依赖它。原理与示例见 `scripts/README.md`，自行按需实现，注意脚本以 UTF-8 保存并显式设置 `[Console]::OutputEncoding`。
</details>

### 5. 验证（发布后必做）

```bash
npm view <包名> version --registry=https://registry.npmjs.org --prefer-online  # 应输出刚发布的版本
npm view <包名> --registry=https://registry.npmjs.org --prefer-online           # 完整信息，含主页 https://www.npmjs.com/package/<包名>

# 可选：临时目录试装
mkdir /tmp/npm-verify && cd /tmp/npm-verify
npm install <包名> --registry=https://registry.npmjs.org
```

**验证不过 → 视同发布失败，排查后修复再发。** 全局 registry 为镜像时，验证必须显式 `--registry` 否则会因镜像同步延迟误判。

### 6. 版本迭代

1. 改 `package.json` 的 `version`（语义化：修复 `+0.0.1` / 新功能 `+0.1.0` / 破坏性 `+1.0.0`）
2. 重跑 §2（dry-run）→ §4 → §5
3. 每次发布都需 2FA（不要为省事创建长期 bypass 令牌）

### 7. 撤回（仅 72 小时内，且慎重）

```bash
npm unpublish <包名>@<版本> --registry=https://registry.npmjs.org
```

- **72 小时后不可删除，只能 `npm deprecate` 标记废弃**：
  ```bash
  npm deprecate <包名>@<版本> "reason" --registry=https://registry.npmjs.org
  ```
- 撤回后重发同名同版本可能仍被拒绝（历史记录保留），此时升版本。
- 发布即公开，发布前先当“发出去就收不回”来想。

## 硬规则（无跳过通道）

1. **发布前必跑 `npm pack --dry-run`**——内容不干净一律不发布
2. **包名先查占用**（`npm view` 404 才可用），不抢不猜
3. **版本号只增不减**，绝不重发同名同版本
4. **令牌绝不进聊天 / 仓库 / 日志 / 命令行历史留存**——泄露即到 `https://www.npmjs.com/settings/<用户>/tokens` 吊销
5. **发布必须走官方源** `https://registry.npmjs.org`——镜像只下载、不发布；命令行 `--registry` 优先级最高
6. **`"private": true` 的包禁止发布**
7. **2FA 发布走交互式终端 + 浏览器网页审批**，不隔空传码；`npm_config_registry` 环境变量优先级高于 `.npmrc`，用 `--registry=` 显式覆盖
8. **每次发布都走 2FA**——不依赖 bypass-2FA 长期令牌（npm 已逐步限制该类令牌的发布与账户管理能力）

## 软规则（心法，非清单）

- **发布 = 公开 + 几乎不可撤回**：动手前先当收不回来想
- **镜像与官方源的心法**：下载加速走镜像没问题；登录/发布永远只认官方源
- **失败先读码**：E403/E401/E404/E409/EOTP 各有一类原因，报错码是第一线索
- **最小发布面**：`files` 白名单能少则少，少一个文件比多一个安全
- **令牌像密码**：不粘贴、不截图、不共享、用后即考虑吊销

## 坑位表

完整记录见 [`references/pitfalls.md`](./references/pitfalls.md)。高频四条：

1. 镜像源拦截登录/发布 → 命令行 `--registry=https://registry.npmjs.org` 单条覆盖
2. 2FA 门槛 → 交互终端网页审批流，`--otp` 备选
3. 令牌泄露 → 立即 revoke，改走 2FA
4. 非交互环境必 EOTP → 必须交互终端手跑；不要重定向输出；验证时 `--prefer-online` + 显式官方源

## 输出

- 发布成功：确认行 `+ <包名>@<版本>` + 包主页 `https://www.npmjs.com/package/<包名>`
- 验证结果：`npm view` 的 version / 临时目录试装结果
- 失败：报错码 + 对应处理（见 §4 表）

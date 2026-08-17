---
name: npm-publish
description: 把本地目录 / 包发布为 **npm 官方源**包的全流程技能：发布前检查（包名占用 / 登录态 / 打包内容 / registry 源）→ npm pack --dry-run 预览 → 登录 → 发布（2FA 交互式网页审批流 / schtasks 发布窗口）→ npm view 验证 → 版本迭代 → 72h 内撤回。当用户要发布 npm 包、发新版本 / 升版重发、撤回 unpublish、检查打包内容、登录 npm 账号，或 npm 报镜像 / 2FA / EOTP / E403 类错误时使用。
---

# npm-publish

> 把本地目录 / 包发布为 **npm 包**的全流程技能：检查 → 打包预览 → 登录 → 发布 → 验证 → 版本迭代 → 撤回。
> 覆盖 DSH 插件包（`dsh.client` 声明）发布；已实测发布 `dsh-opencode-tui-theme@1.0.0`。

## 管什么 / 不管什么（30 秒边界）

**管**：
- 发布到 npm **官方源**（registry.npmjs.org）的完整操作序列
- 发布前检查（包名占用 / 登录态 / 打包内容 / registry 源）
- 发布后验证（`npm view` / 试装）
- 版本迭代（升版重发）与撤回（72h 内 unpublish）
- 账号安全：2FA 政策、令牌管理（吊销 / 不泄露）
- DSH 插件包的特殊声明（`package.json` 的 `dsh.client` + `exports["./client"]`）

**不管**：
- 不写包的业务代码（那是各技能自己的事）
- 不管私有 registry（Verdaccio / 公司源）、GitHub Packages
- 不管其他语言包发布（pip / cargo / gem）
- 不做 npm 之外的安装问题排查（DSH 怎么用插件见 `dsh-plugin/dsh-opencode-tui-theme/README.md`）

## 触发词表（4 元组 = 动作 + 对象 + 维度 + 类型）

| 核心触发词 | 变体（同义 / 口语 / 模糊） | 动作序列 |
|---|---|---|
| 发布 npm 包 | 把 X 发到 npm / 帮我发布 / 发一下 / 上传到 npm | 全流程（§流程 1→5） |
| 检查发布内容 | 包里有什么 / 预览包 / 打包看看 / 查一下会发布啥 | §流程 2（dry-run） |
| 登录 npm | 登 npm 账号 / 我还没登录 / whoami | §流程 3 |
| 验证包 | 试试装 / 装一下验证 / 确认发布成功 | §流程 5 |
| 发新版本 | 升版本 / 更新包 / 发 1.0.1 / 版本号+1 | §流程 6 |
| 撤回包 | 下架 / unpublish / 删掉这个版本 | §流程 7 |
| 管理令牌 | 吊销令牌 / 令牌泄露了 / revoke token | §规则 硬规则-4 |

## 路由规则 · 与其他技能的边界

- 「安装 DSH 插件 / 主题怎么用」→ 走 `dsh-plugin/`（本技能只负责**发布**，不负责 DSH 侧安装）
- 「写插件代码」→ 不是本技能；本技能假设包已就绪
- 「registry 被镜像 / CNPM 报错」→ 本技能 §坑位 1（**在本技能内解决**，不路由走）

## 发布流程

### 0. 前置三查（每次发布前必做）

```powershell
node -v; npm -v              # ① 环境
npm whoami                   # ② 登录态（空输出 = 未登录 → §流程 3）
npm view <包名>              # ③ 包名占用（404 = 可用；有版本 = 已被占用/需升版）
npm config get registry      # ④ 当前源（见坑位 1：镜像坑）
```

### 1. 包就绪检查（改 `package.json` 后必查）

| 字段 | 要求 |
|---|---|
| `name` | 全网唯一（§流程 0 已查）；小写英文 + 连字符 |
| `version` | 只增不减；npm 拒绝重发同名同版本（E403/E409） |
| `description` | 有；中文英文均可（npm 页面展示） |
| `files` | **白名单**（如 `["lib"]`）——只发必要文件，`.npmrc`/测试/文档杂项不进包 |
| `license` | 有（如 MIT） |
| `exports["./client"]` + `dsh.client` | **仅 DSH 插件包**需要；其他 npm 包跳过 |

DSH 插件包的最小 `package.json` 骨架见 `references/dsh-plugin-manifest.md`。

### 2. 打包预览（发布前最后一道关卡，**必跑**）

```powershell
cd <包目录>
npm pack --dry-run
```

确认：Tarball Contents 只含预期文件、无 `node_modules`、无 `.npmrc`、无 `.env`、无密钥。
**这一步不过关 → 禁止发布。**

### 3. 登录

```powershell
npm login --auth-type=web --registry=https://registry.npmjs.org   # 推荐：浏览器登录 + 2FA（npm 10）
npm whoami          # 必须输出用户名，否则回到 0
```

- **npm 10 首选网页登录**：`--auth-type=web` 打印浏览器授权链接，完成登录 + 2FA 后 CLI 自动写令牌（不输密码到终端）。
- 旧式交互登录（用户名/密码/OTP）在 npm 10 仍可用，但密码输入不回显、且 2FA 需另输码——能用 web 就用 web。
- **未登录 ≠ 2FA 审批**：未登录时 `npm publish` 直接报 ENEEDAUTH（不发 Auth URL）；必须先登录拿到令牌，之后 publish 的 2FA 才走网页审批流。

- 密码输入时不回显（正常现象）
- 登录凭证按 registry 分开存；镜像登录 ≠ 官方登录
- 若报 `Public registration is not allowed` → 坑位 1

### 4. 发布

```powershell
npm publish --registry=https://registry.npmjs.org
```

- **2FA 首选：交互式网页审批流（2026-08 实测，推荐）**——在**交互终端**（人可直接操作的 PowerShell/CMD）里跑上面的命令，
  账号开 2FA 时 npm 会打印：

  ```
  Authenticate your account at: https://www.npmjs.com/auth/cli/<uuid>
  Press ENTER to open in the browser...
  ```

  用户按回车 → 浏览器打开授权页 → 完成登录 + 2FA 审批（**无认证器 App 绑定时，2FA 输入框可填一个没用过的恢复码**）→
  回终端按回车 → 出现 `+ <包名>@<版本>` 即发布成功。**全程无需把码发来发去。**
- 备选：`--otp=<码>` 直接带（认证器当前 6 位码，30 秒轮换；恢复码也可作 OTP 提交但用一次少一个）
- 成功标志：`+ <包名>@<版本>`

> **Agent 代跑铁律（本次实战教训）**：非交互环境（`Start-Process` 重定向、后台 job、CI 无 TTY）下 npm **不发 URL、直接报 EOTP**；
> 也不要隔空让用户把 6 位 TOTP 码发进聊天再代跑——30 秒轮换 + 传递时延 = 必过期。正确做法：
> **把命令交给用户在交互终端自己跑**，或起一个用户可达的真实 TTY 进程后再走网页审批流。

> **Agent 启动发布窗口（2026-08-14 实测 · 推荐做法）**：Agent 不能代跑 2FA，但可以
> **把发布窗口启动到用户桌面**——用户只负责「看 + 按回车 + 浏览器审批」，不用自己开终端：
>
> ```powershell
> # ① Agent：创建交互式计划任务（窗口将出现在用户交互桌面）
> schtasks /create /tn "DSHPublish" /tr "<powershell.exe 完整路径> -NoProfile -ExecutionPolicy Bypass -File "<npm-publish/scripts/publish-window.ps1>" -PackageDir "<包目录>" /sc once /st 23:59 /it /f
> # ② Agent：启动窗口
> schtasks /run /tn "DSHPublish"
> # ③ 用户：看窗口 → 按回车开浏览器 → 2FA 审批 → 再按回车 → 看到 + <包名>@<版本>
> # ④ Agent：收尾
> schtasks /delete /tn "DSHPublish" /f
> ```
>
> 脚本 `npm-publish/scripts/publish-window.ps1`（**UTF-8 BOM 保存**；参数 `-PackageDir` 必填，
> `-Preview` 只预览不真发）。设计理念三条：
> 1. **2FA 铁律不变**：网页审批流必须真实 TTY + 用户本人，Agent 只负责把窗口送到用户桌面；
> 2. **窗口怎么送到用户桌面**：Agent 直接 `Start-Process` 的窗口开在用户不可见的会话
>    （实测 `MainWindowHandle=0`）；必须用 `schtasks /it`（交互式任务）启动
>    `powershell.exe` 到用户交互桌面；
> 3. **编码适配**：系统代码页可能是 65001（UTF-8）——GBK 编码的 bat 中文必乱码；
>    脚本一律 UTF-8(BOM) + 脚本内显式 `[Console]::OutputEncoding = UTF8`；
>    脚本与参数路径避免中文（放仓库无中文路径下）。

失败分支（**先读报错码，再动手**）：

| 报错 | 含义 | 处理 |
|---|---|---|
| E403 `Two-factor authentication ... required` | 2FA 未开/未输码 | 走上方「交互式网页审批流」；无认证器 App 用恢复码填 2FA 框 |
| EOTP（非交互环境） | 无 TTY 时 npm 不发 URL 直接拒绝 | 必须在交互终端跑；或 `--otp=` 带当前码 |
| E403 `cannot publish over previously published version` | 版本重复 | 升 version 再发 |
| E401 / ENEEDAUTH | 未登录或令牌失效 | §流程 3 重新登录（npm 10 未登录时 publish 不发 URL 直接 ENEEDAUTH，先 login 再 publish） |
| E404 发布路径 404 | 包名被抢 / registry 错 | 查 `npm view`；确认 `--registry` |
| E409 | 版本冲突 | 升 version |

### 5. 验证（发布后必做）

```powershell
npm view <包名> version        # 应输出刚发布的版本
npm view <包名>                # 完整信息（主页 URL = https://www.npmjs.com/package/<包名>）
```

可试装：`npm install <包名> --registry=https://registry.npmjs.org`（在临时目录）。
**验证不过 → 视同发布失败，排查后修复再发。**

### 6. 版本迭代

1. 改 `package.json` 的 `version`（语义化：修复 +0.0.1 / 新功能 +0.1.0 / 破坏 +1.0.0）
2. 重跑 §流程 2（dry-run）→ §流程 4 → §流程 5
3. 若开了 2FA，每次都输验证码（**不要**为此创建 bypass-2FA 令牌，见硬规则）

### 7. 撤回（仅 72 小时内，且慎重）

```powershell
npm unpublish <包名>@<版本> --registry=https://registry.npmjs.org
```

- **72 小时窗口后不可删除，只能 `npm deprecate` 标记废弃**（发布即公开，先想清楚）
- 撤回再发同名同版本：可能被 npm 拒绝（有历史记录），此时升版本

## 硬规则（无跳过通道）

1. **发布前必跑 `npm pack --dry-run`**——内容不干净一律不发布
2. **包名先查占用**（`npm view` 404 才可用），不抢不猜
3. **版本号只增不减**，绝不重发同名同版本
4. **令牌绝不进聊天 / 仓库 / 命令行历史留存**——泄露即吊销（本次实战教训：令牌发进聊天后立即 revoke）
5. **发布必须走官方源** `registry.npmjs.org`——镜像（npmmirror 等）只下载、不发布
6. **`"private": true` 的包禁止发布**（发布前检查）
7. **2FA 政策时间表**（2026-07-08 npm 公告，已实测）：
   - 2026-08 起：bypass-2FA 令牌**不能再做账户/包管理操作**（含创建令牌本身）
   - 2027-01 起：bypass-2FA 令牌**不能再直接发布**（只能暂存 + 人工 2FA 批准）
   - → **个人发布一律用交互式 2FA（认证器 OTP）**，不依赖 bypass 令牌
8. 环境变量 `npm_config_registry` 优先级高于 `.npmrc`——命令行 `--registry=` 永远带上（见坑位 1）
9. **2FA 发布走「交互式终端 + 浏览器网页审批」**，不隔空传码：非交互环境 npm 不发 URL 直接 EOTP，聊天传 6 位 TOTP 码必过期（2026-08-14 实测）

## 软规则（心法，非清单）

- **发布 = 公开 + 几乎不可撤回**：动手前先当"发出去就收不回"来想
- **镜像与官方源的心法**：下载加速走镜像没问题；"登录/发布"永远只认官方源——镜像是对外只读的
- **失败先读码**：E403/E401/E404/E409 各有一类原因，报错码是 npm 给你的第一线索，别急着重试
- **最小发布面**：`files` 白名单能少则少，包里少一个文件比多一个安全得多
- **令牌像密码一样对待**：不粘贴、不截图、不共享、用完即吊销

## 坑位表

完整踩坑记录（含报错原文、根因、解决）见 [references/pitfalls.md](./references/pitfalls.md)。高频四条：

1. **镜像源拦截登录/发布**：`~/.npmrc` 或环境变量 `npm_config_registry` 指向 npmmirror → `npm login/publish` 报 `Public registration is not allowed`。解决：**命令行 `--registry=https://registry.npmjs.org`**（参数优先级最高，且不动全局镜像配置）。
2. **2FA 门槛**：npm 强制发布 2FA，`npm publish` 报 `Two-factor authentication ... is required`。解决：官网/CLI 开认证器 2FA，发布输 6 位码。
3. **令牌泄露**：令牌出现在聊天/日志 = 已泄露，**立即 revoke**，发布能力用 2FA 补上（不要"反正能用就先留着"）。
4. **非交互环境发布必 EOTP**：Start-Process / 后台 job / CI 跑 `npm publish` 时 npm 跳过网页审批直接报 EOTP（不发 URL）。
   - **未登录先登录（2026-08-16 实测）**：npm 10 未登录时 publish 不发 Auth URL、直接 `ENEEDAUTH`——必须先 `npm login --auth-type=web`（浏览器登录 + 2FA 拿令牌），之后 publish 的 2FA 才走网页审批流。发布窗口脚本已内置登录检测（未登录自动先引导登录）。
   解决：把命令交给用户在**交互终端**自己跑，npm 会打印 `Authenticate your account at: <URL>` + `Press ENTER to open in the browser...`，
   浏览器完成 2FA 审批（无认证器 App 时填恢复码）即发布成功。
   - **输出重定向也会触发 EOTP**（2026-08-14 实测）：`npm publish > result.txt 2>&1` 让 stdout 非 TTY → npm 跳过网页审批直接要 OTP。
     发布命令**绝不重定向输出**。
   - **Agent 启动发布窗口**：见 §流程 4「Agent 启动发布窗口」——schtasks /it 把窗口送到用户桌面，用户只按回车 + 浏览器审批。
   - **编码坑**（2026-08-14 实测）：系统代码页 65001（UTF-8）时 GBK 编码 bat 中文全乱码；窗口脚本一律
     UTF-8(BOM) + `[Console]::OutputEncoding=UTF8`，用 powershell.exe 执行（cmd/bat 慎用中文）。
   - **查发布状态必须指定官方源**（2026-08-14 实测）：全局 registry 是 npmmirror 时，`npm view` 走镜像，
     镜像同步有延迟 → 刚发布的版本查不到被误判失败。**验证一律 `--registry=https://registry.npmjs.org --prefer-online`**。

## 输出

- 发布成功：确认行 `+ <包名>@<版本>` + 包主页 URL
- 验证结果：`npm view` 的 version / 试装结果
- 失败：报错码 + 对应处理（见 §流程 4 表）
- 无 HTML 输出（12.A / 12.B 不适用——纯流程技能，按总纲 04 原则 0 豁免 HTML 镜像）

## 5 层自检（02 §5 清单适配）

- ① 数据层：**N/A**（无状态技能，无 DB / 无迁移）
- ② 操作层：命令全部原子化（一次一动作）；外部失败有明确报错码分支（§流程 4 表）✅
- ③ 规则层：硬规则 8 条集中在 SKILL.md，无跳过通道 ✅；软规则用"心法"表达 ✅
- ④ 接口层：接口 = npm CLI 命令本身（非自有 CLI）；命令清单即文档（§流程）✅
- ⑤ 文档层：SKILL.md 第一段 30 秒可答边界 ✅；触发词表 ✅；references/ 拆为 pitfalls + dsh-plugin-manifest ✅；HTML 镜像按原则 0 豁免 ✅

## 改动前必答 3 问（05 §改动前）

1. 影响哪些文件？→ 本技能目录下 SKILL.md / references/ / README.md
2. 有没有数据迁移？→ 无
3. 回滚方案？→ git commit 备份后改；出错 `git revert`

## 工程记录

- 2026-08-14：技能创建。流程来自 `dsh-opencode-tui-theme@1.0.0` 实盘发布（镜像坑 / 2FA 门槛 / bypass 令牌公告）。
- 2026-08-14（同日追加）：`dsh-opencode-tui-theme@1.1.0` 实盘发布发现**网页审批流**——交互终端 `npm publish` 会打印
  `Authenticate your account at: <URL>` 授权链接，浏览器完成 2FA 后回车即发布成功；非交互环境（Agent 重定向/后台）不发 URL
  直接 EOTP，聊天传码必过期。本技能 §流程 4 已按此更新（硬规则 9 / 坑位 4）。
- 2026-08-14（同日追加）：`dsh-harness-desktop@1.0.2` 实盘发布落地**发布窗口方案**——Agent 用 `schtasks /it` 把
  powershell.exe 窗口启动到用户交互桌面（直接 Start-Process 的窗口用户不可见）；脚本 UTF-8(BOM) 适配 65001 代码页；
  记录「输出重定向触发 EOTP」「镜像同步延迟导致验证误判」两个新坑。新增 `scripts/publish-window.ps1`（§流程 4）。
- 2026-08-16（实盘补丁，`dsh-opencode-palette@1.6.1`）：**bypass-2FA 旧令牌被 npm 政策限制**（stderr 提示
  `tokens that bypass 2FA are being restricted for direct publishing`）→ publish 拿失效令牌直接 PUT 返回
  **E404（假象）**，且不发 Auth URL。修复：`npm logout` 清旧令牌 → 重新发布触发网页登录。
  同时发现 **npm 10 未登录 publish 直接 ENEEDAUTH**（不发 URL）→ publish-window.ps1 升级：
  内置登录检测（未登录先 `npm login --auth-type=web`，浏览器 2FA，成功后再 publish）。
  另：edit 工具改 ps1 会丢 UTF-8 BOM（Windows PowerShell 按 GBK 读中文乱码致语法错误）——
  改完必须用 `UTF8Encoding($true)` 重写补 BOM。
- Tested-By: exempt(无 fresh agent + 发布有真实外部副作用不适合黑盒重放 · 详见 备忘录/docs/adr/0005-d-exemptions-and-rituals.md)

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
npm login --registry=https://registry.npmjs.org
npm whoami          # 必须输出用户名，否则回到 0
```

- 密码输入时不回显（正常现象）
- 登录凭证按 registry 分开存；镜像登录 ≠ 官方登录
- 若报 `Public registration is not allowed` → 坑位 1

### 4. 发布

```powershell
npm publish --registry=https://registry.npmjs.org [--otp=123456]
```

- 账号开了 2FA → npm 提示 `Enter one-time password:`，输认证器当前 6 位码；或 `--otp=` 直接带
- 成功标志：`+ <包名>@<版本>`

失败分支（**先读报错码，再动手**）：

| 报错 | 含义 | 处理 |
|---|---|---|
| E403 `Two-factor authentication ... required` | 2FA 未开/未输码 | 开 2FA 或用带 OTP 重发 |
| E403 `cannot publish over previously published version` | 版本重复 | 升 version 再发 |
| E401 / ENEEDAUTH | 未登录或令牌失效 | §流程 3 重新登录 |
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

## 软规则（心法，非清单）

- **发布 = 公开 + 几乎不可撤回**：动手前先当"发出去就收不回"来想
- **镜像与官方源的心法**：下载加速走镜像没问题；"登录/发布"永远只认官方源——镜像是对外只读的
- **失败先读码**：E403/E401/E404/E409 各有一类原因，报错码是 npm 给你的第一线索，别急着重试
- **最小发布面**：`files` 白名单能少则少，包里少一个文件比多一个安全得多
- **令牌像密码一样对待**：不粘贴、不截图、不共享、用完即吊销

## 坑位表

完整踩坑记录（含报错原文、根因、解决）见 [references/pitfalls.md](./references/pitfalls.md)。高频三条：

1. **镜像源拦截登录/发布**：`~/.npmrc` 或环境变量 `npm_config_registry` 指向 npmmirror → `npm login/publish` 报 `Public registration is not allowed`。解决：**命令行 `--registry=https://registry.npmjs.org`**（参数优先级最高，且不动全局镜像配置）。
2. **2FA 门槛**：npm 强制发布 2FA，`npm publish` 报 `Two-factor authentication ... is required`。解决：官网/CLI 开认证器 2FA，发布输 6 位码。
3. **令牌泄露**：令牌出现在聊天/日志 = 已泄露，**立即 revoke**，发布能力用 2FA 补上（不要"反正能用就先留着"）。

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
- Tested-By: exempt(无 fresh agent + 发布有真实外部副作用不适合黑盒重放 · 详见 备忘录/docs/adr/0005-d-exemptions-and-rituals.md)

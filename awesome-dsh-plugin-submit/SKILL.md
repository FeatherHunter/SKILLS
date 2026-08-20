---
name: awesome-dsh-plugin-submit
description: 把**本地 DSH 插件包**提交到 awesome-dsh-plugin 官方策展注册表（https://awesome-dsh-plugin.com）的全流程技能：提交前自检（dsh.bundle 声明 / 1 天+10 提交门槛 / dsh-plugin GitHub topic / 描述准确性）→ fork awesome-dsh-plugin/awesome-dsh-plugin → 写入 `data/plugins/<owner>__<repo>.yml`（YAML 字段：url/name/category/description.en/zh/可选 tarball/可选 npm）→ 跑 `node scripts/generate-readme.mjs` 重新生成 README → 一个 PR 完成收录。触发词「收录到 awesome-dsh-plugin」「提交插件到插件市场」「让插件进 awesome-dsh-plugin 列表」「生成 awesome-dsh-plugin 收录 PR」「dsh plugin 入 awesome 列表」。也用于：移除 / 改分类 / 修描述 / 加截图 / 处理 CI 报错（缺 dsh.bundle / 仓库太新 / 提交数不足 / peer 范围不含 prerelease 分支）。
---

# awesome-dsh-plugin-submit

> 把 DSH 插件收录到 awesome-dsh-plugin（DSH 官方策展注册表，**awesome-dsh-plugin.com**）的全流程技能。
> 一个 YAML 文件 + 一个 PR = 收录完成。README 由脚本生成，**禁止手工编辑**。

## 管什么 / 不管什么（30 秒边界）

**管**：

- 在 https://awesome-dsh-plugin.com 注册表里**收录、修改、移除**插件条目
- 提交前自检：`dsh.bundle` 声明、仓库 ≥1 天、提交数 ≥10、`dsh-plugin` GitHub topic、描述准确性
- YAML 文件模板（`data/plugins/<owner>__<repo>.yml`）的正确写法（含 `: ` 必须加引号、category 20 选 1、en/zh 双语规范）
- 重新生成 README（`node scripts/generate-readme.mjs`）
- 可选加分项：npm 发布、GitHub Release tarball、`data/screenshots.json` 截图、`peerDependencies` prerelease 分支
- 处理 CI 报错（缺 `dsh.bundle` / 仓库年龄 / 提交数 / YAML 格式 / 截图 URL 不合规）
- 评审互动（被维护者评论打回 → 按行修改 → 重新 commit，同分支推送即可，不重开 PR）

**不管**：

- **不写插件代码本身**——本技能假设你的 `package.json` / `cordis.patch.yml` / `lib/` 已就绪
- **不在 awesome-dsh-plugin.com 网站上提交 UI**——收录只在 GitHub 上做（PR 流程）
- **不收录非 DSH 插件**——本技能只针对**有 `dsh.bundle` 声明**的 DSH 插件包
- **不收录私有 / 仅本地的插件**——awesome-dsh-plugin 强制公开 GitHub 仓库
- **不收录单纯的 themes/skins**到 `ui` 分类——themes 应放 `theme`（市场有专用 Tab）
- **不收录非官方 `@deepseek-ai/*` 之外的替代 harness 插件**——awesome-dsh-plugin 只服务于 DeepSeek Harness

## 触发词表（4 元组 = 动作 + 对象 + 维度 + 类型）

| 核心触发词 | 变体 | 动作序列 |
|---|---|---|
| 收录插件到 awesome-dsh-plugin | 提交到插件市场 / 加入 awesome 列表 / 进 awesome-dsh-plugin / 让插件上 awesome-dsh-plugin.com | §流程 1 → 6 |
| 生成 awesome-dsh-plugin 收录 PR | 生成 YAML / 帮我开个收录 PR / 写收录文件 / 准备提交 | §流程 3 → 6 |
| 检查收录前自检 | 能不能收录 / 我这插件够格吗 / 自检一下 / 入 awesome 前要准备啥 | §流程 1 |
| 处理 CI 报错 | CI 没过 / dsh.bundle 缺失 / 仓库太新 / 提交数不够 / YAML 不合法 | §坑位 1-5 |
| 修改/移动/移除已收录条目 | 改描述 / 换分类 / 移除死项目 / 更新 npm 字段 | §流程 7 |
| 加截图 | 加截图到 awesome 列表 / 让市场详情页显示图 | §流程 8 |
| peerDependencies prerelease 报错 | ERESOLVE / prerelease 装不上 / 我的 @deepseek-ai/* 范围错了 | §流程 9 + 硬规则 6 |

## 路由规则 · 与其他技能的边界

- 「**写插件代码**（改 lib/、加 client、cordis.patch.yml 怎么写）」→ 不是本技能；本技能**只负责收录**
- 「**发布到 npm 官方源**」→ 走 `npm-publish/`（先发布 npm，再收录时加 `npm:` 字段；可选但推荐）
- 「**DSH 插件打包出 tgz**（GitHub Release 附件）」→ 是本技能 §流程 5 的可选加分项，但**打 tgz 的具体步骤**与 `npm-publish` 的 `npm pack` 路径不同，参考官方市场发行指南（如有）；本技能只覆盖"如何在 YAML 里引用它"
- 「**awesome-dsh-plugin.com 网站本身的搜索 / 浏览**」→ 不归本技能（这是普通用户场景，不需要 AI 协助）
- 「**dsh-market / dsh-plugin-manager / dsh-plugin-hub 这些"市场插件"的二次开发**」→ 不归本技能（那些是消费者侧 UI）

## 收录流程

#### 0. 心法先于流程

> **awesome-dsh-plugin 不是竞赛排行榜，也不是质量奖**。维护者原话："我们不是插件好坏的裁判"。
> 收录规则只为一件事：让打开这个页面的人，**装上后**它确实做描述里写的那件事。
> 被维护者评论打回 ≠ 插件差；按行修一下就行，**绝不会**因分类被打回。

### 流程 1 · 提交前自检（每次 PR 前必跑）

```bash
# ① 必填：dsh.bundle 声明 + cordis.patch.yml
test -f package.json && grep -q '"bundle"' package.json && echo "OK dsh.bundle" || echo "FAIL: 缺 dsh.bundle"
test -f cordis.patch.yml && echo "OK cordis.patch.yml" || echo "FAIL: 缺 cordis.patch.yml"

# ② GitHub 元数据（必填项）
gh repo view <owner>/<repo> --json createdAt,description,repositoryTopics | jq .
# 检查项：
#   createdAt < 今天 - 1 天（仓库 ≥ 1 天）
#   topics 含 "dsh-plugin"（GitHub 仓库标签）
#   description 有内容

# ③ 提交数（≥ 10）
gh api repos/<owner>/<repo>/commits --jq 'length'   # 注意：API 默认只返回 1 页，
                                                     # 实际 ≥ 10 应用 gh repo view 看

# ④ 描述准确性自检（防"夸大是打回主因"）
#    把 description.en / description.zh 里所有数字、命令名、API 名逐项 grep 一遍源码
#    例如写"25 个技能"就要能找到 25 个
grep -rE "dsh-skill-" lib/ | wc -l
```

**自检清单**（全 ✓ 才能开 PR，否则先补齐）：

| 项 | 检查方式 | 通过标准 |
|---|---|---|
| `package.json` 含 `dsh.bundle` | `grep '"bundle"' package.json` | 必须有；仅 `dsh.client` **不算**（这是被拒主因） |
| `cordis.patch.yml` 在仓库根 | `test -f cordis.patch.yml` | 必须有，格式见 §流程 3 模板 |
| 仓库创建 ≥ 1 天 | `gh repo view --json createdAt` | CI 自动卡 |
| 提交数 ≥ 10 | `gh repo view --json` 或 `git log --oneline \| wc -l` | CI 自动卡 |
| 仓库有真实代码 | `ls lib/` `ls package/` 等 | 非占位、非 README-only |
| 仓库打 `dsh-plugin` topic | gh 仓库 → About → Topics | 必填，没打不会被抓取 |
| description 无营销词、无夸大数字 | 逐项 grep 验证 | "46 个工具" = 真 46 个；提到命令/API 就该存在 |
| 分类选最贴近的 1 个 | 见 §流程 3 分类表 | 选错不打回，维护者会改 |
| 项目活跃维护 | 最近 30 天有 commit | 不活跃 → 维护者会标跟踪 issue，最终移除 |
| peerDependencies 带 prerelease 分支 | 见 §流程 9 | **漏了 → 用户 ERESOLVE，体验事故** |

### 流程 2 · Fork & 克隆

```bash
# 1. 在 GitHub 上 fork awesome-dsh-plugin/awesome-dsh-plugin
gh repo fork awesome-dsh-plugin/awesome-dsh-plugin --remote=true

# 2. 克隆到本地
cd ~/work
git clone https://github.com/<你的GitHub用户名>/awesome-dsh-plugin.git
cd awesome-dsh-plugin
npm ci                                # 装 scripts/generate-readme.mjs 依赖
git checkout -b add-<owner>-<repo>    # 分支名建议 add-<owner>-<repo>
```

### 流程 3 · 创建 YAML 文件

**文件名**（**双下划线 `__`**，GitHub-friendly，不带特殊字符）：

```
data/plugins/<owner>__<repo>.yml              # 普通插件
data/plugins/<owner>__<repo>--<subpath>.yml   # monorepo 子包（"--"分隔）
```

例如你的 `FeatherHunter/dsh-mattpocock-skills-deck` → 文件名应是
**`data/plugins/FeatherHunter__dsh-mattpocock-skills-deck.yml`**

**YAML 内容模板**（精确保留此格式）：

```yaml
url: https://github.com/FeatherHunter/dsh-mattpocock-skills-deck
name: FeatherHunter/dsh-mattpocock-skills-deck
category: skill                    # 见下方"分类速查"
description:
  en: "Matt Pocock skills deck: right-side details panel injecting 25 engineering and productivity skills (wayfinder routing, triage labels, grilling, handoff)."
  zh: "Matt Pocock 技能面板：右侧 details 面板，注入 25 个工程与效率技能（wayfinder 路由、triage 标签、grilling、handoff）。"

# 可选：以下 4 个字段全部可选，0 个也行；推荐至少填 npm 或 tarball 二选一
# npm: dsh-mattpocock-skills-deck
# tarball: https://github.com/FeatherHunter/dsh-mattpocock-skills-deck/releases/latest/download/dsh-mattpocock-skills-deck.tgz
```

**YAML 写法硬约束**（下面 4 个坑 CI 会卡）：

1. **描述含 `: ` 必须加引号**——YAML 把冒号加空格当嵌套键

   ```yaml
   description:
     en: 'Vision toolkit: OCR, grounding and pixel diff.'   # ✅ 加单引号
     zh: '识图工具包：OCR、定位与像素比对。'                  # 中文全角冒号无此问题，但加也无妨
   ```

2. **`description.en` 是唯一必填**；`zh` 可空，维护者会补——**不要因为不会写中文就不开 PR**

3. **URL 必须与仓库完全一致**——分支大小写、`.git` 后缀、是否含 `/tree/main` 都对（monorepo 子包需 `/tree/<branch>/<subpath>`）

4. **monorepo 子包**（如 `DamonKoy/dsh-web-ui/tree/main/packages/dsh-web-ui-all`）：

   ```yaml
   url: https://github.com/DamonKoy/dsh-web-ui/tree/main/packages/dsh-web-ui-all
   name: DamonKoy/dsh-web-ui#dsh-web-ui-all
   # 文件名: DamonKoy__dsh-web-ui--packages-dsh-web-ui-all.yml
   ```

**分类速查**（20 选 1，选最贴近的，不必纠结）：

| 分类 | 适合 |
|---|---|
| `ui` | 通用界面增强 / 控制面板（**注意**：themes/skins **不要**放这里） |
| `theme` | 主题 / 皮肤（市场有专用 Tab，会被自动聚合） |
| `skill` | 注入技能 / skills 套件 |
| `tools` | 通用工具集（FS / shell / http 等） |
| `model` | 模型相关（路由、限速、自定义模型） |
| `session` | 会话管理（存档、导出、恢复） |
| `memory` | 记忆 / 上下文持久化 |
| `workflow` | 工作流 / 多 agent 编排 |
| `git` | Git 集成（commit、diff、PR 操作） |
| `notify` | 通知（飞书 / 钉钉 / Slack / 邮件） |
| `dev` | 开发辅助（code review / lint / 测试） |
| `security` | 安全（凭据、审计、防泄露） |
| `vision` | 视觉 / 图像处理 / OCR |
| `voice` | 语音 / TTS / STT |
| `docs` | 文档生成 / 检索 / RAG |
| `browser` | 浏览器自动化 |
| `remote` | 远程 / SSH / 桌面控制 |
| `market` | 插件市场 / 插件管理器 / 注册表 |
| `usage` | 用量 / 计费 / 成本监控 |
| `fun` | 桌宠 / 游戏 / 整活 |

**官方原话**："不会有人因为分类被打回——选错维护者直接改。挑最接近的一个即可，不必纠结。"

### 流程 4 · 重新生成 README（脚本，别手工）

```bash
node scripts/generate-readme.mjs
# 会同时生成 README.md 和 README.zh.md
git diff README.md README.zh.md | head -50     # 自检：你的条目是否正确出现在对应分类
```

**注意**：脚本生成时**会重新排序**——不要担心位置，先出现≠永久位置。

### 流程 5 · 提交 & 推分支

```bash
git add data/plugins/FeatherHunter__dsh-mattpocock-skills-deck.yml README.md README.zh.md
git commit -m "Add FeatherHunter/dsh-mattpocock-skills-deck

- category: skill
- dsh.bundle: present
- short: right-side details panel injecting 25 skills"
git git push origin add-FeatherHunter-dsh-mattpocock-skills-deck
```

### 流程 6 · 开 PR（GitHub 网页或 gh CLI）

```bash
gh pr create \
  --repo awesome-dsh-plugin/awesome-dsh-plugin \
  --title "Add FeatherHunter/dsh-mattpocock-skills-deck" \
  --body "Adds my plugin: dsh-mattpocock-skills-deck

- Right-side details panel injecting Matt Pocock's 25 skills (wayfinder routing, triage, grilling, handoff)
- dsh.bundle declared, cordis.patch.yml in repo root
- Repo: https://github.com/FeatherHunter/dsh-mattpocock-skills-deck"
```

PR 标题**保持简洁**（"Add <owner>/<repo>"），正文**说明插件功能 + 自检通过的项目**。

合并后网站自动重建，无需做任何其它事。

### 流程 7 · 修改 / 移动 / 移除已收录条目

```bash
# 改描述 / 改分类 / 改 npm 字段 → 直接编辑对应的 YAML 文件
$EDITOR data/plugins/<owner>__<repo>.yml
node scripts/generate-readme.mjs    # 重生成
git commit -am "Update <owner>/<repo>: <简短原因>"
git push                            # 同分支直接推送，PR 自动更新

# 移除条目
rm data/plugins/<owner>__<repo>.yml
node scripts/generate-readme.mjs
git commit -am "Remove <owner>/<repo>: <简短原因（archived / 不再维护 / 仓库已删）>"
```

**铁律**（维护者反复强调）：**改自己条目的 PR 只能动自己那一条**。不要顺手改别人的描述——README 是生成的，行号会移位，会撞到邻居。维护者用 #1348 这种 issue 跟踪这类事故。

### 流程 8 · 加截图（可选 · 强烈推荐）

在 `data/screenshots.json` 里以你的 GitHub URL 为 key 加 1–8 张图片：

```jsonc
{
 "https://github.com/FeatherHunter/dsh-mattpocock-skills-deck": [
  "https://raw.githubusercontent.com/FeatherHunter/dsh-mattpocock-skills-deck/main/assets/screenshot-1.png",
  "https://raw.githubusercontent.com/FeatherHunter/dsh-mattpocock-skills-deck/main/assets/screenshot-2.png"
 ]
}
```

**硬约束**：

- 必须是 **GitHub 托管的 https URL**（`raw.githubusercontent.com` / `user-images.githubusercontent.com` / `camo.githubusercontent.com`）
- 第三方图床（imgur / sm.ms / 自有 CDN）**会被构建拒绝**（用户隐私原因）
- 建议图片放在你自己的仓库 `assets/` 目录，跟版本一起维护
- 不加也没事：市场会从你 README 自动抽图（顺序不可控）

### 流程 9 · peerDependencies prerelease 分支（**关键坑**）

如果你的 `package.json` 依赖 `@deepseek-ai/*`：

```jsonc
// ❌ 看起来很宽，实际上静默排除所有 0.1.0-* prerelease
"peerDependencies": { "@deepseek-ai/dsh-tools": ">=0.0.1-rc.1 <0.2.0" }

// ✅ 在 0.1.0 这个元组上显式带 prerelease 标签
"peerDependencies": { "@deepseek-ai/dsh-tools": ">=0.0.1-rc.1 <0.1.0 || >=0.1.0-rc.1 <0.2.0-0" }
```

**为什么**：node-semver 只在范围里有**同一 `major.minor.patch` 元组且自身带 prerelease 标签**的比较符时，才放行 prerelease 版本。看起来很宽的 `>=0.0.1-rc.1 <0.2.0` 实际匹配不到 `0.1.0-rc.6`——用户 `npm install` 时会撞 `ERESOLVE`，要手工解决，体验事故。

---

## 硬规则（无跳过通道）

1. **必须有 `dsh.bundle` 声明 + `cordis.patch.yml`**——仅 `dsh.client` 不算。这是被拒主因
2. **仓库 ≥ 1 天 + 提交数 ≥ 10**——CI 自动卡。不到就把功能做完再提，**重新提交不会有任何影响**
3. **仓库打 `dsh-plugin` GitHub topic**——没打 = 不会被抓取 = 不会被任何市场发现
4. **description 必须属实**——逐项 grep 验证。**"夸大是让一个本来不错的插件被打回的主要原因"**（官方原话）
5. **不要顺手改别人的条目**——这是 README 行号撞车事故的常见起因。改自己条目 → 改自己 YAML → 重生成
6. **peerDependencies 必须带 prerelease 分支**——否则用户装不上你的 prerelease harness，ERESOLVE 体验事故
7. **URL 必须与仓库完全一致**——不要瞎改分支名 / 路径
8. **截图必须 GitHub 托管的 https URL**——第三方图床会被构建拒绝（用户隐私）
9. **YAML 描述含 `: ` 必须加引号**——否则 CI 解析失败

## 软规则（心法，非清单）

- **收录不是永久的**——停止维护、有 bug、长期 dormant 会被移除。被收录 ≠ 既得利益
- **fork 也可能被收录**——只要维护得更好或真做了新东西，规则是"谁更好"不是"先来后到"
- **分类选错不打回**——维护者会直接改。不要纠结，挑最接近的一个
- **PR 评论打回 ≠ 拒绝**——按行修一下即可，**绝不会**因分类 / 命名风格 / 措辞被打回（除非夸大）
- **不要描述"怎么装"**——列表只说"做什么"。安装方式市场自动生成
- **npm 发布是加分项不是必填**——但发布后用户安装免 `allowBuilds` 步骤，体验明显更好

## 坑位表

完整踩坑记录（含报错原文、根因、解决）见 [references/pitfalls.md](./references/pitfalls.md)。高频 9 条：

1. **缺 `dsh.bundle` / 只有 `dsh.client`**：CI 第一关会挂。**最常见被拒原因**。修复：在 `package.json` 加 `dsh.bundle.patch: ./cordis.patch.yml`，并在仓库根放 `cordis.patch.yml`（含 `- insert: - id: 你的插件id`）
2. **仓库太新（< 1 天）**：CI 卡"创建时间"。不是对插件质量的评价，只是防"PR 前几分钟才建好"的仓。修复：把功能做完再提
3. **提交数 < 10**：CI 卡"commit count"。修复：把功能做完再提，**重新提交不会有任何影响**
4. **YAML 含未引号的 `: `**：CI YAML lint 失败。修复：描述加单引号
5. **分类选错**：**不会被打回**，维护者会直接改成更贴切的。所以不必纠结
6. **`peerDependencies` 漏 prerelease 分支**：用户 `npm install` 时撞 `ERESOLVE`。修复：用显式 `||` 在匹配的 `major.minor.patch` 元组上带 prerelease 标签
7. **截图用了第三方图床**（imgur 等）：构建拒绝（用户隐私）。修复：放自己仓库 `assets/`，用 `raw.githubusercontent.com`
8. **改了 README 没改 YAML**：README 是生成的，下次重生成就被覆盖。**禁止手工编辑 README**
9. **改自己条目时顺手改了别人**：维护者用 #1348 跟踪这种事故。修复：只 `git add` 自己那个 YAML + 重生成的 README，其它条目不要动

## 输出

- 流程成功：YAML 文件路径 + 生成后的 README diff（关键行）+ PR URL
- CI 报错：报错码 + 对应坑位（见 §坑位 1-9）
- 自检未通过：清单 + 修复建议（按"硬规则 1-9"逐项打勾）
- 修改条目：YAML diff + README 变化行
- **不输出 HTML**（按总纲 04 原则 0 豁免 HTML 镜像——本技能是流程技能，无可视化需求）

## 5 层自检（02 §5 清单适配）

- ① 数据层：**N/A**（无状态技能，无 DB / 无迁移）
- ② 操作层：所有步骤（git/gh/gh api/node scripts/generate-readme.mjs）原子化，单步可重试 ✅
- ③ 规则层：硬规则 9 条集中在 SKILL.md，无跳过通道 ✅；软规则用"心法"表达 ✅
- ④ 接口层：接口 = GitHub REST API + gh CLI + `scripts/generate-readme.mjs`（非自有 CLI）；命令清单即文档 ✅
- ⑤ 文档层：SKILL.md 第一段 30 秒可答边界 ✅；触发词表 ✅；references/ 拆为 pitfalls ✅；HTML 镜像按原则 0 豁免 ✅

## 改动前必答 3 问（05 §改动前）

1. 影响哪些文件？→ `SKILL.md` / `references/pitfalls.md`（如有新坑）/ `README.md`（如本技能本身也要登记到根 README）
2. 有没有数据迁移？→ 无
3. 回滚方案？→ `git revert` 提交；YAML 文件删除后 `git checkout HEAD~1`

## 工程记录

- 2026-08-18：技能创建。流程来自用户调研 awesome-dsh-plugin.com（1283 个插件 / 827 个独立作者）+ 官方 `awesome-dsh-plugin/awesome-dsh-plugin/contributing.md` 全量阅读 + 用户本地插件 `FeatherHunter/dsh-mattpocock-skills-deck` 实战自检。
- 落地首批产物：本技能 `SKILL.md` + `references/pitfalls.md`（高频 9 条坑位）。
- 与既有技能边界：与 `npm-publish` 互补（先 npm 发布 → 再 awesome 收录时加 `npm:` 字段）。
- 用户目标插件 `FeatherHunter/dsh-mattpocock-skills-deck` 自检结果（2026-08-18 调研时）：
  - ✓ `dsh.bundle` 声明 + `cordis.patch.yml`（位于 `package/cordis.patch.yml`，`dsh.bundle.patch` 指向 `./cordis.patch.yml`）
  - ✓ 仓库有真实代码（lib/）
  - ? 仓库创建时间 / 提交数 / GitHub topic 需查 gh CLI
  - ⚠ description 当前是营销味浓的长描述（含"npm 标准安装"等"怎么装"内容），收录前需重写为纯功能描述
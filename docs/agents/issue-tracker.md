# 问题追踪：GitHub Issues

本仓库的问题（issue）与规格（PRD）统一发布到 GitHub Issues（`FeatherHunter/SKILLS`），通过 `gh` CLI 读写。各技能共享同一份 issue 列表，靠**标题前缀 + label 命名空间**做分区。

## 多技能隔离策略

### 标题前缀（强约束）

新建 issue 必须以 `[技能名]` 起首，便于人类浏览与 `gh issue list --search` 过滤：

- `[备忘录] 心愿表支持字段补全`
- `[卡路里] 营养目标页面的卡路里柱状图错位`
- `[居家管家] 标签合并不应触发盘点重算`
- `[饼干记账] 月度对比页的加载态缺失`
- `[智剪工坊] 模板 `健身vlog` 渲染失败`
- `[作息管家] 帮助页 73 场景首次打开报错`
- `[SKILL开发总纲] 待开发章节的占位规则`

### Label 命名空间

- 技能分区：`skill:备忘录` / `skill:卡路里` / `skill:居家管家` / `skill:饼干记账` / `skill:智剪工坊` / `skill:作息管家` / `skill:总纲` / `skill:私家大厨` / `skill:学习系统` / `skill:面试系统`(2026-08-03 配色统一 + 新增 3 个技能 label) / `skill:公共组件`(Base Skill 跨技能公共层, 2026-08-13 补登记)
- 分类：`bug` / `enhancement`
- 状态：`needs-triage` / `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix`
- 自定义（如跨技能主题）：`cross-skill` / `docs` / `infra`

每个被处理的 issue 同时携带 1 个技能 label、1 个分类 label、1 个状态 label。

## 命令约定

> ⚠️ **gh 未加入 PATH**（2026-08-02 核实：`shutil.which('gh')` 返回 None）。gh 可执行文件在 **`D:\0Tools\GitHubCLI\gh.exe`**。PowerShell 调用方式：
>
> ```powershell
> # 方式 1:call operator 全路径
> & "D:\0Tools\GitHubCLI\gh.exe" issue list --state open --label "skill:卡路里"
> # 方式 2:session 内临时加 PATH(本 session 内直接写 gh)
> $env:Path += ";D:\0Tools\GitHubCLI"
> ```
>
> 本文档及 wayfinder 相关协议中出现的所有 `gh` 命令均指此路径；在 PATH 配置好前不要假设 `gh` 可直接调用。

`gh` CLI 在仓库根目录运行自动推断 `owner/repo`，无需显式传参。

```bash
gh issue create \
  --title "[卡路里] 营养目标页面的卡路里柱状图错位" \
  --body-file <(cat <<'EOF'
## 现象
…
## 复现步骤
…
EOF
) \
  --label "skill:卡路里,bug,needs-triage"

gh issue list --state open --label "skill:卡路里"
gh issue list --state open --label "ready-for-agent"
gh issue view 42 --comments
gh issue edit 42 --add-label "ready-for-agent" --remove-label "needs-triage"
gh issue close 42 --comment "已合入 #43"
```

读取完整结构化数据：

```bash
gh issue list --state open \
  --json number,title,body,labels,comments \
  --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'
```

## Wayfinding operations（wayfinder 子议题约定 · 2026-08-13）

wayfinder map 的父/子关系与进度追踪用 GitHub **原生子议题（sub-issues）** 表达（gh ≥ 2.63 支持；本机 2.97.0 已验证，仓库 API 可用）：

- 建子票：`gh issue create --parent <map号>`（新票直接挂父）
- 存量补挂：`gh issue edit <map号> --add-sub-issue <号,号,...>`，或对单票 `gh issue edit <子票号> --parent <map号>`
- **进度条自动维护**：父 issue 页面原生渲染「子议题」进度（n/N），子票 closed 自动更新——map body 内**不再维护手动勾选清单/状态列**（与原生进度重复会漂移），保留「票索引表」作对照即可
- 解绑：`gh issue edit <子票号> --remove-parent`
- 阻塞关系（原生依赖图，gh ≥ 2.97）：`gh issue create --blocked-by/--blocking` / `gh issue edit --add-blocked-by/--add-blocking`——可替代 body 内「⛓ 阻塞」文字约定
- 子议题与普通 issue 在列表中无区别（仍是独立 issue，可独立打标签/指派/关闭）

## 本地 .scratch 与 GitHub 的关系（历史迁移）

仓库初始化前，部分技能（`作息管家/`、`备忘录/` 等）已经在 `.scratch/<feature>/issues/NN-*.md` 内维护本地 markdown ticket。以**本次提交日为分界线**：

- **历史**：`.scratch/<feature>/issues/*.md` 视为**只读归档**，保留作为 ADR/spec 引用证据与决策追溯；不要删除。
- **未来**：新建/讨论/关闭 issue 全部走 GitHub Issues（`gh issue create` / `gh issue view`）。
- 在 `CONTEXT.md` 或子技能 `AGENTS.md` 里引用本地 md 时，可以继续用相对路径（如 `作息管家/.scratch/skill-optimize/issues/01-adr0001-help-sync.md`）。

### 迁移建议（不做强制）

未来如需把某条历史 md 转成 GitHub issue，单条转换命令：

```bash
gh issue create \
  --title "[作息管家] <原标题>" \
  --body-file "作息管家/.scratch/<feature>/issues/<NN>-<slug>.md" \
  --label "skill:作息管家,enhancement,needs-triage"
```

不需要批量迁移；保持历史归档即可。

## `.out-of-scope/` 目录

`/triage` 拒绝 enhancement 请求时会把"为什么拒绝"写到 `<技能目录>/.out-of-scope/<slug>.md`。本仓库在每个有 `.scratch/` 的技能下各建一份（共 7 个）。目录内 `README.md` 说明写入规范。

## 安全备注

`git remote -v` URL 当前**内嵌 GitHub PAT**（明文写入 `.git/config`），任何 clone 本仓库的协作者都能读到该 token 的访问权限。建议尽快：

1. 在 GitHub Settings → Developer settings → Personal access tokens **revoke** 该 token
2. `git remote set-url origin git@github.com:FeatherHunter/SKILLS.git`（切 SSH）
3. 后续 `gh auth login` 走系统 keyring（`Logged in to github.com ... (keyring)` 已确认）

未撤销前，任何对 `FeatherHunter/SKILLS` 的 push 都通过该 PAT 完成；token 撤销后切 SSH 前所有 push 会立即失败。

## 配置文件归档

各技能目录原有的 `docs/agents/issue-tracker.md`、`docs/agents/triage-labels.md` 若内容仍描述"本地 markdown"，视为本仓库迁移前快照，可在下次维护时同步成本文件描述。
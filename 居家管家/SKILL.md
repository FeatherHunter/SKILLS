---
name: 居家管家
description: >
  家庭物品全生命周期管理技能。当用户使用以下指令时触发：
  查物品、看物品（搜索/查看详情）、
  录物品、拍物品（文字录入/拍照录入）、
  改物品、移物品、补物品、减物品、标物品、废物品、借物品、修物品（更新类）、
  盘物品、盘全部（盘点）、
  穿什么（穿搭推荐）、
  带物品、归物品（旅游归位）、
  统物品、查高频、查低频（频率统计）、
  查过期（过期检查）、
  看标签、合标签（标签管理）、
  查快递（快递查询）、
  查账号、存账号、改账号（账号密码管理）、
  购买记录（购买记录查询/统计）、保修（保修与保养）、证件（证件管理）、账号（账号密码·脱敏）、
  批量录入、补录（批量/历史录入）、
  紧急定位、筛选浏览、拍照找物品、查重复（查找进阶）、
  数量变更、状态变更、合并物品、撤销操作、物品关联（更新进阶）、
  管标签、管分类、整理建议（标签分类管理）、
  查看照片、管照片、照片墙（照片档案）、
  盘点记录、差异处理、搬家盘点（盘点进阶）、
  历史（物品历史）、
  借用、家人档案（家庭协作）、
  查闲置（闲置检测）、盘点统计（盘点统计与建议）、
  联动总览、记到卡路里、记到记账（跨技能联动）、
  首次使用（初始化工作流）、备份导出（数据资产）、导入恢复（迁移）、
  查异常（数据健康检查）。
  所有操作通过 Python CLI 执行数据库读写，AI 负责解析自然语言和交互确认；录物品/拍物品流程在写入前生成 HTML 预览供用户确认。
metadata:
  openclaw:
    emoji: 🏠
    requires:
      python: ">=3.7"
      pip:
        - cryptography
  help_wake_word: "居家管家 帮助"
---

## 📘 关于 `居家管家.html`(总纲 04 §原则 4 · 镜像)

**本 HTML 文件就是 `python3 scripts/home_manager.py help` 输出的精确副本。**

- 修改唤醒词/场景 → 改 `references/scenarios.yaml` → 跑 `python3 scripts/build_manual.py` 同步。
- 不要手动编辑 `居家管家.html`(脚本会覆盖)。
- 测试 `tests/test_manual_sync.py` 用 SHA256 哈希断言字节一致,**若有人忘了同步,测试失败报警**(不阻断 commit,只报警)。
- 同步脚本自动注入 `HELP_FIXED_TIMESTAMP="0000-00-00 00:00 (快照)"`,确保可重现生成(不被 `datetime.now()` 干扰)。

> **总纲 04 §原则 4(本 skill 改造版,2026-07-27)**: 每个技能目录都需要有 `{技能名}.html` 文件,**该文件就是技能 HELP HTML 最新版本的复制品**。


**🔗 联动提示：** 完成本技能主操作后，检查技能路由器（`图片路由/SKILL.md`）的联动规则，判断是否需要联动其他技能（如用户提到物品价格→询问是否记录支出；物品是食品/饮料→询问是否记录卡路里）。详见路由器的联动规则表。

## ⚠️ HTML 同步规范（最高优先级）

> **此规范优先级高于本文件中所有其他规定。**

1. **全量同步**：该技能的所有优化和变动、脚本的所有变动都必须体现在 `居家管家.html` 上。任何功能模块的新增、修改、删除，任何唤醒词的调整，任何 CLI 命令的变化，任何脚本逻辑的改动——都必须同步更新 HTML 页面中对应的内容。
2. **最高优先级**：本条规定在所有规范中优先级最高。当其他流程或习惯与本条冲突时，以本条为准。
3. **逐行确认**：对该技能的所有文件、脚本的任何一行修改，都需要明确得到用户的 1 次确认后方可执行。不得批量静默修改，不得跳过确认步骤。

---

## ⚠️ Commit 硬规则（强制）

> 优先级与"HTML 同步规范"平级，所有写代码的 AI / 协作者必须遵守。

1. **禁止** `git commit --no-verify` —— 会跳过 pre-commit hook 测试
2. **禁止** 使用 git 库（`gitpython` / `simple-git` / `libgit2` 等）直接 API 调用 —— 绕过 shell，hook 不触发
3. **必须** 通过 pre-commit hook 的 71 个 pytest 测试才能 commit
4. **新机器首次使用本 skill 前**，必须执行 `bash scripts/install_hooks.sh` 配置本地 hook

**hook 工作机制**（SKILLS/ 是单 git 仓库，多 skill 子目录）：
- git 仓库根：`SKILLS/.githooks/pre-commit`
- 改动路径含 `居家管家/*` → 自动跑 `居家管家/tests/` 下的 71 个 pytest
- 改动路径含 `卡路里/*` → 跑 `卡路里/tests/`
- 其他改动（文档/HTML 手册/架构规范）→ 跳过测试

**为什么需要这层约束**：本地 `.githooks/pre-commit` 跑 pytest 是 CI 的本地替代方案。详见 `git-hooks-security-analysis.html`（已归档于 opencode output 目录）。

---

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

---

## ⚠️ 分类命名规范（强制）

**所有写入 categories 表的 name 字段必须满足以下规则。违规会被 `category_manager.py` 拒收，不入库。**

### 规则

| # | 规则 | 违规示例 | 原因 |
|---|---|---|---|
| 1 | 非空,strip 后 1-30 字 | `""` / `"   "` | 占位/空白无意义 |
| 2 | **禁数字前缀** | `3. 家居` / `2 衣物` / `[1]数码` / `(2)图书` | DB id 137/138/205-210 已是天然编号,name 再加 = 双重编号 = 装饰 |
| 3 | 禁 emoji | `🎉 食物` | 装饰,破坏纯文本 |
| 4 | 同 parent 下 name 唯一 | 两个同名二级 | 防止 merge 漏掉产生歧义 |

### 第一性

- 数字编号是 **DB id 的事**,name 负责语义
- 8 顶级 name **统一不带前缀**:`食物与饮品` / `衣物与穿戴` / `家居与陈设` / `工具与器材` / `数码与电子` / `健康与医药` / `文体与娱乐` / `资产与凭证`
- 跨次加节点时,先看现有 name 风格,跟齐

### 实现位置

`scripts/category_manager.py` 的 `_validate_name(name, parent_name, conn)` 函数,被 `cmd_import` / 未来 `cmd_add` 调用。

---

## 路由表

AI 收到用户输入后，按以下表匹配唤醒词，命中即加载对应功能。

| # | 唤醒词 | 功能 | 加载文件 | 需要物品名？ |
|---|--------|------|----------|-------------|
| 1 | **居家管家 帮助** | **技能速查（HELP）** | `python3 scripts/home_manager.py help`（生成 HELP HTML） | 否 |
| 2 | 查物品 | 物品搜索 | features/search.md | 可选（无则列全部） |
| 3 | 看物品 | 物品详情 | features/search.md → detail | 是（多件时让用户选） |
| 4 | 录物品 | 文字录入 | features/add.md | 否（AI 解析描述） |
| 5 | 拍物品 | 拍照录入 | features/add.md → 图片子流程 | 否（从图片提取） |
| 6 | 改物品 | 通用更新 | features/update.md | 是 |
| 7 | 移物品 | 位置移动 | features/update.md → 位置移动 | 是 |
| 8 | 补物品 | 数量增加 | features/update.md → 数量变更 | 是 |
| 9 | 减物品 | 数量减少 | features/update.md → 数量变更 | 是 |
| 10 | 标物品 | 标签更新 | features/update.md → 标签更新 | 是 |
| 11 | 废物品 | 标记废弃 | features/update.md → 状态变更 | 是 |
| 12 | 借物品 | 标记借出 | features/update.md → 状态变更 | 是 |
| 13 | 修物品 | 标记维修 | features/update.md → 状态变更 | 是 |
| 14 | 盘物品 | 按位置盘点 | features/inventory.md | 是（位置） |
| 15 | 盘全部 | 全屋盘点 | features/inventory.md | 否 |
| 16 | 穿什么 | 穿搭推荐 | features/fashion.md | 否 |
| 17 | 带物品 | 出门标记 | features/travel.md → 出门前 | 是 |
| 18 | 归物品 | 回家归位 | features/travel.md → 回家后 | 否（查所有旅游中） |
| 19 | 统物品 | 总体统计 | features/stats.md → summary | 否 |
| 20 | 查高频 | 高频物品（并入物品总览） | features/stats.md → summary（T5 裁决：并入总览高频 TOP 区块） | 否 |
| 21 | 查低频 | 低频物品（并入闲置检测） | features/stats.md → idle（T5 裁决：语义由查闲置承接） | 否 |
| 22 | 查过期 | 过期检查 | features/stats.md → expiring | 否 |
| 23 | 看标签 | 列出标签 | features/tags.md → 列表 | 否 |
| 24 | 合标签 | 合并标签 | features/tags.md → 合并 | 是（from/to） |
| 25 | 查快递 | 快递跟踪（查/超时/收货确认） | `python3 scripts/快递购物/cli.py express [--timeout-days 7]` → 快递购物/express.html | 否 |
| 26 | 推位置 | 位置推荐 | features/add.md → Step 2.5 | 是（category-id 整数） |
| 27 | 找位置 | 参考锚定 | features/add.md → Step 2.6 | 是（reference） |
| 28 | 查账号 | 查看账号（密码脱敏·类型组织） | `python3 scripts/票据凭证/cli.py account list` / `show --platform "XX" --master-key "XX"` → 票据凭证/accounts.html | 是（平台名，无则列全部） |
| 29 | 存账号 | 新增账号（密码加密存储） | `python3 scripts/票据凭证/cli.py account add --platform "XX" --user "XX" --pass "XX" --master-key "XX" [--type 购物\|银行\|社交\|其他]` | 是 |
| 30 | 改账号 | 更新账号（重新录入语义） | `python3 scripts/票据凭证/cli.py account update --platform "XX" --master-key "XX" [--user] [--pass] [--type]` | 是（平台名） |
| 31 | 查异常 | 数据健康检查 | `python3 scripts/开始使用/cli.py lint` → 开始使用/health_report.html | 否 |
| 32 | 查物品(HTML) | 物品搜索(默认输出 HTML) | features/search.md → Step 4 | 可选（无则列全部） |
| 33 | 看物品(HTML) | 物品详情(默认输出 HTML) | features/search.md → Step 4 | 是（多件时先选） |
| 34 | 统物品(HTML) | 总体统计(默认输出 HTML) | features/search.md → Step 4 | 否 |
| 35 | 借用 | 借用管理（借出/借入/归还/催还） | `python3 scripts/home_manager.py family --action borrow-list` → family_borrow.html | 否（登记时选/填） |
| 36 | 家人档案 | 家人档案（成员/物品归属标记） | `python3 scripts/home_manager.py family --action member-list` → family_members.html | 否 |
| 37 | 管位置 | 位置管理（查看/新建/改名/合并） | features/位置.md → 管位置 | 否（操作+详情） |
| 38 | 固定位 | 设置固定位（常用件锚定） | features/位置.md → 固定位 | 是（物品） |
| 39 | 收纳建议 | 收纳位置建议（AI 推荐） | features/位置.md → 收纳建议 | 否（可多件/批量） |
| 40 | 空间视图 | 空间视图浏览（位置树下钻） | features/位置.md → 空间视图 | 否（位置可选） |
| 37 | 查闲置 | 闲置物品检测 | `python3 scripts/home_manager.py stats --type idle [--days 90|180|365] [--category-id N] --output` → stats/idle.html | 否 |
| 38 | 盘点统计 | 盘点统计与建议 | `python3 scripts/home_manager.py stats --type inventory-stat --output` → stats/inventory_stat.html | 否 |
| 42 | 首次使用 | 首次使用初始化（6 步向导，幂等可重试） | `python3 scripts/开始使用/cli.py check` / `init` / `init-status` → 开始使用/first_use_wizard.html | 是（路径确认，默认即确认） |
| 43 | 备份导出 | 备份与导出（数据资产） | `python3 scripts/开始使用/cli.py backup` / `backup-list` / `export --format json\|csv` → 开始使用/backup_receipt.html | 是（操作/格式） |
| 44 | 导入恢复 | 导入与恢复（迁移，预告式文件） | `python3 scripts/开始使用/cli.py import-preview --file X` / `import --file X [--mode skip\|overwrite]` → 开始使用/import_restore.html | 是（文件预告式） |
| 45 | 批量录入 | 批量录入多件物品（清单/照片） | `python3 scripts/home_manager.py sm1-add-batch --json-file X [--commit]` → 物品/add_form.html | 否 |
| 46 | 补录 | 补录历史物品（指定日期） | `python3 scripts/home_manager.py sm1-add --backfill-date YYYY-MM-DD` → 物品/add_form.html | 否（AI 解析描述） |
| 47 | 紧急定位 | 紧急查找物品位置（一屏直达） | `python3 scripts/home_manager.py sm1-locate --name X` → 物品/locate.html | 是（名称/描述） |
| 48 | 筛选浏览 | 按条件筛选浏览物品（分组/排序） | `python3 scripts/home_manager.py sm1-browse [--group-by] [--location] [--tag]` → 物品/browse.html | 否 |
| 49 | 拍照找物品 | 拍照反向查找物品（图搜） | `python3 scripts/home_manager.py sm1-search --name X`（AI 图搜 → 关键词）→ 物品/search_list.html | 否（照片） |
| 50 | 查重复 | 检查重复物品 | `python3 scripts/home_manager.py sm1-duplicates` → 物品/duplicates.html | 否 |
| 51 | 合并物品 | 合并重复物品（保留主条/数量相加） | `python3 scripts/home_manager.py sm1-merge --target N --sources 1,2` → 物品/receipt.html | 是（target/源） |
| 52 | 撤销操作 | 撤销最近操作（一次性回滚） | `python3 scripts/home_manager.py sm1-undo-list` / `sm1-undo --event-id N` → 物品/undo_select.html | 否 |
| 53 | 物品关联 | 设置/解除物品关联（配件等） | `python3 scripts/home_manager.py sm1-relate --id N --related M [--action unlink]` → 物品/relations.html | 是 |
| 54 | 管标签 | 标签管理（总览/改名/合并/清理） | `python3 scripts/home_manager.py sm1-tag-overview` / `tag-merge` → 物品/tag_manage.html | 否 |
| 55 | 管分类 | 分类管理（树/新建/改名/合并） | `python3 scripts/home_manager.py sm1-category [--action add\|rename\|merge]` → 物品/category_manage.html | 否 |
| 56 | 整理建议 | 标签分类整理建议（AI 检测相近） | `python3 scripts/home_manager.py sm1-similar-tags` → 物品/tag_manage.html | 否 |
| 57 | 查看照片 | 查看物品照片（含类型筛选） | `python3 scripts/home_manager.py sm1-photos --id N` → 物品/photos.html | 是 |
| 58 | 管照片 | 管理物品照片（排序/主图/类型） | `python3 scripts/home_manager.py sm1-photo-update --id N --json-file X` → 物品/photos.html | 是 |
| 59 | 照片墙 | 照片墙浏览（分类/位置/类型） | `python3 scripts/home_manager.py sm1-photo-wall [--group-by] [--type]` → 物品/photo_wall.html | 否 |
| 60 | 盘点记录 | 查看盘点记录（含复查入口） | `python3 scripts/home_manager.py sm1-inventory-records` → 物品/inventory_records.html | 否 |
| 61 | 差异处理 | 处理盘点差异（缺/多/异/待确认） | `python3 scripts/home_manager.py sm1-inventory-diff [--record-id N]` / `sm1-inventory-resolve` → 物品/inventory_diff.html | 否（记录级） |
| 62 | 搬家盘点 | 搬家打包盘点（带走/不带走） | `python3 scripts/home_manager.py sm1-move-checklist` / `sm1-move-commit` → 物品/move_checklist.html | 否 |
| 63 | 历史 | 查看物品历史（时间线/轨迹） | `python3 scripts/home_manager.py sm1-history --id N` → 物品/history.html | 是 |
| 64 | 数量变更 | 变更物品数量（补充/消耗/用完） | `python3 scripts/home_manager.py sm1-qty --id N [--plus\|--minus\|--set]` → 物品/receipt.html | 是 |
| 65 | 状态变更 | 变更物品状态（废弃/借出/维修/恢复，状态机守卫） | `python3 scripts/home_manager.py sm1-status --id N --status X` → 物品/receipt.html | 是 |
| 66 | 盘点 | 盘点核对（按位置/分类/全屋，产生差异集） | `python3 scripts/home_manager.py sm1-inventory-round [--scope location\|category\|all]` → 物品/inventory_round.html | 否（可指定范围） |
| 67 | 购物清单 | 购物清单（组织/例行/采购闭环） | `python3 scripts/快递购物/cli.py list` → 快递购物/list.html | 否（可带条目） |
| 68 | 缺货检测 | 缺货检测（自动进清单） | `python3 scripts/快递购物/cli.py missing [--category-id N]` → 快递购物/missing.html | 否（可选范围） |
| 69 | 囤货盘点 | 囤货盘点（库存/阈值/不足检测） | `python3 scripts/快递购物/cli.py stock` → 快递购物/stock.html | 否 |
| 70 | 联动总览 | 跨技能联动能力索引 + 偏好设置 | `python3 scripts/联动/cli.py sm9-overview` → 联动/link_overview.html（或 home_manager.py sm9-overview，T2 注册后） | 否 |
| 71 | 记到卡路里 | 食品联动（记到今日饮食/查热量） | features/联动.md → 食品联动 | 是（先查物品确认） |
| 72 | 记到记账 | 价格联动（记支出/记收入） | features/联动.md → 价格联动 | 是（先查物品确认） |
| 73 | 购买记录 | 购买记录（查询/统计/票据归档·退货窗口） | `python3 scripts/票据凭证/cli.py purchase list [--item-id N] [--year YYYY] [--month MM]` / `stats [--year YYYY]` → 票据凭证/purchase_records.html | 否（物品/时间可选） |
| 74 | 保修 | 保修与保养（登记/到期/维修记录/保养周期） | `python3 scripts/票据凭证/cli.py warranty list [--status 在保\|即将到期\|已过\|全部]` / `register --item-id N --kind 保修\|保养` / `repair --warranty-id N` / `maintain --warranty-id N` → 票据凭证/warranty.html | 否（物品可选） |
| 75 | 证件 | 证件管理（登记/到期/归档·号码脱敏） | `python3 scripts/票据凭证/cli.py cert list` / `add --type 护照\|身份证\|驾照\|签证\|保险单\|其他 --expires-at D` → 票据凭证/certificates.html | 否 |
| 76 | 账号 | 账号密码（加密存/查/改·敏感复制分离） | `python3 scripts/票据凭证/cli.py account list` → 票据凭证/accounts.html（密码 ******；复制数据默认不含密码） | 否 |

### 匹配规则

1. **精确匹配**：用户输入包含表中唤醒词即命中
2. **最长匹配**：同时命中多个时，取最长的（如"查高频"优先于"查"）
3. **物品名提取**：唤醒词前后的文字作为物品名/参数
4. **缺失物品名**：需要物品名但用户未提供时，追问
5. **变体匹配（v0.1 · 语料储备,行为待激活）**：用户输入若包含 `references/scenarios.yaml` 中某 scenario 的 `variants[].phrase`,视为命中该 scenario 的 `wake_word`,走对应 CLI 命令
   - **当前状态(2026-07-28)**:变体语料已入库(TOP 5 核心词 × 每词 6 变体),但**匹配行为尚未在 AI 路由层生效**——AI 读取本规则后应自觉执行变体匹配,但无代码强制。`tests/test_variants.py` 只锁数据结构(direction/phrase/非空/无禁用字符),不锁匹配行为。
   - **激活路径**:未来若加代码层硬执行(改 home_manager.py 路由层读 variants 字段做匹配),本规则从"语料储备"升级为"硬规则"。
   - **示例**:用户说"帮我找找" → 匹配 `查物品` scenario 的 `variants[direction=口语].phrase="帮我找找"` → 视为命中 `查物品` → 走 `search --name "XX"` 等
   - **变体方向**(总纲 §钩子 3 · 3 方向):
     - `同义` — 正式唤醒词的等价表达(如"搜索物品" → 查物品)
     - `口语` — 自然口语化(如"帮我找找" → 查物品)
     - `模糊` — 意图模糊但可推断(如"那个啥在哪" → 查物品)
   - **歧义处理**:若变体同时匹配多个唤醒词(如"看看"可能匹配 `看物品` 或 `查物品`),AI 必须询问用户确认,不得私自选择(沿用规则 4)


   **FAT 暴露的边界 case 处理(v0.1 · 2026-07-28 fresh agent 跑后补)**:

   - **容错规则(规则 5a)**:变体匹配默认**精确子串包含**(`prompt.includes(phrase)`)。不支持近似/同义词替换——如"那件东西的信息"不能自动匹配变体"那个东西的信息"(一字之差)。若用户输入与变体仅一字之差但语义同,AI 可**主动建议**该变体("您是想看物品详情吗?"),但不算命中,需用户确认。这避免误匹配,代价是 fresh agent 对一字之差无法自洽——这是有意的,防止"差不多就路由"导致误操作。

   - **混合输入处理(规则 5b)**:当 prompt = 变体短语 + 解释性从句时(如"那个啥在哪,就是我上次买的蓝牙耳机"),AI 应:
     1. 先用变体短语("那个啥在哪")判定命中 `查物品`
     2. 再从**解释性从句**("就是我上次买的蓝牙耳机")提取有效参数("蓝牙耳机" 作为物品名)
     3. 若从句无法提取明确参数,走规则 4(缺失物品名 → 追问)

   - **未命中变体但语义近似(规则 5c)**:若 prompt 未匹配任何变体短语,但语义上明显属于某唤醒词的范畴(如"统计一下"未在变体清单但语义近 `统物品` 的"统计物品"),AI **不得**自动路由(防止误匹配),应**追问用户**:"您是想看家里物品总览(统物品)吗?"——这比规则 4 的"缺失物品名追问"更具体,是变体未覆盖时的兜底。**未来扩充变体语料**时,这类近义项应正式登记为新变体。

   - **变体覆盖不足的 fail mode**:若同一核心词的近义项反复出现(如"统计一下""整体看下""总览一下"都未在 `统物品` 变体清单),说明变体语料不足,应扩充 `scenarios.yaml` 的 variants 字段(加新 phrase),而非依赖规则 5c 的追问兜底。这是**变体管理的反馈循环**——FAT 暴露覆盖缺口 → 扩充语料 → 下次 FAT 验证。
> ⚠️ **变体匹配的 fail mode**:若 AI 读了本规则但仍只用精确匹配(忽略 variants),视为 §⛓ HTML-First 协议的 silent failure(用户口语化 prompt 无法命中唤醒词 = 行为 fail mode)。commit 前自检清单的 `html-first-n/a` 不适用本场景——变体匹配是路由层行为,不是 HTML 层。

### 唤醒词 CLI 映射

| 唤醒词 | CLI 命令 |
|--------|---------|
| **居家管家 帮助** | `python3 scripts/home_manager.py help`（生成 HELP HTML） |
| 查物品 | `search --name "XX"` 或 `search --location "XX"` 或 `search --tag "XX"` |
| 看物品 | `detail --id {ID}` |
| 录物品 | `add --name "XX" --category-id N --location "XX"` (category-id 必填,从 categories 表查) |
| 拍物品 | 先看图并保存到 `HOME_PHOTOS_DIR` → `add --name "XX" --category-id N --location "XX" --tags "...≥10" --remark "..." --photo "XX"` 一次写入 |
| 改物品 | `update --id {ID}` + 对应参数 |
| 移物品 | `update --id {ID} --new-location "新位置" --location "原位置"` |
| 补物品 | `update --id {ID} --plus N` |
| 减物品 | `update --id {ID} --minus N` |
| 标物品 | `update --id {ID} --tags "新标签"` |
| 废物品 | `update --id {ID} --location-status "已废弃"` |
| 借物品 | `update --id {ID} --location-status "借用中"` |
| 修物品 | `update --id {ID} --location-status "维修中"` |
| 盘物品 | `inventory --location "位置" [--output PATH]` (--output 走 inventory_check.html) |
| 盘全部 | `list`（无筛选条件） |
| 穿什么 | `list --category-id 138 --status "在家"` (衣物顶级) + `list --category-id 148 --status "在家"` (鞋类二级) |
| 带物品 | `update --id {ID} --location-status "旅游中"` |
| 归物品 | `search --status "旅游中"` → 逐个 `update --id {ID} --location-status "在家"` |
| 统物品 | `stats --type overview --output`（物品总览 HTML，含状态/分类/位置/价值TOP/高频TOP/趋势） |
| 查高频 | `stats --type overview --output`（T5 裁决：并入物品总览高频 TOP 区块） |
| 查低频 | `stats --type idle [--days 90] --output`（T5 裁决：语义由闲置检测承接） |
| 查闲置 | `stats --type idle [--days 90|180|365] [--category-id N] [--output PATH]` (--output 走 stats/idle.html) |
| 查过期 | `stats --type expiring [--days 30] [--expired-only] [--category-id N] [--output PATH]` (--output 走 stats/expiring.html) |
| 盘点统计 | `stats --type inventory-stat [--output PATH]` (--output 走 stats/inventory_stat.html) |
| 看标签 | `tag-list` |
| 合标签 | `tag-merge --from "旧" --to "新"` |
| 查快递 | `python3 scripts/快递购物/cli.py express [--timeout-days 7] [--output PATH]` → 快递购物/express.html（含超时提醒/收货确认闭环） |
| 购物清单 | `python3 scripts/快递购物/cli.py list`（HTML 视图）\| `list-add --name "XX" --quantity N [--routine 每周\|每月]` \| `list-check --ids 1,2` |
| 缺货检测 | `python3 scripts/快递购物/cli.py missing [--category-id N]`（HTML 视图）\| `missing-to-list --ids 1,2` |
| 囤货盘点 | `python3 scripts/快递购物/cli.py stock`（HTML 视图）\| `stock-set-threshold --id N --threshold M` \| `stock-fix --id N --quantity M` |
| 推位置 | `suggest-locations --category-id N [--with-examples]` |
| 找位置 | `find-location --reference "XX"` |
| 查账号 | `python3 scripts/票据凭证/cli.py account list`（清单 HTML·密码脱敏）或 `account show --platform "XX" --master-key "XX"`（敏感回显） |
| 存账号 | `python3 scripts/票据凭证/cli.py account add --platform "XX" --user "XX" --pass "XX" --master-key "XX" [--type 购物\|银行\|社交\|其他]`（加密存储） |
| 改账号 | `python3 scripts/票据凭证/cli.py account update --platform "XX" --master-key "XX" [--user] [--pass] [--type]`（重新录入语义） |
| 查异常 | `python3 scripts/开始使用/cli.py lint` (数据检查 8 项, 走 开始使用/health_report.html) |
| 首次使用 | `python3 scripts/开始使用/cli.py check` → `init`(建库+种子 60 节点)→ `init-status`(幂等) |
| 备份导出 | `python3 scripts/开始使用/cli.py backup` / `backup-list` / `export --format json\|csv` |
| 导入恢复 | `python3 scripts/开始使用/cli.py import-preview --file X` → `import --file X [--mode skip\|overwrite]` |
| 查物品 | `search --name "XX"` 默认输出 HTML |
| 看物品 | `detail --id {ID}` 默认输出 HTML |
| 统物品 | `list` 默认输出 HTML |
| 管位置 | `sm2-manage --action view`（查看）· `--action create --path "XX"`（新建）· `--action rename --old "XX" --new "YY"`（改名）· `--action merge --src "XX" --tgt "YY"`（合并）· `--action delete --path "XX"`（删除）· `--action similar`（相似检测） |
| 固定位 | `sm2-fixed --action list`（清单）· `--action set --item-id N --location "XX"`（设置）· `--action clear --item-id N`（解除） |
| 收纳建议 | `sm2-suggest --item-id N`（单件）· `--item-ids "1,2"`（指定多件）· `--batch [--limit N]`（批量:没固定位的常用件） |
| 空间视图 | `sm2-view [--path "XX"]`（缺省=顶层） |
| 联动总览 | `python3 scripts/联动/cli.py sm9-overview`（能力索引+偏好 HTML；`sm9-prefs --key food\|price --value ask\|remember\|off` 设偏好） |
| 记到卡路里 | `python3 scripts/联动/cli.py sm9-food --item-id N [--action log\|query]`（log=记到今日饮食, query=查热量） |
| 记到记账 | `python3 scripts/联动/cli.py sm9-price --item-id N [--direction expense\|income]`（expense=支出, income=收入/退货退款） |
| 借用 | `family --action borrow-list [--output PATH]`(清单 HTML·双向区隔/超期/催还) · `--action borrow-add --direction 借出\|借入 --item-id N 或 --item-name "XX" --object "XX" [--borrowed-at D] [--due-date D]`(登记·借出自动改状态借用中) · `--action borrow-return --borrow-id N`(归还·状态回在家) · `--action borrow-remind --borrow-id N`(催还文案纯文本) |
| 家人档案 | `family --action member-list [--output PATH]`(成员 HTML·归属统计) · `--action member-add --name "XX" [--relation "XX"] [--note "XX"]`(添加) · `--action member-remove --name "XX"`(移除·归属回使用者) · `--action member-assign --name "XX" --item-ids "1,2,3"`(批量标记归属) |
| 购买记录 | `python3 scripts/票据凭证/cli.py purchase list [--item-id N] [--year YYYY] [--month MM] [--output PATH]`（清单 HTML·退货窗口计算）· `purchase add --item-id N --date D [--price X] [--channel] [--merchant-contact] [--receipt-photo] [--return-window N]`（登记·票据照片预告式）· `purchase stats [--year YYYY]`（消费统计） |
| 保修 | `python3 scripts/票据凭证/cli.py warranty list [--status 在保\|即将到期\|已过\|到期未做\|全部] [--output PATH]`（清单 HTML·状态徽章·维修记录）· `warranty register --item-id N --kind 保修\|保养 --start-date D --duration-days N`（登记）· `warranty repair --warranty-id N --date D [--cost X]`（维修记录）· `warranty maintain --warranty-id N --date D`（保养执行·刷新下次日） |
| 证件 | `python3 scripts/票据凭证/cli.py cert list [--output PATH]`（清单 HTML·号码 ****后4位·按到期排序）· `cert add --type 护照\|身份证\|驾照\|签证\|保险单\|其他 --expires-at D [--holder] [--number] [--photo]`（登记·脱敏存储） |
| 账号 | `python3 scripts/票据凭证/cli.py account list [--output PATH]`（清单 HTML·密码 ******·类型分组）· `account init-master --master-key M`（首设主密钥）· `account add`（加密存储）· `account show`（敏感回显）· `account update`（修改）· `account set-master`（换密钥） |

---

## 🧩 变体管理（总纲 §钩子 3 · 变体）

> 引用 [SKILL 开发总纲 §钩子 3](../SKILL开发总纲V1.0/03-触发词设计v2.md)：每个核心唤醒词配 2-3 个自然语言等价表达,覆盖 3 方向(同义 / 口语 / 模糊)。SKILL.md 只标方向,不写具体话(避免硬编码语料);具体话术在 `references/scenarios.yaml` 的 `variants` 字段。

### TOP 5 核心唤醒词变体方向

按 audit 使用频率(grilling Q7=audit),TOP 5 核心词均已配齐 3 方向变体:

| 唤醒词 | 变体方向 | 变体示例(完整见 scenarios.yaml) |
|--------|---------|------------------------------|
| 查物品 | 同义 + 口语 + 模糊 | 搜索物品 / 帮我找找 / 那个啥在哪 |
| 看物品 | 同义 + 口语 + 模糊 | 查看物品 / 给我看看这个 / 那个东西的信息 |
| 录物品 | 同义 + 口语 + 模糊 | 登记物品 / 帮我记一下 / 这个收进来 |
| 盘物品 | 同义 + 口语 + 模糊 | 清点物品 / 数数这里 / 看看齐不齐 |
| 统物品 | 同义 + 口语 + 模糊 | 统计物品 / 家里都有啥 / 一共多少件 |

> **变体数量说明**:总纲 §CONTEXT.md `变体` 定义为"配 2-3 个自然语言等价表达,覆盖 3 方向"。本 Skill 在 scenarios.yaml 中每 TOP 5 唤醒词存 6 变体(每方向 2 个)作为语料储备,SKILL.md 上表只展示每方向 1 个代表。`tests/test_variants.py` 锁下限(≥ 2 direction)不锁上限,允许语料扩充。

### 单一事实源

变体清单的唯一事实源是 `references/scenarios.yaml` 的 `variants` 字段(每个 variant = `{direction: str, phrase: str}`)。`tests/test_variants.py` 用 5 个测试锁住结构契约(direction ∈ {同义,口语,模糊} / 每 TOP 5 ≥ 2 direction / phrase 非空 / 无禁用字符)。

### ⚠️ Risk B:新增 TOP 核心词需同步标注变体方向

**新增 TOP 核心词时,必须同步在 `scenarios.yaml` 加 `variants` 字段,否则视为 incomplete scenario**——因为缺变体的核心词无法匹配口语化 prompt,违反钩子 3。`tests/test_variants.py` 的 TOP5 列表当前是硬编码,新增 TOP 核心词时需同步更新该列表。

---

## 安装与配置

**依赖**：Python 3.x

**环境变量**（可选）：
- `SKILLS_DB_PATH`：数据库目录
- `HOME_PHOTOS_DIR`：照片目录

**网页版**：[SkillBoard](https://featherhunter.github.io/StudyNotes/skillboard/) - 通过浏览器使用本系统，支持电脑和手机。使用时选择 `home.db` 文件即可。

**一键安装**：复制以下 prompt 给 AI：
```
帮我安装"居家管家"技能：
1. 检查 Python 环境
2. 引导我配置环境变量
3. 显示当前环境变量配置
4. 告诉我如何更改数据目录
```

---

## 📌 输出位置

本 Skill 的 HTML 输出遵循 [SKILL 开发总纲 §原则 12](../SKILL开发总纲V1.0/04-可视化与注入v2.md)（HTML 输出路径约定），分类标 12.A（数据/过程）和 12.B（HELP）。

### 路径根与子目录

路径根按 env 链解析（总纲 12.X 优先级）：

```
$SKILLS_DATA_DIR  >  $SKILLS_DB_PATH  >  Skill 自带 fallback (Windows: D:\.db\ / WSL: /mnt/d/.db/)
```

所有 HTML 输出落在 `<根>/home_manager_html/` 子目录下（Skill 标识 = `home_manager`，与 Python 包名一致）。

### 12.A 数据/过程 HTML

**命名形态**：`<根>/home_manager_html/<command_cn>_<YYYYMMDD>_<HHMMSS>.html`

**command_cn** 中文前缀来自 render 层的 `template → command_cn` 静态映射表（继承 SKILL §触发词速览表字面）：

| template | command_cn |
|----------|-----------|
| `search_results.html` | 查物品 |
| `delivery_check.html` | 查快递 |
| `add_preview.html` | 录物品 |
| `item_detail.html` | 看物品 |
| `list_overview.html` | 统物品（v1，保留给盘全部） |
| `inventory_check.html` | 盘物品 |
| `expiring_alert.html` | 查过期（v1，已迁移至 stats/expiring.html） |
| `outfit_picker.html` | 穿什么 |
| `travel_trip.html` | 出行清单（涵盖带物品 pack + 归物品 return） |
| `位置/space_view.html` | 空间视图 |
| `位置/location_manage.html` | 管位置 |
| `位置/fixed_spot.html` | 固定位 |
| `位置/suggest_storage.html` | 收纳建议 |
| `stats/overview.html` | 统物品（v2 物品总览，T5） |
| `stats/idle.html` | 查闲置（T5） |
| `stats/expiring.html` | 查过期（v2，T5） |
| `stats/inventory_stat.html` | 盘点统计（T5） |
| `票据凭证/purchase_records.html` | 购买记录（T7 · 域内渲染器命名） |
| `票据凭证/warranty.html` | 保修（T7 · 域内渲染器命名） |
| `票据凭证/certificates.html` | 证件（T7 · 域内渲染器命名） |
| `票据凭证/accounts.html` | 账号（T7 · 域内渲染器命名） |

例子：`home_manager_html/查物品_20260728_171500.html`

### 12.B HELP HTML

**命名形态**：`<根>/home_manager_html/居家管家_HELP_<YYYYMMDD>_<HHMMSS>.html`

以 `_HELP_` 为保留字（中段，可被 grep 一抓出来）。`<skill 中文名>` 前缀 = `居家管家`（SKILL.md frontmatter 声明）。

例子：`home_manager_html/居家管家_HELP_20260728_171500.html`

### 显式 override

`--output <path>` 仍可绕过自动命名，直接写到指定路径（不强制走 `home_manager_html/` 子目录）。

### ⚠️ 与总纲 12.X 的偏离

本 Skill 在以下两项与总纲 12.X 显式偏离,**详见 [ADR-0001](./docs/adr/0001-local-time-over-utc-for-html-filenames.md)**（单一真相,Q4=A 决策）：

- **本地时间**(非 UTC):用户看文件名时间戳期望与钟表一致
- **直接覆盖**(无 `_N` 后缀):本场景无保留历史输出需求,运行产物已 `.gitignore`

本节不重复 ADR 细节,如需修改偏离请改 ADR-0001 并保持 SKILL.md 引用指向。

---

## 🧪 FAT 协议（总纲 §钩子 6 · Fresh Agent 黑盒测试）

> 引用 [SKILL 开发总纲 §05 工程仪式 · FAT 协议](../SKILL开发总纲V1.0/05-工程仪式.md) + [§钩子 6](../SKILL开发总纲V1.0/02-5层骨架.md)：commit 前的商用级关卡。由零上下文 agent 执行唤醒词(3-5 个核心 × 每个 ≥ 3 个人类 prompt),对比预期工作流。fail → 改 SKILL.md 不改代码,循环 ≤ 3 次。

### 分级 Tested-By 规则

commit message 必含 `Tested-By:` 字段,分级如下:

| 改动类型 | Tested-By 取值 | 门槛 |
|---------|---------------|------|
| **改代码 / 数据 / CLI** | `pytest-pass-YYYY-MM-DD` | `python -m pytest` 全 PASS 即可 commit |
| **改 SKILL.md**(触发词 / 路由表 / 说明 / frontmatter / 行为契约) | `fresh-agent-v1` | 必须 fresh agent 实际跑过 FAT 9 步 |
| **豁免**(typo / 格式调整 / 注释) | `exempt` + 豁免依据 | 1 行说明为何豁免 |

**分级理由(Q2=yes)**:接受分级而非 strict-only,因 SKILL.md 改动多属文档契约,pytest 测不到;但代码改动用 pytest 足够。分级子规则防止 SKILL.md 退化(改 SKILL.md 必 fresh agent,不能拿 pytest 充数)。

### FAT 9 步协议(引用总纲 §05)

完整 9 步协议见 [总纲 §05 工程仪式 · FAT 9 步协议](../SKILL开发总纲V1.0/05-工程仪式.md)。摘要:

1. 选 3-5 个核心唤醒词(高频 + 复杂 + 易错)
2. 准备 fresh context(新会话,不保留开发记忆)
3. 最小化加载(只给 SKILL.md + 必要 scripts)
4. 每核心词 ≥ 3 个人类 prompt(含口语化/略错,非 AI 风格)
5. 捕获执行证据(命令/数据/输出)
6. 对比预期工作流 vs 实际
7. 判定 pass/fail(工作流一致 + 输出一致 + 无副作用 = PASS)
8. fail → 改 SKILL.md 不改代码,再循环(≤ 3 次)
9. 人工抽查 ≥ 1 个测试结果(防 AI 自评漏)

**循环上限**:SKILL.md 改 3 次仍未通过 → 暂停,人工介入(可能 SKILL 设计问题 / 测试选择不当 / 代码 bug)。

### ⚠️ Risk C:Tested-By 流于形式

**Tested-By 字段缺失 / 错误标签 / 与 commit 内容不符 = 总纲 [`02-5层骨架.md §8 反模式 #4 静默失败`](../SKILL开发总纲V1.0/02-5层骨架.md)`(except: pass` 风格的协议级沉默),需立即补全或 revert。例:
- 改了 SKILL.md 触发词却标 `pytest-pass-2026-07-28`(应 `fresh-agent-v1`)→ silent failure
- 改了代码却标 `fresh-agent-v1`(应 `pytest-pass`)→ 标签错配
- 完全不标 Tested-By → 协议不完整,等同豁免依据缺失

引用总纲 §8 反模式 #4 静默失败让 AI 有 external 压力,不流于形式。

---

## HTML 渲染器（Phase 7 重构）

所有 HTML 模板的注入渲染由 `scripts/render/` 包提供，与 home_manager 数据/操作层解耦：

| 模板 | 触发命令 | 交互 |
|---|---|---|
| `add_preview.html` | `add --preview` | 静态预览 + 复制 CLI |
| `search_results.html` | `search` | 只读卡片 |
| `delivery_check.html` | `search --status "快递中"` | 已收到/废弃/维修 + 回执 |
| `item_detail.html` | `detail` | 只读详情 |
| `list_overview.html` | `list` | 只读统计（含状态/分类分布） |
| `inventory_check.html` | `inventory --output` | 状态/数量变更 + 回执 |
| `expiring_alert.html` | `stats --type expiring --output` | 已处理/废弃 + 回执 |
| `stats/overview.html` | `stats --type overview --output` | 物品总览（指标/分布图表/价值TOP/高频TOP/趋势下钻）+ 复制数据/日志 |
| `stats/idle.html` | `stats --type idle --output` | 闲置勾选处理（废弃/送人/先不处理）+ 复制数据/日志 |
| `stats/expiring.html` | `stats --type expiring --output` | 过期勾选处理（用完/废弃/忽略）+ 复制数据/日志 |
| `stats/inventory_stat.html` | `stats --type inventory-stat --output` | 盘点统计（趋势/差异/建议复查）+ 复制数据/日志 |

**架构**：渲染器在 `scripts/render/__init__.py`（独立包）；home_manager 包不再反向依赖。详见 `scripts/render/__init__.py` 文档字符串。

**硬规则**（与《预置HTML并注入数据指导手册》v2 对齐）：
- 模板必须包含恰好 1 个 `<!--INJECT-DATA-->` 占位符
- 注入前校验 `payload.status === 'ok'`，非 ok 拒收
- 模板 JS 守门 `validate(payload)`，渲染前再校验一次

---

## 功能概述

- **物品录入**：自然语言描述物品，AI 解析后写入数据库
- **物品查找**：按名称/位置/标签/分类/状态搜索
- **物品更新**：位置变动、状态变更、数量调整、标签修改
- **物品盘点**：按需盘点指定位置的所有物品
- **穿搭推荐**：根据天气+标签推荐今日穿搭
- **旅游归位**：出门带物+回家归位的完整流程
- **频率统计**：区分高频/低频物品，识别长期未用物品
- **标签管理**：合并相似标签
- **照片管理**：支持配置照片存储路径（环境变量 `HOME_PHOTOS_DIR`，默认为技能目录/photos）
- **购买记录**：购买日期/价格/渠道/商家客服/退货窗口计算/票据照片归档 + 消费统计（按年/分类聚合）
- **保修与保养**：保修期登记与状态计算（在保/即将到期/已过）+ 维修记录 + 保养周期与执行状态
- **证件管理**：证件登记（护照/身份证/驾照/签证/保险单）按到期排序，号码脱敏显示，照片归档
- **账号密码**：主密钥 Fernet 加密存储，类型组织（购物/银行/社交/其他），密码全脱敏，复制数据默认不含密码
- **🖼 单图架构**：一件物品 = 一张照片（`item.photo` 是单字段）。
  - **多图录入**：用户发多张图时，**第 1 张 = DB 主图（必须存 photos 目录）**，**后续图 = 只读不复制**（信息整合到 `tags` + `remark`，不再重复存档到文件系统）
  - **套装共享**：多件商品共用 1 张图时，每件复制一份并分别命名，各自 DB 存 1 个主图
  - **命名规范**：`YYYYMMDD_{ID}_{中文描述}.jpg`，无 `'` / `:` / `/` 等 Windows 非法字符；`add --photo` 会在内部拿到 ID 后复制为该规范名并写入 `item.photo`

## 快速导航

| 唤醒词 | 功能 | 参考文档 |
|--------|------|----------|
| 查物品 | 物品搜索 | features/search.md |
| 看物品 | 物品详情 | features/search.md |
| 录物品 | 物品录入 | features/add.md |
| 拍物品 | 拍照录入 | features/add.md |
| 改物品 | 通用更新 | features/update.md |
| 移物品 | 位置移动 | features/update.md |
| 补物品 | 数量增加 | features/update.md |
| 减物品 | 数量减少 | features/update.md |
| 标物品 | 标签更新 | features/update.md |
| 废物品 | 标记废弃 | features/update.md |
| 借物品 | 标记借出 | features/update.md |
| 修物品 | 标记维修 | features/update.md |
| 盘物品 | 按位置盘点 | features/inventory.md |
| 盘全部 | 全屋盘点 | features/inventory.md |
| 穿什么 | 穿搭推荐 | features/fashion.md |
| 带物品 | 出门标记 | features/travel.md |
| 归物品 | 回家归位 | features/travel.md |
| 统物品 | 总体统计 | features/stats.md |
| 查高频 | 高频物品 | features/stats.md |
| 查低频 | 低频物品 | features/stats.md |
| 查过期 | 过期检查 | features/stats.md |
| 看标签 | 列出标签 | features/tags.md |
| 合标签 | 合并标签 | features/tags.md |
| 查快递 | 快递跟踪 | scripts/快递购物/cli.py |
| 购物清单 | 购物清单管理 | scripts/快递购物/cli.py |
| 缺货检测 | 缺货自动进清单 | scripts/快递购物/cli.py |
| 囤货盘点 | 库存阈值管理 | scripts/快递购物/cli.py |
| 推位置 | 位置推荐 | features/add.md |
| 找位置 | 参考锚定 | features/add.md |
| 查账号 | 查看账号（密码脱敏） | scripts/票据凭证/cli.py |
| 存账号 | 新增账号（加密存储） | scripts/票据凭证/cli.py |
| 改账号 | 更新账号（重新录入） | scripts/票据凭证/cli.py |
| 购买记录 | 购买记录查询/统计/票据归档 | scripts/票据凭证/cli.py |
| 保修 | 保修与保养（到期/维修/保养） | scripts/票据凭证/cli.py |
| 证件 | 证件管理（到期/归档·号码脱敏） | scripts/票据凭证/cli.py |
| 账号 | 账号密码（加密存/查/改·脱敏） | scripts/票据凭证/cli.py |
| 查异常 | 数据健康检查 | SKILL.md（Lint 检查） |
| 查物品 | 物品搜索→HTML | features/search.md |
| 看物品 | 物品详情→HTML | features/search.md |
| 统物品 | 总体统计→HTML | features/search.md |
| 管位置 | 位置管理→HTML | features/位置.md |
| 固定位 | 固定位清单→HTML | features/位置.md |
| 收纳建议 | 收纳建议→HTML | features/位置.md |
| 空间视图 | 空间视图→HTML | features/位置.md |

---

## ⚠️ 核心使用原则

1. **任何写操作前必须交互确认**：AI 先展示将要执行的操作，用户说"对"才执行
2. **多物品冲突时让用户选**：搜到多个同名物品，列出来让用户选，不默认选任何一个
3. **物品只增不删，可修改**：物品不会物理删除。item_locations 中 quantity=0 时自动删除该位置记录；位置状态为"已用完"或"已废弃"时需用户明确表态
4. **AI 不得自行推断**：当用户意图存在多种可能时，AI 必须询问确认，不得私自选择
5. **库存补充必须问**：搜索到名称相同的"已用完"或"已废弃"物品时，AI 必须询问用户是"补充到现有记录"还是"新建记录"，用户确认前不得写入数据库

---

## ⛓ HTML-First 行为契约（总纲 §原则 11 · 强约定）

> 引用 [SKILL 开发总纲 §原则 11](../SKILL开发总纲V1.0/04-可视化与注入v2.md)：唤醒词命中 SKILL 后,若 SKILL 声明有 HTML 输出路径,**默认行为 = invoke HTML 工作流**。文字答是 fail mode,不是 fallback。与 §原则 10 互补(10 管出向 · 复制 prompt,11 管入向 · 默认 HTML)。

### 必须 invoke HTML 的唤醒词（16 个）

命中下列唤醒词后,**必须** invoke HTML 工作流,文字答视为 fail mode:

| 类别 | 唤醒词 |
|------|--------|
| 查看类 | `查物品` / `看物品` |
| 盘点类 | `盘物品` / `盘全部` |
| 统计类 | `统物品` / `查高频` / `查低频` / `查过期` |
| 出行类 | `查快递` / `穿什么` / `带物品` / `归物品` |
| 空间类 | `管位置` / `固定位` / `收纳建议` / `空间视图` |
| 票据凭证类 | `购买记录` / `保修` / `证件` / `账号`（SM6 域 CLI 默认输出 HTML） |

这些唤醒词的 HTML 输出路径见 [§📌 输出位置](#-输出位置) 的 `template → command_cn` 映射表。

### 优雅降级

若 HTML 生成失败(磁盘满 / 模板错 / 渲染异常),fallback 到**结构化文本 + 错误回执**,不要直接报错中断。结构化文本应包含:操作名 / 关键数据 / 失败原因 / 建议下一步。用户看到错误回执后可手动重试或反馈。

> **fail mode 判定**:`查物品` 命中后只回一行文字"找到 3 件物品:..."而不生成 HTML = fail mode,需立即补 invoke HTML。

### fail mode 自检清单(commit 前必跑)

> 本清单是软规则 §HTML-First 的硬执行替代——没有代码强制,但 AI 在每次涉及 12 唤醒词的 commit 前**必须自检**,未过自检不得 commit。这是对抗式审查后补的(P1-3),解决"强约定无硬执行"的空壳问题。

**自检步骤**(AI 在 commit message 的 Tested-By 字段记录结果):

1. **本轮是否触发了 12 唤醒词中的任意一个?**
   - 否 → 本清单不适用,跳过
   - 是 → 继续

2. **每个被触发的唤醒词,本轮是否 invoke 了 HTML 工作流?**
   - 是 → PASS,记录 `html-first-pass`
   - 否 → 进入 fail mode 处理

3. **fail mode 处理(命中但未 invoke HTML)**:
   - 检查是否有 HTML 生成失败(磁盘满 / 模板错 / 渲染异常)
   - 失败 → 走优雅降级(结构化文本 + 错误回执),记录 `html-first-fallback + 原因`
   - 未失败但没 invoke → **silent failure**,不得 commit,先补 invoke HTML

**Tested-By 字段标法**(与 §🧪 FAT 协议 分级规则互补):
- `html-first-pass` — 12 唤醒词命中后都 invoke 了 HTML
- `html-first-fallback + 原因` — HTML 失败走了优雅降级
- `html-first-n/a` — 本轮未触发 12 唤醒词(纯文档 / 纯测试改动)
- 不标 → 视为 silent failure,等同 §8 反模式 #4

**示例**:
- 改 SKILL.md §HTML-First 章节(commit 4):`Tested-By: html-first-n/a (纯文档,未触发 12 唤醒词)`
- 改 search 命令的 HTML 模板:`Tested-By: html-first-pass (查物品 命中后 invoke search_results.html)`
- 查物品 命中但只回文字:`Tested-By: html-first-fail (silent failure,不得 commit)`

---

## 联动说明（SM9 联动功能域 · 双入口单实现）

联动逻辑已集中到技能路由器（`图片路由/SKILL.md`），本技能不再单独维护联动规则。完成主操作后请检查路由器的联动规则表。

**SM9 场景**（3 个，流程详见 `features/联动.md`）：

| 唤醒词 | 场景 | CLI | 说明 |
|--------|------|-----|------|
| 联动总览 | 联动功能总览 | `sm9-overview` | 能力索引（食品→卡路里/价格→饼干记账/健身→出行清单）+ 偏好频控 |
| 记到卡路里 | 食品联动 | `sm9-food --item-id N [--action log\|query]` | 物品确认 → 动作选择 → 复制 prompt 到卡路里（单工闭环） |
| 记到记账 | 价格联动 | `sm9-price --item-id N [--direction expense\|income]` | 物品确认（含价格）→ 方向选择 → 复制 prompt 到饼干记账 |

**双入口顺路建议（G6 第 3 层 · 规格硬要求）**：

- **独立触发**：用户直接说「记到卡路里 / 记到记账 / 联动总览」→ 按上表路由
- **录入顺路建议**：完成「录物品/拍物品」（1-1/1-2）回执后，AI 检查联动偏好（`sm9-prefs` 设置，存 `$SKILLS_DB_PATH/link_prefs.json`）：
  - `ask`（每次询问）→ 始终在回执顺路提醒区给出联动建议
  - `remember`（记住上次选择）→ 按上次用户是否接受联动决定
  - `off`（关闭）→ 不打扰，不回执建议
  - 食品/饮品物品 → 建议「记到卡路里」（查热量或记一餐）；有价格物品 → 建议「记到记账」（记支出/收入）
  - 建议内容 = 调用 `sm9-food / sm9-price` 生成的 prompt，附在回执 HTML 顺路提醒区

**执行边界**：联动执行 = 复制 prompt 到对应技能（卡路里/饼干记账），居家管家不直接调用对方 CLI（跨技能物理隔离，单工闭环）。

---

## Lint 检查（数据健康检查 · SM8 开始使用域）

**唤醒词**：`查异常`

### 执行方式(SM8 实施后 · 2026-08-05)

`python3 scripts/开始使用/cli.py lint` → 结构化 JSON → 渲染 `templates/开始使用/health_report.html`(查看+选择)。
输出 = 环境信息头部 + 8 检查项(问题/涉及数/严重度)+ 勾选复制修复引导。

### 检查项(8 项 · v2.0)

1. **无标签物品** — item_tags 无记录 → 修复引导:改物品补标签
2. **无位置物品** — 无 item_locations 行(盘点会漏)→ 修复引导:改物品补位置
3. **状态长期未更新** — 快递中>7 天 / 旅游中>30 天 / 维修中>30 天 / 借用中>30 天
4. **单级位置** — 位置路径不含 `/`(如只有"客厅")→ 修复引导:移物品规范化
5. **无照片物品** — photo 为空 → 修复引导:拍物品补拍(预告式)
6. **未录价格** — purchase_price 为空 → 修复引导:改物品补价格(联动 SM4 价格覆盖率)
7. **无购买/过期日期** — item_locations 无日期 → 修复引导:改物品补日期
8. **相似位置未合并** — 去掉分隔符后同名(如 `卧室/东南角` vs `卧室东南角`)→ 修复引导:移物品合并

### 处理原则

- 发现问题后列出清单，让用户勾选确认(HTML 勾选 → 复制修复引导)
- **只建议不自动改**：AI 不得直接修改数据,只能复制对应场景 prompt 引导用户
- 用户说"检查一下"时执行，不主动触发

---

## 开始使用域流程(SM8 · 首次使用/备份导出/导入恢复)

**唤醒词**：`首次使用` / `备份导出` / `导入恢复`

### 首次使用(初始化工作流 · 6 步)

1. 环境检测:`python3 scripts/开始使用/cli.py check`(OS/Python/目录可写/DB 状态)
2. 路径确认:展示 check 输出的 `db_path`(AI 预填建议路径),**必须征求用户确认**,不静默
3. 建库+建分类:`python3 scripts/开始使用/cli.py init`(幂等:已有库/已有分类 → 跳过)
4. 状态确认:`python3 scripts/开始使用/cli.py init-status`(未初始化/库已建/已初始化)
5. 渲染向导 HTML:`render_开始使用.emit_sm8("first_use_wizard.html", ...)`(6 步步骤条 + 环境信息 + 建库结果 + 下一步按钮)
6. 完成:提示可录第一批(建议拍物品);失败 → `emit_error` 错误回执 HTML(步骤/原因/建议)+ 一键重试

### 备份导出(数据资产)

1. 查询历史:`cli.py backup-list [--keep-n N]`(备份文件/大小/时间/距上次备份天数)
2. 确认备份:用户确认 → `cli.py backup`(db+照片全量打包 zip,自动保留 N 份清理最旧)
3. 导出(可选):`cli.py export --format json|csv [--output 路径]`
4. 渲染:`emit_sm8("backup_receipt.html", ...)`(备份结果 + 历史列表 + 距上次备份天数 + 导出按钮)
5. 删除旧备份:确认式 `cli.py backup-delete --file 文件名`;失败 → 错误回执 + 重试

### 导入恢复(迁移 · 预告式文件)

1. 预告式:按钮复制「【导入文件即将发送:】」→ AI 进入等待态 → 用户发文件
2. 校验+冲突预览:`cli.py import-preview --file X`(格式/版本兼容 + 同名冲突计数)
3. 确认导入:`cli.py import --file X [--mode skip|overwrite]`(导入前自动备份,失败回滚数据不变)
4. 渲染:`emit_sm8("import_restore.html", ...)`(步骤条 + 校验结果 + 冲突预览 + 确认/撤销按钮)
5. 撤销(确认式):`python3 scripts/开始使用/cli.py import-undo --file <导入前备份>`(覆盖前自动再备份当前库为安全网;非法备份 → 错误回执)

---

## 快递购物域流程(SM5 · 购物清单/缺货检测/快递跟踪/囤货盘点)

**唤醒词**：`购物清单` / `缺货检测` / `查快递` / `囤货盘点`

### 购物清单(组织/例行/采购闭环)

1. 视图:`python3 scripts/快递购物/cli.py list` → 快递购物/list.html（条目 + 来源标注:手动/缺货检测/例行+周期 + 清单内查重提示 + 例行到期顺路提醒）
2. 添加:`cli.py list-add --name "XX" --quantity N [--source 手动|缺货检测|例行] [--routine 每周|每月]`（同名「待买」重复添加 → 拒绝并提示合并）
3. 销项(勾选已买):`cli.py list-check --ids 1,2`（例行条目记 last_done_at,超周期自动重新激活为待买 + 顺路提醒「本周采购清单已生成」）
4. 采购闭环(按钮复制 prompt → AI 引导):新物品 → 录物品(1-1);已有物品 → 补数量(3-3)
5. 空态:引导缺货检测自动填清单

### 缺货检测(自动进清单)

1. 检测:`cli.py missing [--category-id N]` → 快递购物/missing.html（当前数量+阈值+建议量「当前 0/阈值 1/建议买 2」）
2. 阈值来源:囤货设置(`stock-set-threshold`);未设置 → 默认 1 估算并标注「默认」
3. 一键进清单(勾选):`cli.py missing-to-list --ids 1,2`（按建议量入清单;已在待买 → 跳过并提示合并）
4. 空态:库存充足

### 快递跟踪(查/超时/收货确认)

1. 视图:`cli.py express [--timeout-days 7]` → 快递购物/express.html（照片+名称+数量+「快递中」+已等 N 天+超时红色徽章+顺路提醒）
2. 确认收货(勾选):`cli.py express-receive --id N [--to 在家|备用]`（状态变更 + 写 item_events）
3. 超时处理:按钮复制 prompt → AI 联系卖家/标记遗失

### 囤货盘点(库存/阈值/不足检测)

1. 视图:`cli.py stock` → 快递购物/stock.html（名称+当前数量+阈值+库存状态:充足/低/空）
2. 设置阈值:`cli.py stock-set-threshold --id N --threshold M`（缺货检测的阈值数据源）
3. 修正数量(勾选 → 3-3):`cli.py stock-fix --id N --quantity M`（写数量变更事件）
4. 空态:引导为常用物品设阈值（高频无阈值物品提示）

---

## 错误处理

| 场景 | AI 处理方式 |
|------|------------|
| 搜不到物品 | 告知用户，询问是否换个关键词或新建物品 |
| 搜到多个同名物品 | 列出让用户选择，不默认选任何一个 |
| 录入时发现同名"已用完/已废弃"物品 | 列出选项让用户选择，不能自动决定 |
| 补充库存时原物品状态为"已用完/已废弃" | 询问用户新状态是什么（在家/备用/快递中/其他） |
| 用户输入模糊无法解析 | 追问确认 |
| 数据库写入失败 | 告知用户失败原因，询问重试 |
| 首次使用（无数据库） | 走 SM8 初始化工作流:`check` → 路径确认 → `init`(建库+种子 60 节点),失败=错误回执 HTML+重试 |
| 初始化已存在库 | 幂等跳过建库建分类,提示「已初始化,直接使用」 |
| 备份失败 | 错误回执 HTML(原因/建议)+ 一键重试;备份前不动原数据 |
| 导入文件不兼容 | 校验失败 → 错误回执;导入失败自动回滚,数据不变 |
| 盘点中途退出 | 已确认的已写入，未确认的保持原样 |
| 穿搭推荐无匹配 | 告知无匹配衣物，建议扩展标签或录入 |
| 天气数据获取失败 | 告知无法获取天气，改用纯标签筛选 |
| 标签合并不存在 | 脚本输出"标签不存在"，AI 告知用户 |
| 购物清单添加重复条目 | 脚本拒绝并提示「已在购物清单中,可改数量」,AI 转告用户,不自动合并 |
| 收货确认时无快递中记录 | 脚本报错「没有快递中位置记录」,AI 告知无需确认收货 |
| 囤货修正无库存位置 | 脚本报错,AI 提示先录入或确认收货后再修正 |

# SKILL 开发总纲 V1.0

定义 Skill 这一产物的设计、改造、演化规则的元规范。本表只收"Skill 开发"领域专属术语,不收通用编程概念,不收会话级约定。

## Language

### 核心产物

**Skill**:
一个领域 + 工具 + 文档 + 规则的完整封装,定义一整个领域(如某家庭物品管理)。包含实体、操作、规则、接口、文档五者。
_Avoid_: 插件、模块、扩展、脚本(这些都不要求 5 层骨架)

**SKILL.md**:
Skill 的契约主入口,YAML frontmatter + 领域边界声明 + 触发词表 + 钩子清单。AI 与任意 agent 都按它的字面执行。
_Avoid_: README、配置文件、入口文件

**HTML 镜像**:
SKILL.md 的可视化副本,与 SKILL.md 同 commit 同步(钩子 1 硬规则)。命名 `<skill>.html`,与 SKILL.md 同目录。
_Avoid_: 落地页、官网、演示页

### 唤醒词与场景

**唤醒词 (wake word)**:
用户触发 Skill 的自然语言入口,4 元组结构(动作 + 对象 + 维度 + 类型,后两个可选)。8 ≤ N,无上限。
_Avoid_: 命令、指令、关键词(这些不含 4 元组结构)

**HELP 唤醒词**:
每个 Skill 必须登记的 ≥ 1 个能力速查入口,专属化,不充当普通业务唤醒词。HELP 自身不展示在它生成的 HTML 中(防死循环)。
_Avoid_: 帮助命令、菜单

**变体 (variant)**:
一个核心唤醒词配 2-3 个自然语言等价表达,覆盖 3 方向(同义 / 口语 / 模糊)。SKILL.md 只标方向,不写具体话(避免硬编码语料)。
_Avoid_: 同义词、别名

**场景资产 (scenario asset)**:
HELP HTML 的唯一规范事实源,位于 `<skill>/references/scenarios.<format>`。人类视图、机读视图、HELP HTML 都是从它生成的派生物,不准手工维护独立副本。
_Avoid_: 场景列表、用例表

**场景 (scenario)**:
一个业务唤醒词在某个维度组合下的合法执行路径。最小必填 7 字段:wake_word / scenario_id / scenario_title / dimensions / prompt / status / result。
_Avoid_: 测试用例、功能点

**稳定 prompt**:
场景资产里用户复制的意图表达,只含稳定用户意图 + 预期结果,不暴露 CLI / DB / Python / 模板路径 / 错误码。实现层重构不需要改 prompt。
_Avoid_: 指令、命令行

### 5 层骨架

**5 层骨架**:
Skill 的强制结构:① 数据层 db.py / ② 操作层 *_ops.py + integrations/ / ③ 规则层 validators.py + references/ / ④ 接口层 CLI / ⑤ 文档层 .md + .html。所有 Skill 必须 5 层全建,无规模逃生口(ADR-0002)。
_Avoid_: MVC、分层架构(这些是通用模式,不强制 5 层命名)

**层间硬规则**:
箭头只能向下(上层 import 下层,下层绝不 import 上层);对外操作是软依赖(外部挂了本地照常工作);对外操作 ≥ 2 个集成点 → 抽 integrations/ 子模块。

### 规则系统

**硬规则 (Hard rule)**:
CLI / DB 层系统强制校验,违反直接报错拒收,无跳过通道(不留 --force / --skip-validation)。集中在 validators.py。
_Avoid_: 校验、断言

**软规则 (Soft rule)**:
AI 自觉遵守的规则,写在 references/ 章节。给心法不给关键词表,给边界示例不给枚举。AI 可以违反但不应该。
_Avoid_: 建议、提示

**钩子 (hook)**:
总纲的 7 条不可违背硬规则:① HTML 同步 / ② 改动前 3 问 / ③ 触发词 v2 / ④ CLI 阻塞判定 / ⑤ HTML 单工铁律 / ⑥ Fresh Agent 验证 / ⑦ HELP 契约。违反即视为改动未准备好。
_Avoid_: 检查项、规则(钩子是不可违背的最高级)

**HTML 单工铁律**:
HTML 是单工设备,永远单向渲染,不能反向触发 LLM。任何过程型 HTML 必须设计"复制 prompt"按钮,让用户的选择回到 AI。原则 10,最高优先级。
_Avoid_: 单向绑定、只读视图

**HTML-First**:
唤醒词命中 SKILL 后,若 SKILL 声明有 HTML 输出路径,默认行为 = invoke HTML 工作流。文字答是 fail mode,不是 fallback。原则 11,与原则 10 互补(10 管出向,11 管入向)。
_Avoid_: 默认 HTML、优先 HTML

### 状态与验证

**【待开发】**:
场景资产的二态状态之一。`status = "【待开发】"` 表示该场景不可执行但仍展示完整 prompt。用户复制该 prompt 给 AI 时,AI 必须停止业务执行并明示待开发,不准绕过 / 假装 / 降级。
_Avoid_: TODO、未完成、占位

**Fresh Agent 黑盒测试 (FAT)**:
commit 前的商用级关卡。由零上下文 agent 执行唤醒词(3-5 个核心 × 每个 ≥ 3 个人类 prompt),对比预期工作流。fail → 改 SKILL.md 不改代码,循环 ≤ 3 次。钩子 ⑥。
_Avoid_: 集成测试、用户测试、单元测试(这些测代码,FAT 测文档契约)

**5 层自检清单**:
§02 的 20+ 项勾选清单,覆盖 5 层每层的关键检查。所有 Skill 必须全跑,无规模分档(ADR-0002)。
_Avoid_: checklist、检查表

### 工程仪式

**改动前 3 问**:
动手前必答:① 影响哪些文件 / ② 有没有数据迁移 / ③ 回滚方案。答不上来 = 改动未准备好。钩子 ②。
_Avoid_: 影响评估、风险分析

**FAT 豁免**:
当改动不改变 reader 看到的 contract 时,FAT 可豁免。判定矩阵:纯文档格式化 / 纯代码重构(行为不变)/ 纯测试 / 纯配置 / 显式 revert 可豁免;涉及 SKILL.md 任何字符永不豁免。
_Avoid_: 跳过测试

**Tested-By 字段**:
commit message 必含字段,记录 FAT 结果:`fresh-agent-v1` + 唤醒词列表 + 人类 prompt + 结果,或 `exempt` + 豁免依据 + 自检说明。没填 = 协议不完整。
_Avoid_: 测试报告、CI 状态

### 可加载资产

**可加载资产**:
总纲提供的 3 个复用文件:_assets/style.css(设计令牌)/ _assets/injector.py(注入函数)/ _assets/template_skeleton.html(4 段式骨架)。Skill 复用而非重设计。
_Avoid_: 库、依赖、包

**占位符注入**:
HTML 模板里 `<!--INJECT-DATA-->` 恰好 1 次,注入器校验唯一性,JSON 序列化后转义 `</` 防断标签,写入 `window.__DATA__`。5 个必须:占位符唯一 / `</` 转义 / typeof 守卫 / 5 状态 fallback / escapeHTML。
_Avoid_: 模板渲染、字符串替换

**4 段式模板**:
HTML 模板的标准结构:首屏 HERO(标题 + KPI)/ 主体 BODY(分组折叠)/ 交互 INTERACT(轻 JS)/ 尾部 TAIL(复制 prompt + 回顶)。5 状态必有:正常 / 空 / 缺数据 / 错误 / 离线。
_Avoid_: 布局、页面结构

### 演化

**RULE Forms**:
从历史案例抽出的规则形式,非硬编码案例。所有 Skill 可复用。含 3 维度评估 / 4 Phase 模式 / 通用改造顺序 / BUG 优先级。
_Avoid_: 最佳实践、案例库

**4 Phase 模式**:
Skill 改造按"先低阻力后高阻力"顺序:A 最小阻力 → B 数据已合规 → C 规范化已有 HTML → D CLI 重构解锁阻塞。每 Phase 一个 commit,违反顺序 = 返工。
_Avoid_: 迭代、阶段

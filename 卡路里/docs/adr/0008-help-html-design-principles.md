# HELP HTML 设计原则(用户导向 · 不展示底层)

Status: accepted

Phase 1 #13 收尾时,对抗式审查发现:我曾提议加 "aliases 字段" 等内部元数据到 scene_data + HELP HTML,但用户反驳 "用户不需要知道别名" + "HELP 不该展示底层原理" — 撤回后沉淀此原则。Phase 2 #2 ~ #11 必须遵守,否则每个分类 agent 都会重复踩同样的坑。

我们决定:**HELP HTML 是用户指导手册,不是开发者文档**。3 条必须遵守 + 3 条禁止做。修改 `templates/help_center.html` 或新增场景元数据展示前,先读本 ADR。

考虑过的选项:
- **不沉淀原则,各自判断** — 每个 agent 凭直觉设计。缺点:Phase 2/3 各自会重复同样的过度设计(展示 aliases / 重复 output_type / 漏 data_source `python` 前缀)。
- **写入 SKILL.md 强制协议段** — 跟 HTML-First / ADR-0007 一样放 §⚠️。缺点:SKILL.md 是给 AI 看的运行时协议,设计原则更适合放 ADR 库。
- **当前方案(本 ADR)** — 跟 ADR-0001 / 0007 同位置,Phase 2/3 ticket body 引用 `docs/adr/0008-*.md`。改动小,可版本化,reversibility 高(git revert)。

后果:
- **正向**:Phase 2 agent 开工前读 ADR-0008 即可一次性避免 3 类常见错误。templates/help_center.html 顶部注释指向本 ADR。
- **trade-off**:用户加新需求时(比如想在 HELP 显示 xxxx),需先评估"这个对用户有用吗"——若不是,会被本 ADR 拒掉。
- **维护成本**:低,本 ADR 只在 HELP HTML 设计原则变更时才需修订。

详见:
- `templates/help_center.html` 顶部注释(改模板前必读)
- `scripts/check_scene_data.py` `data_source` 校验规则(`python` 前缀约定)
- Phase 2 #2 ~ #11 ticket body 必读段("设计原则引用 ADR-0008")
- GitHub issue #1 meta Decisions-so-far 引用
- 历史决策:ADR-0001(HELP 作为根镜像)/ 0005(HTML-First 默认)/ 0007(AI 验证协议)

---

## 必须遵守 3 条

### 1. HELP 是用户指导手册,不是开发者文档
展示这个场景能做什么 + 怎么用(复制 prompt 贴给 AI)。不展示底层原理(AI 怎么识别 alias、字段名 snake_case、internal data flow)。

### 2. 展示功能,不展示实现
用户需要知道的信息:场景名、描述(用户视角)、prompt 文本(可直接复制)。用户不需要的信息:output_type 详细语义、data_fields snake_case 字段名、depends_on_external 标志位。

### 3. `data_source` 必须带 `python ` 前缀(.py 脚本)
- ✅ 正确:`"python scripts/render_home.py"`(可一键复制执行)
- ❌ 错误:`"scripts/render_home.py"`(用户看到不知道怎么跑)
- 例外:Python 函数路径如 `"analysis.dashboard"` 直接写模块名(没有 .py 后缀)

---

## 禁止做 3 条

### 1. ❌ 在 HELP HTML L4 详情展示 aliases
AI 通过 SKILL.md frontmatter 匹配 alias,不是从 HELP HTML。用户从 HELP 复制 prompt 是主流流程,不需要知道别名。展示 = 干扰。

### 2. ❌ 在 HELP HTML L4 详情重复展示 output_type
L3 行 chip 已显示 `RESULT` / `PROCESS` / `RECEIPT`,L4 再展示 = 视觉冗余。output_type 是行为层信息,不是内容层。

### 3. ❌ 在 HELP HTML 展示 data_fields / depends_on_external 等元数据
data_fields 是开发者字段名(snake_case),用户看不懂;depends_on_external 是内部实现标志,用户不关心。放 schema 里供开发者校验即可。

---

## 实施规范

### scene_data 字段填写约定

| 字段 | 必填 | L4 是否显示 | 用途 |
|---|---|---|---|
| `data_source` | ✅ | ✅ cli 块 | L4 直接显示;约定带 `python` 前缀 |
| `output_type` | ✅ | ❌ L3 行 chip 已显示 | 行为层信息,L4 不重复 |
| `html_template` | ✅ | ❌ 内部参考 | 渲染实现,不放 HELP |
| `user_intent` | ✅ | ✅ intent | 用户口吻一句话 |
| `prompt_template` | ✅ | ✅ prompt-pre | 完整 prompt(可直接复制) |
| `data_fields` | ❌ | ❌ 不放 HELP | 校验用 |
| `depends_on_external` | ❌ | ❌ 不放 HELP | 校验用 |
| `wake_word` | ✅ | ✅ L3 行 | 主唤醒词 |
| `aliases` | ❌ **schema 不存在** | ❌ AI 通过 SKILL.md 匹配 | 别名不进 schema |

### templates/help_center.html 修改约束

未来修改 HELP 模板时:
- 不要给 L4 详情加新字段(除非有明确 UX 价值)
- 不要给 L3 行 chip 加新类型(只 process/result/receipt)
- 不要破坏 4 层结构(L1 分类 → L2 子功能 → L3 场景 → L4 详情)
- 顶部搜索框保持 sticky + 实时过滤 + 自动展开含匹配
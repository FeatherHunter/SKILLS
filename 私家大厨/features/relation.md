# 派生关系

> 路由：SKILL.md 用例 H → features/relation.md
> v4.0 T12(2026-08-09)：新增 rel-3「从已有派生新菜」+ rel-2 家族树(render_派生.py tree)；rel-1 确认卡 + 回执落地。

---

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

---

## 功能说明

派生关系用于标记一道菜基于另一道菜的变体（衍生、改良、变体），形成"食谱族谱"。

支持的场景：
- **派生**：改良版宫保虾球 → 宫保虾球（父本）
- **变体**：川式麻婆豆腐 vs 粤式麻婆豆腐
- **改良**：低脂版红烧肉 → 经典红烧肉
- **从已有派生新菜（rel-3 · 派生域核心价值）**：说「做咖喱鸡,类似咖喱牛腩」→ AI 拉母本全字段按差异预填（标色）→ 过程 HTML 用户改 → 确认 → 创建新菜谱 + 自动建派生关系一次完成

**遵循规范**：SKILL.md 中的"AI使用规范"和"字段推测规则"。

---

## 内部分流逻辑

```
用户说"添加派生关系"
    → 询问父本菜名（必填）
    → 询问子本菜名（必填）
    → relation_type 推测（派生/变体/改良，根据上下文）
    → change_summary 可选（描述改了什么）
    → render_派生.py confirm(确认卡) → 执行 relation_manager.py add

用户说"查看派生关系"
    → render_派生.py tree <菜名> → 家族树(根=当前菜,向上祖先/向下后代,多代连链)
    → 底层: 派生/cli.py tree → ops.relation_tree(list-all 全量关系 BFS 组装)

用户说"从已有派生新菜"(rel-3)
    → 派生/cli.py mother <母本>（母本不存在/已废弃 → 拒绝+提示）
    → AI 按差异预填(差异字段标色 guessed;空字段 missing 红补) → render_派生.py derive-edit(过程 HTML)
    → 用户改 → 确认 → 派生/cli.py derive-commit <payload.json>
    → 同事务写库(recipe 创建 + recipe_relations 插入) → render_派生.py receipt(成功 diff+撤销 / 失败重试)
```

---

## 工作流

### 添加派生关系（rel-1）

```
用户说"添加派生关系"
    ↓
【问父本】菜名或 ID
    ↓
【问子本】菜名或 ID
    ↓
【问类型】派生 / 变体 / 改良（默认派生）
    ↓
【问改动说明】可空
    ↓
【确认卡】render_派生.py confirm <payload.json>(父/子/类型/说明)
    ↓
【写库】relation_manager.py add \
    --parent_id <ID> --child_id <ID> \
    [--relation_type 派生] [--change_summary "..."]
    ↓
【回执】render_派生.py receipt(成功+撤销 / 失败原因+重试)
```

### 查看派生关系（rel-2 · 家族树）

```
用户说"查看派生关系 宫保虾球"
    ↓
【组装】render_派生.py tree 宫保虾球
    → 派生/cli.py tree → ops.relation_tree
    → 全量关系拉取 → 邻接表 → BFS 双向扩展(根=当前菜,祖先/后代多代连链,废弃菜不入树)
    ↓
【渲染】templates/派生/relation_tree.html(08 双按钮 + 双通道)
```

### 从已有派生新菜（rel-3 · 同事务）

```
用户说"做咖喱鸡,类似咖喱牛腩"
    ↓
【母本读取】派生/cli.py mother 咖喱牛腩
    → 不存在/已废弃 → 拒绝 + 提示(不造值)
    ↓
【差异预填】AI 拉母本全字段按差异预填:牛腩→鸡,咖喱少放,加椰浆
    → 差异字段标色(guessed,对齐 G2 三态「AI 推测」视觉)
    → 母本字段天然完整,不走缺字段拒绝制;改坏/删空 → missing 红补
    ↓
【过程 HTML】render_派生.py derive-edit <payload.json>
    ↓
【用户修改 + 确认】→ 复制确认 prompt 给 AI
    ↓
【同事务写库】派生/cli.py derive-commit <payload.json>
    → orchestrate_import:recipe 创建 + relations 插入 = 同一事务
    → 派生自身非法 / 母本废弃 / 缺 change_summary → 拒绝
    ↓
【回执】render_派生.py receipt(成功:新菜+diff+撤销;失败:原因+修正重试)
```

---

## 字段映射

| 字段 | 必填 | 推断 | 说明 |
|------|------|------|------|
| `parent_id` | ✅ | — | 父本食谱 UUID（必须存在，未废弃） |
| `child_id` | ✅ | — | 子本食谱 UUID（必须存在） |
| `relation_type` | ❌ | 派生（默认）/ 变体 / 改良 | 关系类型枚举 |
| `change_summary` | ❌ | — | 自由文本，说明改了什么（rel-3 必填 = 差异总结） |

---

## 错误处理

| 场景 | 行为 |
|------|------|
| 父本或子本不存在 | 报错"未找到食谱"，要求重输 |
| 父本 == 子本 | 报错"不能派生自身" |
| 同一对已存在 | 报错"已存在关系"，可选择更新 change_summary |
| 双方均已废弃 | 警告"双方都已废弃，是否仍要登记？" |
| rel-3 母本废弃/不存在 | 拒绝 + 提示（不造值），换母本或先恢复 |
| rel-3 缺 change_summary | 拒绝（差异总结必填，写库层 L1 兜底） |

---

## 边界

- 仅支持 1 对 1（不直接支持网状关系，需多次 add；家族树支持多父/多子展示）
- 不级联：删一道菜时不会自动删它的关系（待评估是否需要 ON DELETE CASCADE）
- 家族树默认不含已废弃菜（废弃 = 从树中淡出）
- 跨技能：不联动到 居家管家（菜谱实体不共享）
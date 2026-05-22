# P5 烹饪历史功能 - 工作流审计报告

> 审计日期：2026-05-23
> 审计范围：`features/history.md` + `scripts/history_manager.py` + 相关引用
> 审计路径：2条
> 状态：DONE_WITH_CONCERNS

---

## 审计路径1：今天做了宫保虾球，评分4.5

### 模拟流程

**用户输入**："今天做了宫保虾球，评分4.5"

#### 第1步：路由匹配（SKILL.md P17-P18）

| 优先级 | 触发词扫描 | 结果 |
|--------|-----------|------|
| P1 | 做菜模式/开始做/进入烹饪/开始烹饪/做这道菜 | 未命中 |
| P2 | 看看/菜谱/做法/步骤/详情/查看/给我看 | 未命中 |
| P3 | 找/搜/有哪些/哪些菜/什么菜/哪个 | 未命中 |
| P4 | 改成/换成/加食材/加个食材/修改/难度 | 未命中 |
| **P5** | 做过/**评分**/历史/复盘/记录/烹饪记录 | **命中 "评分"** |

意图识别结果：P5 烹饪历史。

#### 第2步：菜名提取

按路由算法 R4："评分"后面紧跟的文字 → `4.5`

- `4.5` 仅3个字符，但不是合法菜名（是数字）
- 路由算法 R6：菜名提取失败 → 追问用户

**实际问题**：用户意图是"记录做菜"，但路由算法从"评分"后面抓取的是分数而非菜名。`history.md` 示例展示了"今天做了宫保虾球，评分4.5"应该可行，但路由表不支持从"做了"后面提取菜名。

#### 第3步：功能文件加载（features/history.md）

- 命令格式：`python scripts/history_manager.py add <recipe_id> --cook_date 2026-05-15 --rating 4.5 --feedback "..."`
- AI 需要先获取 recipe_id

#### 第4步：cook_date 默认值处理

```python
# history_manager.py 第20行
cook_date = args.get("--cook_date") or datetime.now().strftime("%Y-%m-%d")
```

- 用户说"今天"且未提供 --cook_date → 默认当天日期
- 处理正确，无问题

#### 第5步：rating 范围验证

```python
# history_manager.py 第48行
args.get("--rating")  # 直接传入，无验证
```

- rating 字段为 `REAL` 类型（SQLite 无约束）
- `history_manager.py` 无任何范围验证
- 评分参考表定义 1-5 分，但代码不执行校验
- 用户输入 4.5 → 直接存入数据库，**无问题**（在范围内）
- 但若输入 0 或 6，也会被接受（设计缺陷）

#### 第6步：feedback 是否必须

```python
# history_manager.py 第48行
args.get("--feedback")  # 可选，None 时 SQLite 存 NULL
```

- 用户未提供 feedback → 值为 None → 存入 NULL
- history.md 字段说明："用户未提供→询问用户"
- **矛盾**：字段推测规则说"未提供→询问用户"，但代码层面 feedback 是可选的
- commands.md 标注 feedback 为"可选"，与字段说明矛盾

#### 第7步：recipe_id 获取

- `history_manager.py add()` 第25行：`cursor.execute("SELECT name, status FROM recipes WHERE id = ?", (recipe_id,))`
- **必须传入 recipe_id（UUID），不支持菜名**
- AI 执行者必须先用 `recipe_manager.py show "宫保虾球"` 获取 ID
- 这一步在 `history.md` 和 `commands.md` 中**未说明**

#### 第8步：首次做菜状态更新

```python
# history_manager.py 第51-52行
if recipe["status"] == "未做":
    cursor.execute("UPDATE recipes SET status = '已做' WHERE id = ?", (recipe_id,))
```

- 首次做该菜 → 自动更新 status 为 "已做"
- 处理正确

---

## 审计路径2：宫保虾球做过几次了

### 模拟流程

**用户输入**："宫保虾球做过几次了"

#### 第1步：路由匹配

| 优先级 | 扫描结果 |
|--------|---------|
| P1-P4 | 未命中 |
| **P5** | 命中 **"做过"** |

意图识别结果：P5 烹饪历史。

#### 第2步：菜名提取

- "做过"后面的文字 → `几次了`（3字符，但不是菜名）
- 按 R4 规则，菜名提取失败

**但是**：按 R4 严格解读，"宫保虾球做过几次了"中"做过"后面的文本是"几次了"。真正的菜名"宫保虾球"在触发词**前面**。

**路由算法设计缺陷**：R4 规定"触发词后面紧跟的文字视为菜名"，但 P5 的"做过"场景中，菜名往往出现在触发词**前面**（如"宫保虾球做过几次了"），而非后面。

**解决方案**：AI 执行者应智能处理 — 将"宫保虾球"从触发词前面提取。SKILL.md 路由表中"做过"的说明为"后面跟菜名，如'宫保虾球做过几次了'"，但实际上菜名在前面。

#### 第3步：执行命令

history.md 示例：
```bash
python scripts/history_manager.py list <recipe_id>
```

- `list` 命令要求 `recipe_id`（UUID）
- `history.md` 示例中写的是：`python scripts/history_manager.py list 宫保虾球`
- **矛盾**：示例用菜名，代码要求 recipe_id

#### 第4步：history_manager.py list 代码分析

```python
# history_manager.py 第66-101行
def list(args):
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False

    cursor.execute("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    recipe = cursor.fetchone()
    if not recipe:
        print(f"未找到食谱：{recipe_id}")
        conn.close()
        return False
```

- 参数名 `<recipe_id>` 表示只接受 ID
- SQL 查询用 `WHERE id = ?` — 精确匹配 UUID
- **传入菜名 "宫保虾球" → 查询失败 → "未找到食谱"**
- `recipe_manager.py show` 支持 `WHERE id = ? OR name LIKE ?`，但 `history_manager.py` 不支持

#### 第5步：stats 命令输出差异

history.md 中的统计示例：
```
总次数：3次
平均评分：4.23分
最高评分：4.5分（2026-05-15）
最低评分：4.0分（2026-05-10）
```

history_manager.py 实际输出：
```
做过次数：{times}
平均评分：{avg_rating:.1f}
最后做菜：{last_date}
```

- "总次数" vs "做过次数" — 标签不一致
- 代码输出 `avg_rating:.1f`（1位小数），文档示例 `4.23`（2位小数）
- 代码不输出最高/最低评分，文档要求输出

---

## 故障清单

### [P0-阻塞] history_manager.py 不支持菜名查询

- **位置**：`scripts/history_manager.py` 第25行、第75行
- **现象**：AI 执行者直接用 `history_manager.py list "宫保虾球"` 执行会失败，因为代码只接受 recipe_id（UUID），不支持菜名
- **复现路径**：用户"宫保虾球做过几次了" → AI 执行 `python scripts/history_manager.py list 宫保虾球` → "未找到食谱"
- **影响范围**：P5 全部4种操作（add/list/stats/update）均需 recipe_id
- **文档证据**：`history.md` 第53行示例 `python scripts/history_manager.py list 宫保虾球` 和 `commands.md` 第523行 `python scripts/history_manager.py list <recipe_id>` 直接矛盾
- **修复建议**：
  - 方案A（推荐）：在 `history_manager.py` 的 `list` 和 `stats` 中增加名称查询支持，参照 `recipe_manager.py show` 的 `WHERE id = ? OR name LIKE ?` 逻辑
  - 方案B：在 `history.md` 中明确说明 AI 必须先用 `recipe_manager.py show "菜名"` 获取 ID，再传给 `history_manager.py`

### [P1-严重] 路由算法无法从"今天做了[菜名]，评分X"提取菜名

- **位置**：`SKILL.md` 路由表 P5
- **现象**：用户说"今天做了宫保虾球，评分4.5"，路由命中 P5 触发词"评分"，但菜名在"评分"前面而非后面，R4 规则（触发词后面抓取）无法提取菜名
- **复现路径**：用户"今天做了宫保虾球，评分4.5" → 命中"评分" → 菜名提取 "4.5"（失败）→ 追问用户
- **影响范围**：P5 记录做菜场景
- **修复建议**：
  - 方案A（推荐）：在 SKILL.md P5 路由表增加触发词"做了"（说明：后面跟菜名，如"做了宫保虾球"）
  - 方案B：在路由算法中增加"前面回溯"规则 — 当后面无有效菜名时，检查触发词前面的文字

### [P1-严重] stats 输出格式与文档不一致

- **位置**：`scripts/history_manager.py` 第146-149行 vs `features/history.md` 第68-73行
- **现象**：
  - 文档要求输出"最高评分"和"最低评分"（含日期），代码不输出
  - 文档"总次数"，代码"做过次数"
  - 文档 `avg_rating` 显示2位小数（4.23），代码显示1位小数（4.1）
- **复现路径**：用户"宫保虾球平均评分多少？" → 执行 stats → 输出缺少最高/最低评分
- **影响范围**：P5 统计查看功能
- **修复建议**：修改 `history_manager.py` 的 `stats` 函数，增加最高/最低评分查询，统一标签和精度

### [P2-中等] rating 无范围验证

- **位置**：`scripts/history_manager.py` 第48行
- **现象**：`--rating` 参数直接存入数据库，无 1-5 范围校验。用户输入 0、6、-1 等值均会被接受
- **复现路径**：用户"评分6" → 执行 `history_manager.py add <id> --rating 6` → 成功（不应成功）
- **影响范围**：P5 记录做菜功能的数据完整性
- **数据库**：`rating REAL` 字段无 CHECK 约束（`init_db.py` 第214行）
- **修复建议**：在 `history_manager.py add()` 中增加范围校验 `if not 1 <= float(rating) <= 5: print("评分需在1-5之间")`

### [P3-轻微] feedback 字段推测规则矛盾

- **位置**：`features/history.md` 第145行 vs `references/commands.md` 第511行
- **现象**：
  - history.md 字段说明：feedback "用户未提供→询问用户"
  - commands.md 参数说明：feedback "可选"
  - history.md 命令参考第103行：`python scripts/history_manager.py add <recipe_id> --rating 4.5`（无 feedback）
- **影响范围**：AI 执行者不确定是否必须追问 feedback
- **修复建议**：统一为"可选"，删除字段说明中"询问用户"的描述，或改为"用户未提供→留空"

### [P3-轻微] 路由表"做过"示例与实际路由行为不符

- **位置**：`SKILL.md` 第139行
- **现象**：路由表说明"做过"后面跟菜名，示例为"宫保虾球做过几次了"，但实际菜名在触发词前面，R4 规则无法提取
- **影响范围**：P5 "做过"类查询
- **修复建议**：将示例改为菜名在后面的形式，如"做过宫保虾球几次了"，或调整路由算法

---

## 一致性检查矩阵

| 检查项 | history.md | commands.md | history_manager.py | init_db.py | 结论 |
|--------|-----------|-------------|-------------------|------------|------|
| add 参数 recipe_id | `<recipe_id>` 必需 | `<recipe_id>` 必需 | `args.get("<recipe_id>")` | - | 一致 |
| add 参数 cook_date | 默认今天 | 默认今天 | `or datetime.now()` | - | 一致 |
| add 参数 rating | 1-5 | 1-5 | 无验证 | REAL 无约束 | 不一致（无校验） |
| add 参数 feedback | 未提供→询问 | 可选 | 直接存入 | TEXT NULL | 不一致（规则矛盾） |
| list 参数 | `<recipe_id>` | `<recipe_id>` | 只接受 ID | - | 一致 |
| list 示例 | `list 宫保虾球` | `list <recipe_id>` | 不支持菜名 | - | 不一致（示例错误） |
| stats 输出 | 总次数/平均/最高/最低 | 总次数/平均/最高/最低 | 做过次数/平均/最后做菜 | - | 不一致（输出差异） |
| stats 精度 | 4.23（2位） | 4.23（2位） | `:.1f`（1位） | - | 不一致 |
| rating 类型 | 1-5 分 | 1-5 分 | 传入即存 | REAL | 一致（但无约束） |

---

## 评分参考与数据库约束一致性

| 维度 | 评分参考表 | 数据库 | 代码 | 结论 |
|------|-----------|--------|------|------|
| 范围 | 1-5 | 无约束（REAL） | 无验证 | 不一致 |
| 精度 | 0.5 步进（5.0/4.5/4.0/3.5/3.0） | REAL（任意精度） | 无限制 | 不一致 |
| 小数支持 | 支持（4.5/3.5） | 支持（REAL） | 支持 | 一致 |
| 边界值 | < 3.0 为失败 | 无限制 | 无限制 | 不一致 |

结论：评分参考定义了 1-5 范围和 0.5 步进，但数据库和代码层均无任何约束。SQLite REAL 类型可接受任意数值，包括负数和超出范围的值。

---

## 总结

| 严重程度 | 数量 | 关键问题 |
|---------|------|---------|
| P0-阻塞 | 1 | history_manager.py 不支持菜名查询 |
| P1-严重 | 2 | 路由无法提取菜名 + stats 输出格式不一致 |
| P2-中等 | 1 | rating 无范围验证 |
| P3-轻微 | 2 | feedback 规则矛盾 + 路由示例不符 |

**核心结论**：P5 烹饪历史功能存在1个阻塞性故障 — `history_manager.py` 的 `list`/`stats` 命令不支持菜名查询，而 `history.md` 和 `commands.md` 中的示例均使用菜名。AI 执行者按文档示例操作会直接失败。此外，路由算法无法从"今天做了宫保虾球"这类自然语言中提取菜名，需要增加"做了"触发词或调整菜名提取策略。

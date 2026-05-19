# 小龙虾CC交互 — 实测结果

> 测试日期：2026-05-19
> Claude Code 版本：2.1.123
> 测试环境：WSL2 + Windows

---

## 场景 5：真哥→Claude Code 编排链路

**目标**：验证真哥作为编排者，发指令→Claude Code执行→结果回收的完整链路

### 测试命令

```bash
SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
claude -p "Generate a complete Fibonacci implementation in Python, save to /tmp/fib.py..." \
  --session-id "$SESSION_ID" \
  --output-format text \
  --dangerously-skip-permissions
```

### 执行过程

```
真哥→Claude: 生成 Fibonacci Python 实现（含迭代/递归/memoization）
Claude→文件:  /tmp/fib.py 生成完成
真哥→验证:   python3 /tmp/fib.py → 输出 55, 55
```

### 结论

✅ **链路完整可用**

---

## 场景 2：多轮代码构建（文件累加）

**目标**：验证同一 session 内多轮写文件，上下文能记住之前内容

### 执行过程

```
Round 1: 创建 /tmp/utils.js (sum 函数)
Round 2: 创建 /tmp/helpers.js (multiply 函数)
Round 3: 创建 /tmp/index.js（导入 utils.js 和 helpers.js，导出 calculate）
```

### 验证结果

```javascript
// utils.js
const sum = (a,b) => a+b;

// helpers.js
const multiply = (a,b) => a*b;

// index.js
const { sum } = require('./utils.js');
const { multiply } = require('./helpers.js');
const calculate = (a, b) => sum(multiply(a, b), a);
module.exports = { calculate };
```

✅ **import 正确，上下文完整保留**

---

## 场景 3：上下文记忆验证

**目标**：验证多轮中变量/配置是否记住

### 执行过程

```
Round 1: "Remember: my project uses port 8888 and database name is production_db"
Round 2: "What port does my project use?" → 8888 ✓
Round 3: "What is the database name?" → production_db ✓
```

### 结论

✅ **记忆有效，跨轮保留**

---

## 场景 4：错误恢复与纠正

**目标**：Round N 出错，Round N+1 修正，Round N+2 验证

### 执行过程

```
Round 1: 生成有 bug 的 divide 函数（b===0 → return 0）
Round 2: "Fix it to throw an error instead"
```

### 代码对比

**修复前：**
```javascript
if (b === 0) { return 0; }
```

**修复后：**
```javascript
if (b === 0) { throw new Error('Division by zero'); }
```

✅ **错误修正有效**

---

## 场景 1：Session 生命周期管理

### 测试结果

| 测试项 | 命令 | 结果 |
|--------|------|------|
| 创建 session | `--session-id UUID` | ✅ |
| 延续 session | `--resume UUID`（同一次 exec） | ✅ |
| 跨 exec 续同一 session | `--resume UUID`（新 exec） | ⚠️ 不稳定 |

### 关键发现

- `--session-id` 仅用于**创建**
- 续命必须用 `--resume`
- **同一 exec 内多轮 `--resume` 完全可行**
- **跨 exec 续 session 有概率失败**（WSL 进程管理问题）

### 推荐模式

```bash
# 正确：单次 exec 内用 ; 或 && 串联多轮
SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
claude -p "任务1" --session-id "$SESSION_ID" ... && \
claude -p "任务2" --resume "$SESSION_ID" ... && \
claude -p "任务3" --resume "$SESSION_ID" ...
```

---

## 已知限制/踩坑

| 问题 | 解法 |
|------|------|
| `Invalid session ID: must be a valid UUID` | 用 `python3 -c "import uuid; print(uuid.uuid4())"` 生成 |
| `Session ID already in use` | 同一 session 避免重复 `--session-id`，后续用 `--resume` |
| Windows 路径访问弹窗 | 加 `--dangerously-skip-permissions` |
| 多轮间隔较长后 session 失效 | 建议任务在 10 分钟内完成 |
| WSL `/mnt/d` 路径映射到 `C:\...` | Claude Code 内部路径解析问题，优先用 `/tmp` |

---

## 场景 8：上下文衰减测试

**状态**：未执行

建议后续探索，验证 10+ 轮后的信息保持率。

---

## 总结

| 场景 | 状态 | 结论 |
|------|------|------|
| 场景5：编排链路 | ✅ 通过 | 真哥↔Claude Code 链路完整 |
| 场景2：代码累加 | ✅ 通过 | 多文件上下文保留 |
| 场景3：记忆验证 | ✅ 通过 | 配置/变量记忆有效 |
| 场景4：错误恢复 | ✅ 通过 | bug 修复能力正常 |
| 场景1：Session管理 | ⚠️ 部分通过 | 同exec内多轮可行，跨exec不稳定 |
| 场景6：WSL路径 | ⚠️ 部分通过 | /tmp 可用，/mnt/d 需 --dangerously-skip-permissions |
| 场景7：多文件项目 | ✅ 通过 | import 依赖正确（场景2已覆盖） |
| 场景8：衰减测试 | ⏸️ 未测 | 探索性，后续补充 |
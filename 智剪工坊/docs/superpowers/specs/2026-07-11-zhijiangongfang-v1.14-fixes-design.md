# 智剪工坊 v1.14 修复 Design（v1.13 实测发现的问题）

> **状态**：v1.13 在 DAY9 真实视频工作区实测发现 6 个问题。设计修复方案。
> **背景**：v1.11.1 建的日志系统，v1.12 修复了 references/，v1.13 修了脚本端。但 DAY9 实测暴露：AI 0% 写 JSONL + HTML 5 个点与 SKILL 不同步 + 日志路径错乱。

**目标**：把"纸面规范"v1.13 变成"用户实跑能成功"的 v1.14。

**架构**：1 spec + 3 独立 sub-project（v1.14 spec 改 / lib+scripts 改 / HTML 改）。

**Tech Stack**：Python 装饰器 + 强制调用 / Markdown / HTML/JavaScript

---

## 1. 背景：DAY9 实测发现

| 问题 | 严重 | 实测证据 |
|---|---|---|
| **P0-1** AI 0% 写 JSONL 日志 | 🔴 | `find DAY9 -name "*.jsonl"` 无输出 |
| **P1-1** HTML "保存(V1→V2)" 只覆盖，不新增历史 | 🟠 | intent.json revision=2，intent_v1.json 存在但 HTML 不写 |
| **P1-2** HTML 无 "复制路径给 AI" 便捷操作 | 🟠 | 需手动复制粘贴 |
| **P1-3** HTML Sequence 标题无限制（应只对开头视频开放） | 🟠 | 任意视频都可填 |
| **P1-4** HTML 目标时长无"不确定"选项 | 🟠 | input 是 text 但没"不确定"提示 |
| **P1-5** HTML cover.type 包含 `still-frame`（SKILL 不支持） | 🟠 | `<option value="still-frame">视频帧</option>` |
| **P2-1** 日志目录 `00_智剪/粗加工/中间产物/logs/` 位置错乱 | 🟡 | 粗加工还没开始，日志不该在粗加工子目录 |

---

## 2. 设计：3 个 sub-project

### Sub-project A：lib/common.py + scripts/*.py 加 `log_decision` 强制机制（P0 修复）

**问题**：v1.13 spec 说"AI 用 `open('a').write(...)` 写 JSONL"，但 AI 不执行。0 个 JSONL 文件生成。

**根因**：依赖 AI 自觉 = 不执行

**修复方案**：
1. `lib/common.py` 新增 `log_decision(stage, step, action, decision, thinking, result, error=None)` 函数
2. 该函数**自动** append JSONL 到 `<workspace>/00_智剪/logs/<task_id>.jsonl`（注：v1.14 起路径在 `00_智剪/logs/` 顶层，不嵌套）
3. **不**依赖 AI 写文件 —— AI 调用 `log_decision()` 即可
4. AI 在每个 CLI 调用前**必须**调一次 `log_decision()`
5. scripts/*.py 中的核心 CLI 调用（如 trim/asr/cover）封装一个 wrapper，AI 必须通过 wrapper 调 CLI（wrapper 自动 log_decision）

**API 设计**：

```python
# lib/common.py 新增
def log_decision(stage: str, step: str, action: str, decision: str,
                 thinking: str, result: str = "", error: str = None,
                 task_id: str = None):
    """AI 在每个 CLI 调用前必调，自动写 JSONL

    参数：
      stage: 当前阶段（"2"/"step_10_review"/"refine" 等）
      step: stage 内步骤
      action: 操作类型（trim/color/asr/review）
      decision: AI 决策内容
      thinking: AI 思考过程
      result: CLI exit code / 异常类型
      error: 错误信息（None = 无错误）
      task_id: 任务 ID（默认从 intent.json 读）

    自动：
      1. 定位 <workspace>/00_智剪/logs/<task_id>.jsonl
      2. 追加一行 JSON entry（time/stage/step/action/decision/thinking/result/error 8 字段）
      3. 失败时回退到 stderr（不阻断主流程）
    """
    # 实现见 Sub-project A 详细设计
```

**stage 枚举**（v1.14 统一）：
- `"0"` `"1"` `"2"` `"3"` `"4"` `"5"`
- `"step_10_review"` `"refine"` `"step_12_review"` `"finalize"`
- `"reuse_backup"` `"reuse_apply"`

**AI 使用示例**：

```python
# AI 跑粗加工 9.3 单视频处理
from common import log_decision

# 调 CLI 前
log_decision(
    stage="2", step="9.3", action="trim",
    decision="trim 0-5s for video_3",
    thinking="用户说剪开头抖动",
    result=""
)
subprocess.run(["python", "scripts/video/trim.py", "-i", video_path, "-ss", "0", "-t", "5", "-o", output_path])

# 调 CLI 后
log_decision(
    stage="2", step="9.3", action="trim",
    decision="trim 0-5s for video_3",
    thinking="用户说剪开头抖动",
    result="exit 0"
)
```

**v1.14 spec §AI 行为约束**（更新）：
- ❌ **禁止** AI 用 `open('a').write(json.dumps(...))` 直接写 JSONL（v1.13 的错误做法）
- ✅ **必须** AI 调 `log_decision()` 函数
- AI 不遵守 → 监控脚本会统计 `log_decision()` 调用次数 vs CLI 次数，差异 ≥ 20% 警告

---

### Sub-project B：HTML 5 个点修改

**位置**：`智剪工坊-意图编辑.html`（4.5MB / 1917 行）

#### B-1：保存改名 `intent_<timestamp>.json`（不覆盖）

**当前**：保存覆盖 `intent.json`
**修复**：保存生成 `intent_<YYYYMMDD_HHMMSS>_<slug>.json`，**不覆盖**历史

**关键逻辑**：
```javascript
// 旧：覆盖
saveBtn.click = () => {
  fs.writeFile('intent.json', JSON.stringify(data));
};

// 新：每次保存新文件
saveBtn.click = () => {
  const ts = formatDate(new Date(), 'YYYYMMDD_HHMMSS');
  const slug = slugify(data.project.title);
  const filename = `intent_${ts}_${slug}.json`;
  // 用户填的 workspace = 当前目录
  fs.writeFile(filename, JSON.stringify(data));
  // 显示"已保存为 <filename>"
  showSuccess(`已保存到 ${filename}`);
};
```

**保留** `intent.json`：保存时同时写 `intent.json`（**最新版**） + 历史快照 `intent_<timestamp>_<slug>.json`

**理由**：AI 加载时只看 `intent.json`（最新版），但用户可看历史。

#### B-2：保存后"复制路径给 AI"按钮

**当前**：保存后无后续操作
**修复**：保存成功 toast 含 "复制路径" 按钮

**关键 UI**：
```html
<div class="save-success" style="display:none">
  ✅ 已保存到 <code>intent_<timestamp>_<slug>.json</code>
  <button class="copy-path">📋 复制路径</button>
  <textarea class="full-path" readonly></textarea>
</div>
```

**关键 JS**：
```javascript
copyPathBtn.click = async () => {
  await navigator.clipboard.writeText(fullPathTextarea.value);
  copyPathBtn.textContent = '✅ 已复制';
  setTimeout(() => copyPathBtn.textContent = '📋 复制路径', 2000);
};
```

#### B-3：Sequence 标题只对开头视频开放

**当前**：所有 video 都有 seq-title-input 可填
**修复**：只 `sequences[].videos[0]` 那个视频的 seq-title 可填（其他 disable 或隐藏）

**关键 JS**：
```javascript
// 对每个 video，如果它不是任何 sequence 的 videos[0]，disable seq-title-input
sequences.forEach(seq => {
  const firstVideoIndex = seq.videos[0]; // 1-indexed
  // 其他 video 的 seq-title-input 设为 disabled
  // 只 firstVideoIndex 那个可填
});
```

#### B-4：目标时长"不确定"选项

**当前**：`<input type="text">` 自由文本
**修复**：加 "我不确定" 按钮 + 占位提示

**关键 HTML**：
```html
<input type="text" data-path="project.target_length" placeholder="如 3 或 3-5">
<button class="unsure-btn" type="button">我不确定</button>
```

**关键 JS**：
```javascript
unsureBtn.click = () => {
  document.querySelector('[data-path="project.target_length"]').value = '不确定';
};
```

**AI 协议补充**（v1.14 spec）：target_length 接受 `"数字"` / `"数字-数字"` / `"不确定"` 三种格式

#### B-5：cover.type 删除 `still-frame`

**当前**：
```html
<option value="ai">AI 生图</option>
<option value="text">纯文字</option>
<option value="image">图片</option>
<option value="still-frame">视频帧</option>
```

**修复**：删除 `still-frame`（SKILL 不支持）

**修复后**：
```html
<option value="ai">AI 生图</option>
<option value="text">纯文字</option>
<option value="image">图片</option>
```

**SKILL 协议补充**（v1.14 spec）：cover.type 枚举只支持 `ai` / `text` / `image`（image 由 ai + 用户上传图片合成）

---

### Sub-project C：spec 改日志路径为 `00_智剪/logs/`

**当前**：`00_智剪/粗加工/中间产物/logs/`（嵌套在粗加工子目录）
**修复**：`00_智剪/logs/`（顶层，与粗加工/精加工/出片 同级）

**修改文件**：
- `references/AI行为日志协议.md` §6（路径定义）
- `references/主流程-阶段编排.md` §5.1（announce 协议引用路径）
- `references/二次加工-复用工作流.md` §3.1（完整性校验检查路径）
- `commands/查看日志.sh`（脚本内的 log dir 路径）
- `commands/查看粗加工日志.sh`（同上）
- `commands/复盘.sh`（同上）

**新路径模板**（v1.14 spec）：
```
<workspace>/
├── 00_智剪/
│   ├── logs/                              # ← v1.14 新顶层
│   │   └── <task_id>.jsonl
│   ├── 粗加工/
│   ├── 精加工/
│   └── 出片/
```

---

## 3. 文件变更清单

### 修改（spec/references/commands）

1. `references/AI行为日志协议.md`（Sub-project A 接口 + Sub-project C 路径）
2. `references/主流程-阶段编排.md`（Sub-project C 路径 + Sub-project A 引用）
3. `references/二次加工-复用工作流.md`（Sub-project C 路径）
4. `commands/查看日志.sh`（Sub-project C 路径）
5. `commands/查看粗加工日志.sh`（Sub-project C 路径）
6. `commands/复盘.sh`（Sub-project C 路径）

### 修改（代码）

7. `lib/common.py`（新增 `log_decision()` 函数 ~50 行）

### 修改（HTML）

8. `智剪工坊-意图编辑.html`（5 个点修改）

### 不修改

- `references/精加工-两路径.md` / `references/审查-用户交互循环.md` / `references/粗加工-执行契约.md`（已 v1.12/v1.13 修复完）
- `lib/ffmpeg/*.py`（v1.13 已应用装饰器）
- `scripts/*` 的核心 CLI（v1.14 不动脚本内部，只让 AI 在调用前后加 log_decision 调用）

### 新增（spec/plan）

9. `docs/superpowers/specs/2026-07-11-zhijiangongfang-v1.14-fixes-design.md`（本文档）
10. `docs/superpowers/plans/2026-07-11-zhijiangongfang-v1.14-fixes.md`

---

## 4. 验收标准

### Sub-project A（log_decision 强制机制）

- [ ] `lib/common.py` 包含 `log_decision()` 函数
- [ ] 函数签名匹配 spec §2 Sub-project A
- [ ] AI 调 `log_decision()` 后 JSONL 文件**自动生成**（无需 AI 写文件）
- [ ] 8 字段全（time/stage/step/action/decision/thinking/result/error）
- [ ] 写文件失败时回退到 stderr（不阻断主流程）
- [ ] v1.14 spec §AI 行为约束更新（禁止 AI 自写 JSONL）

### Sub-project B（HTML 5 个点）

- [ ] B-1：保存生成 `intent_<timestamp>_<slug>.json`，intent.json 是最新版
- [ ] B-2：保存后 toast 有"复制路径"按钮 + clipboard.writeText
- [ ] B-3：非 sequences[0] 的视频 seq-title input 被 disable
- [ ] B-4："我不确定"按钮可填 target_length="不确定"
- [ ] B-5：cover.type select 删除 `still-frame` 选项
- [ ] HTML 文件大小变化 < 5%（小修改）

### Sub-project C（spec 路径）

- [ ] `references/AI行为日志协议.md` §6 路径改为 `00_智剪/logs/<task_id>.jsonl`
- [ ] `references/主流程-阶段编排.md` §5.1 引用新路径
- [ ] `references/二次加工-复用工作流.md` §3.1 引用新路径
- [ ] 3 个 commands/ 脚本 LOG_DIR 改为 `00_智剪/logs`
- [ ] 全 references/ 扫描残留旧路径（`粗加工/中间产物/logs`）= 0

### 端到端验证（用户重测后）

- [ ] 另一个 AI 重跑完整 13 步流程
- [ ] `<workspace>/00_智剪/logs/<task_id>.jsonl` 存在且有 ≥ 10 行
- [ ] HTML 保存后生成 `intent_<timestamp>_<slug>.json`
- [ ] cover.type=ai/text/image 可用，still-frame 被拒绝

---

## 5. 风险与缓解

| 风险 | 缓解 |
|---|---|
| HTML 4.5MB 修改可能引入新 bug | 只改目标位置 5 处（不是全文重写），用 `read_file + edit_file` 精确编辑 |
| log_decision 在 scripts/*.py 中集成工作量大 | v1.14 **不**改 scripts/.py，只在 AI 调用协议中**要求** AI 调 log_decision()（v1.15 再做 scripts 集成） |
| HTML 修改可能影响其他功能 | 5 处都是**新增**或**禁用**功能，不删核心逻辑 |
| 用户重测需要重新跑整个流程 | 不可避免，**这是修复的目标**：让 v1.14 实测不再发现问题 |
| 旧 intent.json 与新命名规则不兼容 | v1.14 兼容旧格式（intent.json 仍然存在，AI 优先读） |

---

## 6. 不在本次范围（YAGNI）

- ❌ HTML 完整重写（保留 4.5MB 旧代码，只改目标点）
- ❌ scripts/*.py 内部集成 log_decision（v1.15 范围）
- ❌ 日志文件的 Web UI（commands/ 脚本够用）
- ❌ AI 强制机制（spec + 协议约束，依赖 AI 自觉）

---

## 7. 实施顺序（依赖关系）

```
Sub-project A (log_decision 函数) ─┐
                                    ├─→ Sub-project B (HTML 5 点)
Sub-project C (spec 路径)         ─┘
                                          ↓
                                  端到端验证（用户重测）
```

**Sub-project A 和 C 必须先做**（Sub-project B 的 HTML 也引用新路径）。

**Sub-project B 最后做**（HTML 修改需要 log_decision 存在，否则 HTML 提示的"AI 必调 log_decision"无意义）。

---

## 8. 时间估算

- Sub-project A：1h
- Sub-project C：30 min
- Sub-project B：1.5h（HTML 4.5MB 解析+5 处修改）
- 端到端验证：用户重测 30 min
- **总计**：~3.5h
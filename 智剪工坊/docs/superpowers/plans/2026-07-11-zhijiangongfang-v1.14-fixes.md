# 智剪工坊 v1.14 修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 v1.13 DAY9 实测发现的 6 个问题（P0: AI 0% 写 JSONL / P1: HTML 5 个点不同步 / P2: 日志路径错乱），让 v1.14 SKILL 在真实工作区可正常运行。

**Architecture:** 5 个 task 按依赖顺序：(1) spec 路径更新 → (2) log_decision 函数 + AI 协议 → (3-4) HTML 5 个点修改 → (5) 端到端验证（用户重测）。

**Tech Stack:** Python 装饰器 / Markdown / HTML/JavaScript

---

## 文件结构

**修改（7 个）：**
- `references/AI行为日志协议.md`（Sub-project A 接口 + Sub-project C 路径）
- `references/主流程-阶段编排.md`（Sub-project C 路径 + Sub-project A 引用）
- `references/二次加工-复用工作流.md`（Sub-project C 路径）
- `commands/查看日志.sh`（Sub-project C 路径）
- `commands/查看粗加工日志.sh`（Sub-project C 路径）
- `commands/复盘.sh`（Sub-project C 路径）
- `lib/common.py`（新增 `log_decision()` 函数 ~50 行）
- `智剪工坊-意图编辑.html`（5 个点修改）

**新增（1 个）：**
- `docs/superpowers/specs/2026-07-11-zhijiangongfang-v1.14-fixes-design.md`（已写）

**不修改：**
- `lib/ffmpeg/*.py`（v1.13 已应用装饰器）
- `scripts/*`（v1.14 不动脚本内部）
- `references/精加工-两路径.md` / `references/审查-用户交互循环.md` / `references/粗加工-执行契约.md`

---

## Task 1: spec 日志路径更新（Sub-project C）

**Files:**
- Modify: `references/AI行为日志协议.md` §6
- Modify: `references/主流程-阶段编排.md` §5.1
- Modify: `references/二次加工-复用工作流.md` §3.1
- Modify: `commands/查看日志.sh`
- Modify: `commands/查看粗加工日志.sh`
- Modify: `commands/复盘.sh`

**目的：** 把所有"00_智剪/粗加工/中间产物/logs"路径改为"00_智剪/logs"。

- [ ] **Step 1: 找出所有旧路径引用**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -rn "粗加工/中间产物/logs\|粗加工.*中间产物.*logs" references/ commands/ SKILL.md
```

预期：列出所有需要改的位置

- [ ] **Step 2: 更新 AI行为日志协议.md §6**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -n "中间产物/logs" references/AI行为日志协议.md
```

找到路径定义行（应该是 `\`\`\`` 代码块内的 `<workspace>/00_智剪/中间产物/logs/<task_id>_<timestamp>.jsonl`）。

用 Edit 工具替换为：

```markdown
- 绝对路径：`<workspace>/00_智剪/logs/<task_id>_<timestamp>.{md,jsonl}`（v1.14 起放在 `00_智剪/logs/` 顶层，与粗加工/精加工/出片 同级）
```

同时在 §3 JSONL 字段表前加：

```markdown
**v1.14 新增**：`log_decision()` 函数（lib/common.py）—— AI 在每个 CLI 调用前必须调，自动写 JSONL。**禁止** AI 自己用 `open('a').write(...)` 直接写。
```

- [ ] **Step 3: 更新 主流程-阶段编排.md §5.1**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -n "中间产物/logs\|粗加工/中间产物" references/主流程-阶段编排.md
```

找到引用位置，替换路径为 `00_智剪/logs/`。

- [ ] **Step 4: 更新 二次加工-复用工作流.md §3.1**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -n "中间产物/logs\|粗加工/中间产物" references/二次加工-复用工作流.md
```

替换路径为 `00_智剪/logs/`。

- [ ] **Step 5: 更新 3 个 shell 脚本的 LOG_DIR**

对每个脚本：

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
for f in commands/查看日志.sh commands/查看粗加工日志.sh commands/复盘.sh; do
    sed -i 's|00_智剪/中间产物/logs|00_智剪/logs|g' "$f"
    grep -c "00_智剪/logs" "$f"
done
```

预期：每个脚本 grep 输出 ≥ 1

- [ ] **Step 6: 全 references/ 扫描残留**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -rn "粗加工/中间产物/logs\|中间产物/logs" references/ commands/ SKILL.md
```

预期：无输出

- [ ] **Step 7: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add references/AI行为日志协议.md references/主流程-阶段编排.md references/二次加工-复用工作流.md commands/
git commit -m "fix(v1.14): spec 路径更新 - 00_智剪/logs/ 顶层（v1.14）"
```

---

## Task 2: lib/common.py 新增 log_decision() 函数（Sub-project A 核心）

**Files:**
- Modify: `lib/common.py`（新增函数 ~80 行）

**目的：** AI 调 `log_decision()` 自动写 JSONL，替代 v1.13 的"AI 自写"不可靠设计。

- [ ] **Step 1: 定位 lib/common.py 装饰器位置（v1.13 已加 log_ffmpeg_call）**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -n "def log_ffmpeg_call\|def _truncate_args\|^# === v1.13" lib/common.py
```

预期：找到装饰器代码块位置（v1.13 加的）

- [ ] **Step 2: 在 log_ffmpeg_call 之后追加 log_decision 函数**

在 v1.13 装饰器代码块**之后**追加：

```python

# === v1.14 日志强制机制 ===

# 缓存 task_id（避免每次都读 intent.json）
_task_id_cache = None

def _get_task_id(workspace: str = ".") -> str:
    """从 intent.json 读 task_id（缓存）"""
    global _task_id_cache
    if _task_id_cache is not None:
        return _task_id_cache

    intent_path = Path(workspace) / "intent.json"
    if not intent_path.exists():
        _task_id_cache = "unknown_task"
        return _task_id_cache

    try:
        with open(intent_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 优先用 project.title 转 slug，否则用 project.name，否则 fallback
        title = data.get("project", {}).get("title") or data.get("project", {}).get("name") or "task"
        slug = title.lower().replace(" ", "-")
        _task_id_cache = slug
        return _task_id_cache
    except Exception:
        _task_id_cache = "unknown_task"
        return _task_id_cache


def _get_log_path(workspace: str, task_id: str) -> Path:
    """获取 JSONL 日志路径（v1.14: 00_智剪/logs/）"""
    return Path(workspace) / "00_智剪" / "logs" / f"{task_id}.jsonl"


def log_decision(stage: str, step: str, action: str, decision: str,
                 thinking: str, result: str = "", error: str = None,
                 workspace: str = "."):
    """AI 在每个 CLI 调用前必调，自动写 JSONL

    参数：
      stage: 当前阶段（"2"/"step_10_review"/"refine" 等）
      step: stage 内步骤
      action: 操作类型（trim/color/asr/review）
      decision: AI 决策内容
      thinking: AI 思考过程
      result: CLI exit code / 异常类型（默认空）
      error: 错误信息（None = 无错误）
      workspace: 工作目录绝对路径（默认当前目录）

    行为：
      1. 定位 <workspace>/00_智剪/logs/<task_id>.jsonl
      2. 创建 logs/ 目录（如不存在）
      3. 追加一行 JSON entry（8 字段：time/stage/step/action/decision/thinking/result/error）
      4. 写失败时回退到 stderr（不阻断主流程）
    """
    try:
        task_id = _get_task_id(workspace)
        log_path = _get_log_path(workspace, task_id)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        entry = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "stage": stage,
            "step": step,
            "action": action,
            "decision": decision,
            "thinking": thinking,
            "result": result,
            "error": error,
        }

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    except Exception as e:
        # 写失败时回退到 stderr（不阻断主流程）
        sys.stderr.write(f"[log_decision] 写日志失败: {e}\n")
        sys.stderr.flush()
```

⚠️ **重要**：检查 `from datetime import datetime` 是否已 import。若无，添加。

- [ ] **Step 3: 检查/添加 import**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep "from datetime\|import datetime" lib/common.py
```

若无：

```python
# 在 import 区域添加（lib/common.py 顶部）
from datetime import datetime
```

- [ ] **Step 4: 验证函数存在**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -n "def log_decision\|def _get_task_id\|def _get_log_path" lib/common.py
```

预期：3 个函数定义

- [ ] **Step 5: 端到端测试 log_decision**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
mkdir -p /tmp/zhijiangongfang_log_test/00_智剪/logs
cd /tmp/zhijiangongfang_log_test
# 写一个简单的 intent.json
cat > intent.json << 'EOF'
{
  "project": {"title": "测试任务"}
}
EOF
# 调 log_decision
python -c "
import sys
sys.path.insert(0, 'C:/2Study/StudyNotes/SKILLS/智剪工坊/lib')
from common import log_decision
log_decision(stage='2', step='9.3', action='trim', decision='测试', thinking='单元测试', result='exit 0')
print('OK: 函数可调用')
"
# 验证 JSONL 文件
echo "--- 生成的 JSONL ---"
cat 00_智剪/logs/测试任务.jsonl
```

预期：
- 输出 "OK: 函数可调用"
- JSONL 文件含 1 行 entry（含 time/stage/step/action/decision/thinking/result/error 8 字段）

- [ ] **Step 6: 测试错误处理（写失败回退）**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
# 模拟 workspace 不存在的情况
python -c "
import sys
sys.path.insert(0, 'lib')
from common import log_decision
# 故意给个非法的 workspace
try:
    log_decision(stage='X', step='X', action='X', decision='X', thinking='X', workspace='/invalid/path/\x00')
    print('OK: 写失败回退到 stderr 不抛异常')
except Exception as e:
    print(f'FAIL: 函数抛了异常: {e}')
" 2>&1
```

预期：输出 "OK"（即使失败也不抛异常）

- [ ] **Step 7: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add lib/common.py
git commit -m "feat(v1.14): lib/common.py 新增 log_decision() 强制日志写入函数"
```

---

## Task 3: v1.14 spec §AI 行为约束更新（Sub-project A 配套）

**Files:**
- Modify: `references/AI行为日志协议.md` §6

**目的：** 在 spec 中明确 AI 行为约束（v1.13 错误的"AI 自写"被禁止）。

- [ ] **Step 1: 找到 §6 路径定义位置**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -n "## 6\.\|^## 7\." references/AI行为日志协议.md
```

预期：找到 §6 章节

- [ ] **Step 2: 在 §6 末尾追加 AI 行为约束**

打开 `references/AI行为日志协议.md`，在 §6 末尾**追加**新章节 §8（v1.14 新增）：

```markdown

## 8. AI 行为约束（v1.14 强制）

### 8.1 禁止 AI 自写 JSONL

❌ **禁止**：AI 用 `open('a').write(json.dumps(...)+'\n')` 直接写 JSONL（v1.13 的错误做法）

### 8.2 必须调 log_decision()

✅ **必须**：AI 在每个 CLI 调用前后调 `from common import log_decision`

**调用前**（记录决策 + 思考）：
```python
log_decision(
    stage="2", step="9.3", action="trim",
    decision="trim 0-5s for video_3",
    thinking="用户说剪开头抖动",
    result=""
)
```

**调用后**（记录结果）：
```python
log_decision(
    stage="2", step="9.3", action="trim",
    decision="trim 0-5s for video_3",
    thinking="用户说剪开头抖动",
    result="exit 0"  # 或 "timeout" / "error"
)
```

### 8.3 监控机制

- 监控脚本会统计 `log_decision()` 调用次数 vs CLI 次数
- 差异 ≥ 20% → 警告（AI 写日志不全）
- 差异 ≥ 50% → 严重（AI 没遵守协议）
```

- [ ] **Step 3: 验证 §8 已添加**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -c "^## 8\." references/AI行为日志协议.md
```

预期：1

- [ ] **Step 4: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add references/AI行为日志协议.md
git commit -m "docs(v1.14): AI行为日志协议 §8 AI 行为约束（禁止自写 / 必须 log_decision）"
```

---

## Task 4: HTML 5 个点修改（Sub-project B）

**Files:**
- Modify: `智剪工坊-意图编辑.html`（4.5MB / 1917 行）

**目的：** HTML 与 v1.13 SKILL 同步：保存不覆盖 / 复制路径 / Sequence 限制 / 不确定 / 删除 still-frame。

- [ ] **Step 1: 定位 5 个目标位置**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
echo "=== B-5 still-frame 位置 ==="
grep -n "still-frame" 智剪工坊-意图编辑.html
echo ""
echo "=== B-3 seq-title-input 位置 ==="
grep -n "seq-title\|sequence.*title\|Sequence 标题" 智剪工坊-意图编辑.html | head -10
echo ""
echo "=== B-4 目标时长 input 位置 ==="
grep -n "target_length\|目标时长" 智剪工坊-意图编辑.html | head -5
echo ""
echo "=== B-1/B-2 保存按钮位置 ==="
grep -n "保存\|saveBtn\|save-btn" 智剪工坊-意图编辑.html | head -10
```

预期：找到 5 个目标位置

- [ ] **Step 2: B-5 删除 still-frame 选项**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
# 找到 still-frame 整行，删除
grep -n '<option value="still-frame">视频帧</option>' 智剪工坊-意图编辑.html
```

找到后用 Edit 工具删除该行（保留 surrounding 选项）。

- [ ] **Step 3: B-4 加"我不确定"按钮**

找到目标时长 input 行的代码块（约 `<input type="text" data-path="project.target_length">` 附近），在 input 之后**追加**按钮 HTML：

```html
<button type="button" class="unsure-btn" onclick="document.querySelector('[data-path=&quot;project.target_length&quot;]').value='不确定'">我不确定</button>
```

并添加 CSS（在 `<style>` 块内）：

```css
.unsure-btn { padding: 4px 8px; margin-left: 8px; font-size: 12px; cursor: pointer; }
```

- [ ] **Step 4: B-3 Sequence 标题限制（disable 非首个 video）**

找到 `seq-title-input` 的赋值循环逻辑（约 "// v1.10 新增:加载 sequence title" 注释附近）。

找到 JS 函数中遍历 videos 的循环，在循环内**添加**逻辑：

```javascript
// 找出所有 sequence 的第一个 video（videos[0]）
const firstVideos = new Set();
sequences.forEach(seq => {
  if (seq.videos && seq.videos.length > 0) {
    firstVideos.add(seq.videos[0]);
  }
});

// 对每个 seq-title-input，如果不是 firstVideo，disable
document.querySelectorAll('.seq-title-input').forEach(input => {
  const videoIndex = parseInt(input.dataset.videoIndex, 10);
  if (!firstVideos.has(videoIndex)) {
    input.disabled = true;
    input.placeholder = '(仅 sequence 开头视频可填)';
  }
});
```

- [ ] **Step 5: B-1 + B-2 改名 + 复制路径按钮**

找到保存按钮的 click handler（约 `saveBtn.addEventListener('click'` 或 `function save()` 附近）。

**修改保存逻辑**：

找到 `fs.writeFile('intent.json', ...)` 或类似代码（实际可能用 `FileSystemAccess` API 或 `Blob` 下载）。

**关键改动**：

```javascript
// 旧：保存到单一 intent.json
// 新：保存到 intent_<timestamp>_<slug>.json + 同时更新 intent.json
function generateTimestampFilename(data) {
  const ts = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 15); // YYYYMMDD_HHMMSS
  const title = (data.project && (data.project.title || data.project.name)) || 'task';
  const slug = title.toLowerCase().replace(/[^\w一-龥-]/g, '-').slice(0, 50);
  return `intent_${ts}_${slug}.json`;
}

// 在保存函数中：
async function save() {
  const data = collectFormData();
  const filename = generateTimestampFilename(data);
  
  // 同时写：intent.json (最新版) + intent_<timestamp>_<slug>.json (历史快照)
  // 实际写入逻辑取决于 HTML 用的文件系统 API（FileSystemAccess / Blob / Node fs）
  // ... 写两份文件 ...
  
  // 显示成功 + 复制路径按钮
  const fullPath = `${currentWorkspace}/${filename}`;
  showSaveSuccess(filename, fullPath);
}

function showSaveSuccess(filename, fullPath) {
  // 隐藏保存按钮区域
  // 显示成功提示 + 复制按钮
  const successDiv = document.querySelector('.save-success') || createSaveSuccessDiv();
  successDiv.innerHTML = `
    ✅ 已保存到 <code>${filename}</code>
    <button class="copy-path-btn">📋 复制路径</button>
    <textarea class="full-path" readonly style="position:absolute;left:-9999px">${fullPath}</textarea>
  `;
  successDiv.style.display = 'block';
  
  successDiv.querySelector('.copy-path-btn').onclick = async () => {
    await navigator.clipboard.writeText(fullPath);
    const btn = successDiv.querySelector('.copy-path-btn');
    btn.textContent = '✅ 已复制';
    setTimeout(() => { btn.textContent = '📋 复制路径'; }, 2000);
  };
}
```

⚠️ **重要**：HTML 实际使用的文件系统 API 可能是 FileSystemAccess（modern Chrome）或 Blob 下载（fallback）。**subagent 需先 grep 看实际代码，再适配。**

- [ ] **Step 6: 验证 HTML 文件大小变化**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
ls -la 智剪工坊-意图编辑.html
```

预期：大小变化 < 5%（小修改）

- [ ] **Step 7: 验证 5 处修改都生效**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
echo "still-frame 应=0:"
grep -c "still-frame" 智剪工坊-意图编辑.html
echo "我不确定 应≥1:"
grep -c "我不确定" 智剪工坊-意图编辑.html
echo "seq-title disable 应≥1:"
grep -c "firstVideos\|seq-title-input.*disabled" 智剪工坊-意图编辑.html
echo "复制路径 应≥1:"
grep -c "复制路径\|navigator.clipboard" 智剪工坊-意图编辑.html
echo "intent_<timestamp>_<slug> 应≥1:"
grep -c "generateTimestampFilename\|intent_\${ts}" 智剪工坊-意图编辑.html
```

预期：4 项 ≥ 1，still-frame = 0

- [ ] **Step 8: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add 智剪工坊-意图编辑.html
git commit -m "feat(v1.14): HTML 5 点修改（保存改名+复制路径+Sequence限制+不确定+删still-frame）"
```

---

## Task 5: 端到端验证（用户重测）

**Files:**
- Verify: 全部修改

**目的：** 用户用另一个 AI 跑完整 13 步流程，确认 v1.14 修复有效。

- [ ] **Step 1: 验证 spec 路径一致性**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
echo "旧路径残留（应=0）:"
grep -rn "粗加工/中间产物/logs\|中间产物/logs" references/ commands/ SKILL.md
echo ""
echo "新路径出现次数（应≥5）:"
grep -c "00_智剪/logs" references/AI行为日志协议.md references/主流程-阶段编排.md references/二次加工-复用工作流.md commands/查看日志.sh commands/查看粗加工日志.sh commands/复盘.sh
```

预期：旧路径=0，新路径≥5

- [ ] **Step 2: 验证 log_decision 函数**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -n "def log_decision" lib/common.py
echo "---"
# 快速调用测试
python -c "
import sys
sys.path.insert(0, 'lib')
from common import log_decision
log_decision(stage='TEST', step='verify', action='test', decision='验证 log_decision 可用', thinking='Task 5 验证', result='ok')
print('OK')
"
```

预期：函数定义存在 + 调用成功 + 输出 "OK"

- [ ] **Step 3: 验证 HTML 5 点修改**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
echo "=== HTML 5 项验证 ==="
echo "1. still-frame 已删（应=0）: $(grep -c 'still-frame' 智剪工坊-意图编辑.html)"
echo "2. 我不确定 按钮（应≥1）: $(grep -c '我不确定' 智剪工坊-意图编辑.html)"
echo "3. Sequence 限制 firstVideos（应≥1）: $(grep -c 'firstVideos' 智剪工坊-意图编辑.html)"
echo "4. 复制路径 + clipboard（应≥1）: $(grep -c 'navigator.clipboard\|复制路径' 智剪工坊-意图编辑.html)"
echo "5. 改名函数 generateTimestampFilename（应≥1）: $(grep -c 'generateTimestampFilename' 智剪工坊-意图编辑.html)"
```

- [ ] **Step 4: 用户重测（不在本 plan 范围）**

```bash
echo "本 step 由用户执行："
echo "1. 用另一个全新 AI 加载智剪工坊 SKILL"
echo "2. 跑完整 13 步流程（DAY9 工作区或新工作区）"
echo "3. 把 00_智剪/logs/<task_id>.jsonl 发给本 AI 分析"
echo "4. 验证 AI 写日志 ≥ 10 行（v1.13 实测=0）"
```

- [ ] **Step 5: 汇总 git log**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git log --oneline -8
```

预期：v1.14 相关 5 个 commit（spec + Task 1-4）

---

## Self-Review

**1. Spec coverage:**
- ✅ Sub-project A（P0 修复）→ Task 2 + Task 3
- ✅ Sub-project B（HTML 5 点）→ Task 4
- ✅ Sub-project C（路径）→ Task 1
- ✅ 端到端验证 → Task 5
- ✅ spec §4 验收标准 → 各 task step 覆盖

**2. Placeholder scan:**
- 无 TBD / TODO / "implement later"
- 所有命令完整（带 cd 路径）
- 所有代码块完整
- Task 4 Step 5 用 `⚠️` 警告 subagent 需先 grep HTML 实际 API

**3. Type consistency:**
- `log_decision()` 函数签名跨 Task 2 定义 + Task 3 spec 引用 ✓
- stage 枚举值（"2"/"step_10_review"等）跨 spec + plan ✓
- 路径 `00_智剪/logs/<task_id>.jsonl` 跨 spec + plan + commands/ ✓
- HTML 5 点修改跨 plan + spec ✓
# 智剪工坊 v1.13 日志系统补完 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 v1.12 日志系统的 3 个隐藏漏洞（stage 字段冲突 / 用户找不到日志 / lib/ffmpeg 0% 覆盖），让 v1.11.1 建的日志协议**真正可用**。

**Architecture:** 5 个 task 按依赖顺序：(1) 装饰器 → (2) 18 文件应用 → (3) stage 字段统一（独立）→ (4) commands/ 脚本（独立）→ (5) SKILL.md 更新（依赖 4）→ (6) 端到端验证。

**Tech Stack:** Python 装饰器 / Markdown / Shell（python3 inline）

---

## 文件结构

**修改（21 个）：**
- `lib/common.py`（新增装饰器 ~30 行）
- `lib/ffmpeg/audio/channel.py`、`denoise.py`、`detect.py`、`effect.py`、`enhance.py`、`extract.py`、`measure.py`、`normalize.py`、`transform.py`、`utility.py`、`visualize.py`（11 个）
- `lib/ffmpeg/video/color.py`、`subtitle.py`、`timing.py`、`transform.py`、`transition.py`、`watermark.py`（7 个）
- `references/粗加工-执行契约.md`（6 处 stage 字段）
- `references/主流程-阶段编排.md`（2 处 stage 字段）
- `SKILL.md`（触发词 + Loading 触发器）

**新增（3 个）：**
- `commands/查看日志.sh`
- `commands/查看粗加工日志.sh`
- `commands/复盘.sh`

**不修改：**scripts/、references/ 其他文件、setup.*、verify.py、requirements*.txt

---

## Task 1: lib/common.py 新增 @log_ffmpeg_call 装饰器

**Files:**
- Modify: `lib/common.py`（在文件末尾追加）

**目的：** 提供装饰器函数，18 个 lib/ffmpeg 文件应用此装饰器即可自动日志。

- [ ] **Step 1: 读取 lib/common.py 末尾**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
tail -20 lib/common.py
```

预期：查看现有函数定义，找到末尾插入点。

- [ ] **Step 2: 检查现有 import**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
head -30 lib/common.py
```

预期：找到现有 import（如 `import json`, `import subprocess` 等），确认是否需要 `import functools`。

- [ ] **Step 3: 在 lib/common.py 末尾追加装饰器代码**

打开 `lib/common.py`，在文件**最末尾**追加：

```python

# === v1.13 日志装饰器 ===

import functools

def _truncate_args(args, max_len=200):
    """截断长参数（如视频路径）避免日志过长"""
    s = str(args)
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s


def log_ffmpeg_call(func):
    """装饰器：自动记录 ffmpeg 调用的输入/输出/错误

    用法：
        @log_ffmpeg_call
        def extract_audio(input_path, output_path, fmt="wav"):
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        args_repr = _truncate_args(args)
        log_info(f"[{func.__module__}.{func.__name__}] 调用: args={args_repr}")
        try:
            result = func(*args, **kwargs)
            log_info(f"[{func.__module__}.{func.__name__}] 完成: result_type={type(result).__name__}")
            return result
        except FFmpegError as e:
            log_error(f"[{func.__module__}.{func.__name__}] FFmpegError: {e}")
            raise
        except Exception as e:
            log_error(f"[{func.__module__}.{func.__name__}] 异常: {type(e).__name__}: {e}")
            raise
    return wrapper
```

⚠️ **注意**：
- `import functools` 行如果已存在，删掉这一行（不重复 import）
- 装饰器必须在 `log_info` / `log_error` / `FFmpegError` 定义**之后**
- 如果这些函数在文件中部，装饰器放到文件末尾即可（Python 解释时按调用顺序）

- [ ] **Step 4: 验证装饰器存在**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -n "def log_ffmpeg_call\|def _truncate_args" lib/common.py
```

预期：找到两行函数定义

- [ ] **Step 5: 验证 import 唯一**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -c "^import functools" lib/common.py
```

预期：1（不重复 import）

- [ ] **Step 6: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add lib/common.py
git commit -m "feat(v1.13): lib/common.py 新增 @log_ffmpeg_call 装饰器"
```

---

## Task 2: 给 18 个 lib/ffmpeg 文件应用装饰器

**Files:**
- Modify: 18 个 `lib/ffmpeg/**/*.py` 文件

**目的：** 每个 lib/ffmpeg 公开函数前加 `@log_ffmpeg_call`，自动记录调用。

⚠️ **重要**：每个文件的装饰器 import 行可能需要单独添加。

- [ ] **Step 1: 列出所有 lib/ffmpeg 文件**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
find lib/ffmpeg -name "*.py" -not -name "__init__.py" | sort
```

预期：18 个文件

- [ ] **Step 2: 处理 lib/ffmpeg/audio/ 11 个文件**

对每个文件执行以下操作：

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
for f in lib/ffmpeg/audio/channel.py lib/ffmpeg/audio/denoise.py lib/ffmpeg/audio/detect.py lib/ffmpeg/audio/effect.py lib/ffmpeg/audio/enhance.py lib/ffmpeg/audio/extract.py lib/ffmpeg/audio/measure.py lib/ffmpeg/audio/normalize.py lib/ffmpeg/audio/transform.py lib/ffmpeg/audio/utility.py lib/ffmpeg/audio/visualize.py; do
    echo "Processing: $f"
    # 检查并添加 import（如果还没有）
    if ! grep -q "from common import.*log_ffmpeg_call\|from common import.*log_ffmpeg_call\|from lib.common import" "$f"; then
        # 添加 import 到现有 import 行
        # 假设文件中已有 from common import XXX
        sed -i '/^from common import/a\from common import log_ffmpeg_call' "$f" || echo "WARN: $f 需要手动加 import"
    fi
done
```

⚠️ 如果某些文件用了 `from lib.common import` 路径，需要调整 sed 命令。

- [ ] **Step 3: 检查 lib/ffmpeg/audio/ 的 import 状态**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
for f in lib/ffmpeg/audio/*.py; do
    if [ -f "$f" ] && [ "$(basename $f)" != "__init__.py" ]; then
        if grep -q "log_ffmpeg_call" "$f"; then
            echo "✓ $f: 装饰器已导入"
        else
            echo "✗ $f: 装饰器未导入"
        fi
    fi
done
```

预期：所有 11 个文件都是 ✓

- [ ] **Step 4: 处理 lib/ffmpeg/video/ 7 个文件**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
for f in lib/ffmpeg/video/color.py lib/ffmpeg/video/subtitle.py lib/ffmpeg/video/timing.py lib/ffmpeg/video/transform.py lib/ffmpeg/video/transition.py lib/ffmpeg/video/watermark.py; do
    echo "Processing: $f"
    if ! grep -q "log_ffmpeg_call" "$f"; then
        sed -i '/^from common import/a\from common import log_ffmpeg_call' "$f" || echo "WARN: $f 需要手动加 import"
    fi
done
```

- [ ] **Step 5: 检查 lib/ffmpeg/video/ 的 import 状态**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
for f in lib/ffmpeg/video/*.py; do
    if [ -f "$f" ] && [ "$(basename $f)" != "__init__.py" ]; then
        if grep -q "log_ffmpeg_call" "$f"; then
            echo "✓ $f: 装饰器已导入"
        else
            echo "✗ $f: 装饰器未导入"
        fi
    fi
done
```

预期：所有 7 个文件都是 ✓

- [ ] **Step 6: 给所有公开函数前加 @log_ffmpeg_call**

对每个文件执行：

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
for f in lib/ffmpeg/audio/*.py lib/ffmpeg/video/*.py; do
    if [ -f "$f" ] && [ "$(basename $f)" != "__init__.py" ]; then
        # 找到所有 `def <公开函数>` 行（不在 class 内的），在前面加装饰器
        # 简化版：用 python 脚本
        python3 -c "
import re
with open('$f', 'r', encoding='utf-8') as fp:
    lines = fp.readlines()
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # 匹配顶层 def（不是 class 内）
    if re.match(r'^def [a-zA-Z_]', line):
        # 检查前一行是否已是装饰器
        if not (new_lines and new_lines[-1].strip().startswith('@')):
            # 检查前一行是否是装饰器或其他装饰器
            prev_lines = [l.strip() for l in new_lines[-3:] if l.strip()]
            if not any('@' in pl for pl in prev_lines):
                indent = '    ' if line.startswith('def ') else ''
                new_lines.append(f'{indent}@log_ffmpeg_call\n')
    new_lines.append(line)
    i += 1
with open('$f', 'w', encoding='utf-8') as fp:
    fp.writelines(new_lines)
" 2>&1 || echo "WARN: $f 装饰器添加失败"
    done
```

⚠️ 上述 Python 脚本有简化：实际公开函数识别需人工 verify。

- [ ] **Step 7: 验证装饰器应用数**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
echo "=== 总装饰器应用数 ==="
grep -c "@log_ffmpeg_call" lib/ffmpeg/audio/*.py lib/ffmpeg/video/*.py | grep -v ":0$" | wc -l
echo ""
echo "=== 各文件装饰器数 ==="
for f in lib/ffmpeg/audio/*.py lib/ffmpeg/video/*.py; do
    count=$(grep -c "@log_ffmpeg_call" "$f")
    if [ "$count" -gt 0 ]; then
        echo "  $f: $count"
    fi
done
```

预期：总装饰器数 ≥ 18，每个有装饰器的文件至少 1 个

- [ ] **Step 8: 测试装饰器生效（快速 sanity test）**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
python3 -c "
import sys
sys.path.insert(0, 'lib')
from common import log_ffmpeg_call, log_info

@log_ffmpeg_call
def test_func(x):
    return x * 2

# 应该看到两行日志：调用 + 完成
result = test_func(21)
assert result == 42
print('OK: 装饰器生效')
" 2>&1
```

预期：输出包含 "[lib.common.test_func] 调用: args=(21,)" 和 "[lib.common.test_func] 完成: result_type=int"，以及 "OK: 装饰器生效"

- [ ] **Step 9: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add lib/ffmpeg/
git commit -m "feat(v1.13): 给 18 个 lib/ffmpeg 文件应用 @log_ffmpeg_call 装饰器"
```

---

## Task 3: 统一 references/ 中 stage 字段值（中文 → 数字）

**Files:**
- Modify: `references/粗加工-执行契约.md`（6 处）
- Modify: `references/主流程-阶段编排.md`（2 处）

**目的：** 8 处违反 AI行为日志协议 §3 的 stage 字段值统一改为数字（"2" 或 "1"）。

- [ ] **Step 1: 找出所有 stage=粗加工/stage=意图对齐 的位置**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -rn "stage=粗加工\|stage=意图对齐" references/
```

预期：列出 8 处位置（粗加工-执行契约 ~6 处 + 主流程-阶段编排 ~2 处）

- [ ] **Step 2: 批量替换 references/粗加工-执行契约.md 的 6 处**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
sed -i 's/stage=粗加工/stage="2"/g' references/粗加工-执行契约.md
```

预期：6 处全部从 `stage=粗加工` 改为 `stage="2"`

- [ ] **Step 3: 验证粗加工-执行契约.md 替换完成**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
echo "旧值残留（应=0）:"
grep -c "stage=粗加工" references/粗加工-执行契约.md
echo ""
echo "新值出现次数（应=6）:"
grep -c 'stage="2"' references/粗加工-执行契约.md
```

预期：旧值=0，新值=6

- [ ] **Step 4: 批量替换 references/主流程-阶段编排.md 的 2 处**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
sed -i 's/stage=粗加工/stage="2"/g; s/stage=意图对齐/stage="1"/g' references/主流程-阶段编排.md
```

预期：1 处 `stage=粗加工` → `stage="2"`，1 处 `stage=意图对齐` → `stage="1"`

- [ ] **Step 5: 验证主流程-阶段编排.md 替换完成**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
echo "旧值残留（应=0）:"
grep -c "stage=粗加工\|stage=意图对齐" references/主流程-阶段编排.md
echo ""
echo '新 stage="2" 出现次数（应=1）:'
grep -c 'stage="2"' references/主流程-阶段编排.md
echo '新 stage="1" 出现次数（应=1）:'
grep -c 'stage="1"' references/主流程-阶段编排.md
```

预期：旧值=0，新值 stage="2"=1, stage="1"=1

- [ ] **Step 6: 全 references/ 扫描残留**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
echo "全 references/ 中 stage=粗加工/stage=意图对齐 残留（应=0）:"
grep -rn "stage=粗加工\|stage=意图对齐" references/
```

预期：无输出

- [ ] **Step 7: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add references/粗加工-执行契约.md references/主流程-阶段编排.md
git commit -m "fix(v1.13): 统一 references/ stage 字段（中文 → 数字）"
```

---

## Task 4: 创建 commands/ 目录 + 3 个 shell 脚本

**Files:**
- Create: `commands/查看日志.sh`
- Create: `commands/查看粗加工日志.sh`
- Create: `commands/复盘.sh`

**目的：** 用户 1 秒查看日志，不依赖 AI 解析。

- [ ] **Step 1: 创建 commands/ 目录**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
mkdir -p commands
ls -la commands/
```

预期：空目录创建

- [ ] **Step 2: 创建 commands/查看日志.sh**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
cat > commands/查看日志.sh << 'SHEOF'
#!/bin/bash
# 列出当前任务的所有日志 + 统计
# 用法：bash 查看日志.sh

set -e
cd "$(dirname "$0")/.."

LOG_DIR="00_智剪/中间产物/logs"

if [ ! -d "$LOG_DIR" ]; then
    echo "❌ 日志目录不存在：$LOG_DIR"
    echo "可能原因：1) AI 还没开始任务  2) 路径不对"
    exit 1
fi

echo "=== 日志文件列表（按时间倒序）==="
ls -lt "$LOG_DIR" 2>/dev/null | head -20

LATEST_JSONL=$(ls -t "$LOG_DIR"/*.jsonl 2>/dev/null | head -1)

if [ -z "$LATEST_JSONL" ]; then
    echo ""
    echo "（暂无 JSONL 日志）"
    exit 0
fi

echo ""
echo "=== 最新 JSONL: $(basename $LATEST_JSONL) ==="
echo "  行数: $(wc -l < "$LATEST_JSONL")"

echo ""
echo "=== 按 stage 统计 ==="
python3 -c "
import json, collections
with open('$LATEST_JSONL', encoding='utf-8') as f:
    counter = collections.Counter()
    errors = 0
    for line in f:
        if line.strip():
            try:
                obj = json.loads(line)
                counter[obj.get('stage', '?')] += 1
                if obj.get('error'):
                    errors += 1
            except: pass
print(f'  错误 entry: {errors}')
for stage, count in sorted(counter.items()):
    print(f'  {stage}: {count} entries')
"

echo ""
echo "=== 最近 5 条决策 ==="
tail -5 "$LATEST_JSONL" | python3 -c "
import sys, json
for line in sys.stdin:
    if line.strip():
        try:
            obj = json.loads(line)
            t = obj.get('time', '?')[:16]
            print(f'  [{t}] stage={obj.get(\"stage\")} action={obj.get(\"action\")} decision={obj.get(\"decision\", \"\")[:60]}')
        except: pass
"
SHEOF
chmod +x commands/查看日志.sh
ls -la commands/查看日志.sh
```

预期：脚本创建 + 可执行

- [ ] **Step 3: 创建 commands/查看粗加工日志.sh**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
cat > commands/查看粗加工日志.sh << 'SHEOF'
#!/bin/bash
# 显示所有 stage="2"（粗加工）的 entry
# 用法：bash 查看粗加工日志.sh

set -e
cd "$(dirname "$0")/.."

LATEST=$(ls -t 00_智剪/中间产物/logs/*.jsonl 2>/dev/null | head -1)

if [ -z "$LATEST" ]; then
    echo "❌ 无日志"
    exit 1
fi

echo "=== 粗加工（stage=2）entries from $(basename $LATEST) ==="
grep '"stage": "2"' "$LATEST" | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        obj = json.loads(line)
        t = obj.get('time', '?')[:19]
        print(f'  [{t}] step={obj.get(\"step\")} action={obj.get(\"action\")} decision={obj.get(\"decision\", \"\")[:50]}')
    except: pass
"
SHEOF
chmod +x commands/查看粗加工日志.sh
ls -la commands/查看粗加工日志.sh
```

预期：脚本创建 + 可执行

- [ ] **Step 4: 创建 commands/复盘.sh**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
cat > commands/复盘.sh << 'SHEOF'
#!/bin/bash
# 完整复盘：人类可读 .md + 关键 .jsonl 决策
# 用法：bash 复盘.sh

set -e
cd "$(dirname "$0")/.."

LOG_DIR="00_智剪/中间产物/logs"

LATEST_MD=$(ls -t "$LOG_DIR"/*.md 2>/dev/null | head -1)
LATEST_JSONL=$(ls -t "$LOG_DIR"/*.jsonl 2>/dev/null | head -1)

if [ -z "$LATEST_MD" ]; then
    echo "❌ 无 .md 日志"
    exit 1
fi

echo "=== 人类可读 (.md) ==="
cat "$LATEST_MD"

if [ -n "$LATEST_JSONL" ]; then
    echo ""
    echo "=== 关键 JSONL 决策 ==="
    grep '"action": "review"\|"action": "yaml_stage_complete"\|"error"' "$LATEST_JSONL" | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        obj = json.loads(line)
        t = obj.get('time', '?')[:19]
        err = obj.get('error') or '-'
        print(f'  [{t}] action={obj.get(\"action\")} decision={obj.get(\"decision\", \"\")[:60]} error={err}')
    except: pass
"
fi
SHEOF
chmod +x commands/复盘.sh
ls -la commands/复盘.sh
```

预期：脚本创建 + 可执行

- [ ] **Step 5: 验证 3 个脚本都存在且可执行**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
ls -la commands/*.sh
```

预期：3 个文件，每个 `-rwxr-xr-x`

- [ ] **Step 6: 测试 查看日志.sh（无日志时优雅退出）**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
bash commands/查看日志.sh 2>&1 | head -10
```

预期：输出 "❌ 日志目录不存在" 或 "（暂无 JSONL 日志）"，不报错退出

- [ ] **Step 7: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add commands/
git commit -m "feat(v1.13): commands/ 目录新增 3 个查看日志 shell 脚本"
```

---

## Task 5: 更新 SKILL.md（触发词 + Loading 触发器）

**Files:**
- Modify: `SKILL.md`

**目的：** 用户说"查看日志"时 AI 能识别触发，并加载新脚本。

- [ ] **Step 1: 定位 SKILL.md YAML 触发词位置**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -n "triggers:\|^  # ===\|改帧率" SKILL.md | tail -20
```

预期：找到 `triggers:` 起始行 + `改帧率` 末尾行

- [ ] **Step 2: 在 YAML 触发词末尾追加 8 个新触发词**

打开 `SKILL.md`，找到 `# === 视频底层 lib 触发词（v1.6）===` 章节末尾（在 `改帧率` 行**之后**），追加：

```yaml
  # === v1.13 日志查询（新增）===
  - 查看日志
  - 日志在哪
  - 查看 process
  - 日志查询
  - 我刚才的操作
  - 复盘
  - audit
  - log
```

- [ ] **Step 3: 验证 YAML 触发词包含 8 个新词**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
echo "新触发词命中数（应=8）:"
grep -cE "^  - (查看日志|日志在哪|查看 process|日志查询|我刚才的操作|复盘|audit|log)$" SKILL.md
```

预期：8

- [ ] **Step 4: 定位 Loading 触发器位置**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -n "AI 遇到 muted video 拼接异常" SKILL.md
```

预期：找到 Loading 触发器末尾位置

- [ ] **Step 5: 在 Loading 触发器末尾追加 1 行**

找到行为协议触发表格中 `| AI 遇到 muted video 拼接异常 | ... |` 行，在它**之后**追加：

```markdown
| **用户说"查看日志/复盘/audit"** | `commands/查看日志.sh`（shell 优先）+ `AI行为日志协议.md` |
```

- [ ] **Step 6: 验证 Loading 触发器新增**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -c "查看日志/复盘/audit" SKILL.md
```

预期：≥ 1

- [ ] **Step 7: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add SKILL.md
git commit -m "feat(v1.13): SKILL.md 新增 8 个日志查询触发词 + Loading 触发器"
```

---

## Task 6: 端到端验证

**Files:**
- Verify: 全部修改/新增文件

**目的：** 确认 spec §4 验收标准全部满足。

- [ ] **Step 1: 验证 stage 字段统一（spec §4.1）**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep "stage=粗加工\|stage=意图对齐" references/*.md
```

预期：无输出

- [ ] **Step 2: 验证 commands/ 脚本存在且可执行（spec §4.2）**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
ls -la commands/*.sh
```

预期：3 个文件 `-rwxr-xr-x`

- [ ] **Step 3: 验证 commands/查看日志.sh 输出 JSONL 统计（spec §4.3）**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
bash commands/查看日志.sh 2>&1 | head -20
```

预期：执行无报错（即使无日志也优雅退出）

- [ ] **Step 4: 验证 SKILL.md 触发词（spec §4.4）**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -cE "^  - (查看日志|日志在哪|查看 process|日志查询|我刚才的操作|复盘|audit|log)$" SKILL.md
```

预期：8

- [ ] **Step 5: 验证装饰器存在（spec §4.5）**

```bash
cd "D:/Study/StudyNotes/SKILLS/智剪工坊"
grep "def log_ffmpeg_call" lib/common.py
```

预期：找到函数定义

- [ ] **Step 6: 验证 18 个 lib/ffmpeg 文件都应用装饰器（spec §4.6）**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
total_files=$(find lib/ffmpeg -name "*.py" -not -name "__init__.py" | wc -l)
decorated_files=$(grep -l "log_ffmpeg_call" lib/ffmpeg/audio/*.py lib/ffmpeg/video/*.py 2>/dev/null | wc -l)
echo "lib/ffmpeg 总文件: $total_files"
echo "已应用装饰器: $decorated_files"
```

预期：18 / 18

- [ ] **Step 7: 验证装饰器生效（spec §4.7）**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
python3 -c "
import sys
sys.path.insert(0, 'lib')
from common import log_ffmpeg_call

@log_ffmpeg_call
def sanity_test(x):
    return x * 2

result = sanity_test(21)
assert result == 42
print('OK')
"
```

预期：输出 "OK"，且 stderr 有装饰器日志

- [ ] **Step 8: 最终 git log**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git log --oneline -8
```

预期：6 个新 commit 对应 6 个 task

---

## Self-Review

**1. Spec coverage:**
- ✅ §3 问题 1 stage 字段冲突 → Task 3
- ✅ §3 问题 2 触发词 + 脚本 → Task 4 + Task 5
- ✅ §3 问题 3 装饰器 → Task 1 + Task 2
- ✅ §4 验收标准 7 项 → Task 6 全部覆盖
- ✅ §7 实施顺序 5 步 → 6 个 task 完整对应

**2. Placeholder scan:**
- 无 TBD / TODO / "implement later"
- 所有命令完整（带 cd 路径）
- 所有代码块完整（无占位）

**3. Type consistency:**
- 装饰器函数名 `log_ffmpeg_call`（Task 1 定义，Task 2 使用）✓
- stage 字段值：`"0"`/`"1"`/`"2"`/新 stage 名（Task 3 统一）✓
- 脚本路径：`commands/查看日志.sh` 等（Task 4 创建，Task 5 引用）✓
- 触发词："查看日志" 等（Task 5 定义，Task 5 引用）✓
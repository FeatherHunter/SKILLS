# 智剪工坊 v1.13 日志系统补完 Design（v1.12 修复的隐藏漏洞）

> **状态**：v1.12 修复完主流程 references/ 的日志集成，但对抗式审计发现 3 个**隐藏漏洞**未修：
> 1. stage 字段冲突（8 处违反协议）
> 2. 用户找不到日志（无触发词 + 无脚本）
> 3. lib/ffmpeg 0% 日志覆盖（18 个底层模块）

**目标**：补齐这 3 个漏洞，让 v1.12 的日志协议**真正可用**。

**架构**：单 spec 涵盖 3 个独立子系统（stage 字段统一 + 用户接口 + 底层覆盖），按依赖顺序：先 1（契约）→ 2（接口）→ 3（实现）。

**Tech Stack**：Markdown / Shell / Python 装饰器

---

## 1. 背景与动机

### v1.11.1 建的日志系统
- AI 行为日志协议 §3 定义 JSONL schema（8 个字段）
- §6 定义路径：`<workspace>/00_智剪/中间产物/logs/<task_id>_<timestamp>.jsonl`
- §3 定义 stage 枚举（含 v1.12 新增的 step_10_review / refine / step_12_review / finalize / reuse_backup / reuse_apply）

### v1.12 修复的局限
v1.12 修复让主流程 4 个聚焦文件（粗加工-执行契约 / 精加工-两路径 / 审查-用户交互循环 / 二次加工-复用工作流）**声明了日志要求**。但：

- ❌ 实际 stage 字段值违反协议（8 处）
- ❌ 用户找不到日志（无触发词、无脚本）
- ❌ 18 个 lib/ffmpeg 文件无日志调用

### 对抗式审计发现（v1.12 修复后）
详见 `docs/superpowers/plans/2026-07-10-zhijiangongfang-v1.12-fixes.md` Self-Review + Task 8 验证。

---

## 2. 设计：3 个独立修复

### 问题 1：stage 字段冲突（🔴 P0）

**当前状态**：
- `AI行为日志协议.md` §3 定义 `stage="2"`（数字）或新 stage 名
- 其他 8 处 references 用 `stage=粗加工`（中文）
- 后果：审计脚本按协议 grep `"stage": "2"` 搜不到任何记录

**修复方案**：全改为**数字**（理由：JSONL 是机器消费，数字最稳定）

**权威 stage 枚举**（唯一真理源，AI行为日志协议.md §3）：
```python
stage = "0" | "1" | "2" | "3" | "4" | "5"  # 老阶段
       | "step_10_review" | "refine" | "step_12_review" | "finalize"
       | "reuse_backup" | "reuse_apply"
```

**修改文件 + 行数**：
- `references/粗加工-执行契约.md`：6 处 `stage=粗加工` → `stage="2"`
- `references/主流程-阶段编排.md`：
  - 1 处 `stage=粗加工` → `stage="2"`
  - 1 处 `stage=意图对齐` → `stage="1"`

**验收**：
```bash
grep "stage=粗加工\|stage=意图对齐" references/*.md
# 输出应为 0
```

---

### 问题 2：触发词 + 查看日志脚本（🟠 P1）

**当前状态**：
- 用户问"日志在哪"AI 不知道怎么处理（无触发词）
- 即使 AI 知道路径，shell 跑 1 秒 vs AI 跑 5 秒

**修复方案**：3 个 shell 脚本 + SKILL.md 触发词 + Loading 触发器

#### 新增 `commands/` 目录 + 3 个 shell 脚本

**`智剪工坊/commands/查看日志.sh`**：

```bash
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
echo "  大小: $(wc -l < "$LATEST_JSONL") 行"
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
            print(f'  [{obj.get(\"time\", \"?\")[:16]}] stage={obj.get(\"stage\")} action={obj.get(\"action\")} decision={obj.get(\"decision\", \"\")[:60]}')
        except: pass
"
```

**`智剪工坊/commands/查看粗加工日志.sh`**：

```bash
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
        print(f'  [{obj.get(\"time\", \"?\")[:19]}] step={obj.get(\"step\")} action={obj.get(\"action\")} decision={obj.get(\"decision\", \"\")[:50]}')
    except: pass
"
```

**`智剪工坊/commands/复盘.sh`**：

```bash
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
        print(f'  [{obj.get(\"time\", \"?\")[:19]}] action={obj.get(\"action\")} decision={obj.get(\"decision\", \"\")[:60]} error={obj.get(\"error\") or \"-\"}')
    except: pass
"
fi
```

**SKILL.md 触发词新增**（在 v1.12 YAML 末尾追加）：

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

**SKILL.md Loading 触发器新增**：

```markdown
| **用户说"查看日志/复盘/audit"** | `commands/查看日志.sh`（shell 优先）+ `AI行为日志协议.md` |
```

---

### 问题 3：lib/ffmpeg 0% 覆盖（🟠 P1）

**当前状态**：
- 18 个 lib/ffmpeg/*.py 文件**完全不调用 log_info/log_error**
- 后果：底层 ffmpeg 失败时无诊断

**修复方案**：装饰器模式（DRY，0 遗漏）

**`lib/common.py` 新增装饰器**：

```python
import functools

def log_ffmpeg_call(func):
    """装饰器：自动记录 ffmpeg 调用的输入/输出/错误
    
    用法：
        @log_ffmpeg_call
        def extract_audio(input_path, output_path, fmt="wav"):
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 截断长路径避免日志过长
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

def _truncate_args(args, max_len=200):
    """截断长参数（如视频路径）避免日志过长"""
    s = str(args)
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s
```

**应用范围**：18 个 lib/ffmpeg/*.py 文件中的**所有公开函数**

**修改清单**（每个函数前加 1 行 `@log_ffmpeg_call`）：
- `lib/ffmpeg/audio/channel.py`
- `lib/ffmpeg/audio/denoise.py`
- `lib/ffmpeg/audio/detect.py`
- `lib/ffmpeg/audio/effect.py`
- `lib/ffmpeg/audio/enhance.py`
- `lib/ffmpeg/audio/extract.py`
- `lib/ffmpeg/audio/measure.py`
- `lib/ffmpeg/audio/normalize.py`
- `lib/ffmpeg/audio/transform.py`
- `lib/ffmpeg/audio/utility.py`
- `lib/ffmpeg/audio/visualize.py`
- `lib/ffmpeg/video/color.py`
- `lib/ffmpeg/video/subtitle.py`
- `lib/ffmpeg/video/timing.py`
- `lib/ffmpeg/video/transform.py`
- `lib/ffmpeg/video/transition.py`
- `lib/ffmpeg/video/watermark.py`

**示例效果**（以 `extract_audio` 为例）：

```python
# 修改前：
def extract_audio(input_path, output_path, fmt="wav"):
    ...

# 修改后：
@log_ffmpeg_call
def extract_audio(input_path, output_path, fmt="wav"):
    ...
```

调用 `extract_audio(...)` 时**自动输出**：
```
[lib.ffmpeg.audio.extract.extract_audio] 调用: args=('D:\\video.mp4', 'D:\\audio.wav', 'wav')
[lib.ffmpeg.audio.extract.extract_audio] 完成: result_type=tuple
```

调用失败时：
```
[lib.ffmpeg.audio.extract.extract_audio] 调用: args=('D:\\bad.mp4', 'D:\\out.wav', 'wav')
[lib.ffmpeg.audio.extract.extract_audio] FFmpegError: ffmpeg 返回非 0 exit code
```

---

## 3. 文件变更清单

**修改（10 个）**：
1. `references/AI行为日志协议.md`（可能需要追加装饰器引用）
2. `references/粗加工-执行契约.md`（6 处 stage 字段）
3. `references/主流程-阶段编排.md`（2 处 stage 字段）
4. `references/AI行为日志协议.md`（1 处 stage 字段如果有）
5. `lib/common.py`（新增装饰器函数 ~30 行）
6-23. 18 个 `lib/ffmpeg/**/*.py`（每个函数前加 `@log_ffmpeg_call`）
24. `SKILL.md`（触发词 +1 section，Loading 触发器 +1 行）

**新增（3 个）**：
- `commands/查看日志.sh`
- `commands/查看粗加工日志.sh`
- `commands/复盘.sh`

**不修改**：scripts/、references/ 其他文件、setup.*、verify.py、requirements*.txt

---

## 4. 验收标准

1. ✅ `grep "stage=粗加工\|stage=意图对齐" references/*.md` 输出 0
2. ✅ `commands/` 目录下 3 个 .sh 文件存在且可执行
3. ✅ `bash commands/查看日志.sh` 输出 JSONL 统计
4. ✅ `SKILL.md` 触发词包含 8 个新词（日志查询类）
5. ✅ `lib/common.py` 包含 `@log_ffmpeg_call` 装饰器
6. ✅ 18 个 lib/ffmpeg 文件的所有公开函数都加 `@log_ffmpeg_call`
7. ✅ 调用任意 ffmpeg 函数时输出日志（验证装饰器生效）

---

## 5. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 装饰器破坏现有逻辑 | 函数包装透明（functools.wraps 保留元数据），不修改函数行为 |
| 18 个文件手动改遗漏 | 装饰器一次写好，每个文件机械应用 1 行/函数 |
| stage 改后历史 JSONL 不匹配 | 新任务用新值，旧任务日志不影响（grep 加 task_id 过滤） |
| 触发词与其他 skill 冲突 | 限定为"日志查询"语义，不影响其他领域 |
| shell 脚本 Windows 兼容性 | 使用 `python3` 调用（已安装），`set -e` 保证错误退出 |

---

## 6. 不在本次范围（YAGNI）

- ❌ 日志查询的 Web UI（用 shell 已够）
- ❌ 日志压缩/归档机制（目前文件小，无压力）
- ❌ 实时日志流（v1.13 不做实时监控）
- ❌ AI 日志写入的强制机制（依赖 AI 自己写）
- ❌ lib/common.py 装饰器之外的日志工具（如计数器、性能监控）

---

## 7. 实施顺序（依赖关系）

```
1. lib/common.py 新增装饰器（先）
   ↓
2. 18 个 lib/ffmpeg 文件应用装饰器（依赖 1）
   ↓
3. references/ 改 stage 字段（独立）
   ↓
4. commands/ 创建 3 个脚本（独立）
   ↓
5. SKILL.md 触发词 + Loading 触发器更新（依赖 4）
```

---

## 8. 版本影响

- v1.13 增量
- 与 v1.12 完全兼容（v1.12 的协议 + 文档保持有效）
- 变更仅在以下层：
  - 协议字段值（stage 中文 → 数字）
  - 新增 commands/ 目录
  - lib/ffmpeg 装饰器

---

## 9. 验证清单

```bash
# 1. stage 字段统一
grep "stage=粗加工\|stage=意图对齐" references/*.md
# 预期: 无输出

# 2. 装饰器存在
grep "def log_ffmpeg_call" lib/common.py
# 预期: 找到定义

# 3. 18 个文件应用装饰器
for f in lib/ffmpeg/audio/*.py lib/ffmpeg/video/*.py; do
    echo -n "$f: "
    grep -c "@log_ffmpeg_call" "$f"
done
# 预期: 每个文件至少 1 行装饰器（但部分文件可能有多个公开函数）

# 4. shell 脚本存在且可执行
ls -la commands/*.sh
# 预期: 3 个文件，-rwxr-xr-x

# 5. 触发词新增
grep -c "查看日志\|复盘\|audit" SKILL.md
# 预期: ≥ 3（triggers YAML + Loading 触发器）
```

---

## 10. 时间估算

- Task 1 (stage 字段): 15 min
- Task 2 (装饰器 + 18 文件): 1h
- Task 3 (commands/ 脚本): 30 min
- Task 4 (SKILL.md 触发词): 10 min
- 验证: 15 min

**总计**: 2-2.5 小时
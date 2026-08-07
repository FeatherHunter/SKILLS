# R2 开源清仓处置清单（#191 · Q5/Q6/Q7/Q14 落清单）

> 状态：**规格清单已定稿**（本文件），实施阶段按此清单逐项执行。
> 决策来源：Q5 开源清仓全部处理 · Q6 路径统一链 `SKILLS_DB_PATH env → D:/.db(win) → ~/.local/share/schedule-guardian/db(linux)` · Q7 作息管家/ 独立 MIT 子 LICENSE · Q14 收敛为「底层 schedule_db.py + 中间层 schedule_cli.py」两层 · Q10 git 历史不清理、README 不提及历史。
> 本票红线：仅 `git add`/`git commit`，禁 push/rebase/reset/checkout/stash/amend/clean/add -A，不切分支，历史零改写。**下列 `git rm`/`git mv` 等操作属实施阶段执行**，本票只落清单。

---

## 1. 处置清单表

| # | 项（文件/路径/产物） | 处置方式 | 具体改动点（文件:行号） | 备注 |
|---|---|---|---|---|
| 1 | `作息管家/scripts/batch_add.py` | 收敛 → `schedule_cli.py batch-add` 子命令 | 整文件删；新逻辑见 §4 | 唯一批量导入入口；收敛后删除，Q14 两层 |
| 2 | `作息管家/scripts/direct_add.py` | 删 | 整文件删 | 与 batch_add 重复 ~85%；硬编码 `2026-05-30`（L16）与 `/tmp/records_0530_page1.json`（L17）一次性数据 |
| 3 | `作息管家/batch_add_morning.py` | 删 | 整文件删 | 8 月晨练一次性任务已完成（docstring L3-4 明示），走 `ensure-plan-event` 幂等 |
| 4 | `作息管家/scripts/schedule_db.py` | 改 | L13 docstring、L61-93 路径配置、L66-76 `_fallback_db_dir`、L78-89 `_find_db_path` | 路径统一链，见 §2 |
| 5 | `作息管家/scripts/schedule_html_render.py` | 改 | L375-378 `_html_base_dir()` | 硬编码 `'D:/.db'` → 复用 schedule_db 统一解析器，见 §2 |
| 6 | `作息管家/scripts/help_render.py` | 改 | L48-51 `get_html_base_dir()` | `SKILL_DIR/.db` 相对 fallback → 复用统一解析器，见 §2 |
| 7 | `作息管家/scripts/validators.py` | 改 | L22 `WHITELIST_PATH` → `Path(__file__).parent.parent / "category_whitelist.yaml"` | 白名单 YAML 迁出 `.db/`（配合 #8）；L12/L47 docstring 同步 |
| 8 | `作息管家/.db/category_whitelist.yaml` | 迁移（跟踪保留） | `git mv` → `作息管家/category_whitelist.yaml`；同步引用：`schedule_cli.py:2778`、`schedule_cli.py:2869`（两处改 `from validators import WHITELIST_PATH`）、`SKILL.md:181`、`references/分类心法.md:4` | 用户/AI 维护的配置，须随技能入库；迁出后 `.db/` 可整体忽略（#9） |
| 9 | `作息管家/.db/` 目录及派生产物 | 忽略整目录 | 根 `.gitignore`：L2-5（schedule.db/-shm/-wal/-journal 四条细则）+ L86（schedule_html/ 细则）合并为一条 `作息管家/.db/` | 旧 DB 位置，Q6 后运行时数据全在外部基目录；未跟踪产物（如 schedule_html/ 输出）无需处理 |
| 10 | `作息管家/plan.json`、`plan_clean.json`、`plan_nobom.json` | 删 | `git rm` 三文件 | 迁移/排障一次性产物；根 `.gitignore:45` 本已声明 `作息管家/plan_*.json` 忽略 → 规则与实际不符的漂移 |
| 11 | `作息管家/作息管家.html` | 取消跟踪 + 忽略 | `git rm --cached`（保留工作区文件，运行时自动重生成）；根 `.gitignore` 增 `作息管家/作息管家.html` | ADR-0001 稳定镜像，每次 help_render 覆盖写（`help_render.py:361-363`）→ 派生产物 |
| 12 | `作息管家/LICENSE` | 新增 | 新建文件，内容见 §3 | 独立 MIT 子 LICENSE（Q7） |
| 13 | `作息管家/.gitignore` | 改 | L12-13 注释掉的 `# 数据库文件…`/`# *.db` 删除（`.db/` 已在根 .gitignore 管） | 其余 `__pycache__/`/`.pytest_cache/`/`.env` 规则保留 |
| 14 | 文档绝对路径 5 处 | 改 | SKILL.md:778-779、CHANGELOG.md:828/1158、docs/agents/×3 | 见 §5 |
| 15 | `作息管家/scripts/migrate_categories.py` | 改 | L17-20 `STUDYNOTES_DIR`/`DB_PATH` 硬绑 → `from schedule_db import DB_PATH` | 一次性诊断工具保留；Q6 后同一库（`schedule_db.DB_PATH`），去掉 `SKILL_DIR.parent.parent` 依赖 |
| 16 | `作息管家/SKILL.md` | 改 | L265 陈旧 DB 查找链（「技能目录→父目录 .db/」）→ 对齐 Q6 链 | 见 §5 补充项 |

**实施阶段 git 操作汇总（按红线允许的命令）**：`git rm` #2/#3/#10、`git rm --cached` #11、`git mv` #8、`git add` #1(新 batch-add)/#12/LICENSE、`git add -f`（如 .scratch 工件需入库，见 §6 说明）、`git commit` 若干（全中文 + Tested-By）。

---

## 2. 路径统一链改造方案

统一链（Q6）：`SKILLS_DB_PATH 环境变量 > D:/.db(win32) > ~/.local/share/schedule-guardian/db(非 win32)`。
现状 3 套不一致逻辑 + 1 处相对路径，全部收敛到 **schedule_db.py 单一解析器**，其余模块 import 复用。

### 2.1 schedule_db.py（唯一权威解析器）

**改 `schedule_db.py:61-93`**，新逻辑：

```python
# ============ 路径配置（Q6 统一链：env > D:/.db(win) > ~/.local/share/schedule-guardian/db(linux)）============
SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "schedule_data.db"
DR_FILENAME = "daily_recorder.db"

def _fallback_db_dir() -> Path:
    """平台 fallback：Windows → D:/.db；其他平台 → ~/.local/share/schedule-guardian/db（Q6）"""
    if sys.platform == 'win32':
        return Path('D:/.db')
    return Path.home() / '.local' / 'share' / 'schedule-guardian' / 'db'

def get_db_base_dir() -> Path:
    """统一 DB 基目录（Q6 链）：SKILLS_DB_PATH 环境变量 > 平台 fallback。全技能共用入口。"""
    env_path = os.environ.get('SKILLS_DB_PATH')
    base = Path(env_path) if env_path else _fallback_db_dir()
    base.mkdir(parents=True, exist_ok=True)
    return base

DB_DIR = get_db_base_dir()      # 语义修正：不再指向 SKILL_DIR
DB_PATH = DB_DIR / DB_FILENAME
DR_DB_PATH = DB_DIR / DR_FILENAME
```

要点：
- **删除** `_find_db_path`（schedule_db.py:78-89），逻辑并入 `get_db_base_dir()`；原仅 L92-93 两处调用。
- **删除** WSL `/mnt/d` 探测与 RuntimeError 分支（L70-76）——Q6 后非 win32 一律走 `~/.local/share/schedule-guardian/db`。
- **改** L13 docstring：`路径两层查找：环境变量 SKILLS_DB_PATH > D:/.db（WSL 转 /mnt/d/.db/）` → `路径统一链：SKILLS_DB_PATH env > D:/.db(win) > ~/.local/share/schedule-guardian/db(linux)（Q6）`。
- `DB_DIR` 语义：L91 `DB_DIR = SKILL_DIR  # 兼容旧代码` 删除兼容注释，改为统一基目录；L103/L117 `DB_DIR.mkdir` 保留无害（基目录已存在）。

### 2.2 schedule_html_render.py（硬编码 D:/.db）

**改 `schedule_html_render.py:375-378`**：

```python
def _html_base_dir() -> Path:
    """延迟求值,避免模块加载时 DB 基目录还不存在导致 RECORD_DIR 永久冻结为空"""
    from schedule_db import get_db_base_dir
    return get_db_base_dir() / 'schedule_html'
```
（L377 `os.environ.get('SKILLS_DB_PATH') or 'D:/.db'` 删除；`import os` L333 如无他用一并删）

### 2.3 help_render.py（SKILL_DIR/.db 相对路径）

**改 `help_render.py:48-51`**：

```python
def get_html_base_dir() -> Path:
    """作息管家 HTML 输出基目录（同 schedule_html_render.py::_html_base_dir）"""
    from schedule_db import get_db_base_dir
    return get_db_base_dir() / 'schedule_html'
```
（`os` import L34 如无他用一并删；`from schedule_db import ...` 可用：直接 `python scripts/help_render.py` 时脚本目录在 sys.path[0]，被 schedule_cli import 时 schedule_cli.py:20 已插入 scripts 目录）

### 2.4 validators.py（白名单路径，配合 #8 迁移）

**改 `validators.py:22`**：
```python
WHITELIST_PATH = Path(__file__).parent.parent / "category_whitelist.yaml"
```
`schedule_cli.py:2778` 与 `:2869` 的重复表达式改为 `from validators import WHITELIST_PATH` 复用。

---

## 3. LICENSE 草案（作息管家/LICENSE）

与根 LICENSE 同源（根为 MIT，版权人 王辰浩，2026），全文：

```text
MIT License

Copyright (c) 2026 王辰浩

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

（与根 `LICENSE` 逐字一致，仅放置目录不同。）

---

## 4. batch-add CLI 子命令设计

### 4.1 命令签名

```bash
python scripts/schedule_cli.py batch-add <date> --json @records.json [--dry-run] [--stop-on-error]
```

- `<date>`：必填，目标日期，走 `_normalize_date` 归一（YYYY-MM-DD / YYYYMMDD / 斜杠 / 点）。
- `--json @file.json`：必填；records = JSON **数组**，每条为对象。`@` 前缀表示从文件读（对齐 `add` 的 `--json @file` 约定，schedule_cli.py:2946-2953）。
- `--dry-run`：只校验不写库（对齐 migrate_categories.py 的 dry-run 惯例）。
- `--stop-on-error`：遇错即停；默认逐条容错继续（对齐 batch_add.py:26-52 行为）。

### 4.2 校验复用（不重复实现，逐条委托）

| 校验 | 复用点 | 说明 |
|---|---|---|
| 必填字段 | `cmd_add_record` 的 field_map 校验（schedule_cli.py:2975-3008） | 9 字段缺一报错；`date` 缺省用命令行 `<date>`（`rec.get('date', date_str)`）；`source_timestamps`/`analysis_reasoning` 缺省填空串（对齐 batch_add.py:45-46） |
| category 白名单 | `add_record_full` 内部 `validators.validate_category`（schedule_db.py:378-382） | 不在 CLI 层重复校验，对齐 schedule_cli.py:3010-3011 注释 |
| 时间归一 | `schedule_db.normalize_time`（L24-32） | 新增：`24:00 → 23:59`（batch_add.py 原未处理，对齐 add 链路） |
| duration 计算 | 省略时按 batch_add.py:28-35 算法 | `(end-start) 分钟差，负值 +24*60`（跨日） |
| 写库 | `add_record_full(**kwargs)` | 与单条 add 完全同一入口 |

### 4.3 输出格式（对齐 CLI JSON 契约，stdout 纯净 JSON）

逐条进度写 **stderr**（`✓ [i] HH:MM-HH:MM activity` / `✗ ...`），stdout 单 JSON：

```json
{
  "status": "ok" | "partial" | "error",
  "data": {
    "date": "2026-08-01",
    "total": 12, "success": 11, "failed": 1,
    "ids": [101, 102, 103],
    "errors": [{"index": 5, "message": "写入失败: category 校验失败: ..."}]
  },
  "message": "✓ 批量写入完成: 成功 11/12 条(失败 1 条,见 data.errors)"
}
```

- `status`：全部成功 `ok`；部分失败 `partial`；全部失败 / 参数错 / JSON 解析错 `error`。
- 单条失败不抛异常打断，收集进 `data.errors`（batch_add.py 同款容错）。

### 4.4 注册

- `schedule_cli.py:657-658`（`elif cmd == "add"` 后）加 `elif cmd == "batch-add": cmd_batch_add(args)`。
- 新函数 `cmd_batch_add(args)` 置于 `cmd_add_record`（L2924）之后。
- `cmd_help()`（L3055 区）「基础」段 L3061 `add` 行后加：`batch-add <date> --json @records.json  批量写入作息记录(JSON 数组,逐条校验,对齐 add)`。
- **删除** `scripts/batch_add.py`（处置 #1）。
- 幂等性：**不提供**。作息记录无唯一键，重复执行会重复插入；批量导入场景为一次性 AI 分析结果写入（与 `ensure-plan-event` 的幂等语义不同，文档注明）。

---

## 5. 文档绝对路径清理点

票面「5 处」，核实后共 **7 行 / 5 文件**（docs/agents 实为 3 文件各 1 行），另有 2 处同性质新发现（§5.2）。

### 5.1 票面 5 处

| # | 位置 | 现状 | 改法 |
|---|---|---|---|
| 1 | `SKILL.md:778` | 示例 JSON `"file_path":"D:\\2Study\\StudyNotes\\.db\\schedule_html\\record\\2026-07-15_record_report.html"` | 泛化为 `$SKILLS_DB_PATH/schedule_html/record/<date>_record_report.html`（示例文案） |
| 2 | `SKILL.md:779` | `<media src="D:\\...\\2026-07-15_record_report.html" .../>` | 改为 `$SKILLS_DB_PATH/schedule_html/record/...` 占位示例 |
| 3 | `CHANGELOG.md:828` | 表行 `D:/Downloads`(跨平台 fallback) | 改 `$HOME/Downloads`（保留事实、去绝对路径） |
| 4 | `CHANGELOG.md:1158` | 参考 `D:\2Study\StudyNotes\SKILLS\html\review_5710525.html` | 内部审查报告开源后不存在 → 改相对 `html/review_5710525.html` 或整行删 |
| 5 | `docs/agents/domain.md:3` / `issue-tracker.md:5` / `triage-labels.md:3` | 各引用 `D:\2Study\StudyNotes\SKILLS\docs\agents\*.md` | 改仓库内相对路径 `` `docs/agents/xxx.md` ``（相对仓库根） |

### 5.2 同性质新增发现（核实过程发现，建议一并处理）

| # | 位置 | 现状 | 改法 |
|---|---|---|---|
| 6 | `SKILL.md:265` | 陈旧 DB 查找链「`SKILLS_DB_PATH` 环境变量 → 技能目录 → 父目录 `.db/` 文件夹 → 自动创建 `.db/` 目录」 | 对齐 Q6 链：`SKILLS_DB_PATH env → D:/.db(win) → ~/.local/share/schedule-guardian/db(linux)` |
| 7 | `references/CLI命令.md:310` | 错误示例含 `D:\\.db\\schedule_html\\record` | 泛化为 `$SKILLS_DB_PATH/schedule_html/record` |
| 8 | `SKILL.md:181` | 写到 `.db/category_whitelist.yaml` | 随 #8 改 `category_whitelist.yaml` |

---

## 6. 盘点外观察项（核实发现，票面未列入；仅供 PM 决策，不属本票处置范围）

1. **`作息管家/.notes/`（5 个跟踪文件）**：`_gen_scenarios.py`（docstring 自述「一次性脚本,生成后废弃」）、`fat-skill-optimize-2026-07-29.md`、`grilling-session.html`、`issues-summary.html`、`review-html-改造方案-2026-07-23.html` —— 内部过程/审查产物，开源建议整体 `git rm` + 忽略 `.notes/`。
2. **`作息管家/.out-of-scope/README.md`**：triage wontfix 记录机制说明（内部流程协议），开源时建议移出或隐藏。
3. **`作息管家/scripts/migrate_plan_to_events.py`**：一次性迁移工具（与 migrate_categories 同类）；建议与 #15 同批评估（保留走统一 DB 路径 / 删除）。
4. **仓库级已跟踪 `__pycache__`（作息管家范围外）**：`iflytek-ocr-to-en-word/ocr-skill/scripts/__pycache__/pdf_ocr.cpython-313.pyc`、`iflytek-ocr-to-en-word/scripts/__pycache__/ocr_translate.cpython-313.pyc`、`学习系统/scripts/__pycache__/progress_api.cpython-310.pyc` —— 根 `.gitignore:33` 已有 `__pycache__/` 规则，属「规则与实际不符」同类漂移；建议仓库级一次 `git rm -r --cached` 清理（作息管家自身 pycache 未跟踪、已忽略，无需处理）。
5. **Q10 落地现状**：`作息管家/README.md` **不存在**；SKILL.md 无历史提及 → 无需改动，仅须确保后续新增文档不写历史（不提及「历史未清理」）。

---

## 7. 本票红线执行记录

- 仅 `git add`（对忽略路径用 `-f`，先例：`.scratch/` 下已跟踪的 spec/ticket 工件，见根 `.gitignore:125-127` 选择性放行）+ `git commit`。
- 未 push / rebase / reset / checkout / stash / amend / clean / add -A；未切分支（当前 `main`）。
- git 历史零改写（Q10）；本票只新增本清单文件。
- commit 全中文标题 + `Tested-By:` 行末（ADR-0005 豁免）。

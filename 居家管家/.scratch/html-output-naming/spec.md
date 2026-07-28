# Spec: HTML 输出命名与路径规范化

**Status:** ready-for-agent
**Triage Label:** ready-for-agent
**Created:** 2026-07-28

## Problem Statement

作为居家管家 Skill 的使用者,我发现 Skill 生成的 HTML 输出文件名是英文(`search_results_20260728_091642.html`),与 SKILL开发总纲 §原则 12 规定的中文 `<command_cn>` 命名约定不一致;同时所有输出文件平铺在 Skill 自带的 `output/` 目录下,既没有跨 Skill 共享的根目录,也没有 `<skill 标识>_html/` 子目录,违反总纲 12.X 的路径形态规范。这使得:

- 文件名无法一眼看出"这是哪个 Skill 的哪种查询产出"(英文 template 名 `search_results` 对中文用户不直观)
- 多个 Skill 各自维护 `output/` 目录,无法在统一位置查阅所有 HTML 输出
- HELP HTML 和数据/过程 HTML 用同一命名逻辑,违反 12.A/12.B 分类(HELP 应该用 `<skill 中文名>_HELP_<datetime>.html`)

## Solution

让居家管家的 HTML 输出符合 SKILL开发总纲 §原则 12:

1. **路径根**:按 env 链解析 `$SKILLS_DATA_DIR` > `$SKILLS_DB_PATH` > Skill 自带 fallback,所有 HTML 输出统一在 `<根>/home_manager_html/` 子目录下
2. **12.A 数据/过程 HTML**:文件名形态 `<command_cn>_<YYYYMMDD>_<HHMMSS>.html`,中文前缀来自 render 层的 `template → command_cn` 静态映射表
3. **12.B HELP HTML**:文件名形态 `居家管家_HELP_<YYYYMMDD>_<HHMMSS>.html`,以 `_HELP_` 为保留字
4. **本地时间**:文件名时间戳用 `datetime.now()`(本地北京时间),显式偏离总纲 12.X 的 UTC 规定 —— 见 ADR-0001
5. **覆盖策略**:同名文件直接覆盖(无 `_N` 后缀),显式偏离总纲 12.X 的冲突不覆盖规则 —— 在 SKILL.md §📌 输出位置 章节声明
6. **显式 override**:`--output <path>` 仍可绕过自动命名,直接写指定路径
7. **SKILL.md 补全**:新增 §📌 输出位置 章节,标 12.A/12.B,记录偏离
8. **清空历史**:落地后清空 `output/` 下 107 个历史运行产物(保留根目录的 `居家管家.html` git 跟踪文件和 `.notes/` 开发文档)

## User Stories

1. 作为居家管家的使用者,我希望生成的 HTML 文件名用中文(`查物品_20260728_091642.html`),这样我一眼就能看出这是哪次查询的产出
2. 作为居家管家的使用者,我希望所有 Skill 的 HTML 输出集中在一个根目录下(而非每个 Skill 各自的 `output/`),这样我在一个地方就能查阅所有产出
3. 作为居家管家的使用者,我希望居家管家的 HTML 输出在独立的子目录 `home_manager_html/` 下,这样不同 Skill 的产出不会互相覆盖
4. 作为居家管家的使用者,我希望 HELP HTML 用 `居家管家_HELP_20260728_091642.html` 命名,这样我能用 `_HELP_` 保留字一眼识别这是 Skill 自我介绍页
5. 作为居家管家的使用者,我希望文件名时间戳和我钟表看到的时间一致(本地时间),这样我看到下午 5 点生成的文件名上就是 17:xx 而不是 09:xx
6. 作为居家管家的使用者,我希望同秒同名生成新文件时直接覆盖旧的,这样我不会被一堆 `_1` `_2` 后缀的旧版本文件淹没
7. 作为居家管家的使用者,我希望仍能用 `--output <path>` 显式指定输出路径,这样我能把临时产物写到 /tmp 或自定义位置
8. 作为居家管家的开发者,我希望 render 层维护一个 `template → command_cn` 静态映射表,这样调用者(CLI 子命令)无需感知命名规则,新增 template 时也只需改一个地方
9. 作为居家管家的开发者,我希望 SKILL.md 有 §📌 输出位置 章节标 12.A/12.B,这样未来读者能看到本 Skill 的命名约定和显式偏离
10. 作为居家管家的开发者,我希望路径解析逻辑兼容现有的 env 链(`SKILLS_DATA_DIR` > `SKILLS_DB_PATH` > fallback),这样数据库目录与 HTML 输出根同级,部署时只需设置一个 env var
11. 作为居家管家的开发者,我希望 `travel_trip.html` 用综合名 `出行清单` 作 command_cn,这样能涵盖 `带物品`(pack)和 `归物品`(return)两个唤醒词,无需拆 template
12. 作为居家管家的开发者,我希望 `delivery_check.html` 映射到 `查快递`,这样 `--status 快递中` 自动切到专用 template 时,文件名也跟着变,与 `查物品` 区分开
13. 作为居家管家的开发者,我希望落地前清空 `output/` 下的历史运行产物(107 个文件 ~110 MB),这样新规则生效后不会遗留旧命名风格的文件
14. 作为居家管家的开发者,我希望保留根目录的 `居家管家.html`(git 跟踪的 HELP mirror)和 `.notes/` 下的开发文档,这样 git 历史和审计报告不丢失
15. 作为居家管家的开发者,我希望测试通过 `render_page()` 函数这一个 seam 验证所有命名/路径/覆盖行为,这样测试不依赖 DB 也不依赖 CLI 入口,运行快且稳定
16. 作为居家管家的开发者,我希望新测试追加到现有 `tests/test_render.py` 同一 seam,这样所有 render 层测试集中在一处,易于维护
17. 作为居家管家的开发者,我希望 ADR-0001 记录"本地时间而非 UTC"的决策理由,这样未来读者看到文件名时间戳与总纲 12.X 不符时能找到原因
18. 作为居家管家的开发者,我希望 CONTEXT.md 定义 `command_cn` / `Skill 标识` / `出行清单` / `_HELP_ 保留字` / `12.A vs 12.B` 等领域术语,这样后续 spec 和 ticket 能引用统一词汇

## Implementation Decisions

### 模块改动

**render 层(`scripts/render/__init__.py`)** —— 唯一的实现层改动:

- `OUTPUT_DIR = SKILL_DIR / "output"` 改为按 env 链解析得到的路径,新增 `resolve_output_root()` 函数实现三层查找:`$SKILLS_DATA_DIR` > `$SKILLS_DB_PATH` > Skill 自带 fallback(沿用 `home_manager/db.py` 的 fallback 逻辑,Windows 落到 `D:\.db\`,WSL 落到 `/mnt/d/.db/`)
- `OUTPUT_DIR` 之下追加 `home_manager_html/` 子目录(对应 SKILL 标识,与 Python 包名一致)
- 新增 `TEMPLATE_TO_COMMAND_CN` 静态映射 dict,10 个 template 全部登记:

  ```
  search_results  → 查物品
  delivery_check  → 查快递
  add_preview     → 录物品
  item_detail     → 看物品
  list_overview   → 统物品
  inventory_check → 盘物品
  expiring_alert  → 查过期
  outfit_picker   → 穿什么
  travel_trip     → 出行清单
  help_center     → (特殊,走 12.B 路径)
  ```

- `render_page()` 的"未指定 output_path"分支改写:
  - 12.A 类(非 help_center):`<OUTPUT_ROOT>/home_manager_html/<command_cn>_<YYYYMMDD>_<HHMMSS>.html`
  - 12.B 类(help_center):`<OUTPUT_ROOT>/home_manager_html/居家管家_HELP_<YYYYMMDD>_<HHMMSS>.html`
  - 时间戳:`datetime.now().strftime("%Y%m%d_%H%M%S")`(本地时间,见 ADR-0001)
  - 冲突:直接 `write_text` 覆盖(无 `_N` 后缀,见 SKILL.md §输出位置声明)
  - 子目录不存在时 `mkdir(parents=True, exist_ok=True)`
- `--output <path>` 显式 override 分支保持不变:用户给什么写什么

### 文档改动

- **SKILL.md** 新增 §📌 输出位置 章节:
  - 显式引用总纲 §原则 12
  - 标 12.A(数据/过程)和 12.B(HELP)分类
  - 列出 10 个 template → command_cn 映射
  - 显式声明偏离:本地时间(非 UTC)、覆盖(无 _N 冲突后缀)、Skill 标识 = `home_manager`
  - 指向 ADR-0001
- **CONTEXT.md**(已在上一步 grilling 产出,无需再改)
- **docs/adr/0001-local-time-over-utc-for-html-filenames.md**(已产出,无需再改)

### 历史清理

- 清空 `output/` 目录下所有文件(107 个 ~110 MB)
- 保留:
  - 根目录的 `居家管家.html`(git 跟踪的 HELP mirror,`test_manual_sync.py` 强制 SHA256 一致)
  - `.notes/` 下的开发文档(审计报告、计划书、grilling rounds)
  - `.db/` 下的测试 sync artifact(如果是 git 跟踪)

### CLI 层无改动

`scripts/home_manager/home_manager.py` 中的所有 `emit(payload, template_name, args.output)` 调用**不动**:
- 现有代码已传 template_name 给 emit,render 层用映射表自解 command_cn
- 现有代码已传 args.output(默认 None),render 层在 None 时走自动命名
- 不新增 CLI 参数

### Template 文件无改动

10 个 `templates/*.html` 文件本身不动。文件名是 render 层的概念,template 内部不需要知道自己的 command_cn。

### features/*.md 无改动

工作流文档引用的是 template 路径(`templates/search_results.html`),不是输出文件名。无需更新。

## Testing Decisions

### 什么是好的测试

只测 `render_page()` 函数的外部行为(给定 template + payload + 不传 output_path,生成的文件路径/文件名/内容是否符合契约),不测实现细节(不 mock env 链内部函数、不断言私有函数调用次数)。每个测试用 `tmp_path` 隔离环境,用 `monkeypatch.setenv` 控制 env var。

### 测试 seam

**单一 seam:`render_page(template_name, payload, output_path=None)`** —— 现有 `tests/test_render.py` 已在这个 seam 上有 9 个测试,新增测试在同一文件追加。

理由:
- 所有命名/路径/覆盖决策都集中在 `render_page()` 的"未指定 output_path"分支
- 这是 render 层的最高入口,不依赖 DB、不依赖 CLI argparse
- 现有 test_render.py 已建立模式(`tmp_path` + 真实 template + 断言生成文件内容)

### 测试覆盖清单(新增到 test_render.py)

1. **12.A 自动命名**:`render_page("search_results.html", payload)` 不传 output_path → 断言生成文件路径含 `home_manager_html/查物品_YYYYMMDD_HHMMSS.html`
2. **12.B 自动命名**:`render_page("help_center.html", payload)` 不传 output_path → 断言路径含 `居家管家_HELP_YYYYMMDD_HHMMSS.html`
3. **映射表覆盖**:对 9 个非 help_center template 参数化测试,每个的 command_cn 都正确
4. **env 链 SKILLS_DATA_DIR 优先**:`monkeypatch.setenv("SKILLS_DATA_DIR", tmp_path)` → 输出在 `tmp_path/home_manager_html/`
5. **env 链 SKILLS_DB_PATH 兜底**:unset `SKILLS_DATA_DIR`,`monkeypatch.setenv("SKILLS_DB_PATH", tmp_path)` → 输出在 `tmp_path/home_manager_html/`
6. **fallback**:unset 两个 env var → 输出在 Skill 自带 fallback 路径(测试时 mock 或接受硬编码 `D:\.db\` 跳过)
7. **--output override**:`render_page(..., output_path=str(tmp_path / "custom.html"))` → 写到 custom.html,不触发自动命名
8. **本地时间**:`render_page("search_results.html", payload)` → 文件名时间戳接近 `datetime.now()`(允许 1 秒误差)
9. **覆盖行为**:预先生成同名文件 → 再次 render_page 不报错,文件被覆盖(内容为新版本)
10. **子目录自动创建**:`tmp_path/home_manager_html/` 不存在 → render_page 自动创建,不抛异常
11. **时间戳格式**:正则 `^\d{8}_\d{6}$` 匹配,不是 ISO 也不是 Unix timestamp
12. **文件名无保留字符**:command_cn 不含 `/ \ : * ? " < > |`(因为映射表都是中文,自然满足,但锁住不变)
13. **--output 显式 override 也走子目录**?——否,显式 override 写到用户指定路径,不强制 home_manager_html/(保持现状)

### 现有测试不被破坏

现有 9 个 test_render.py 测试都传了显式 `output_path`,走 override 分支,**不受新命名逻辑影响**,应全部继续通过。

### Prior art

- `tests/test_render.py::test_render_real_template_works` —— 现有"用真实模板验证生成流程"模式,新测试照抄结构
- `tests/conftest.py::sample_ok_payload` —— 现成可用 ok payload fixture
- `tests/test_help_center.py` —— HELP HTML 集成测试(已用 `python home_manager.py help --output` 调 CLI),新测试在更低 seam 验证 12.B 命名,补充而非替代

## Out of Scope

- **历史文件迁移**:不把 `output/` 里 107 个旧命名文件改名迁到新路径,直接清空
- **`travel_trip.html` 拆 template**:不拆成 pack/return 两个 template,用 `出行清单` 综合名涵盖
- **跨 Skill 共享 `_HELP_` 检索工具**:不写 grep 工具或 HELP 索引页,只规范文件名
- **新增 `_N` 冲突后缀**:明确不做(覆盖策略已定)
- **UTC 时区改造**:明确不做(本地时间已定,见 ADR-0001)
- **总纲修订**:不改 SKILL开发总纲V1.0,只在 居家管家 Skill 层偏离并声明
- **Web SkillBoard 适配**:不改 SkillBoard 的 HTML 加载逻辑(它已直接读 `home.db`,不依赖 output/ 路径)
- **`features/*.md` 重写**:不改工作流文档(它们引用 template 路径,不是输出文件名)
- **`scripts/help_center.py` 重写**:不改 HELP 渲染器(它已通过 `render_page()` 调用,自动获得 12.B 命名)
- **`scripts/build_manual.py` 重写**:不改 HELP mirror 同步脚本(它显式 `--output` 到临时路径,走 override 分支,不受影响)

## Further Notes

### 相关文档

- `CONTEXT.md` —— 领域术语(command_cn / Skill 标识 / 出行清单 / _HELP_ 保留字 / 12.A vs 12.B)
- `docs/adr/0001-local-time-over-utc-for-html-filenames.md` —— 本地时间偏离决策
- `D:\2Study\StudyNotes\SKILLS\SKILL开发总纲V1.0\04-可视化与注入v2.md` 原则 12 —— 权威规则源
- `D:\2Study\StudyNotes\SKILLS\居家管家\SKILL.md` §📌 输出位置 —— 待新增章节
- `D:\2Study\StudyNotes\SKILLS\居家管家\scripts\render\__init__.py` —— 唯一实现改动点
- `D:\2Study\StudyNotes\SKILLS\居家管家\tests\test_render.py` —— 唯一测试 seam

### 验收标准

1. 10 个 template 各自生成符合 12.A/12.B 命名约定的文件名
2. 路径根由 env 链解析,子目录统一为 `home_manager_html/`
3. `output/` 下旧文件清空,新规则生效后生成的文件全部在新路径
4. SKILL.md §📌 输出位置 章节存在,标 12.A/12.B,显式声明偏离
5. ADR-0001 存在,CONTEXT.md 含相关术语
6. 69 个原有 pytest 测试全部继续通过(新增测试不破坏现有)
7. 新增约 13 个测试覆盖命名/路径/env 链/覆盖/时间戳格式

### 与总纲的偏离记录

| 偏离项 | 总纲规定 | 本 Skill 取值 | 记录位置 |
|--------|---------|-------------|---------|
| 时区 | UTC | 本地时间(`datetime.now()`) | ADR-0001 + SKILL.md §输出位置 |
| 冲突处理 | `_N` 后缀不覆盖 | 直接覆盖 | SKILL.md §输出位置 |
| Skill 标识 | 由 Skill 自决 | `home_manager` | CONTEXT.md + SKILL.md §输出位置 |

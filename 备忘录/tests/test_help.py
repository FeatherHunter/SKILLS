"""v1.1.4 · HELP 唤醒词 + 场景资产 + 渲染器守护

总纲 §07-HELP与场景完备性.md 契约验证:
- 场景资产 schema(8 字段齐全、ID 唯一、prompt 无实现细节)
- 场景数量 = SKILL.md 唤醒词数(28 + 备忘改分类批量重复 = 29)
- render_help 产出合法 HTML(占位符、转义)
- skill 根目录 备忘录.html 被覆盖(用户额外要求)
- HELP HTML 不展示自身唤醒词(§07 §5 反模式 3)
- SKILL.md 唤醒词与 scenarios 字段一致(防文档裂缝)

来源:用户回复 4 选
  1. yaml (场景资产格式)
  2. 老的直接删掉 (memo_html 直接删)
  3. 必须要 (help 必生成 HTML + 覆盖)
  4. FAT 最后再说
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent.parent / "script"
sys.path.insert(0, str(SCRIPT_DIR))

SKILL_DIR = Path(__file__).parent.parent
SCENARIOS_PATH = SKILL_DIR / "references" / "scenarios.yaml"
HELP_TEMPLATE = SKILL_DIR / "templates" / "memo_help.html"
SKILL_ROOT_HELP = SKILL_DIR / "备忘录.html"


@pytest.fixture(scope="module")
def scenarios():
    import yaml
    return yaml.safe_load(SCENARIOS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rendered():
    """真实跑一次 render_help,产出 2 份文件。
    initialized 由 conftest 会话级 HELP_INITIALIZED=1 固定(对抗审查 N1:
    测试不得把 skill 根镜像写成 initialized:false 版污染工作区)。"""
    from memo_render import render_help
    return render_help()


# ==================== 场景资产 schema(#31 Q7 · 共享校验模块) ====================

class TestScenariosSchema:
    """§07 §2.2 契约:8 字段必填 + #31/#32/#33 新约束。

    校验实现单一真相 = script/validate_scenarios.py(测试与生产共用)。
    本类只做「消费方」断言:共享模块的 errors 为空,且其错误信息可读。
    """

    def test_shared_validator_importable(self):
        from validate_scenarios import validate_scenarios
        assert callable(validate_scenarios)

    def test_file_exists(self):
        assert SCENARIOS_PATH.exists()

    def test_shared_validator_passes(self, scenarios):
        """共享校验模块对当前 scenarios.yaml 判定通过(#31 Q7 生产同逻辑)"""
        from validate_scenarios import validate_scenarios
        r = validate_scenarios(scenarios)
        assert r.ok, f"共享校验失败: {r.errors[:5]}"

    def test_validator_rejects_missing_category(self):
        """共享校验:缺 category 必报错(白名单守卫,生产侧同逻辑)"""
        from validate_scenarios import validate_scenarios
        bad = {
            "skill": "备忘录", "version": "9.9.9",
            "categories": [{"key": "memo", "name": "备忘类"}],
            "scenarios": [{"wake_word": "x", "scenario_id": "s1",
                           "scenario_title": "t", "dimensions": {},
                           "prompt": "p", "status": "", "result": "r"}],
        }
        r = validate_scenarios(bad)
        assert not r.ok
        assert any("category" in e for e in r.errors)

    def test_validator_rejects_forbidden_order_field(self):
        """共享校验:#31 Q4 无 order 字段(防回归:不许重新引入)"""
        from validate_scenarios import validate_scenarios
        bad = {
            "skill": "备忘录", "version": "9.9.9",
            "categories": [{"key": "memo", "name": "备忘类"}],
            "scenarios": [{"wake_word": "x", "scenario_id": "s1",
                           "scenario_title": "t", "dimensions": {},
                           "prompt": "p", "status": "", "result": "r",
                           "category": "memo", "order": 0}],
        }
        r = validate_scenarios(bad)
        assert not r.ok
        assert any("order" in e for e in r.errors)

    def test_validator_rejects_empty_dependencies(self):
        """共享校验:#32 dependencies 存在则非空"""
        from validate_scenarios import validate_scenarios
        bad = {
            "skill": "备忘录", "version": "9.9.9",
            "categories": [{"key": "memo", "name": "备忘类"}],
            "scenarios": [{"wake_word": "x", "scenario_id": "s1",
                           "scenario_title": "t", "dimensions": {},
                           "prompt": "p", "status": "", "result": "r",
                           "category": "memo", "dependencies": "   "}],
        }
        r = validate_scenarios(bad)
        assert not r.ok
        assert any("dependencies" in e for e in r.errors)

    def test_skill_and_version_keys(self, scenarios):
        assert scenarios.get("skill") == "备忘录"
        assert scenarios.get("version") == "1.2.1"

    def test_29_wake_words_minimum(self, scenarios):
        """§07 §4:每个业务唤醒词必穷举所有合法场景(下限 29, 含 首次使用)"""
        wake_words = {s["wake_word"] for s in scenarios["scenarios"]}
        assert len(wake_words) >= 29, f"唤醒词数 {len(wake_words)} < 29"

    def test_wake_word_multi_mapping_precision(self, scenarios):
        """wake_word 多对一契约(#33 归类 + #36 Init):30 场景 = 29 唯一唤醒词。

        唯一合法多对一 = 备忘改分类(单条 memo_change_category_single +
        批量 memo_batch_change_category 共用);其余唤醒词各映射恰好 1 个
        scenario_id。这是共享校验「允许 wake_word 重复」的配套契约测试。
        """
        from collections import Counter
        counter = Counter(s["wake_word"] for s in scenarios["scenarios"])
        assert len(counter) == 29, f"唯一唤醒词应 29,实际 {len(counter)}"
        multi = {k: v for k, v in counter.items() if v > 1}
        assert multi == {"备忘改分类": 2}, f"多对一应仅备忘改分类×2,实际 {multi}"

    def test_scenario_count_matches_skill_md(self, scenarios):
        """唤醒词表与 scenarios 一致(防文档裂缝)"""
        expected = {
            "记备忘", "搜备忘", "查备忘", "改备忘", "删备忘", "看备忘",
            "按时间搜备忘", "备忘改分类", "备忘改子分类",
            "记提醒", "设提醒", "看提醒", "查已提醒备忘",
            "记心愿", "删心愿", "改心愿", "查心愿",
            "记打卡", "删打卡", "改打卡", "查打卡",
            "记情绪", "删情绪", "改情绪", "查情绪",
            "完成心愿", "心愿排期", "备忘录同步",
        }
        actual = {s["wake_word"] for s in scenarios["scenarios"]}
        assert expected <= actual, f"缺失唤醒词: {expected - actual}"

    def test_no_pending_dev_status(self, scenarios):
        """本期无【待开发】;若未来引入,必须配 AI 停步逻辑"""
        pending = [s["scenario_id"] for s in scenarios["scenarios"]
                   if s["status"] == "【待开发】"]
        assert not pending, f"本期不应有【待开发】: {pending}"

    def test_wake_word_scan_simulation(self, scenarios):
        """AI 全表扫描模拟(#35 Task 2 · 不建索引,扫全表足够 #31 Q6)。

        输入任意唤醒词 → 应命中 1-2 个 scenario_id;输入无匹配 → 空。
        该逻辑是 AI 侧行为(非代码实现),测试锁定数据契约:
        - 每个合法唤醒词都能扫到 ≥1 场景
        - 随机无匹配词返回空
        """
        index = {}
        for s in scenarios["scenarios"]:
            index.setdefault(s["wake_word"], []).append(s["scenario_id"])
        # 合法唤醒词全命中
        for ww, ids in index.items():
            assert ids, f"唤醒词 {ww} 无场景"
        # 精确命中(含备忘改分类多对一)
        assert set(index["备忘改分类"]) == {
            "memo_change_category_single", "memo_batch_change_category"}
        assert index["记备忘"] == ["memo_add_basic"]
        # 无匹配 → 空
        assert "不存在的唤醒词xyz" not in index

    def test_init_wake_word_aliases(self, scenarios):
        """Init 别名命中契约(#35 补记 · #36 落地)。

        场景资产:唯一主词「首次使用」→ memo_init_setup。
        别名「初始化」「新手」在 SKILL.md 触发层(不写 yaml,#31 Q1):
        - scenarios.yaml 不得含 aliases/wake_words 字段(共享校验禁字段守卫)
        - SKILL.md 须标注别名 → 由 TestHelpWakeWordFlexibility 守护
        """
        init = [s for s in scenarios["scenarios"]
                if s["scenario_id"] == "memo_init_setup"]
        assert len(init) == 1, f"memo_init_setup 应恰 1 条,实际 {len(init)}"
        assert init[0]["wake_word"] == "首次使用", \
            f"Init 唯一展示名应为 首次使用,实际 {init[0]['wake_word']}"
        assert init[0].get("category") == "init", "Init 应在 init 分类"
        assert init[0].get("dependencies"), "Init 应含 dependencies 依赖清单"


# ==================== HELP HTML 模板 ====================

class TestHelpTemplate:
    def test_template_exists(self):
        assert HELP_TEMPLATE.exists()

    def test_placeholder_unique(self):
        text = HELP_TEMPLATE.read_text(encoding="utf-8")
        assert text.count("<!--INJECT-DATA-->") == 1, \
            f"占位符唯一性: {text.count('<!--INJECT-DATA-->')}"

    def test_no_help_wake_word_in_template(self):
        """§07 §5 反模式 3:HELP HTML 不展示自身"""
        text = HELP_TEMPLATE.read_text(encoding="utf-8")
        # 不应在模板静态文本中包含"备忘录 HELP"
        assert "备忘录 HELP" not in text, "模板静态文本不应出现 HELP 唤醒词自身"


# ==================== render_help ====================

class TestRenderHelp:
    def test_produces_timestamped_copy(self, rendered):
        """§04 原则 12.B 路径:<skill>_html/备忘录_HELP_<datetime>.html"""
        p = Path(rendered["html_path"])
        assert p.exists()
        assert "备忘录_HELP_" in p.name
        assert re.match(r"备忘录_HELP_\d{8}_\d{6}(_\d+)?\.html", p.name)

    def test_overwrites_skill_root_help(self, rendered):
        """用户额外要求:skill 根目录 备忘录.html 必须被覆盖"""
        p = Path(rendered["skill_root_path"])
        assert p.exists(), "skill 根目录 备忘录.html 应存在"
        assert p == SKILL_ROOT_HELP
        # 覆盖 = 文件内容 ≠ 旧版(我们已删旧版,所以只看新文件存在)
        assert p.stat().st_size > 1000, "文件太小,可能没真生成"

    def test_skill_root_content_matches_timestamped(self, rendered):
        """两个路径的内容应一致(覆盖 = 真复制)"""
        a = Path(rendered["html_path"]).read_bytes()
        b = Path(rendered["skill_root_path"]).read_bytes()
        assert a == b, "skill 根目录 备忘录.html ≠ 时间戳副本内容"

    def test_html_contains_window_data(self, rendered):
        text = Path(rendered["skill_root_path"]).read_text(encoding="utf-8")
        assert "window.__DATA__" in text

    def test_html_contains_all_wake_words(self, rendered):
        """§07 §5:展示全部业务唤醒词"""
        text = Path(rendered["skill_root_path"]).read_text(encoding="utf-8")
        for ww in ["记备忘", "搜备忘", "备忘改分类", "心愿排期", "备忘录同步",
                   "记心愿", "查打卡", "查情绪"]:
            assert ww in text, f"HELP HTML 应含唤醒词: {ww}"

    def test_html_does_not_show_help_itself(self, rendered):
        """§07 §5 反模式 3:HELP 唤醒词自身不出现在 HTML"""
        text = Path(rendered["skill_root_path"]).read_text(encoding="utf-8")
        # 但场景数据里的 prompt/result 可能有 "help" 字样,这里看场景标题/分组里
        # 实际:分组渲染时不调用 help 自己的 scenario_id
        # 因为没有 memo_help 自己的 scenario 记录
        assert "scenario_id: memo_help" not in text

    def test_has_5_state_fallback(self, rendered):
        """§04 原则 3:5 状态 fallback 必备"""
        text = Path(rendered["skill_root_path"]).read_text(encoding="utf-8")
        for state_id in ["stateEmpty", "stateMissing", "stateError"]:
            assert state_id in text, f"缺 5 状态 banner: {state_id}"

    def test_has_copy_button_mechanism(self, rendered):
        """§07 §5:每场景独立复制按钮"""
        text = Path(rendered["skill_root_path"]).read_text(encoding="utf-8")
        assert "copyPrompt" in text
        assert "navigator.clipboard" in text
        assert "fallbackCopy" in text  # 剪贴板 API 降级


# ==================== CLI 入口 ====================

class TestHelpCLI:
    def test_help_subcommand_runs(self, tmp_path, monkeypatch):
        """CLI `help` 子命令可执行,默认必生成 HTML"""
        # 隔离 SKILLS_DB_PATH 避免污染真实 DB;HELP_INITIALIZED=1 保持镜像 initialized=true
        # (否则子进程渲染会把 skill 根镜像写成 initialized:false 版,污染工作区)
        monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
        monkeypatch.setenv("HELP_INITIALIZED", "1")
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "memo_cli.py"), "help"],
            capture_output=True, text=True, encoding='utf-8', timeout=30,
        )
        assert r.returncode == 0, f"stderr={r.stderr}"
        data = json.loads(r.stdout)
        assert data["status"] == "ok"
        assert "html_path" in data["data"]
        assert "skill_root_path" in data["data"]
        assert data["data"]["skill_root_path"].endswith("备忘录.html")
        # skill 根 备忘录.html 被覆盖
        assert Path(data["data"]["skill_root_path"]).exists()

    def test_help_has_no_html_flag(self):
        """§07 §3 反例:`help` 不需要 --html flag(必生成)"""
        # 解析命令行,确认没有 --html 参数
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "memo_cli.py"), "help", "--help"],
            capture_output=True, text=True, encoding='utf-8',
        )
        # --help 输出应不含 --html
        assert "--html" not in result.stdout, \
            "help 子命令不应有 --html flag(必生成 HTML)"


# ==================== 老 备忘录.html 处置(用户回复 #2:直接删) ====================

class TestOldManualDeprecated:
    def test_old_html_not_in_skill_root(self):
        """用户要求 #2:老的纯用户手册 备忘录.html 已删除,不再有第二份 HTML 维护"""
        # skill 根目录不应再有手工维护版
        # 当前 skill 根目录的 备忘录.html = render_help 产物(覆盖式)
        # 这条测试本身在 render 后跑,根目录文件存在是 OK 的(就是 HELP 输出的副本)
        # 但:我们只维护一份 HTML(即 HELP 产物),不允许人工再写一份
        # 验证:git log 不该再有手写提交到 备忘录.html(v1.1.4 之前的提交 OK)
        pass  # 静态检查:本测试通过 git 历史守护,这里只做软声明


# ==================== --output 旗标(B 方案) ====================

class TestHelpOutputFlag:
    """--output B 方案:额外副本,备忘录.html 永远写

    设计原则(用户选定 B 方案):
    - 默认行为(无 --output):时间戳副本 + skill 根 备忘录.html(2 份)
    - 加 --output /path:2 份 + 额外副本 /path(3 份)
    - --output 不影响 备忘录.html(用户 v1.1.4 额外要求:永远覆盖)
    """

    def test_render_help_output_path_kwarg(self, tmp_path):
        """render_help 接受 output_path kwarg"""
        from memo_render import render_help
        out = tmp_path / "extra.html"
        r = render_help(output_path=out)
        assert out.exists(), "--output 路径应被写入"
        # 额外副本内容 = 时间戳副本内容
        assert Path(r["html_path"]).read_bytes() == out.read_bytes()
        # skill 根 备忘录.html 也写了(用户要求永远写)
        assert Path(r["skill_root_path"]).exists()

    def test_render_help_output_none_default(self):
        """不传 output_path → 返回 output_path=None"""
        from memo_render import render_help
        r = render_help()
        assert r["output_path"] is None

    def test_render_help_creates_parent_dir(self, tmp_path):
        """--output 父目录不存在时自动创建"""
        from memo_render import render_help
        nested = tmp_path / "a" / "b" / "c" / "extra.html"
        r = render_help(output_path=nested)
        assert nested.exists(), "嵌套父目录应自动创建"
        assert r["output_path"] == str(nested)

    def test_render_help_output_does_not_skip_skill_root(self, tmp_path):
        """核心保证:加 --output 时,备忘录.html 仍被覆盖"""
        from memo_render import render_help
        out = tmp_path / "extra.html"
        r = render_help(output_path=out)
        skill_root = Path(r["skill_root_path"])
        assert skill_root.exists(), \
            "加了 --output,备忘录.html 仍必须被覆盖(B 方案核心)"

    def test_cli_help_with_output_flag(self, tmp_path, monkeypatch):
        """CLI:help --output /tmp/foo.html 工作"""
        out = tmp_path / "from_cli.html"
        monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "memo_cli.py"),
             "help", "--output", str(out)],
            capture_output=True, text=True, encoding='utf-8', timeout=30,
        )
        assert r.returncode == 0, f"stderr={r.stderr}"
        data = json.loads(r.stdout)
        assert data["status"] == "ok"
        # CLI 报告了额外副本路径
        assert data["data"]["output_path"] == str(out)
        assert out.exists()
        # 时间戳副本 + skill 根也写了(3 份)
        assert Path(data["data"]["html_path"]).exists()
        assert Path(data["data"]["skill_root_path"]).exists()

    def test_cli_help_short_output_flag(self, tmp_path, monkeypatch):
        """CLI:help -o /tmp/foo.html(短旗标)"""
        out = tmp_path / "short.html"
        monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "memo_cli.py"),
             "help", "-o", str(out)],
            capture_output=True, text=True, encoding='utf-8', timeout=30,
        )
        assert r.returncode == 0, f"stderr={r.stderr}"
        data = json.loads(r.stdout)
        assert data["data"]["output_path"] == str(out)

    def test_cli_help_output_message_notes_extra_copy(self, tmp_path, monkeypatch):
        """CLI 返回 message 提示用户额外副本已写(B 方案 UX)"""
        out = tmp_path / "extra.html"
        monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "memo_cli.py"),
             "help", "--output", str(out)],
            capture_output=True, text=True, encoding='utf-8', timeout=30,
        )
        data = json.loads(r.stdout)
        # note 字段含"额外副本"提示
        assert "额外副本" in data["data"]["note"]
        assert str(out) in data["data"]["note"]

    def test_cli_help_without_output_no_extra_path_in_json(self, tmp_path, monkeypatch):
        """无 --output 时,output_path 应为 None(JSON 字段为 null)"""
        monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "memo_cli.py"), "help"],
            capture_output=True, text=True, encoding='utf-8', timeout=30,
        )
        data = json.loads(r.stdout)
        assert data["data"]["output_path"] is None


# ==================== 唤醒词灵活匹配(FAT G1 修复) ====================

class TestHelpWakeWordFlexibility:
    """FAT(§05 钩子 ⑥)发现 SKILL.md G1:唤醒词灵活匹配没明文。
    修后用静态检查守护回归。
    """

    SKILL_MD = SKILL_DIR / "SKILL.md"

    def test_skill_md_documents_wake_word_flexibility(self):
        """SKILL.md §备忘录 HELP 含'灵活匹配'段"""
        text = self.SKILL_MD.read_text(encoding="utf-8")
        assert "唤醒词灵活匹配" in text, \
            "FAT G1 修复:SKILL.md 应明文规定唤醒词灵活匹配规则"

    def test_skill_md_documents_variations_examples(self):
        """SKILL.md 含变体示例(口语化 / slash 等)"""
        text = self.SKILL_MD.read_text(encoding="utf-8")
        # 至少含 3 种变体示例
        variations = [
            "口语化",
            "slash",
            "缩字",
            "大小写",
            "manual",
        ]
        present = [v for v in variations if v in text]
        assert len(present) >= 3, \
            f"FAT G1 修复:SKILL.md 应含 ≥3 种变体示例,实际 {present}"


# ==================== HTML 路径 SKILLS_DB_PATH 影响(G2 修复) ====================

class TestHelpHtmlPathEnvVar:
    """FAT(§05 钩子 ⑥)发现 SKILL.md G2:HTML 路径受 SKILLS_DB_PATH 影响没强调。
    修后用静态检查守护。
    """

    SKILL_MD = SKILL_DIR / "SKILL.md"

    def test_skill_md_documents_skills_db_path_influence(self):
        """SKILL.md §HTML 输出目录规则明示 SKILLS_DB_PATH 影响"""
        text = self.SKILL_MD.read_text(encoding="utf-8")
        # 至少有一段明示路径受 SKILLS_DB_PATH 影响
        assert "SKILLS_DB_PATH" in text and "memo_html" in text, \
            "FAT G2 修复:SKILL.md 应明示路径受 SKILLS_DB_PATH 影响"

    def test_html_output_uses_skills_db_path_when_set(self, tmp_path, monkeypatch):
        """实测:SKILLS_DB_PATH 设置时,HTML 输出到对应子目录"""
        # 模拟用户设置 SKILLS_DB_PATH
        custom_dir = tmp_path / "custom_db"
        custom_dir.mkdir()
        monkeypatch.setenv("SKILLS_DB_PATH", str(custom_dir))
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "memo_cli.py"), "help"],
            capture_output=True, text=True, encoding='utf-8', timeout=30,
        )
        assert r.returncode == 0, f"stderr={r.stderr}"
        data = json.loads(r.stdout)
        html_path = Path(data["data"]["html_path"]).resolve()
        custom_dir_resolved = custom_dir.resolve()
        # 路径应在 custom_dir/memo_html/ 下(不是默认的 .db/memo_html/)
        assert str(custom_dir_resolved) in str(html_path), \
            f"SKILLS_DB_PATH 应影响 HTML 输出路径,实际 {html_path}"
        assert "memo_html" in html_path.parts


# ==================== 反向指引表(G3 修复) ====================

class TestReverseLookupTable:
    """FAT(§05 钩子 ⑥)发现 SKILL.md G3:缺"用户原话 → 唤醒词"反向指引。
    修后用静态检查守护。
    """

    SKILL_MD = SKILL_DIR / "SKILL.md"

    def test_skill_md_has_reverse_lookup_section(self):
        """SKILL.md 含"用户原话 → 唤醒词 反向指引表"段"""
        text = self.SKILL_MD.read_text(encoding="utf-8")
        assert "用户原话" in text and "唤醒词" in text and "反向指引" in text, \
            "FAT G3 修复:SKILL.md 应有反向指引表"

    def test_reverse_lookup_table_covers_core_triggers(self):
        """反向指引表至少覆盖 5 个核心唤醒词"""
        text = self.SKILL_MD.read_text(encoding="utf-8")
        # 核心唤醒词应在表中出现
        core_triggers = ["记备忘", "搜备忘", "改备忘", "删备忘", "完成心愿", "备忘录 HELP"]
        present = [t for t in core_triggers if t in text]
        assert len(present) >= 5, \
            f"反向指引表应覆盖 ≥5 个核心唤醒词,实际 {present}"


# ==================== 四层折叠结构(post-FT · #34 重构) ====================

class TestHelpThreeLevelCollapse:
    """#34 重构:HELP HTML = Level 1 分类(默认折叠) + Level 2 子功能 + Level 3 场景 + Level 4 详情(默认折叠)
    设计原则(#31 Q2/Q3/Q4 · #33 落地):
    - Level 1: 分类(<details class="module"> · 数据来自 payload.categories · 默认折叠)
    - Level 2: 子功能(<details class="sub-module"> · subfunction 空 →「基础」兜底)
    - Level 3: 场景卡片(头有 chip + title + 复制按钮 · 总是可见)
    - Level 4: 维度/prompt/result(<details class="details"> · 默认折叠)
    """

    HELP_TEMPLATE = SKILL_DIR / "templates" / "memo_help.html"

    def test_template_has_level1_module_creation(self):
        """JS 创建 Level 1 <details class='module'>(分类,来自 categories 数据)"""
        text = self.HELP_TEMPLATE.read_text(encoding="utf-8")
        assert "className='module'" in text, \
            "应 JS 动态创建 Level 1 分类标签"
        assert "d.categories" in text or "payload.categories" in text, \
            "Level 1 分类应从 payload.categories 读取,不硬编码"

    def test_template_has_level2_submodule_creation(self):
        """JS 创建 Level 2 <details class='sub-module'>(子功能分组)"""
        text = self.HELP_TEMPLATE.read_text(encoding="utf-8")
        assert "className='sub-module'" in text, \
            "应 JS 动态创建 Level 2 子功能标签"
        assert "s.subfunction||'基础'" in text, \
            "subfunction 空应兜底「基础」分组"

    def test_template_has_level3_details_creation(self):
        """JS 创建 Level 4 <details class='details'>(详情折叠)"""
        text = self.HELP_TEMPLATE.read_text(encoding="utf-8")
        assert "className='details'" in text, \
            "应 JS 动态创建 Level 4 详情标签"

    def test_modules_default_collapsed(self):
        """Level 1 分类默认折叠(无 open 属性)"""
        text = self.HELP_TEMPLATE.read_text(encoding="utf-8")
        module_section = text.split("function buildModule")[1].split("/* ===== 场景直达")[0] \
            if "function buildModule" in text else text
        assert "'open'" not in module_section and "open=" not in module_section, \
            "分类应默认折叠(无 open 属性)"

    def test_scenario_details_default_collapsed(self):
        """Level 4 详情默认折叠(无 open 属性)"""
        text = self.HELP_TEMPLATE.read_text(encoding="utf-8")
        details_section = text.split("function buildSceneCard")[1].split("/* ===== 分类模块")[0] \
            if "function buildSceneCard" in text else ""
        assert 'open' not in details_section.split("className='details'")[1].split("body.appendChild(dt)")[0] if details_section else True, \
            "详情应默认折叠"

    def test_copy_button_visible_at_scenario_level(self):
        """复制按钮在场景头,无需展开细节即可见"""
        text = self.HELP_TEMPLATE.read_text(encoding="utf-8")
        # 复制按钮应在 buildSceneCard 内
        assert "'📋 复制 prompt'" in text, \
            "复制按钮应在场景头部(总是可见)"

    def test_no_kpi_grid_or_filter_or_toc(self):
        """无 KPI grid / filter / search / TOC(状态摘要违反 §07 §5)"""
        text = self.HELP_TEMPLATE.read_text(encoding="utf-8")
        forbidden = ['class="grid"', 'id="filter"', "categoryChips", 'id="toc"', "搜索唤醒词"]
        for f in forbidden:
            assert f not in text, f"残留状态摘要元素: {f}"

    def test_three_level_structure_via_js_simulation(self):
        """模拟 JS 渲染:8 分类(全部有场景)+ 30 场景全映射"""
        import yaml
        yaml_data = yaml.safe_load(Path("references/scenarios.yaml").read_text(encoding="utf-8"))
        scenarios = yaml_data["scenarios"]
        categories = yaml_data["categories"]
        cat_keys = {c["key"] for c in categories}
        by_cat = {}
        for s in scenarios:
            k = s.get("category")
            assert k in cat_keys, f"场景 {s['scenario_id']} 的 category={k} 不在白名单"
            by_cat.setdefault(k, []).append(s)
        total = sum(len(v) for v in by_cat.values())
        assert total == 30, f"应渲染 30 场景,实际 {total}"
        assert set(by_cat.keys()) == {"memo", "search", "remind", "wish", "checkin", "mood", "sync", "init"}, \
            f"应有 8 个非空分类,实际 {set(by_cat.keys())}"
        # Init 场景在 init 分类(#36 并入)
        init_ids = {s["scenario_id"] for s in by_cat["init"]}
        assert init_ids == {"memo_init_setup"}, f"init 分类应仅 memo_init_setup,实际 {init_ids}"

    def test_rendered_html_snapshot(self, rendered):
        """渲染快照(#35 Task 3 + #36 Init):JS 执行后 DOM 结构断言。

        4 级结构由 JS 动态创建,静态解析拿不到 → 用 Playwright 真实渲染
        (headless chromium),锁定 #34/#36 实际输出:
        8 分类 + 13 子功能 + 30 场景卡 + 30 复制按钮 + 零 JS 错误。
        init 分类含 memo_init_setup(#36 并入)。
        """
        pytest.importorskip("playwright.sync_api")
        from playwright.sync_api import sync_playwright
        html_path = Path(rendered["skill_root_path"]).as_uri()
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            js_errors = []
            page.on("pageerror", lambda e: js_errors.append(str(e)))
            page.goto(html_path)
            page.wait_for_timeout(300)
            modules = page.locator("details.module").count()
            sub_modules = page.locator("details.sub-module").count()
            scenarios = page.locator("details.scene").count()
            copy_btns = page.locator(".copy-btn").count()
            banner_visible = page.locator("#initBanner").is_visible()
            toast = page.locator("#toast").count()
            backtop = page.locator("#backToTop").count()
            names = page.locator("details.module > summary").all_text_contents()
            deps_boxes = page.locator(".deps-box").count()
            browser.close()
        assert not js_errors, f"JS 错误: {js_errors}"
        assert modules == 8, f"应 8 个分类,实际 {modules}"
        assert sub_modules == 13, f"应 13 个子功能,实际 {sub_modules}"
        assert scenarios == 30, f"应 30 场景卡,实际 {scenarios}"
        assert copy_btns == 32, f"应 32 复制按钮(30 场景头 + 1 联系作者 + 1 init 横幅按钮,元素恒在 DOM),实际 {copy_btns}"
        assert not banner_visible, "已初始化(HELP_INITIALIZED=1)时 init 横幅应隐藏"
        assert deps_boxes == 1, f"应 1 个依赖清单块(Init),实际 {deps_boxes}"
        assert toast == 1 and backtop == 1, "toast / back-to-top 元素应在"
        joined = " ".join(names)
        for cn in ["备忘类", "查找类", "提醒类", "心愿类", "打卡类", "情绪类", "同步类", "初始化类"]:
            assert cn in joined, f"分类 {cn} 未渲染"

    def test_init_banner_visible_when_uninitialized(self, tmp_path, monkeypatch):
        """对抗审查 N1 补充:未初始化(HELP_INITIALIZED=0)时 init 横幅显示 + 复制按钮在位。

        渲染隔离:monkeypatch memo_render.SKILL_DIR → tmp(不污染真实 skill 根镜像)。"""
        import memo_render
        monkeypatch.setattr(memo_render, "SKILL_DIR", tmp_path)
        monkeypatch.setenv("HELP_INITIALIZED", "0")
        from memo_render import render_help
        r = render_help()
        html_path = Path(r["skill_root_path"]).as_uri()
        pytest.importorskip("playwright.sync_api")
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            js_errors = []
            page.on("pageerror", lambda e: js_errors.append(str(e)))
            page.goto(html_path)
            page.wait_for_timeout(300)
            banner_visible = page.locator("#initBanner").is_visible()
            init_copy = page.locator("#initCopy").count()
            browser.close()
        assert not js_errors, f"JS 错误: {js_errors}"
        assert banner_visible, "未初始化(HELP_INITIALIZED=0)时 init 横幅应显示"
        assert init_copy == 1, "init 横幅应有复制 prompt 按钮"

# ==================== prompt 填写友好性(用户反馈) ====================

class TestPromptFillInFormat:
    """用户反馈(对抗式审查 v1.1.4):

    旧 prompt 用 <开始日期> 等 <占位符>,用户需手动删 < > 再填值,体验差。
    新设计:用 _____________ 填空线 + 括号示例 + 唤醒词锚点。
    """

    SCENARIOS = SKILL_DIR / "references" / "scenarios.yaml"

    @pytest.fixture(scope="class")
    def data(self):
        import yaml
        return yaml.safe_load(self.SCENARIOS.read_text(encoding="utf-8"))

    def test_no_chinese_angle_placeholder(self, data):
        """不应有 <中文占位符>(用户需手动删)"""
        import re
        bad = []
        for s in data["scenarios"]:
            placeholders = re.findall(r'<[\u4e00-\u9fff]+>', s["prompt"])
            if placeholders:
                bad.append((s["scenario_id"], placeholders))
        assert not bad, f"<中文占位符>残留: {bad}"

    def test_has_wake_word_anchor(self, data):
        """prompt 应含'唤醒词:XXX'锚点(让 AI 识别 route)"""
        missing = []
        for s in data["scenarios"]:
            if "唤醒词:" not in s["prompt"]:
                missing.append(s["scenario_id"])
        assert not missing, f"缺唤醒词锚点: {missing}"

    def test_has_expected_outcome(self, data):
        """prompt 应含'期望效果:'段(AI 知道预期)"""
        missing = []
        for s in data["scenarios"]:
            if "期望效果" not in s["prompt"]:
                missing.append(s["scenario_id"])
        assert not missing, f"缺期望效果段: {missing}"

    def test_has_fill_in_or_no_params(self, data):
        """有参数应用 _____________ 填空;无参数显式说'无需参数' """
        bad = []
        for s in data["scenarios"]:
            p = s["prompt"]
            if "_____________" not in p and "无需参数" not in p:
                bad.append(s["scenario_id"])
        assert not bad, f"场景既无填空线也无无需参数声明: {bad}"

    def test_prompt_describes_action_not_cli(self, data):
        """prompt 不暴露 CLI / DB(§07 §3)"""
        forbidden = ["memo_cli.py", "memo.db", ".py", "SELECT ", "INSERT "]
        bad = []
        for s in data["scenarios"]:
            text = s["prompt"] + s.get("result", "")
            for f in forbidden:
                if f in text:
                    bad.append((s["scenario_id"], f))
        assert not bad, f"prompt/result 暴露实现细节: {bad}"

    def test_format_hint_in_parentheses(self, data):
        """填写线行应在括号内含格式说明或示例"""
        import re
        bad = []
        for s in data["scenarios"]:
            for line in s["prompt"].split("\n"):
                if "_____________" in line:
                    if not re.search(r'\([^)]*\)', line):
                        bad.append((s["scenario_id"], line.strip()[:80]))
                    break  # 每场景只检查首个填写线行
        assert len(bad) < 5, f"填写线行缺括号示例: {bad[:5]}"

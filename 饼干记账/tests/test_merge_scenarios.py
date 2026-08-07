"""merge_scenarios.py 合并器测试(公共层 · T0 #164)

覆盖:汇总结构 / 跨域唤醒词唯一 / scenario_id 唯一 / 字段契约 / prompt 骨架 / 幂等
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import merge_scenarios as ms  # noqa: E402


def _scene(**overrides) -> dict:
    """构造一个合法场景条目(字段齐全)"""
    base = {
        "id": "t-1-1",
        "scenario_id": "test_scene",
        "scenario_title": "测试场景",
        "type": "查看",
        "status": "",
        "html": {"template": "测试/t.html", "command_cn": "测试", "data_source": "bills"},
        "prompt": "请加载「饼干记账」技能,帮我测试(唤醒词:测试):\n",
        "result": "HTML 展示测试结果",
    }
    base.update(overrides)
    return base


def _domain(key: str, scenes=None) -> dict:
    return {
        "version": ms.VERSION,
        "domain": key,
        "subs": [
            {
                "name": "测试",
                "wake_words": [
                    {"wake_word": "测试词", "scenes": scenes or [_scene()]},
                ],
            }
        ],
    }


# ── 汇总结构 ──────────────────────────────────────────────────────────────────


class TestSummary:
    def test_domains_declares_all_seven(self):
        """汇总 domains meta 固定声明 7 域(即使未枚举);顺序 = HELP 展示依据"""
        summary = ms.build_summary({})
        assert len(summary["domains"]) == 7
        keys = [d["key"] for d in summary["domains"]]
        assert keys == ["write", "query", "analysis", "goal", "account", "link", "setup"]

    def test_scenes_only_enumerated_domains(self):
        """scenes 只含已枚举域;未枚举域不出现在 scenes"""
        summary = ms.build_summary({"setup": _domain("setup")})
        assert len(summary["scenes"]) == 1
        assert summary["scenes"][0]["key"] == "setup"

    def test_help_wake_words_preserved(self):
        summary = ms.build_summary({})
        assert summary["help_wake_words"] == ["饼干记账 HELP", "饼干记账 帮助", "查帮助", "能做什么"]

    def test_nested_structure(self):
        """嵌套结构:域 → sub → wake_word → scenes"""
        summary = ms.build_summary({"setup": _domain("setup")})
        dom = summary["scenes"][0]
        assert dom["subs"][0]["name"] == "测试"
        assert dom["subs"][0]["wake_words"][0]["wake_word"] == "测试词"
        sc = dom["subs"][0]["wake_words"][0]["scenes"][0]
        assert sc["scenario_id"] == "test_scene"
        assert set(sc.keys()) == {"id", "scenario_id", "scenario_title", "type", "status", "html", "prompt", "result"}

    def test_real_three_domains_count(self):
        """真实 4 域合并:61 场景(write 15 + query 15 + analysis 25 + setup 6),60 唤醒词"""
        domain_data = {}
        for key in ms.DOMAIN_KEYS:
            data = ms.load_domain_yaml(key)
            if data is not None:
                domain_data[key] = data
        summary = ms.build_summary(domain_data)
        stats = ms.collect_stats(summary)
        assert stats["scenes"] == 61
        assert stats["wake_words"] == 60


# ── 全局校验 ──────────────────────────────────────────────────────────────────


class TestGlobalValidation:
    def test_wake_word_global_conflict_detected(self):
        """跨域唤醒词重复必须报错(合并器抓「恢复」冲突的先例)"""
        errors = []
        summary = ms.build_summary({"write": _domain("write"), "setup": _domain("setup")})
        ms.validate_global(summary, errors)
        assert any("唤醒词全局重复" in e for e in errors)

    def test_scenario_id_global_conflict_detected(self):
        errors = []
        summary = ms.build_summary({"write": _domain("write"), "setup": _domain("setup")})
        ms.validate_global(summary, errors)
        assert any("scenario_id 全局重复" in e for e in errors)

    def test_scene_id_global_conflict_detected(self):
        errors = []
        summary = ms.build_summary({"write": _domain("write"), "setup": _domain("setup")})
        ms.validate_global(summary, errors)
        assert any("场景 id 全局重复" in e for e in errors)

    def test_clean_summary_no_errors(self):
        errors = []
        summary = ms.build_summary({"write": _domain("write", scenes=[_scene()])})
        ms.validate_global(summary, errors)
        assert errors == []


# ── 域内校验 ──────────────────────────────────────────────────────────────────


class TestDomainValidation:
    def test_missing_required_field(self):
        errors = []
        ms.validate({"version": ms.VERSION, "domain": "setup", "subs": []}, "setup", errors)
        assert errors == []

    def test_bad_scene_missing_field(self):
        errors = []
        bad = _scene()
        del bad["result"]
        ms.validate(_domain("setup", [bad]), "setup", errors)
        assert any("缺字段 'result'" in e for e in errors)

    def test_bad_html_missing_field(self):
        errors = []
        bad = _scene(html={"template": "x.html"})
        ms.validate(_domain("setup", [bad]), "setup", errors)
        assert any("html 缺字段 'command_cn'" in e for e in errors)

    def test_empty_prompt_rejected(self):
        errors = []
        bad = _scene(prompt="   \n")
        ms.validate(_domain("setup", [bad]), "setup", errors)
        assert any("prompt 为空" in e for e in errors)

    def test_prompt_head_rule(self):
        errors = []
        bad = _scene(prompt="帮我查一下(唤醒词:测试):\n")
        ms.validate(_domain("setup", [bad]), "setup", errors)
        assert any("prompt 首行不符合骨架" in e for e in errors)

    def test_domain_field_mismatch(self):
        errors = []
        ms.validate(_domain("write"), "setup", errors)
        assert any("domain 字段" in e for e in errors)

    def test_duplicate_wake_word_in_domain(self):
        errors = []
        data = _domain("setup")
        data["subs"][0]["wake_words"].append({"wake_word": "测试词", "scenes": [_scene(id="t-2", scenario_id="x2")]})
        ms.validate(data, "setup", errors)
        assert any("唤醒词在域内重复" in e for e in errors)


# ── 幂等 ──────────────────────────────────────────────────────────────────────


class TestIdempotency:
    def test_dump_is_deterministic(self):
        domain_data = {}
        for key in ms.DOMAIN_KEYS:
            data = ms.load_domain_yaml(key)
            if data is not None:
                domain_data[key] = data
        summary = ms.build_summary(domain_data)
        d1 = ms.yaml.safe_dump(summary, allow_unicode=True, sort_keys=False, width=120)
        d2 = ms.yaml.safe_dump(summary, allow_unicode=True, sort_keys=False, width=120)
        assert d1 == d2


# ── 健壮性 / 产物质量(对抗审查补充) ───────────────────────────────────────────


class TestRobustness:
    def test_bad_yaml_raises_friendly_error(self, tmp_path, monkeypatch):
        """域文件 yaml 语法错误 → 友好 ValueError(而非 traceback)"""
        monkeypatch.setattr(ms, "SCENES_DIR", tmp_path)
        bad = tmp_path / "setup.yaml"
        bad.write_text("subs: [unclosed\n  bad: [", encoding="utf-8")
        with pytest.raises(ValueError, match="yaml 语法错误"):
            ms.load_domain_yaml("setup")

    def test_dump_uses_block_scalar_for_multiline_prompt(self):
        """多行 prompt 序列化为 block 标量(|),汇总人类可读"""
        summary = ms.build_summary({"setup": _domain("setup")})
        dumped = ms.dump_summary(summary)
        assert "prompt: |" in dumped
        # 数据保真:读回后 prompt 内容一致
        reloaded = ms.yaml.safe_load(dumped)
        assert (
            reloaded["scenes"][0]["subs"][0]["wake_words"][0]["scenes"][0]["prompt"]
            == _scene()["prompt"]
        )


class TestCheckMode:
    def _setup(self, tmp_path, monkeypatch):
        scenes_dir = tmp_path / "scenes"
        scenes_dir.mkdir()
        (scenes_dir / "setup.yaml").write_text(
            ms.yaml.safe_dump(_domain("setup"), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        monkeypatch.setattr(ms, "SCENES_DIR", scenes_dir)
        monkeypatch.setattr(ms, "SUMMARY_PATH", tmp_path / "scenarios.yaml")
        return scenes_dir

    def test_check_ok_when_no_diff(self, tmp_path, monkeypatch, capsys):
        self._setup(tmp_path, monkeypatch)
        monkeypatch.setattr(sys, "argv", ["merge_scenarios.py"])  # 先正常生成
        assert ms.main() == 0
        monkeypatch.setattr(sys, "argv", ["merge_scenarios.py", "--check"])
        assert ms.main() == 0
        assert "无 diff" in capsys.readouterr().out

    def test_check_fails_on_diff(self, tmp_path, monkeypatch, capsys):
        scenes_dir = self._setup(tmp_path, monkeypatch)
        monkeypatch.setattr(sys, "argv", ["merge_scenarios.py"])
        assert ms.main() == 0  # 生成基线汇总
        # 修改域文件(新增一个场景)→ 汇总应有 diff
        extra = _domain("setup")
        extra["subs"][0]["wake_words"][0]["scenes"].append(
            _scene(id="t-9", scenario_id="test_scene_2", prompt="请加载「饼干记账」技能,帮我测(唤醒词:测试词):\n")
        )
        (scenes_dir / "setup.yaml").write_text(
            ms.yaml.safe_dump(extra, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        monkeypatch.setattr(sys, "argv", ["merge_scenarios.py", "--check"])
        assert ms.main() == 1
        assert "有 diff" in capsys.readouterr().out

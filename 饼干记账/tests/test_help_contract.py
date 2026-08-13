# -*- coding: utf-8 -*-
"""tests/test_help_contract.py — HELP scene-data 契约 v1 校验(#303 task ④ 新增)

门禁 A 层 1 的可证伪化:
- 独立从 references/scenarios.yaml 重新展平期望值(测试侧独立映射),
  与渲染输出 help-data JSON 逐条对比(71/71:prompt 逐字一致 / id / title / wake_word / types / status)
- Base validate_help_data 硬拦截通过(校验器 = 公共组件资产,非本票产物,防「AI 自证」)
- status 二态合法 / id 全局唯一 / 7 组 / 71 场景 / 横幅 prompt 与源逐字一致

渲染走 render_help.py 子进程(端到端 = 最上层调用 HELP 命令拿到的 HTML)。
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
REPO_ROOT = SKILL_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

BASE_INJECTOR_PATH = REPO_ROOT / "公共组件" / "injector.py"
SCENARIOS_PATH = SKILL_DIR / "references" / "scenarios.yaml"
RENDER_HELP = SCRIPTS_DIR / "render_help.py"

# type 默认配色表(公共组件 help_template TYPE_DEFAULT;测试侧白名单)
KNOWN_TYPES = {"采集", "查看", "向导", "选择", "回执"}

EXPECTED_GROUP_KEYS = ["write", "query", "analysis", "goal", "account", "link", "setup"]
HELP_WAKE_WORDS = ["饼干记账 HELP", "饼干记账 帮助", "查帮助", "能做什么"]


def _base_injector():
    """加载公共组件/injector.py(importlib 按路径加载防撞名)"""
    spec = importlib.util.spec_from_file_location("base_injector", BASE_INJECTOR_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_summary() -> dict:
    return yaml.safe_load(SCENARIOS_PATH.read_text(encoding="utf-8"))


def _flatten_expected(summary: dict) -> list[dict]:
    """测试侧独立展平(scenarios.yaml → 平铺场景期望值,与 render_help 同映射)"""
    scenes = []
    for dom in summary.get("scenes", []):
        for sub in dom.get("subs", []):
            for ww_entry in sub.get("wake_words", []):
                for sc in ww_entry.get("scenes", []):
                    scenes.append({
                        "id": sc.get("scenario_id", ""),
                        "title": sc.get("scenario_title", ""),
                        "wake_word": ww_entry["wake_word"],
                        "type": sc.get("type", ""),
                        "status": sc.get("status", ""),
                        "prompt": sc.get("prompt", ""),
                    })
    return scenes


def _payload_scenes(payload: dict) -> list[dict]:
    return [s for g in payload["groups"] for sg in g["subgroups"] for s in sg["scenes"]]


@pytest.fixture(scope="class")
def payload(tmp_path_factory):
    """渲染产物 help-data JSON(端到端子进程 · 备份/恢复根镜像副作用)"""
    out_dir = tmp_path_factory.mktemp("help_contract_render")
    root_mirror = SKILL_DIR / "饼干记账.html"
    backup = out_dir / "mirror.backup"
    had_root = root_mirror.exists()
    if had_root:
        backup.write_bytes(root_mirror.read_bytes())
    try:
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(out_dir)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        out_path = out_dir / "help.html"
        result = subprocess.run(
            [sys.executable, str(RENDER_HELP), "--out", str(out_path)],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=60,
        )
        assert result.returncode == 0, f"render_help 失败: {result.stderr}"
        text = out_path.read_text(encoding="utf-8-sig")
        m = re.search(r'<script id="help-data"[^>]*>(.*?)</script>', text, re.DOTALL)
        assert m is not None, "渲染产物缺 help-data 数据注入点"
        return json.loads(m.group(1))
    finally:
        if had_root:
            root_mirror.write_bytes(backup.read_bytes())
        elif root_mirror.exists():
            root_mirror.unlink()


# ── 单元:契约构建(横幅状态驱动)───────────────────────────────────────────────

class TestContractBuilder:
    """build_help_contract 单元:init_banner 状态驱动 + 横幅 prompt 逐字一致"""

    def test_init_banner_only_when_uninitialized(self):
        import render_help
        summary = _load_summary()
        c_uninit = render_help.build_help_contract(summary, initialized=False,
                                                   ts="2026-08-13 00:00")
        assert "init_banner" in c_uninit, "未初始化时应带 init_banner"
        expected_prompt = next(
            sc["prompt"] for dom in summary["scenes"] for sub in dom["subs"]
            for ww in sub["wake_words"] for sc in ww["scenes"]
            if sc["scenario_id"] == "setup_init_wizard"
        )
        assert c_uninit["init_banner"]["prompt"] == expected_prompt, \
            "横幅 prompt 必须与源 yaml setup_init_wizard 逐字一致"
        c_init = render_help.build_help_contract(summary, initialized=True,
                                                 ts="2026-08-13 00:00")
        assert "init_banner" not in c_init, "已初始化时不应带 init_banner"


# ── 集成:渲染产物(端到端)─────────────────────────────────────────────────────

class TestRenderedPayload:
    """渲染产物 help-data JSON 契约校验(71 场景逐条对账)"""

    def test_base_validation_passes(self, payload):
        """Base validate_help_data 硬拦截通过(校验器 = 公共组件资产,非本票产物)"""
        ok, msg = _base_injector().validate_help_data(payload)
        assert ok, f"Base 契约校验失败: {msg}"

    def test_top_level_fields(self, payload):
        assert payload["skill_name"] == "饼干记账"
        assert payload["title"] == "使用手册(HELP)"
        assert payload["version"] == "2.0"
        assert "7 功能域" in payload["subtitle"] and "71 场景" in payload["subtitle"]

    def test_groups_order_and_count(self, payload):
        keys = [g["id"] for g in payload["groups"]]
        assert keys == EXPECTED_GROUP_KEYS, f"7 组顺序应固定,实际 {keys}"
        assert all(g["subgroups"] for g in payload["groups"]), "每组应有非空 subgroups"

    def test_scene_count_71(self, payload):
        scenes = _payload_scenes(payload)
        assert len(scenes) == 71, f"场景数应为 71,实际 {len(scenes)}"
        assert all(sg["scenes"] for g in payload["groups"] for sg in g["subgroups"]), \
            "每个 subgroup 应有非空 scenes"

    def test_ids_unique(self, payload):
        gids = [g["id"] for g in payload["groups"]]
        sids = [s["id"] for s in _payload_scenes(payload)]
        assert len(gids) == len(set(gids)), "分组 id 重复"
        assert len(sids) == len(set(sids)), "场景 id 重复"

    def test_status_two_state(self, payload):
        statuses = {s["status"] for s in _payload_scenes(payload)}
        assert statuses <= {"", "【待开发】"}, f"status 只允许 ''/【待开发】,实际 {statuses}"
        expected_statuses = {e["status"] for e in _flatten_expected(_load_summary())}
        assert statuses == expected_statuses, "status 应与源 yaml 一致"

    def test_prompts_zero_diff(self, payload):
        """门禁 A 层 1:复制 prompt 与源 yaml 逐字一致(71/71)"""
        by_id = {s["id"]: s for s in _payload_scenes(payload)}
        expected = _flatten_expected(_load_summary())
        assert len(expected) == 71
        diffs = []
        for e in expected:
            got = by_id.get(e["id"])
            if got is None:
                diffs.append(f"场景缺失: {e['id']}")
                continue
            if got["prompt_template"] != e["prompt"]:
                diffs.append(f"prompt 不一致: {e['id']}")
        assert not diffs, f"prompt 与源 yaml 不一致({len(diffs)} 处):\n" + "\n".join(diffs[:10])

    def test_scene_fields_aligned(self, payload):
        """id/title/wake_word/types 与源 yaml 展平期望一致"""
        by_id = {s["id"]: s for s in _payload_scenes(payload)}
        diffs = []
        for e in _flatten_expected(_load_summary()):
            got = by_id.get(e["id"])
            if got is None:
                diffs.append(f"场景缺失: {e['id']}")
                continue
            if got["title"] != e["title"]:
                diffs.append(f"{e['id']} title 不一致")
            if got["wake_word"] != e["wake_word"]:
                diffs.append(f"{e['id']} wake_word 不一致")
            got_types = got.get("types", [])
            want_types = [e["type"]] if e["type"] else []
            if got_types != want_types:
                diffs.append(f"{e['id']} types 期望 {want_types},实际 {got_types}")
            for t in got_types:
                if t not in KNOWN_TYPES:
                    diffs.append(f"{e['id']} type 不在默认配色表: {t}")
        assert not diffs, "\n".join(diffs[:10])

    def test_wake_words_in_meta_blocks(self, payload):
        blocks = {b["id"]: b for b in payload.get("meta_blocks", [])}
        ww_block = blocks.get("help_wake_words")
        assert ww_block is not None, "缺 help_wake_words meta_block(透传)"
        for ww in HELP_WAKE_WORDS:
            assert ww in ww_block["html"], f"meta_block 缺 HELP 唤醒词: {ww}"
        summary_block = blocks.get("help_summary")
        assert summary_block is not None and "71 场景" in summary_block["html"]

    def test_init_banner_prompt_matches_source(self, payload):
        """tmp DB 未初始化 → 横幅存在,复制内容与源 yaml setup_init_wizard 逐字一致"""
        banner = payload.get("init_banner")
        assert banner is not None, "未初始化渲染应带 init_banner"
        expected_prompt = next(
            sc["prompt"] for dom in _load_summary()["scenes"] for sub in dom["subs"]
            for ww in sub["wake_words"] for sc in ww["scenes"]
            if sc["scenario_id"] == "setup_init_wizard"
        )
        assert banner["prompt"] == expected_prompt

    def test_contact_items(self, payload):
        items = payload["contact"]["items"]
        labels = [it["label"] for it in items]
        assert labels == ["邮箱", "GitHub", "Issues"]
        assert payload["contact"].get("copy_all") is True

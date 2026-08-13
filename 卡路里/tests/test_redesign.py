#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_redesign.py — 卡路里 HTML 重设计 acceptance tests

ticket 01 · 2026-07-29 起,后续 ticket 14 张在此累积 acceptance tests。
依据:.scratch/card-html-redesign/spec.md Testing Decisions · vertical slices。

测试 seam 架构(从高到低):
  1. End-to-end HTML render:run render 脚本 + mock JSON + assert DOM 节点
  2. JSON data-shape assertion:parse window.__DATA__ + assert schema
  3. §04 决策矩阵一致性:scripts/check_decision_matrix.py
  4. 小数精度巡检:scripts/check_decimal_precision.py

当前已落地的 acceptance tests:
  - test_decision_matrix_checker_passes (seam 3)
  - test_decimal_precision_checker_passes (seam 4)
  - test_calorie_trend_precision_round (seam 1+2 · ticket 13)
  - test_help_center_ergonomics (seam 1 · ticket 07)
  - test_water_html_renders (seam 1+2 · ticket 02)
  - test_home_dashboard_quick_actions_use_prompts (seam 1+2 · ticket 09)
  - test_home_dashboard_deficit_math_breakdown (seam 1+2 · ticket 08)
  - test_cross_page_prompt_consistency (seam 2 · ticket 15)

执行:
    cd 卡路里 && python -m pytest tests/test_redesign.py -v
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
TEMPLATES_DIR = SKILL_DIR / "templates"
MOCK_DIR = SKILL_DIR / "tests" / "fixtures" / "mock"


# ============= util =============

def _run_script(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """真跑 render 脚本,return CompletedProcess"""
    return subprocess.run(
        [sys.executable, *args],
        cwd=SKILL_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )


def _extract_payload(html_text: str) -> dict | None:
    """从生成的 HTML 抽取 Base 管线 payload JSON"""
    m = re.search(
        r'<script id="payload" type="application/json">(.*?)</script>',
        html_text, re.DOTALL,
    )
    if not m:
        return None
    return json.loads(m.group(1).replace('<\\/', '</'))


# ============= 基础设施(seam 3+4 · ticket 01 自测) =============

class TestDecisionMatrixChecker:
    """ticket 01 · check_decision_matrix.py 自测"""

    def test_decision_matrix_checker_passes(self):
        """§完整 HTML 模板清单 全 ✅ 行必备:render + template;soft:mock"""
        r = _run_script(str(SCRIPTS_DIR / "check_decision_matrix.py"))
        assert r.returncode == 0, (
            f"check_decision_matrix.py 退出码 {r.returncode}\n"
            f"stdout: {r.stdout}\nstderr: {r.stderr}"
        )
        assert "pass" in r.stdout, f"stdout 应包含 pass 标识,实得: {r.stdout}"


class TestDecimalPrecisionChecker:
    """ticket 01 · check_decimal_precision.py 自测"""

    def test_decimal_precision_checker_passes(self, tmp_path):
        """空 calorie_html 应 pass(无文件可扫)"""
        # 临时把 HTML_DIR 指到一个空目录
        # 用 mock HTML fixture 验证逻辑:故意放一个泄漏精度的 HTML → fail
        bad_html = tmp_path / "calorie_html"
        bad_html.mkdir()
        bad_file = bad_html / "bad_trend.html"
        bad_file.write_text(
            '<html><script>window.__DATA__ = {"status":"ok","data":'
            '{"summary":{"trend_value":-141.6550000000002}}};</script></html>',
            encoding="utf-8",
        )
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "check_decimal_precision.py"),
             "--mock", str(bad_file)],
            cwd=SKILL_DIR, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15,
        )
        assert r.returncode == 1, (
            f"故意泄漏精度的 mock 应该 fail,实得 {r.returncode}\n"
            f"stdout: {r.stdout}\nstderr: {r.stderr}"
        )
        assert "-141.65" in r.stdout or "141.65" in r.stdout, (
            f"应报告 trend_value 精度问题,实得: {r.stdout}"
        )


# ============= vertical slice tests(后续 ticket 累积) =============

class TestCalorieTrendPrecision:
    """ticket 13 · render_calorie_trend.py round(2) 后端"""

    def test_calorie_trend_precision_round(self):
        """trend_value / start_avg / end_avg / series[*].calorie round(2)"""
        r = _run_script(
            str(SCRIPTS_DIR / "render_calorie_trend.py"),
            "--mock", str(MOCK_DIR / "mock_calorie_trend.json"),
            "--output", str(SKILL_DIR / "_test_trend.html"),
        )
        assert r.returncode == 0, f"render failed: {r.stderr}"
        html = (SKILL_DIR / "_test_trend.html").read_text(encoding="utf-8")
        try:
            payload = _extract_payload(html)
            assert payload is not None and payload["status"] == "ok"
            data = payload["data"]
            for field in ("trend_value", "start_avg", "end_avg"):
                v = data["summary"][field]
                assert abs(v - round(v, 2)) < 1e-9, f"summary.{field}={v} 精度 > 2"
            for s in data["series"]:
                assert abs(s["calorie"] - round(s["calorie"], 2)) < 1e-9, (
                    f"series entry calorie={s['calorie']} 精度 > 2"
                )
        finally:
            (SKILL_DIR / "_test_trend.html").unlink(missing_ok=True)


class TestTodayWaterRenders:
    """ticket 02 · render_today_water.py + templates/today_water.html(ADR-0003)"""

    def test_water_html_renders(self):
        """templates/today_water.html 应包含 ring + bar-chart + 注入数据"""
        r = _run_script(
            str(SCRIPTS_DIR / "render_today_water.py"),
            "--mock", str(MOCK_DIR / "mock_today_water_partial.json"),
            "--output", str(SKILL_DIR / "_test_water.html"),
        )
        assert r.returncode == 0, f"render failed: {r.stderr}"
        html = (SKILL_DIR / "_test_water.html").read_text(encoding="utf-8")
        try:
            assert ".ring" in html, "模板缺少 .ring 节点(进度环)"
            assert ".bar-chart" in html, "模板缺少 .bar-chart 节点(7 天 bar)"
            assert ".bar-col" in html, "模板缺少 .bar-col 节点(每日列)"
            assert 'id="payload"' in html, "模板缺少数据注入"
        finally:
            (SKILL_DIR / "_test_water.html").unlink(missing_ok=True)

    def test_water_data_shape(self):
        """JSON data-shape:summary.today_ml/target_ml/week_ml(7)/week_dates(7)"""
        r = _run_script(
            str(SCRIPTS_DIR / "render_today_water.py"),
            "--mock", str(MOCK_DIR / "mock_today_water_partial.json"),
            "--output", str(SKILL_DIR / "_test_water_shape.html"),
        )
        assert r.returncode == 0, f"render failed: {r.stderr}"
        html = (SKILL_DIR / "_test_water_shape.html").read_text(encoding="utf-8")
        try:
            payload = _extract_payload(html)
            assert payload is not None, "未能抽取 payload"
            assert payload["status"] == "ok", f"status 非 ok: {payload}"
            s = payload["data"]["summary"]
            assert isinstance(s["today_ml"], int) and s["today_ml"] == 1500, (
                f"today_ml 应为 int 1500,实得 {s['today_ml']!r}"
            )
            assert isinstance(s["target_ml"], int) and s["target_ml"] == 2000, (
                f"target_ml 应为 int 2000,实得 {s['target_ml']!r}"
            )
            assert isinstance(s["week_ml"], list) and len(s["week_ml"]) == 7, (
                f"week_ml 应为 7 个 int 列表,实得 {s['week_ml']!r}"
            )
            assert all(isinstance(x, int) for x in s["week_ml"]), (
                f"week_ml 每项应为 int,实得 {s['week_ml']!r}"
            )
            assert isinstance(s["week_dates"], list) and len(s["week_dates"]) == 7, (
                f"week_dates 应为 7 个 str 列表,实得 {s['week_dates']!r}"
            )
            meta = payload["data"]["meta"]
            assert meta["date"] == "2026-07-24"
            assert meta["today"] == "2026-07-24"
        finally:
            (SKILL_DIR / "_test_water_shape.html").unlink(missing_ok=True)

    @pytest.mark.parametrize("fixture_name", [
        "mock_today_water.json",
        "mock_today_water_partial.json",
        "mock_today_water_complete.json",
    ])
    def test_water_three_tiers_render(self, fixture_name):
        """空 / 部分 / 已完成 3 档 mock 都能渲染(3 档覆盖 ADR-0003 验收)"""
        r = _run_script(
            str(SCRIPTS_DIR / "render_today_water.py"),
            "--mock", str(MOCK_DIR / fixture_name),
            "--output", str(SKILL_DIR / f"_test_water_{fixture_name}.html"),
        )
        assert r.returncode == 0, (
            f"{fixture_name} 渲染失败:\nstdout: {r.stdout}\nstderr: {r.stderr}"
        )
        (SKILL_DIR / f"_test_water_{fixture_name}.html").unlink(missing_ok=True)


# ============= ticket 07 · HELP HTML ergonomics(#316 起基于 Base 参数化 HELP) =============

class TestHelpCenterErgonomics:
    """ticket 07 · HELP HTML ergonomics

    2026-08-13 · #316: 自研 help_center.html 退役, HELP = Base 参数化 help_template
    (scene-data 契约 v1 · _triggers.py 唯一权威)。
    """
    def _render(self, tmp_path):
        import os
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(tmp_path)
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "render_help_center.py"), "--no-mirror"],
            cwd=SKILL_DIR, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60, env=env,
        )
        assert r.returncode == 0, f"render_help_center 失败: {r.stderr}"
        out = list((tmp_path / "calorie_html").glob("卡路里_HELP_*.html"))
        assert out, "未产出 卡路里_HELP_<TS>.html"
        return out[-1].read_text(encoding="utf-8")

    def test_help_center_uses_base_template(self, tmp_path):
        """HELP 走 Base 参数化模板:help-data 契约注入 + base.js + 复制按钮 + 搜索"""
        html = self._render(tmp_path)
        m = re.search(r'<script id="help-data"[^>]*>(.*?)</script>', html, re.DOTALL)
        assert m, "缺 help-data 注入(scene-data 契约)"
        data = json.loads(m.group(1).replace('<\\/', '</'))
        assert data["skill_name"] == "卡路里"
        assert data["title"] == "唤醒词速查台"
        total = sum(len(sg["scenes"]) for g in data["groups"] for sg in g["subgroups"])
        assert total == 436, f"场景数应为 436(_triggers 全量), 实际 {total}"
        assert len(data["groups"]) == 10, "技能协同 36 条不迁入 → 10 分类"
        # Base 资产已注入 + 复制/搜索可用
        assert "function copyText" in html, "缺 base.js copyText"
        assert "copy-btn" in html, "缺复制按钮样式(copy-btn)"
        assert "搜索" in html or "search" in html, "缺搜索功能"

    def test_help_center_legacy_design_retired(self):
        """#316: 自研 help_center.html 已退役, 渲染不依赖它"""
        assert not (TEMPLATES_DIR / 'help_center.html').exists(), \
            'templates/help_center.html 应已退役删除(#316)'
        renderer = (SCRIPTS_DIR / 'render_help_center.py').read_text(encoding='utf-8')
        assert 'help_center.html' not in renderer, 'render_help_center 仍引用旧模板'

    def test_help_center_gap_disposal(self, tmp_path):
        """#316 缺口处置: 技能协同 36 不迁入; legacy 23 保留(分析/既有唤醒词 22 + 饮食/既有唤醒词 1)"""
        html = self._render(tmp_path)
        m = re.search(r'<script id="help-data"[^>]*>(.*?)</script>', html, re.DOTALL)
        data = json.loads(m.group(1).replace('<\\/', '</'))
        wakes = {s["wake_word"] for g in data["groups"]
                 for sg in g["subgroups"] for s in sg["scenes"]}
        for w in ['协同饼干记账（饮食支出）', '联动作息管家（运动时间窗）', '看跨技能汇总']:
            assert w not in wakes, f"技能协同 {w} 不应在运行时 HELP"
        for w in ['查高热量榜', '复盘', '开启定时复盘', '看「有备注」的饮食记录']:
            assert w in wakes, f"legacy {w} 应保留在 HELP"
        analysis = next(g for g in data["groups"] if g["id"] == "analysis")
        legacy_sub = next((sg for sg in analysis["subgroups"] if sg["label"] == "既有唤醒词"), None)
        assert legacy_sub is not None, "分析 组缺 既有唤醒词 子功能"
        assert len(legacy_sub["scenes"]) == 22, \
            f"分析/既有唤醒词 应为 22(查榜 13 + 复盘 9), 实际 {len(legacy_sub['scenes'])}"

    def test_triggers_have_fill_hints_field(self):
        """每个 TRIGGER 都有 fill_hints 字段(默认空 list)

        2026-08-02 改:饮食 68 场景同步后旧词 记吃了/查今天吃 已替换为 13 字段新格式;
        输入引导从 fill_hints 字段迁移到 prompt_template 的「____」填空行(06/07/08 同款)。
        """
        import sys; sys.path.insert(0, str(SCRIPTS_DIR))
        from _triggers import TRIGGERS
        for t in TRIGGERS:
            assert 'fill_hints' in t, f'trigger {t["wake_word"]} 缺 fill_hints 字段'
            assert isinstance(t['fill_hints'], list)
        # 输入型 trigger 应有非空 fill_hints(旧格式)或 prompt 含填空行(新 13 字段格式)
        water = next(t for t in TRIGGERS if t['wake_word'] == '记喝水')
        if water['fill_hints']:
            assert water['fill_hints'], '记喝水 应有非空 fill_hints'
        else:
            pt = water.get('prompt_template', '')
            assert '____' in pt, '记喝水(新格式)prompt_template 应含填空行'
        # 新格式输入型场景抽查:记一餐 prompt 应有填空行
        meal = next(t for t in TRIGGERS if t['wake_word'] == '记一餐')
        assert '____' in meal.get('prompt_template', ''), '记一餐 prompt_template 应含填空行'


class TestTodayDiet6Kpi:
    """ticket 12 · 今日饮食 6 KPI + mobile"""

    def test_today_diet_6_kpi_render(self):
        r = _run_script(
            str(SCRIPTS_DIR / "render_today_diet.py"),
            "--mock", str(MOCK_DIR / "mock_today_diet.json"),
            "--output", str(SKILL_DIR / "_test_diet.html"),
        )
        assert r.returncode == 0, f"render failed: {r.stderr}"
        html = (SKILL_DIR / "_test_diet.html").read_text(encoding="utf-8")
        try:
            payload = _extract_payload(html)
            assert payload is not None and payload["status"] == "ok"
            s = payload["data"]["summary"]
            assert "record_count" in s, "summary 缺 record_count"
            assert isinstance(s["record_count"], int)
            # 6 个 KPI 关键字段都应存在
            for k in ("calorie", "protein_g", "carb_g", "fat_g", "water_ml", "record_count"):
                assert k in s, f"summary 缺 {k}"
        finally:
            (SKILL_DIR / "_test_diet.html").unlink(missing_ok=True)

    def test_today_diet_template_has_6_kpi_grid(self):
        tpl = (SKILL_DIR / "templates" / "today_diet.html").read_text(encoding="utf-8")
        assert 'repeat(3,1fr)' in tpl, 'KPI 桌面 grid 未改 3 列'
        assert 'record_count' in tpl or '记录数' in tpl, '模板缺 record_count / 记录数'
        assert 'table-wrap' in tpl or 'overflow-x: auto' in tpl, '缺 table-wrap overflow'


class TestHomeDashboardRedesign:
    """tickets 08-11 · home dashboard 4 主题"""

    def test_home_dashboard_has_state_icon_css(self):
        tpl = (SKILL_DIR / 'templates' / 'home_dashboard.html').read_text(encoding='utf-8')
        assert '.todo-row .state' in tpl or '.state {' in tpl, '缺 .state CSS'

    def test_home_dashboard_log_row_grid(self):
        tpl = (SKILL_DIR / 'templates' / 'home_dashboard.html').read_text(encoding='utf-8')
        assert 'grid-template-columns: 44px 1fr auto' in tpl, 'log-row grid 未收紧'

    def test_home_dashboard_quick_actions_use_prompts(self):
        """render_home 输出的 quick_actions 含 prompt 字段"""
        import sys; sys.path.insert(0, str(SCRIPTS_DIR))
        from render_home import _attach_prompts, QUICK_ACTIONS
        result = _attach_prompts(QUICK_ACTIONS)
        assert all('prompt' in a for a in result), 'quick_actions 缺 prompt 字段'
        eat = next(a for a in result if a['label'] == '记录饮食')
        assert '记一餐' in eat['prompt'], f"记录饮食 prompt 应含 '记一餐', 实得: {eat['prompt'][:80]}"

    def test_home_dashboard_deficit_math_breakdown(self):
        tpl = (SKILL_DIR / 'templates' / 'home_dashboard.html').read_text(encoding='utf-8')
        # 缺口 detail 应有 TDEE + 运动 + 应烧 + 摄入 的 math breakdown(2026-08-02 ticket #2:4 KPI 卡 → 6 KPI 卡,缺口公式条保留)
        assert 'TDEE' in tpl and '应烧' in tpl, '缺口 KPI 缺 math breakdown'
        # 公式条应有 缺口 输出 + 理论体重变化(替代旧 size_label badge · ticket #2)
        assert 'formulaDeficit' in tpl, '缺口公式条缺缺口输出'
        assert 'formulaSummary' in tpl, '缺口公式条缺理论体重变化'
        # 6 KPI 卡口径(ticket #2):饮食/运动/体重/目标/进度/连续
        assert '连续' in tpl and '目标' in tpl and '进度' in tpl, '6 KPI 卡缺维度'


class TestHelpMirrorRename:
    """ticket 05 · ADR-0001 HELP render → 卡路里.html 根镜像"""

    def test_render_help_center_has_no_mirror_flag(self):
        """--no-mirror flag 存在"""
        import subprocess, sys
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / 'render_help_center.py'), '--help'],
            cwd=SKILL_DIR, capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=15,
        )
        assert r.returncode == 0
        assert '--no-mirror' in r.stdout, 'render_help_center 缺 --no-mirror flag'

    def test_mirror_to_root_function_exists(self):
        """mirror_to_root 函数可导入"""
        import sys; sys.path.insert(0, str(SCRIPTS_DIR))
        from render_help_center import mirror_to_root
        assert callable(mirror_to_root)

    def test_mirror_creates_root_html(self, tmp_path):
        """mirror_to_root 把 help html 复制到 skill_dir/卡路里.html"""
        import sys; sys.path.insert(0, str(SCRIPTS_DIR))
        from render_help_center import mirror_to_root
        # 准备一个假 skill_dir(tmp_path)
        fake_skill = tmp_path / 'fakeskill'
        fake_skill.mkdir()
        # 放一个旧的 mirror(模拟 SKILL.md 镜像)
        old_mirror = fake_skill / '卡路里.html'
        old_mirror.write_text('OLD SKILL.md MIRROR', encoding='utf-8')
        # 准备新 HELP html
        help_html = tmp_path / '卡路里_HELP_test.html'
        help_html.write_text('NEW HELP RENDER', encoding='utf-8')
        # 执行
        result = mirror_to_root(help_html, fake_skill)
        assert result is not None
        assert result.name == '卡路里.html'
        assert result.read_text(encoding='utf-8') == 'NEW HELP RENDER'
        # 旧 mirror 备份到 archive
        archive = fake_skill / '.scratch' / 'card-html-redesign' / 'archive'
        assert archive.exists()
        backups = list(archive.glob('卡路里_SKILL镜像_*.html'))
        assert len(backups) == 1
        assert backups[0].read_text(encoding='utf-8') == 'OLD SKILL.md MIRROR'


class TestCrossPagePromptConsistency:
    """ticket 15 · D7 · 跨页面 prompt 一致性"""

    def test_check_prompt_soak_passes(self, tmp_path):
        """scripts/check_prompt_soak.py 自检 exit 0(自渲染模式)

        2026-08-01 重构:不再对比用户数据目录(外部状态——别的 session 渲染
        HELP 会让代码没变的 commit 挂掉),改为自渲染:
        1. tmp_path 设 SKILLS_DB_PATH
        2. render_help_center.py 自渲染(_triggers 唯一权威 · #316 归一化, 无 --runtime 参数)
        3. check_prompt_soak tier 1 读 tmp 渲染产物 -> 与 _triggers 对比
        守护对象 = render 管线不篡改 prompt(纯逻辑不变量),不受开发期
        scene_data 覆盖 / 外部渲染影响 -> commit 不再被设计期过渡态阻塞。
        """
        import subprocess, sys, os
        env = os.environ.copy()
        env.pop("SKILLS_DB_PATH", None)
        env["SKILLS_DB_PATH"] = str(tmp_path)
        # 自渲染:--no-mirror 不写仓库根 mirror(避免污染工作区)
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / 'render_help_center.py'), '--no-mirror'],
            cwd=SKILL_DIR, capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=60,
            env=env,
        )
        assert r.returncode == 0, (
            f'render_help_center.py exit {r.returncode}\n{r.stdout}\n{r.stderr}'
        )
        rendered = list((tmp_path / 'calorie_html').glob('*.html'))
        assert rendered, '自渲染未产出 HELP HTML'
        # soak:读 tmp(tier 1) -> 与 _triggers 对比(同源 -> 必一致)
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / 'check_prompt_soak.py')],
            cwd=SKILL_DIR, capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=30,
            env=env,
        )
        assert r.returncode == 0, (
            f'check_prompt_soak.py exit {r.returncode}\n{r.stdout}\n{r.stderr}'
        )

    def test_home_dashboard_quick_action_prompts_match_triggers(self):
        """每个 quick_action.prompt 与 _triggers main_prompt.text 字节相同"""
        import sys; sys.path.insert(0, str(SCRIPTS_DIR))
        from render_home import _attach_prompts, QUICK_ACTIONS
        from _triggers import TRIGGERS
        wake_to_prompt = {t['wake_word']: t['main_prompt']['text'] for t in TRIGGERS}
        for a in _attach_prompts(QUICK_ACTIONS):
            wake = a.get('wake_word')
            assert wake, f'quick_action {a["label"]} 缺 wake_word'
            assert wake in wake_to_prompt, f'wake_word={wake} 不在 TRIGGERS'
            assert a['prompt'] == wake_to_prompt[wake], (
                f'quick_action {a["label"]}: prompt 与 _triggers 不一致\n'
                f'  dashboard: {a["prompt"][:80]!r}\n'
                f'  triggers:  {wake_to_prompt[wake][:80]!r}'
            )
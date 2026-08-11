# -*- coding: utf-8 -*-
"""Base 注入器守卫测试 v1.2

覆盖:
- 正常注入（占位符替换 + base.js/base.css 注入 + payload 注入）
- 硬拦截反例: 缺 SHARED / 缺 SHARED-CSS / 缺 INJECT / 重复 SHARED / 重复 INJECT / CHARTS 重复
- 豁免通道: <!--NO-SHARED--> 显式声明后 SHARED/CSS 可为 0；豁免但 SHARED 重复 → 拦截
- payload 结构校验: --strict-payload 缺必填字段 → error；非 strict 仅 json 合法性
- CLI 端到端: subprocess 跑 injector.py（临时目录, 无 DB 接触）
"""
import json
import pathlib
import subprocess
import sys

import pytest

INJECTOR_DIR = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(INJECTOR_DIR))

from injector import inject, validate_payload  # noqa: E402

INJECT = '<!--INJECT-DATA-->'
SHARED = '<!--SHARED-HELPERS-->'
SHARED_CSS = '<!--SHARED-CSS-->'
NO_SHARED = '<!--NO-SHARED-->'
CHARTS = '<!--CHARTS-HELPERS-->'

VALID_PAYLOAD = {
    'status': 'ok',
    'data': {
        'meta': {
            'command_cn': '录物品',
            'occurred_at': '2026-08-11 09:20',
            'wake_word': '录物品',
            'skill_version': 'v2.0-SM1',
            'skill_name': '居家管家',
        },
        'scene': {
            'scene_id': 'item-receipt',
            'snapshot': {
                'title': '录物品',
                'summary': ['海蛎煎蛋 已录入'],
                'sections': [{'heading': '明细', 'rows': ['id=1001']}],
            },
        },
    },
}

TEMPLATE_OK = (
    '<!doctype html><html><head><title>t</title>'
    f'<style>{SHARED_CSS}</style>'
    '</head><body>'
    f'<script id="payload" type="application/json">{INJECT}</script>'
    f'<script>{SHARED}</script>'
    '</body></html>'
)


def _js():
    return 'function esc(s){return 1;}'


def _css():
    return ':root{--blue:#007aff}'


# ── 正常注入 ──────────────────────────────────────────────

def test_inject_ok():
    html, err = inject(TEMPLATE_OK, VALID_PAYLOAD, js_asset=_js(), css_asset=_css())
    assert err is None
    assert SHARED not in html and INJECT not in html and SHARED_CSS not in html
    assert 'function esc(' in html
    assert ':root{--blue' in html
    assert '海蛎煎蛋' in html


def test_inject_without_css_ok_for_backward_compat():
    # 兼容: 调用方不传 css_asset → SHARED-CSS 替换为空（存量调用不影响 JS 注入）
    html, err = inject(TEMPLATE_OK, VALID_PAYLOAD, js_asset=_js())
    assert err is None
    assert SHARED_CSS not in html


# ── 硬拦截反例 ────────────────────────────────────────────

def test_missing_shared_blocked():
    src = TEMPLATE_OK.replace(SHARED, '')
    html, err = inject(src, VALID_PAYLOAD, js_asset=_js(), css_asset=_css())
    assert err is not None and 'SHARED-HELPERS' in err and '0 个' in err


def test_missing_shared_css_blocked():
    src = TEMPLATE_OK.replace(SHARED_CSS, '')
    html, err = inject(src, VALID_PAYLOAD, js_asset=_js(), css_asset=_css())
    assert err is not None and 'SHARED-CSS' in err and '0 个' in err


def test_missing_inject_blocked():
    src = TEMPLATE_OK.replace(INJECT, '')
    html, err = inject(src, VALID_PAYLOAD, js_asset=_js(), css_asset=_css())
    assert err is not None and 'INJECT-DATA' in err and '0 个' in err


def test_duplicate_shared_blocked():
    src = TEMPLATE_OK.replace(SHARED, SHARED + SHARED)
    html, err = inject(src, VALID_PAYLOAD, js_asset=_js(), css_asset=_css())
    assert err is not None and '2 个' in err


def test_duplicate_inject_blocked():
    src = TEMPLATE_OK.replace(INJECT, INJECT + INJECT)
    html, err = inject(src, VALID_PAYLOAD, js_asset=_js(), css_asset=_css())
    assert err is not None and '2 个' in err


def test_duplicate_charts_blocked():
    src = TEMPLATE_OK.replace(SHARED, SHARED + CHARTS + CHARTS)
    html, err = inject(src, VALID_PAYLOAD, js_asset=_js(), css_asset=_css())
    assert err is not None and 'CHARTS-HELPERS' in err and '2 次' in err


# ── 豁免通道 ──────────────────────────────────────────────

def test_no_shared_exempt_ok():
    # 豁免: SHARED + CSS 都要为 0 → 用 NO-SHARED 替换两个占位符
    src = TEMPLATE_OK.replace(SHARED, NO_SHARED).replace(SHARED_CSS, '')
    html, err = inject(src, VALID_PAYLOAD, js_asset=_js(), css_asset=_css())
    assert err is None
    assert NO_SHARED not in html  # 标记本身被移除
    assert '海蛎煎蛋' in html


def test_no_shared_with_shared_conflict_blocked():
    # 声明豁免但仍有 SHARED → 互斥冲突拦截
    src = TEMPLATE_OK.replace(SHARED, NO_SHARED + SHARED).replace(SHARED_CSS, '')
    html, err = inject(src, VALID_PAYLOAD, js_asset=_js(), css_asset=_css())
    assert err is not None and '豁免' in err


def test_no_shared_duplicate_blocked():
    src = TEMPLATE_OK.replace(SHARED, NO_SHARED + NO_SHARED).replace(SHARED_CSS, '')
    html, err = inject(src, VALID_PAYLOAD, js_asset=_js(), css_asset=_css())
    assert err is not None and 'NO-SHARED' in err and '最多出现 1 次' in err


# ── payload 结构校验 ──────────────────────────────────────

def test_validate_payload_strict_ok():
    assert validate_payload(VALID_PAYLOAD, strict=True) == (True, '')


@pytest.mark.parametrize('mutate,missing', [
    (lambda p: p.update({'status': 'error'}), 'status'),
    (lambda p: p['data']['meta'].pop('command_cn'), 'command_cn'),
    (lambda p: p['data']['meta'].pop('occurred_at'), 'occurred_at'),
    (lambda p: p['data'].pop('scene'), 'scene'),
])
def test_validate_payload_strict_missing(mutate, missing):
    p = json.loads(json.dumps(VALID_PAYLOAD))
    mutate(p)
    ok, msg = validate_payload(p, strict=True)
    assert not ok and missing in msg


def test_validate_payload_non_strict_passes():
    # 非 strict: 仅 json 合法性, 信封字段缺失不拦截（存量技能过渡）
    p = {'status': 'ok', 'data': {'scene': {}}}
    ok, msg = validate_payload(p, strict=False)
    assert ok


def test_inject_strict_missing_meta_blocked():
    p = json.loads(json.dumps(VALID_PAYLOAD))
    p['data']['meta'].pop('command_cn')
    html, err = inject(TEMPLATE_OK, p, js_asset=_js(), css_asset=_css(), strict=True)
    assert err is not None and 'command_cn' in err


# ── CLI 端到端 ────────────────────────────────────────────

def test_cli_end_to_end(tmp_path):
    """真实 CLI 调用: 正常注入 + 硬拦截 + 豁免 + strict 校验（全走临时目录）"""
    tpl = tmp_path / 'tpl.html'
    tpl.write_text(TEMPLATE_OK, encoding='utf-8')
    payload = tmp_path / 'p.json'
    payload.write_text(json.dumps(VALID_PAYLOAD, ensure_ascii=False), encoding='utf-8')
    out = tmp_path / 'out.html'

    r = subprocess.run(
        [sys.executable, str(INJECTOR_DIR / 'injector.py'), str(tpl),
         '--payload', str(payload), '--output', str(out), '--strict-payload'],
        capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert r.returncode == 0, r.stdout + r.stderr
    result = json.loads(r.stdout)
    assert result['status'] == 'ok'
    html = out.read_text(encoding='utf-8')
    assert SHARED not in html and '海蛎煎蛋' in html
    assert ':root { --fg' in html or '--blue: #007aff' in html  # base.css 已注入

    # 硬拦截: 模板缺 SHARED → CLI 退出码 1 + status error
    tpl_broken = tmp_path / 'broken.html'
    tpl_broken.write_text(TEMPLATE_OK.replace(SHARED, ''), encoding='utf-8')
    r2 = subprocess.run(
        [sys.executable, str(INJECTOR_DIR / 'injector.py'), str(tpl_broken),
         '--payload', str(payload), '--output', str(tmp_path / 'b.html')],
        capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert r2.returncode == 1
    assert json.loads(r2.stdout)['status'] == 'error'

    # 硬拦截: 模板缺 SHARED-CSS → CLI 退出码 1
    tpl_nocss = tmp_path / 'nocss.html'
    tpl_nocss.write_text(TEMPLATE_OK.replace(SHARED_CSS, ''), encoding='utf-8')
    r2b = subprocess.run(
        [sys.executable, str(INJECTOR_DIR / 'injector.py'), str(tpl_nocss),
         '--payload', str(payload), '--output', str(tmp_path / 'b2.html')],
        capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert r2b.returncode == 1
    assert 'SHARED-CSS' in json.loads(r2b.stdout)['message']

    # strict 校验: 缺必填字段 → CLI error
    p_bad = {'status': 'ok', 'data': {'scene': {}}}
    payload_bad = tmp_path / 'p_bad.json'
    payload_bad.write_text(json.dumps(p_bad), encoding='utf-8')
    r3 = subprocess.run(
        [sys.executable, str(INJECTOR_DIR / 'injector.py'), str(tpl),
         '--payload', str(payload_bad), '--output', str(tmp_path / 'c.html'),
         '--strict-payload'],
        capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert r3.returncode == 1
    assert 'command_cn' in json.loads(r3.stdout)['message']

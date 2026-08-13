# -*- coding: utf-8 -*-
"""HELP 参数化模板守卫测试 v1

覆盖:
- 模板资产存在 + 3 占位符恰 1（INJECT-DATA / SHARED-HELPERS / SHARED-CSS）
- 示例 scene-data 契约数据注入渲染：输出含技能名/场景数/分组/复制按钮/Toast
- 注入后占位符 0 残留
- 反例：缺必填字段 / status 非法 / 空 groups / id 重复 → validate_help_data 拒绝
- 文件名 sanitize：正常生成 help_<技能名>.html；含路径穿越字符 → 拒绝
- CLI 端到端：subprocess 跑 injector.py --help-template（临时目录, 无 DB 接触）
"""
import json
import pathlib
import subprocess
import sys

import pytest

BASE_DIR = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from injector import validate_help_data, sanitize_help_filename  # noqa: E402

HELP_TEMPLATE = BASE_DIR / 'assets' / 'help_template.html'
INJECT = '<!--INJECT-DATA-->'
SHARED = '<!--SHARED-HELPERS-->'
SHARED_CSS = '<!--SHARED-CSS-->'

VALID_HELP = {
    'skill_name': '作息管家',
    'title': '能力速查台',
    'subtitle': '作息记录与日程计划管理',
    'meta_blocks': [
        {'id': 'usage', 'title': '使用须知', 'html': '<p>先记作息，再看总结。</p>'},
    ],
    'init_banner': {
        'title': '🚀 第一次用作息管家?',
        'subtitle': '自动检测环境、初始化数据库。',
        'button_text': '📋 复制',
        'prompt': '请你加载「作息管家」技能,帮我初始化(唤醒词:首次使用)。',
    },
    'groups': [
        {
            'id': 'record', 'icon': '✍️', 'label': '记作息',
            'subgroups': [
                {
                    'id': 'record_single', 'label': '单条记录',
                    'scenes': [
                        {
                            'id': 'record_add_single', 'title': '添加单条作息记录',
                            'wake_word': '#0 记作息',
                            'types': ['采集', {'text': '过程', 'bg': '#e2f7f5', 'fg': '#00897b'}],
                            'status': '',
                            'prompt_template': '请帮我记一条作息:今天 14:00-15:00 写了 AI 调优代码',
                            'editable_fields': [
                                {'name': 'activity', 'label': '活动', 'value': '',
                                 'hint': '如: 写了 AI 调优代码', 'required': True},
                            ],
                        },
                        {
                            'id': 'record_add_json', 'title': '通过 JSON 文件批量添加',
                            'wake_word': '#0 记作息', 'types': ['采集'], 'status': '【待开发】',
                            'prompt_template': '请帮我批量导入这些作息数据(从 JSON 文件)',
                        },
                    ],
                },
            ],
        },
    ],
}


class TestTemplateAsset:
    """模板资产存在 + 占位符守卫"""

    def test_template_exists(self):
        assert HELP_TEMPLATE.exists(), 'help_template.html 资产缺失'

    def test_three_placeholders_exactly_one(self):
        text = HELP_TEMPLATE.read_text(encoding='utf-8')
        assert text.count(INJECT) == 1, f'{INJECT} 必须恰好 1'
        assert text.count(SHARED) == 1, f'{SHARED} 必须恰好 1'
        assert text.count(SHARED_CSS) == 1, f'{SHARED_CSS} 必须恰好 1'

    def test_asset_comment_no_close_tag(self):
        """资产注释勿含 </script>/</style> 字样（HTML 解析提前截断陷阱）"""
        text = HELP_TEMPLATE.read_text(encoding='utf-8')
        # 提取所有 /* ... */ 注释块（CSS 头 + JS 注释），断言不含闭合标签字样
        import re
        comments = re.findall(r'/\*.*?\*/', text, flags=re.S)
        assert comments, '模板应含注释块'
        for c in comments:
            for bad in ('</script>', '</style>'):
                assert bad not in c, f'注释块含 {bad}: {c[:60]}'


class TestValidateHelpData:
    """scene-data 契约校验"""

    def test_valid_passes(self):
        ok, msg = validate_help_data(json.loads(json.dumps(VALID_HELP)))
        assert ok, msg

    def test_missing_skill_name(self):
        d = json.loads(json.dumps(VALID_HELP))
        del d['skill_name']
        ok, _ = validate_help_data(d)
        assert not ok

    def test_missing_groups(self):
        d = json.loads(json.dumps(VALID_HELP))
        del d['groups']
        ok, _ = validate_help_data(d)
        assert not ok

    def test_empty_groups(self):
        d = json.loads(json.dumps(VALID_HELP))
        d['groups'] = []
        ok, _ = validate_help_data(d)
        assert not ok

    def test_scene_missing_prompt(self):
        d = json.loads(json.dumps(VALID_HELP))
        del d['groups'][0]['subgroups'][0]['scenes'][0]['prompt_template']
        ok, msg = validate_help_data(d)
        assert not ok
        assert 'prompt_template' in msg

    def test_illegal_status(self):
        d = json.loads(json.dumps(VALID_HELP))
        d['groups'][0]['subgroups'][0]['scenes'][0]['status'] = '【已完成】'
        ok, _ = validate_help_data(d)
        assert not ok

    def test_duplicate_scene_id(self):
        d = json.loads(json.dumps(VALID_HELP))
        d['groups'][0]['subgroups'][0]['scenes'].append(
            json.loads(json.dumps(d['groups'][0]['subgroups'][0]['scenes'][0])))
        ok, msg = validate_help_data(d)
        assert not ok
        assert '重复' in msg

    def test_editable_fields_missing_name(self):
        d = json.loads(json.dumps(VALID_HELP))
        d['groups'][0]['subgroups'][0]['scenes'][0]['editable_fields'][0].pop('name')
        ok, _ = validate_help_data(d)
        assert not ok


class TestSanitizeFilename:
    """文件名 sanitize（help-template-contract §4）"""

    def test_normal_skill_name(self):
        name, err = sanitize_help_filename('作息管家')
        assert err is None
        assert name == 'help_作息管家.html'

    def test_ascii_skill_name(self):
        name, err = sanitize_help_filename('card')
        assert err is None
        assert name == 'help_card.html'

    def test_path_traversal_rejected(self):
        for bad in ('../etc/passwd', 'a/b', 'a\\b', '..'):
            name, err = sanitize_help_filename(bad)
            assert err is not None, f'路径穿越应拒绝: {bad}'
            assert name is None


class TestRenderEndToEnd:
    """注入渲染端到端（CLI subprocess · 临时目录）"""

    @pytest.fixture()
    def tmp_out(self, tmp_path):
        return tmp_path / 'out'

    def _run(self, tmp_out, help_data, output=None, extra_args=None):
        payload = tmp_out.parent / 'help_data.json'
        payload.write_text(json.dumps(help_data, ensure_ascii=False), encoding='utf-8')
        args = [sys.executable, str(BASE_DIR / 'injector.py'),
                str(HELP_TEMPLATE), '--payload', str(payload),
                '--help-template', '--output', str(tmp_out / 'x.html')] \
            if output is None else [sys.executable, str(BASE_DIR / 'injector.py'),
                                    str(HELP_TEMPLATE), '--payload', str(payload),
                                    '--help-template', '--output', str(output)]
        if extra_args:
            args.extend(extra_args)
        r = subprocess.run(args, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        return r

    def test_render_ok(self, tmp_out):
        r = self._run(tmp_out, VALID_HELP)
        assert r.returncode == 0, r.stdout + r.stderr
        out = json.loads(r.stdout)
        assert out['status'] == 'ok'
        html = (tmp_out / 'x.html').read_text(encoding='utf-8')
        assert '能力速查台' in html          # title
        assert '作息管家' in html            # skill_name
        assert '添加单条作息记录' in html     # scene title
        assert '请帮我记一条作息' in html     # prompt
        assert '"types"' in html             # types 数组注入（多标签契约）
        assert INJECT not in html            # 占位符 0 残留
        assert SHARED not in html
        assert SHARED_CSS not in html

    def test_render_rejects_invalid_data(self, tmp_out):
        bad = json.loads(json.dumps(VALID_HELP))
        del bad['skill_name']
        r = self._run(tmp_out, bad)
        assert r.returncode == 1
        out = json.loads(r.stdout)
        assert out['status'] == 'error'
        assert 'HELP 数据校验失败' in out['message']

    def test_render_rejects_unsafe_output_filename(self, tmp_out):
        r = self._run(tmp_out, VALID_HELP, output=str(tmp_out / '../evil.html'))
        assert r.returncode == 1
        out = json.loads(r.stdout)
        assert out['status'] == 'error'
        assert ('穿越' in out['message'] or '不安全' in out['message'])

    def test_render_default_filename_by_skill(self, tmp_out):
        """不传 --output 时缺省文件名 = help_<技能名>.html,且落盘在模板同目录 out/ 下

        模板复制到临时目录后再跑无 --output 调用:缺省产物落在临时 out/ 下,
        保留真实缺省语义,同时不触碰仓库目录(防 assets/out 残留,见 #325)。
        """
        tmp_template = tmp_out.parent / 'help_template_copy.html'
        tmp_template.write_bytes(HELP_TEMPLATE.read_bytes())
        payload = tmp_out.parent / 'help_data.json'
        payload.write_text(json.dumps(VALID_HELP, ensure_ascii=False), encoding='utf-8')
        args = [sys.executable, str(BASE_DIR / 'injector.py'),
                str(tmp_template), '--payload', str(payload), '--help-template']
        r = subprocess.run(args, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        assert r.returncode == 0, r.stdout + r.stderr
        out = json.loads(r.stdout)
        expected = tmp_out.parent / 'out' / 'help_作息管家.html'
        assert str(out['data']['output']) == str(expected)
        assert expected.exists(), '缺省产物应落在临时目录 out/ 下'

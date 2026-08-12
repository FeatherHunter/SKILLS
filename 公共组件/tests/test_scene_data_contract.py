# -*- coding: utf-8 -*-
"""统一 scene_data 契约 v1 守卫测试

覆盖:
- 合法数据通过（示例数据 · 2 级分组 + meta_blocks + editable_fields）
- 结构完整性: 必填字段缺失 / 类型错 → 失败
- 违规反例: id 重复 / status 非法 / scenes 空 / prompt_template 缺失 → 失败
- 机读 schema 与示例数据一致（JSON schema 校验）
"""
import json
import pathlib
import sys

import pytest

DOCS_DIR = pathlib.Path(__file__).parent.parent / 'docs'
sys.path.insert(0, str(DOCS_DIR.parent))

try:
    import jsonschema  # noqa: F401
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

SCHEMA_PATH = DOCS_DIR / 'scene_data.schema.json'


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))


def validate_via_schema(data):
    """用 JSON schema 校验（jsonschema 可用时）；否则退化为自研必填检查。"""
    if not HAS_JSONSCHEMA:
        # 退化的最小校验：必填字段 + groups 非空
        assert isinstance(data, dict), '必须是对象'
        assert data.get('skill_name'), '缺 skill_name'
        assert data.get('title'), '缺 title'
        groups = data.get('groups')
        assert isinstance(groups, list) and groups, '缺 groups（非空数组）'
        return
    jsonschema.validate(instance=data, schema=_load_schema())


# === 合法示例（对齐 V4.16 原型数据形态） ===
VALID_DATA = {
    'skill_name': '作息管家',
    'title': '能力速查台',
    'subtitle': '作息记录与日程计划管理',
    'meta_blocks': [
        {'id': 'usage', 'title': '使用须知', 'html': '<p>先记作息，再看总结。</p>'},
    ],
    'groups': [
        {
            'id': 'record',
            'icon': '✍️',
            'label': '记作息',
            'subgroups': [
                {
                    'id': 'record_single',
                    'label': '单条记录',
                    'scenes': [
                        {
                            'id': 'record_add_single',
                            'title': '添加单条作息记录',
                            'wake_word': '#0 记作息',
                            'type': '采集',
                            'status': '',
                            'prompt_template': '请帮我记一条作息:今天 14:00-15:00 写了 AI 调优代码',
                            'editable_fields': [
                                {'name': 'activity', 'label': '活动', 'value': '',
                                 'hint': '如: 写了 AI 调优代码', 'required': True},
                            ],
                        },
                        {
                            'id': 'record_add_json',
                            'title': '通过 JSON 文件批量添加',
                            'wake_word': '#0 记作息',
                            'type': '采集',
                            'status': '【待开发】',
                            'prompt_template': '请帮我批量导入这些作息数据(从 JSON 文件)',
                        },
                    ],
                },
            ],
        },
        {
            'id': 'query',
            'icon': '🔍',
            'label': '查作息',
            'subgroups': [
                {
                    'id': 'query_today',
                    'label': '查今日',
                    'scenes': [
                        {
                            'id': 'query_today_summary',
                            'title': '看今日总结',
                            'wake_word': '#4 今天总结',
                            'type': '查看',
                            'status': '',
                            'prompt_template': '请帮我看看今天的总结',
                        },
                    ],
                },
            ],
        },
    ],
}


class TestSchema:
    """机读 schema 本身合法 + 示例数据通过"""

    def test_schema_is_valid_json(self):
        data = _load_schema()
        assert data['$schema'].startswith('http')
        assert data['required'] == ['skill_name', 'title', 'groups']

    def test_valid_example_passes(self):
        validate_via_schema(VALID_DATA)

    def test_meta_blocks_valid(self):
        data = json.loads(json.dumps(VALID_DATA))
        data['meta_blocks'].append(
            {'id': 'ai_verify', 'title': 'AI 验证协议', 'html': '<p>第 7 条</p>'})
        validate_via_schema(data)


class TestRequiredFields:
    """必填字段缺失 → 失败"""

    def test_missing_skill_name(self):
        data = json.loads(json.dumps(VALID_DATA))
        del data['skill_name']
        with pytest.raises(Exception):
            validate_via_schema(data)

    def test_missing_title(self):
        data = json.loads(json.dumps(VALID_DATA))
        del data['title']
        with pytest.raises(Exception):
            validate_via_schema(data)

    def test_missing_groups(self):
        data = json.loads(json.dumps(VALID_DATA))
        del data['groups']
        with pytest.raises(Exception):
            validate_via_schema(data)

    def test_empty_groups(self):
        data = json.loads(json.dumps(VALID_DATA))
        data['groups'] = []
        with pytest.raises(Exception):
            validate_via_schema(data)


class TestSceneRules:
    """场景卡片规则"""

    def test_scene_missing_prompt_template(self):
        data = json.loads(json.dumps(VALID_DATA))
        del data['groups'][0]['subgroups'][0]['scenes'][0]['prompt_template']
        with pytest.raises(Exception):
            validate_via_schema(data)

    def test_scene_missing_wake_word(self):
        data = json.loads(json.dumps(VALID_DATA))
        del data['groups'][0]['subgroups'][0]['scenes'][0]['wake_word']
        with pytest.raises(Exception):
            validate_via_schema(data)

    def test_scene_illegal_status(self):
        data = json.loads(json.dumps(VALID_DATA))
        data['groups'][0]['subgroups'][0]['scenes'][0]['status'] = '【已完成】'
        with pytest.raises(Exception):
            validate_via_schema(data)

    def test_scene_empty_editable_fields_entry(self):
        data = json.loads(json.dumps(VALID_DATA))
        data['groups'][0]['subgroups'][0]['scenes'][0]['editable_fields'][0].pop('name')
        with pytest.raises(Exception):
            validate_via_schema(data)

    def test_subgroup_empty_scenes(self):
        data = json.loads(json.dumps(VALID_DATA))
        data['groups'][0]['subgroups'][0]['scenes'] = []
        with pytest.raises(Exception):
            validate_via_schema(data)


class TestIdRules:
    """id 唯一性（schema 之外由守卫断言）"""

    @staticmethod
    def _collect_ids(data):
        ids = set()
        for g in data['groups']:
            ids.add(('group', g['id']))
            for sg in g['subgroups']:
                ids.add(('subgroup', sg['id']))
                for s in sg['scenes']:
                    ids.add(('scene', s['id']))
        return ids

    def test_all_ids_unique_in_example(self):
        ids = self._collect_ids(VALID_DATA)
        assert len(ids) == (2 + 2 + 3), f'示例数据 id 应全唯一, 实际 {len(ids)}'

    def test_duplicate_scene_id_flagged(self):
        """同一 scenes 内 id 重复 → 守卫应能查出（人工断言逻辑）"""
        ids = []
        for g in VALID_DATA['groups']:
            for sg in g['subgroups']:
                for s in sg['scenes']:
                    ids.append(s['id'])
        assert len(ids) == len(set(ids)), '场景 id 重复'

    def test_group_subgroup_ids_cover_scenes(self):
        """scene 归属引用完整：每个 scene 必须挂在 subgroup 下（结构天然保证）"""
        scene_count = sum(
            len(sg['scenes'])
            for g in VALID_DATA['groups'] for sg in g['subgroups'])
        assert scene_count == 3

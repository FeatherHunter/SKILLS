#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_profile_setup.py — 设置档案 HTML 渲染器(配置型)

对应 SKILL.md 唤醒词: 设置档案
对应模板: templates/profile_setup.html

数据来源(二选一):
  --mock <json>  mock 数据(测试)
  --live         实读 user_profile(接 DB · #23A 决策 2026-08-02)
"""
import argparse, json, sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'profile_setup.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa


def _load_data(input_path):
    raw = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if raw.get('status') != 'ok':
        raise ValueError('数据状态非 ok')
    return raw


def build_live_data():
    """实读 user_profile 生成设置档案配置(#23A · 2026-08-02)

    已有档案 → 预填当前值(改档案式引导);无档案 → 默认值。
    """
    import profile

    prof = profile.get_profile()
    defaults = {
        'age': prof.get('age') or 30,
        'gender': prof.get('gender') or 'male',
        'height': prof.get('height_cm') or 177,
        'activity': prof.get('activity_level') or 'moderate',
        'note': prof.get('note') or '',
    }
    subtitle = '设置年龄/性别/身高/活动量,系统用 Mifflin-St Jeor 公式计算 BMR 和 TDEE'
    if prof.get('age'):
        subtitle = '修改年龄/性别/身高/活动量,当前值已预填,改完复制 prompt 给 AI'

    fields = [
        {"key": "age", "label": "年龄", "type": "number", "required": True,
         "placeholder": "30", "hint": "用于 BMR 计算"},
        {"key": "gender", "label": "性别", "type": "select", "required": True,
         "options": [{"value": "male", "label": "男"}, {"value": "female", "label": "女"}]},
        {"key": "height", "label": "身高(cm)", "type": "number", "required": True,
         "placeholder": "177", "hint": "用于 BMI"},
        {"key": "activity", "label": "活动量", "type": "select", "required": False,
         "options": [
             {"value": "sedentary", "label": "久坐(几乎不运动)"},
             {"value": "light", "label": "轻度(每周 1-3 次轻度运动)"},
             {"value": "moderate", "label": "中度(每周 3-5 次中等强度运动)"},
             {"value": "active", "label": "活跃(每周 6-7 次高强度运动)"},
             {"value": "very_active", "label": "高度活跃(每天高强度运动 + 体力劳动)"},
         ],
         "hint": "影响 TDEE 系数,不知道选哪个可留空让 AI 推荐"},
        {"key": "note", "label": "备注", "type": "textarea", "hint": "可选"},
    ]

    return {
        'status': 'ok',
        'data': {
            'fields': fields,
            'defaults': defaults,
            'exec_cmd_template': 'calorie_tracker.py profile set {age} {gender} --height {height} --activity {activity} # optional: --note {note}',
            'exec_cmd_optional': 'note',
            'meta': {
                'fetched_at': datetime.now().isoformat(timespec='seconds')[:16].replace('T', ' '),
                'subtitle': subtitle,
            },
        },
        'message': '已生成设置档案 配置(live)',
    }


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description='渲染设置档案 HTML')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--mock', help='mock JSON 文件路径')
    g.add_argument('--live', action='store_true', help='实读 user_profile 接 DB(#23A)')
    p.add_argument('--output')
    args = p.parse_args()
    try:
        if args.mock:
            data = _load_data(args.mock)
        else:
            data = build_live_data()
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, '档案设置')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    print(f'✅ {out_path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

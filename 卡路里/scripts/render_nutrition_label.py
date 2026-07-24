#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_nutrition_label.py — 拍营养表 · AI 识别预览向导 HTML 渲染器

对应 SKILL.md 唤醒词:拍营养表 / 识别营养表 / 营养成分确认

设计原则:
- 过程型 HTML(AI 协同模式 · 原则 10)
- 必含 2 个复制按钮:采纳 + 修改后复制
- 4 部分 prompt 模板:场景+数据+期望+来源

使用流程:
    1. 跑 mmx vision describe --image <图片>
    2. 把 JSON 输出保存到文件
    3. python scripts/render_nutrition_label.py --ai-json <JSON文件>
    4. Chrome 打开 HTML,核对/修改字段
    5. 点'采纳保存'或'复制修改指令'
    6. 把复制内容粘到 AI 对话框,AI 自动存库

用法:
    python scripts/render_nutrition_label.py --ai-json mock_nutrition_label.json
    python scripts/render_nutrition_label.py --ai-json <JSON> --image-meta filename=xxx.jpg  # 可选
    python scripts/render_nutrition_label.py --ai-json <JSON> --output /path/to/wizard.html
"""
import argparse
import json
from html_paths import html_path
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'nutrition_label_wizard.html'


def build_parser():
    p = argparse.ArgumentParser(
        prog="render_nutrition_label",
        description="渲染拍营养表 wizard HTML(过程型 · AI 协同模式)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('--ai-json', required=True,
                   help='mmx vision describe 输出 JSON 文件路径')
    p.add_argument('--output', help='输出文件路径(默认 /tmp)')
    return p


def load_ai_output(ai_json_path: Path) -> dict:
    """加载 mmx 输出 + 标准化字段"""
    if not ai_json_path.exists():
        raise FileNotFoundError(f"AI JSON 文件不存在: {ai_json_path}")

    raw = json.loads(ai_json_path.read_text(encoding='utf-8'))

    # 兼容两种格式:
    # 格式 A: { ai_output: {...}, image_meta: {...} }  (我们约定的格式)
    # 格式 B: 直接就是 {...} (mmx 实际输出)
    if 'ai_output' in raw:
        ai_output = raw['ai_output']
        image_meta = raw.get('image_meta', {})
    else:
        ai_output = raw
        image_meta = raw.pop('image_meta', {})

    # 字段映射(mmx 输出可能字段名不同,这里做标准化)
    field_mapping = {
        'product_name': ['product_name', 'name', 'product', '名称', '食品名称', '产品名'],
        'brand': ['brand', 'manufacturer', '品牌'],
        'calories': ['calories', 'energy', '热量', '能量'],
        'protein': ['protein', '蛋白质'],
        'fat': ['fat', 'total_fat', '脂肪', '总脂肪'],
        'saturated_fat': ['saturated_fat', '饱和脂肪'],
        'carbohydrates': ['carbohydrates', 'carbs', '碳水', '碳水化合物'],
        'sugar': ['sugar', '糖'],
        'fiber': ['fiber', 'dietary_fiber', '膳食纤维', '纤维素'],
        'sodium': ['sodium', 'salt', '钠'],
        'serving_size': ['serving_size', '每份大小'],
        'servings_per_container': ['servings_per_container', '每包装份数'],
        'note': ['note', 'notes', '备注'],
    }

    normalized = {}
    for standard_key, possible_keys in field_mapping.items():
        value = None
        for k in possible_keys:
            if k in ai_output:
                value = ai_output[k]
                break
        normalized[standard_key] = value

    # 推断 image_meta
    if not image_meta:
        image_meta = {
            'filename': ai_json_path.stem,
            'source': 'mmx vision describe',
            'described_at': '未知',
        }

    return {
        'image_meta': image_meta,
        'ai_output': normalized,
    }


def render_html(data: dict) -> str:
    """读模板 + 注入数据"""
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f"模板占位符数量异常: {template.count(placeholder)}")

    payload = json.dumps({'status': 'ok', 'data': data, 'message': '营养成分确认向导已生成'},
                         ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


def main():
    args = build_parser().parse_args()
    ai_json_path = Path(args.ai_json)

    try:
        data = load_ai_output(ai_json_path)
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, f'nutrition_label_wizard_{ai_json_path.stem}')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    meta = data['image_meta']
    print(f'✅ {out_path}')
    print(f'   来源: {meta.get("filename", "?")} · {meta.get("described_at", "?")}')
    print(f'   字段: {len(data["ai_output"])} 个 (13 个标准字段 + note)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
"""硬规则校验器:add / preview 共用单一权威源

按 SKILL 架构第③规则层: 硬规则集中在 validators.py, 无跳过通道。
返回结构: (checks: dict, missing: list[str])
"""
from typing import Any


def _coerce_tags(tags: Any) -> list[str]:
    """接受 list 或逗号分隔字符串, 返回干净的 tag 列表"""
    if isinstance(tags, list):
        return [str(t).strip() for t in tags if str(t).strip()]
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(',') if t.strip()]
    return []


def validate_hard_rules(draft: dict) -> tuple[dict, list[str]]:
    """校验 add 录入的 5 条硬规则

    检查项:
      - has_name:         名称非空
      - has_category_id:  category_id 非空
      - location_depth_ok: 位置路径至少两级(含 '/')
      - tags_ok:          tag 数量 ≥ 10
      - remark_ok:        备注非空

    参数:
      draft: 字典, 接受以下键:
             name (str), category_id (int|str|None),
             location (str), tags (list|str), remark (str)

    返回:
      (checks, missing)
      checks: 5 个 bool + ready_score(float)
      missing: 不通过的检查项对应错误信息(空数组 = 全部通过)
    """
    name = (draft.get('name') or '').strip()
    category_id = draft.get('category_id')
    location = (draft.get('location') or '').strip()
    tags = _coerce_tags(draft.get('tags'))
    remark = (draft.get('remark') or '').strip()

    checks = {
        'has_name': bool(name),
        'has_category_id': category_id not in (None, ''),
        'location_depth_ok': '/' in location.strip('/'),
        'tags_ok': len(tags) >= 10,
        'remark_ok': bool(remark),
    }
    missing: list[str] = []
    if not checks['has_name']:
        missing.append('缺少物品名称')
    if not checks['has_category_id']:
        missing.append('缺少 category_id')
    if not checks['location_depth_ok']:
        missing.append('位置必须至少两级')
    if not checks['tags_ok']:
        missing.append(f'tag 数量 {len(tags)} < 10')
    if not checks['remark_ok']:
        missing.append('备注不能为空')

    checks['ready_score'] = sum(
        1 for k, v in checks.items() if k != 'ready_score' and v is True
    ) / 5

    return checks, missing
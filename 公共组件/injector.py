# -*- coding: utf-8 -*-
"""Base Skill 注入器 v1.1（公共组件/ 正式版）

契约: docs/component-contract.md v1.1
- <!--INJECT-DATA-->     数据注入点: 必须恰好 1 个（缺失/重复 → 硬拦截失败）
- <!--SHARED-HELPERS-->  公共 JS 注入点: 必须恰好 1 个（缺失 → 硬拦截失败）
- <!--NO-SHARED-->       豁免通道: 显式声明后 SHARED 可为 0（白名单式, 防隐式豁免）
- <!--CHARTS-HELPERS-->  图表组件注入点: 0 或 1 个（可选, 第二版）

用法:
  python injector.py <模板.html> --payload <数据.json> [--output <输出.html>] [--js <资产.js>] [--charts <图表.js>] [--strict-payload]

输出: 写文件 + 打印结果 JSON（status ok/error）, 模仿居家管家 emit 契约。
"""
import argparse
import json
import pathlib
import sys

BASE_DIR = pathlib.Path(__file__).resolve().parent
ASSETS = BASE_DIR / 'assets'
DEFAULT_JS = ASSETS / 'base.js'

INJECT_DATA = '<!--INJECT-DATA-->'
SHARED_HELPERS = '<!--SHARED-HELPERS-->'
NO_SHARED = '<!--NO-SHARED-->'
CHARTS_HELPERS = '<!--CHARTS-HELPERS-->'

# payload 信封必填字段（契约 §4）
_REQUIRED = {
    'status': lambda v: v == 'ok',
    'data.meta.command_cn': lambda v: isinstance(v, str) and bool(v.strip()),
    'data.meta.occurred_at': lambda v: isinstance(v, str) and bool(v.strip()),
    'data.scene': lambda v: isinstance(v, dict),
}


def _deep_get(d, dotted):
    cur = d
    for part in dotted.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def validate_payload(payload, strict=False):
    """payload 结构校验。strict=True 时校验信封必填字段。返回 (ok, msg)"""
    if not isinstance(payload, dict):
        return False, 'payload 必须是 JSON 对象'
    if strict:
        missing = [k for k, check in _REQUIRED.items()
                   if not check(_deep_get(payload, k))]
        if missing:
            return False, f'payload 缺必填字段: {", ".join(missing)}（信封契约 §4）'
    return True, ''


def load_asset(path, label):
    if not path.exists():
        return None, f'资产缺失: {path}（{label}）'
    return path.read_text(encoding='utf-8').strip(), None


def inject(template_text, payload, js_asset=None, charts_asset=None, strict=False):
    """核心注入逻辑（可测）。返回 (html, error)"""
    # ── 守卫校验（硬拦截）──
    if template_text.count(INJECT_DATA) != 1:
        return None, (f'模板必须包含恰好 1 个 {INJECT_DATA}，'
                      f'实际 {template_text.count(INJECT_DATA)} 个（缺失或重复）')

    # 豁免通道: 显式 NO-SHARED 声明 → SHARED 必须 0（白名单式）；缺省 → 必须恰好 1
    no_shared_count = template_text.count(NO_SHARED)
    if no_shared_count > 1:
        return None, f'{NO_SHARED} 最多出现 1 次，实际 {no_shared_count} 次'
    no_shared = no_shared_count == 1
    shared_count = template_text.count(SHARED_HELPERS)
    if no_shared:
        if shared_count != 0:
            return None, (f'模板声明 {NO_SHARED} 豁免但仍有 {SHARED_HELPERS} '
                          f'（{shared_count} 个）——豁免与占位符互斥，拒绝渲染')
    elif shared_count != 1:
        return None, (f'模板必须包含恰好 1 个 {SHARED_HELPERS}（公共组件声明点），'
                      f'实际 {shared_count} 个——未接入 Base 管线，拒绝渲染')

    if template_text.count(CHARTS_HELPERS) > 1:
        return None, (f'{CHARTS_HELPERS} 最多出现 1 次，'
                      f'实际 {template_text.count(CHARTS_HELPERS)} 次')

    # payload 结构校验
    ok, msg = validate_payload(payload, strict=strict)
    if not ok:
        return None, f'payload 校验失败: {msg}'

    # ── 注入（SHARED → CHARTS → DATA）──
    html = template_text
    if no_shared:
        # 豁免: 移除 NO-SHARED 标记本身
        html = html.replace(NO_SHARED, '', 1)
    if js_asset is not None:
        html = html.replace(SHARED_HELPERS, js_asset, 1)
    else:
        html = html.replace(SHARED_HELPERS, '', 1)
    if charts_asset is not None:
        html = html.replace(CHARTS_HELPERS, charts_asset, 1)
    else:
        html = html.replace(CHARTS_HELPERS, '', 1)
    payload_text = json.dumps(payload, ensure_ascii=False).replace('</', '<\\/')
    html = html.replace(INJECT_DATA, payload_text, 1)
    return html, None


def main():
    ap = argparse.ArgumentParser(description='Base 注入器 v1.1')
    ap.add_argument('template', help='模板 HTML 路径')
    ap.add_argument('--payload', required=True, help='payload JSON 文件路径')
    ap.add_argument('--output', help='输出 HTML 路径（缺省 = 模板同目录 out/<原名>）')
    ap.add_argument('--js', default=None, help='公共 JS 资产路径（缺省 = assets/base.js）')
    ap.add_argument('--charts', default=None, help='图表资产路径（可选）')
    ap.add_argument('--strict-payload', action='store_true',
                    help='payload 信封结构校验（契约 §4 必填字段）')
    args = ap.parse_args()

    template_path = pathlib.Path(args.template)
    if not template_path.exists():
        print(json.dumps({'status': 'error', 'data': {'template': str(template_path)},
                          'message': f'模板不存在: {template_path}'}, ensure_ascii=False))
        return 1

    payload_path = pathlib.Path(args.payload)
    if not payload_path.exists():
        print(json.dumps({'status': 'error', 'data': {'payload': str(payload_path)},
                          'message': f'payload 不存在: {payload_path}'}, ensure_ascii=False))
        return 1
    try:
        payload = json.loads(payload_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        print(json.dumps({'status': 'error', 'data': {'payload': str(payload_path)},
                          'message': f'payload JSON 解析失败: {e}'}, ensure_ascii=False))
        return 1

    js_asset, js_err = load_asset(pathlib.Path(args.js) if args.js else DEFAULT_JS, '公共 JS')
    if js_err:
        print(json.dumps({'status': 'error', 'message': js_err}, ensure_ascii=False))
        return 1
    charts_asset, charts_err = (load_asset(pathlib.Path(args.charts), '图表 JS')
                                if args.charts else (None, None))
    if charts_err:
        print(json.dumps({'status': 'error', 'message': charts_err}, ensure_ascii=False))
        return 1

    html, err = inject(template_path.read_text(encoding='utf-8'), payload,
                       js_asset=js_asset, charts_asset=charts_asset,
                       strict=args.strict_payload)
    if err:
        print(json.dumps({'status': 'error',
                          'data': {'template': str(template_path)},
                          'message': err}, ensure_ascii=False))
        return 1

    out = pathlib.Path(args.output) if args.output else (
        template_path.parent / 'out' / template_path.name)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding='utf-8')
    print(json.dumps({'status': 'ok',
                      'data': {'output': str(out), 'template': str(template_path)},
                      'message': f'HTML 已生成: {out.name}（{len(html)} bytes）'},
                     ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())

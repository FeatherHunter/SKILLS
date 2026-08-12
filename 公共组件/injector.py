# -*- coding: utf-8 -*-
"""Base Skill 注入器 v1.2（公共组件/ 正式版）

契约: docs/component-contract.md v1.2
- <!--INJECT-DATA-->     数据注入点: 必须恰好 1 个（缺失/重复 → 硬拦截失败）
- <!--SHARED-HELPERS-->  公共 JS 注入点: 必须恰好 1 个（缺失 → 硬拦截失败）
- <!--SHARED-CSS-->      公共 CSS 注入点: 必须恰好 1 个（v1.2 新增, 缺失 → 硬拦截失败）
- <!--NO-SHARED-->       豁免通道: 显式声明后 SHARED 可为 0（白名单式, 防隐式豁免）
- <!--CHARTS-HELPERS-->  图表组件注入点: 0 或 1 个（可选, 第二版）

用法:
  python injector.py <模板.html> --payload <数据.json> [--output <输出.html>] [--js <资产.js>] [--css <资产.css>] [--charts <图表.js>] [--strict-payload]

输出: 写文件 + 打印结果 JSON（status ok/error）, 模仿居家管家 emit 契约。
"""
import argparse
import json
import pathlib
import sys

BASE_DIR = pathlib.Path(__file__).resolve().parent
ASSETS = BASE_DIR / 'assets'
DEFAULT_JS = ASSETS / 'base.js'
DEFAULT_CSS = ASSETS / 'base.css'

INJECT_DATA = '<!--INJECT-DATA-->'
SHARED_HELPERS = '<!--SHARED-HELPERS-->'
SHARED_CSS = '<!--SHARED-CSS-->'
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


def inject(template_text, payload, js_asset=None, css_asset=None, charts_asset=None, strict=False):
    """核心注入逻辑（可测）。返回 (html, error)"""
    # ── 守卫校验（硬拦截）──
    if template_text.count(INJECT_DATA) != 1:
        return None, (f'模板必须包含恰好 1 个 {INJECT_DATA}，'
                      f'实际 {template_text.count(INJECT_DATA)} 个（缺失或重复）')

    # 豁免通道: 显式 NO-SHARED 声明 → SHARED/CSS 必须 0（白名单式）；缺省 → 必须恰好 1
    no_shared_count = template_text.count(NO_SHARED)
    if no_shared_count > 1:
        return None, f'{NO_SHARED} 最多出现 1 次，实际 {no_shared_count} 次'
    no_shared = no_shared_count == 1
    shared_count = template_text.count(SHARED_HELPERS)
    css_count = template_text.count(SHARED_CSS)
    if no_shared:
        if shared_count != 0 or css_count != 0:
            return None, (f'模板声明 {NO_SHARED} 豁免但仍有 {SHARED_HELPERS} '
                          f'（{shared_count} 个）/ {SHARED_CSS}（{css_count} 个）'
                          f'——豁免与占位符互斥，拒绝渲染')
    else:
        if shared_count != 1:
            return None, (f'模板必须包含恰好 1 个 {SHARED_HELPERS}（公共 JS 声明点），'
                          f'实际 {shared_count} 个——未接入 Base 管线，拒绝渲染')
        if css_count != 1:
            return None, (f'模板必须包含恰好 1 个 {SHARED_CSS}（公共 CSS 声明点），'
                          f'实际 {css_count} 个——未接入 Base 管线，拒绝渲染')

    if template_text.count(CHARTS_HELPERS) > 1:
        return None, (f'{CHARTS_HELPERS} 最多出现 1 次，'
                      f'实际 {template_text.count(CHARTS_HELPERS)} 次')

    # payload 结构校验
    ok, msg = validate_payload(payload, strict=strict)
    if not ok:
        return None, f'payload 校验失败: {msg}'

    # ── 注入（SHARED JS → SHARED CSS → CHARTS → DATA）──
    html = template_text
    if no_shared:
        # 豁免: 移除 NO-SHARED 标记本身
        html = html.replace(NO_SHARED, '', 1)
    if js_asset is not None:
        html = html.replace(SHARED_HELPERS, js_asset, 1)
    else:
        html = html.replace(SHARED_HELPERS, '', 1)
    if css_asset is not None:
        html = html.replace(SHARED_CSS, css_asset, 1)
    else:
        html = html.replace(SHARED_CSS, '', 1)
    if charts_asset is not None:
        html = html.replace(CHARTS_HELPERS, charts_asset, 1)
    else:
        html = html.replace(CHARTS_HELPERS, '', 1)
    payload_text = json.dumps(payload, ensure_ascii=False).replace('</', '<\\/')
    html = html.replace(INJECT_DATA, payload_text, 1)
    return html, None


# ── HELP 参数化模式（scene-data 契约 · 见 docs/scene-data-contract.md）──
_HELP_REQUIRED_TOP = ('skill_name', 'title', 'groups')

# 文件名 sanitize（help-template-contract §4）: 只允许安全字符 + 结尾 .html
import re as _re
_HELP_FILENAME_RE = _re.compile(r'^[a-zA-Z0-9_\-\u4e00-\u9fa5]+\.html$')


def validate_help_data(data):
    """scene-data 契约 v1 校验。返回 (ok, msg)。"""
    if not isinstance(data, dict):
        return False, 'HELP 数据必须是 JSON 对象'
    missing = [k for k in _HELP_REQUIRED_TOP if not data.get(k)]
    if missing:
        return False, f'HELP 数据缺必填字段: {", ".join(missing)}（scene-data-contract §1）'
    groups = data.get('groups')
    if not isinstance(groups, list) or not groups:
        return False, 'groups 必须是非空数组'
    seen = set()
    for gi, g in enumerate(groups):
        if not isinstance(g, dict) or not g.get('id') or not g.get('label'):
            return False, f'groups[{gi}] 缺 id/label'
        if g['id'] in seen:
            return False, f'分组 id 重复: {g["id"]}'
        seen.add(g['id'])
        sgs = g.get('subgroups')
        if not isinstance(sgs, list) or not sgs:
            return False, f'groups[{gi}] ({g["id"]}) 缺 subgroups（非空数组）'
        for si, sg in enumerate(sgs):
            if not isinstance(sg, dict) or not sg.get('label'):
                return False, f'groups[{gi}].subgroups[{si}] 缺 label'
            scenes = sg.get('scenes')
            if not isinstance(scenes, list) or not scenes:
                return False, f'groups[{gi}].subgroups[{si}] ({sg.get("label")}) 缺 scenes（非空数组）'
            for sci, s in enumerate(scenes):
                if not isinstance(s, dict):
                    return False, f'groups[{gi}].subgroups[{si}].scenes[{sci}] 必须是对象'
                for f in ('id', 'title', 'wake_word', 'prompt_template'):
                    if not s.get(f):
                        return False, (f'场景 {s.get("id", "?")} 缺字段: {f}'
                                       f'（scene-data-contract §3）')
                # status 允许空串（'' = 可用），单独校验二态
                if s.get('status') not in ('', '【待开发】'):
                    return False, f'场景 {s.get("id")} status 非法: {s.get("status")}（只允许 "" / 【待开发】）'
                if s['id'] in seen:
                    return False, f'场景 id 重复: {s["id"]}'
                seen.add(s['id'])
                efs = s.get('editable_fields')
                if efs is not None:
                    if not isinstance(efs, list):
                        return False, f'场景 {s.get("id")} editable_fields 必须是数组'
                    for ef in efs:
                        if not isinstance(ef, dict) or not ef.get('name') or not ef.get('label'):
                            return False, f'场景 {s.get("id")} editable_fields 条目缺 name/label'
    return True, ''


def sanitize_help_filename(skill_name):
    """skill_name → 安全文件名（help_<skill_name>.html）"""
    name = skill_name.strip()
    if not name:
        return None, 'skill_name 为空，无法生成文件名'
    candidate = f'help_{name}.html'
    if not _HELP_FILENAME_RE.match(candidate):
        return None, f'文件名包含不安全字符: {candidate}（只允许字母数字下划线中文连字符）'
    return candidate, None


def main():
    ap = argparse.ArgumentParser(description='Base 注入器 v1.2 · HELP 参数化 v1')
    ap.add_argument('template', help='模板 HTML 路径')
    ap.add_argument('--payload', required=True, help='payload JSON 文件路径（普通模式 = 信封；--help-template = scene-data 契约）')
    ap.add_argument('--output', help='输出 HTML 路径（缺省 = 模板同目录 out/<原名>；--help-template 缺省 = out/help_<技能名>.html）')
    ap.add_argument('--js', default=None, help='公共 JS 资产路径（缺省 = assets/base.js）')
    ap.add_argument('--css', default=None, help='公共 CSS 资产路径（缺省 = assets/base.css）')
    ap.add_argument('--charts', default=None, help='图表资产路径（可选）')
    ap.add_argument('--strict-payload', action='store_true',
                    help='payload 信封结构校验（契约 §4 必填字段）')
    ap.add_argument('--help-template', action='store_true',
                    help='HELP 参数化模式：payload 按 scene-data 契约 v1 校验 + 文件名 sanitize')
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
    css_asset, css_err = load_asset(pathlib.Path(args.css) if args.css else DEFAULT_CSS, '公共 CSS')
    if css_err:
        print(json.dumps({'status': 'error', 'message': css_err}, ensure_ascii=False))
        return 1
    charts_asset, charts_err = (load_asset(pathlib.Path(args.charts), '图表 JS')
                                if args.charts else (None, None))
    if charts_err:
        print(json.dumps({'status': 'error', 'message': charts_err}, ensure_ascii=False))
        return 1

    template_text = template_path.read_text(encoding='utf-8')

    # ── HELP 参数化模式：契约校验 + 文件名 sanitize + 注入 ──
    if args.help_template:
        ok, msg = validate_help_data(payload)
        if not ok:
            print(json.dumps({'status': 'error',
                              'data': {'payload': str(payload_path)},
                              'message': f'HELP 数据校验失败: {msg}'}, ensure_ascii=False))
            return 1
        # 文件名 sanitize（help-template-contract §4）: 路径允许，防穿越 + 文件名部分必须安全
        if args.output:
            out_arg = pathlib.Path(args.output)
            if '..' in out_arg.parts:
                print(json.dumps({'status': 'error',
                                  'data': {'output': str(out_arg)},
                                  'message': f'输出路径含 .. 穿越: {out_arg}（拒绝）'},
                                 ensure_ascii=False))
                return 1
            if not _HELP_FILENAME_RE.match(out_arg.name):
                print(json.dumps({'status': 'error',
                                  'data': {'output': str(out_arg)},
                                  'message': f'输出文件名不安全: {out_arg.name}'
                                             f'（只允许 [a-zA-Z0-9_-中文]+.html）'},
                                 ensure_ascii=False))
                return 1
            out = out_arg
        else:
            fname, ferr = sanitize_help_filename(payload.get('skill_name', ''))
            if ferr:
                print(json.dumps({'status': 'error', 'message': ferr}, ensure_ascii=False))
                return 1
            out = template_path.parent / 'out' / fname
        html, err = inject(template_text, payload, js_asset=js_asset, css_asset=css_asset,
                           charts_asset=charts_asset, strict=False)
        if err:
            print(json.dumps({'status': 'error',
                              'data': {'template': str(template_path)},
                              'message': err}, ensure_ascii=False))
            return 1
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding='utf-8')
        print(json.dumps({'status': 'ok',
                          'data': {'output': str(out), 'template': str(template_path)},
                          'message': f'HELP HTML 已生成: {out.name}（{len(html)} bytes）'},
                         ensure_ascii=False))
        return 0

    html, err = inject(template_text, payload,
                       js_asset=js_asset, css_asset=css_asset, charts_asset=charts_asset,
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

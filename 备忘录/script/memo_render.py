#!/usr/bin/env python3
"""备忘录 HTML 渲染器 v1.3.0

v1.3.0(2026-08-13 · #299 Base 重构):
  - 自研 `script/injector.py` + `_shared/clipboard.js` 退役,注入全收敛到
    `公共组件/injector.py`(Base 硬拦截:3 占位符恰 1,漏迁即红)
  - 全部业务 payload 升级为 Base 信封:meta(command_cn/occurred_at/skill_name/
    wake_word/skill_version) + scene.snapshot(title/summary/sections) + copy_log(6 段)
  - HELP 迁 Base help_template:scenarios.yaml 不动(SoT),新增转换层
    `_scenarios_to_contract_data()` → scene-data 契约 v1 JSON
  - 输出命名/同秒冲突保护/3 副本机制不变(时间戳副本 + skill 根 备忘录.html + --output)

历史(承袭 v1.1.0 教训):不再依赖任何跨 session 的共享目录,Base 资产路径
由 `SKILL_DIR.parent / "公共组件"` 推导,缺失时 raise RuntimeError 提示安装。
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from memo_cli import DB_FILENAME  # noqa: E402 · _help_initialized 复用路径计算

# v1.0.5: skill ASCII 短码(避免中文路径跨平台编码问题)
SKILL_HTML_NAME = "memo"

SKILL_DIR = Path(__file__).parent.parent
BASE_SKILL_DIR = SKILL_DIR.parent / "公共组件"

TEMPLATE_PATH = SKILL_DIR / "templates" / "memo_query.html"
SYNC_REPORT_TEMPLATE_PATH = SKILL_DIR / "templates" / "sync_report.html"
WISH_PLAN_TEMPLATE_PATH = SKILL_DIR / "templates" / "wish_plan.html"
WISH_COMPLETE_TEMPLATE_PATH = SKILL_DIR / "templates" / "wish_complete.html"
CHANGE_CATEGORY_TEMPLATE_PATH = SKILL_DIR / "templates" / "change_category.html"
INIT_REPORT_TEMPLATE_PATH = SKILL_DIR / "templates" / "init_report.html"
BASE_HELP_TEMPLATE_PATH = BASE_SKILL_DIR / "assets" / "help_template.html"
SCENARIOS_PATH = SKILL_DIR / "references" / "scenarios.yaml"

# 查询命令 → 中文命令名(信封 meta.command_cn + wake_word)
COMMAND_CN_MAP = {
    "search": "查备忘",
    "get": "查备忘详情",
    "search-date": "按日期查备忘",
    "completed": "查已完成提醒",
    "reminders": "查提醒",
}

# 场景 dimensions 键 → 中文标签(转换层 editable_fields 用)
DIM_LABEL_MAP = {
    "id": "笔记 ID",
    "ids": "笔记 ID",
    "content": "内容",
    "category": "分类",
    "sub_category": "子分类",
    "media": "附件",
    "due": "排期日期",
    "with_reminders": "级联删除提醒",
    "true": "跳过二次确认",
    "bulk_indicator": "批量判定",
    "note_id": "笔记 ID",
    "at": "提醒时间",
    "repeat_type": "重复类型",
    "rule": "重复规则",
    "date": "日期",
    "keyword": "关键词",
    "from_category": "原分类",
    "to_category": "目标分类",
    "wish_id": "心愿 ID",
}


def _occurred_at():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _base_injector():
    """懒加载 Base injector(公共组件/injector.py)。

    用 importlib 显式按文件路径加载,避免与同目录任何 `injector` 模块撞名。
    """
    import importlib.util
    injector_path = BASE_SKILL_DIR / "injector.py"
    if not injector_path.exists():
        raise RuntimeError(
            "Base Skill 资产缺失: 找不到 公共组件/injector.py。"
            "请确认 公共组件/ 目录已安装(#268 Base 定稿入库)。"
        )
    spec = importlib.util.spec_from_file_location("base_injector", injector_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _base_assets():
    js = (BASE_SKILL_DIR / "assets" / "base.js").read_text(encoding="utf-8").strip()
    css = (BASE_SKILL_DIR / "assets" / "base.css").read_text(encoding="utf-8").strip()
    return js, css


def _inject(template_text, payload, help_mode=False):
    """Base 注入器(硬拦截):3 占位符恰 1,缺/重 → RuntimeError。"""
    mod = _base_injector()
    js, css = _base_assets()
    if help_mode:
        ok, msg = mod.validate_help_data(payload)
        if not ok:
            raise ValueError(f"HELP 数据校验失败: {msg}")
    html, err = mod.inject(template_text, payload, js_asset=js, css_asset=css, strict=False)
    if err:
        raise RuntimeError(f"Base 注入失败: {err}")
    return html


def _get_html_output_dir():
    """HTML 输出目录 = DB_PATH.parent / f"{SKILL_HTML_NAME}_html"(承袭 v1.0.5)

    动态 import(对抗审查 N2):每次调用读当前 env,避免模块首次 import 时
    缓存常量导致测试隔离(SKILLS_DB_PATH=tmp)失效。
    """
    from memo_cli import DB_PATH
    return DB_PATH.parent / f"{SKILL_HTML_NAME}_html"


def _write(name, html):
    """写 <name>_<YYYYMMDD>_<HHMMSS>[_<N>].html,返回路径(承袭 v1.0.7 冲突保护)。

    逻辑自 v1.1.0 的 script/injector.py 内迁(Base 重构红线:自研 injector 退役)。
    """
    out_dir = _get_html_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"{name}_{ts}.html"
    if out_path.exists():
        n = 2
        while True:
            candidate = out_dir / f"{name}_{ts}_{n}.html"
            if not candidate.exists():
                out_path = candidate
                break
            n += 1
    out_path.write_text(html, encoding="utf-8")
    return str(out_path)


def _envelope(command_cn, wake_word, scene_id, title, summary, sections,
              copy_log, extra, message):
    """Base 信封:meta + scene.snapshot + copy_log + 技能自有字段(extra)混装 data。"""
    occurred = _occurred_at()
    data = {
        "meta": {
            "command_cn": command_cn,
            "occurred_at": occurred,
            "skill_name": "备忘录",
            "wake_word": wake_word,
            "skill_version": "1.3.0",
        },
        "scene": {
            "scene_id": scene_id,
            "snapshot": {"title": title, "summary": summary, "sections": sections},
        },
        "copy_log": copy_log,
        "generated_at": occurred,
    }
    data.update(extra)
    return {"status": "ok", "data": data, "message": message}


def _query_row(x):
    """查询页 snapshot 明细行(兼容备忘/打卡/提醒三类条目字段)。"""
    id_ = x.get("id") or x.get("checkin_note_id") or x.get("reminder_id") or ""
    content = (x.get("content") or x.get("checkin_content")
               or x.get("reminder_content") or x.get("note_content") or "")
    cat = x.get("category") or x.get("repeat_type") or "未分类"
    sub = f"/{x['sub_category']}" if x.get("sub_category") else ""
    created = x.get("created_at") or x.get("checkin_at") or x.get("remind_at") or ""
    return f"#{id_} · [{cat}{sub}] · {content[:80]} · {created}"


def _query_snapshot(payload):
    d = payload.get("data") or {}
    items = d.get("items") or []
    due = sum(1 for x in items if x.get("due"))
    media = sum(1 for x in items if x.get("media_path"))
    remind = sum(1 for x in items if x.get("remind_at") or x.get("reminder_id"))
    return {
        "title": d.get("title") or "备忘录查询结果",
        "summary": [
            f"结果 {len(items)} 条",
            f"有排期 {due} 条",
            f"有附件 {media} 条",
            f"有提醒 {remind} 条",
        ],
        "sections": [{"heading": "明细", "rows": [_query_row(x) for x in items]}],
    }


def render_query(payload, name="备忘录查询"):
    """渲染查询结果页(模板 memo_query.html)"""
    d = payload.get("data") or {}
    command = d.get("command") or "search"
    command_cn = COMMAND_CN_MAP.get(command, "查备忘")
    envelope = _envelope(
        command_cn=command_cn,
        wake_word=command_cn,
        scene_id=command,
        title=d.get("title") or "备忘录查询结果",
        summary=_query_snapshot(payload)["summary"],
        sections=_query_snapshot(payload)["sections"],
        copy_log={
            "thinking": "只读查询 · 按唤醒词路由到对应 SELECT,命中即渲染(无写库)",
            "data_structure": "SQLite notes/checkins/reminders 表(SELECT · FTS5 全文检索)",
            "call_chain": f"memo_cli.py {command} → memo_render.render_query → 公共组件/injector.py",
            "timestamp": d.get("generated_at") or "",
            "exception": "无",
        },
        extra={k: v for k, v in d.items()},
        message=payload.get("message") or "查询完成",
    )
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return _write(name, _inject(template, envelope))


def _sync_snapshot(payload):
    d = payload.get("data") or {}
    num = lambda k: d.get(k) or 0
    synced, backfilled = num("synced"), num("backfilled")
    due_changed = num("due_added") + num("due_overridden") + num("due_removed")
    skipped = num("skipped_no_local_note") + num("skipped_no_memo_id") + num("skipped_already_done")
    errs = len(d.get("errors") or [])
    sections = []
    if synced:
        rows = [f"#{it.get('id', '?')} · {it.get('content', '')}"
                for it in (d.get("synced_items") or [])]
        sections.append({"heading": "完成同步明细", "rows": rows or [f"飞书勾选转本机打卡 {synced} 条"]})
    if due_changed:
        parts = []
        if num("due_added"):
            parts.append(f"新增排期 {num('due_added')} 条")
        if num("due_overridden"):
            parts.append(f"覆盖排期 {num('due_overridden')} 条")
        if num("due_removed"):
            parts.append(f"清除排期 {num('due_removed')} 条")
        sections.append({"heading": "排期变更", "rows": parts})
    if backfilled:
        sections.append({"heading": "补建到飞书", "rows": [f"本机心愿补建飞书 task {backfilled} 条"]})
    if skipped:
        parts = []
        if num("skipped_no_local_note"):
            parts.append(f"飞书已完成但本机无对应心愿 {num('skipped_no_local_note')} 条")
        if num("skipped_no_memo_id"):
            parts.append(f"飞书 task 缺 memo_id {num('skipped_no_memo_id')} 条")
        if num("skipped_already_done"):
            parts.append(f"已处理过 {num('skipped_already_done')} 条")
        sections.append({"heading": "跳过", "rows": parts})
    if errs:
        sections.append({"heading": "错误", "rows": [str(e) for e in (d.get("errors") or [])]})
    return {
        "title": d.get("title") or "备忘录同步报告",
        "summary": [
            f"完成同步 {synced} 条",
            f"补建到飞书 {backfilled} 条",
            f"排期变更 {due_changed} 条",
            f"跳过 {skipped} 条",
            f"错误 {errs} 个",
        ],
        "sections": sections,
    }


def render_sync_report(payload, name="同步报告"):
    """渲染同步报告页(模板 sync_report.html)"""
    d = payload.get("data") or {}
    snap = _sync_snapshot(payload)
    envelope = _envelope(
        command_cn="备忘录同步",
        wake_word="备忘录同步",
        scene_id="sync-from-feishu",
        title=snap["title"],
        summary=snap["summary"],
        sections=snap["sections"],
        copy_log={
            "thinking": "双向对账 · 飞书 done/due 反向同步到本机(只读扫描 + 有变更才写)",
            "data_structure": "feishu_sync.sync_from_feishu 返回 dict(backfilled/synced/due_*/skipped_*/errors)",
            "call_chain": "memo_cli.py sync-from-feishu → feishu_sync → memo_render.render_sync_report → Base injector",
            "timestamp": d.get("generated_at") or "",
            "exception": "; ".join(d.get("errors") or []) or "无",
        },
        extra={k: v for k, v in d.items()},
        message=payload.get("message") or "同步完成",
    )
    template = SYNC_REPORT_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _write(name, _inject(template, envelope))


def _wish_row(w, with_due=True):
    due = w.get("current_due") or ""
    fb = "已同步飞书" if w.get("feishu_task_guid") else "未同步飞书"
    due_part = f" · 排期 {due}" if (with_due and due) else " · 未排期"
    return f"#{w.get('id', '')} · {w.get('content', '')}{due_part} · {fb}"


def render_wish_plan(payload, name="心愿排期"):
    """渲染心愿排期向导页(过程型 HTML)"""
    d = payload.get("data") or {}
    items = d.get("items") or []
    unset = sum(1 for w in items if not w.get("current_due"))
    snap = {
        "title": d.get("title") or "心愿排期向导",
        "summary": [
            f"心愿 {len(items)} 个",
            f"未排期 {unset} 个",
            f"已排期 {len(items) - unset} 个",
            f"建议排期 {d.get('suggest_due') or '(未填)'}",
        ],
        "sections": [{"heading": "心愿清单", "rows": [_wish_row(w) for w in items]}],
    }
    envelope = _envelope(
        command_cn="心愿排期",
        wake_word="心愿排期",
        scene_id="wish-batch-plan",
        title=snap["title"],
        summary=snap["summary"],
        sections=snap["sections"],
        copy_log={
            "thinking": "过程型向导 · 只读收集心愿列表,勾选+填排期后复制指令回 AI(HTML 不写库)",
            "data_structure": "notes 表(category='心愿')· id/content/category/sub_category/due/feishu_task_guid",
            "call_chain": "memo_cli.py wish-batch-plan → memo_render.render_wish_plan → Base injector",
            "timestamp": d.get("generated_at") or "",
            "exception": "无",
        },
        extra={k: v for k, v in d.items()},
        message=payload.get("message") or f"找到 {len(items)} 个心愿",
    )
    template = WISH_PLAN_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _write(name, _inject(template, envelope))


def render_wish_complete(payload, name="心愿完成"):
    """渲染心愿完成向导页(过程型 HTML)"""
    d = payload.get("data") or {}
    items = d.get("items") or []
    with_fb = sum(1 for w in items if w.get("feishu_task_guid"))
    snap = {
        "title": d.get("title") or "心愿完成向导",
        "summary": [
            f"待完成 {len(items)} 个",
            f"已同步飞书 {with_fb} 个",
            f"未同步飞书 {len(items) - with_fb} 个",
        ],
        "sections": [{"heading": "心愿清单", "rows": [_wish_row(w) for w in items]}],
    }
    envelope = _envelope(
        command_cn="心愿完成",
        wake_word="心愿完成",
        scene_id="wish-complete",
        title=snap["title"],
        summary=snap["summary"],
        sections=snap["sections"],
        copy_log={
            "thinking": "过程型向导 · 勾选+填打卡内容后复制指令回 AI(complete-wish 原子转换)",
            "data_structure": "notes 表(category='心愿')· id/content/due/feishu_task_guid",
            "call_chain": "memo_cli.py wish-complete → memo_render.render_wish_complete → Base injector",
            "timestamp": d.get("generated_at") or "",
            "exception": "无",
        },
        extra={k: v for k, v in d.items()},
        message=payload.get("message") or f"找到 {len(items)} 个心愿",
    )
    template = WISH_COMPLETE_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _write(name, _inject(template, envelope))


def render_change_category(payload, name="批量改分类"):
    """渲染批量改分类向导页(过程型 HTML)"""
    d = payload.get("data") or {}
    items = d.get("items") or []
    with_sub = sum(1 for w in items if w.get("sub_category"))
    rows = [
        f"#{w.get('id', '')} · {w.get('content', '')}"
        + (f" · sub: {w['sub_category']}" if w.get("sub_category") else "")
        for w in items
    ]
    snap = {
        "title": d.get("title") or "批量改分类向导",
        "summary": [
            f"候选笔记 {len(items)} 条",
            f"带子分类 {with_sub} 条",
            f"原分类 {d.get('from_category') or '(全部)'} → 目标 {d.get('to_category') or '(待选)'}",
        ],
        "sections": [{"heading": "笔记清单", "rows": rows}],
    }
    envelope = _envelope(
        command_cn="批量改分类",
        wake_word="备忘改分类",
        scene_id="batch-update-category",
        title=snap["title"],
        summary=snap["summary"],
        sections=snap["sections"],
        copy_log={
            "thinking": "过程型向导 · 勾选后复制 update-category 指令回 AI(只改顶层分类,sub_category 不动)",
            "data_structure": "notes 表 · id/content/category/sub_category/media_path/due",
            "call_chain": "memo_cli.py batch-update-category → memo_render.render_change_category → Base injector",
            "timestamp": d.get("generated_at") or "",
            "exception": "无",
        },
        extra={k: v for k, v in d.items()},
        message=payload.get("message") or f"找到 {len(items)} 条笔记",
    )
    template = CHANGE_CATEGORY_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _write(name, _inject(template, envelope))


def _init_snapshot(payload):
    d = payload.get("data") or {}
    items = d.get("items") or []
    todos = d.get("todos") or []
    verify = d.get("verify") or []
    ready = sum(1 for i in items if i.get("status") == "ok")
    warn = sum(1 for i in items if i.get("status") == "warn")
    err = sum(1 for i in items if i.get("status") == "err")
    sections = []
    if items:
        rows = [f"[{'✓' if i.get('status') == 'ok' else '⚠' if i.get('status') == 'warn' else '✗'}] "
                f"{i.get('name', '')} · {i.get('desc', '')}"
                + (f" · 处理: {i['action']}" if i.get("action") else "")
                for i in items]
        sections.append({"heading": "环境检查", "rows": rows})
    if todos:
        rows = [f"{t.get('title', '')}: " + " → ".join(t.get("steps") or [])
                for t in todos]
        sections.append({"heading": "待办指引", "rows": rows})
    if verify:
        rows = [v.get("text", v) if isinstance(v, dict) else v for v in verify]
        sections.append({"heading": "验证清单", "rows": rows})
    return {
        "title": d.get("title") or "备忘录 · 初始化报告",
        "summary": [
            f"检查 {len(items)} 项",
            f"就绪 {ready} 项",
            f"可选缺失 {warn} 项",
            f"必装缺失 {err} 项",
        ],
        "sections": sections,
    }


def render_init_report(payload, name="备忘录_初始化报告"):
    """渲染初始化报告页(过程型 HTML · 承载 AI 执行证据)"""
    d = payload.get("data") or {}
    snap = _init_snapshot(payload)
    envelope = _envelope(
        command_cn="首次使用",
        wake_word="首次使用",
        scene_id="init-report",
        title=snap["title"],
        summary=snap["summary"],
        sections=snap["sections"],
        copy_log={
            "thinking": "首次使用 · AI 诊断结果渲染为报告页(检查清单+待办+验证清单)",
            "data_structure": "--data JSON: {items:[{name,status,desc,action}], todos:[{title,steps}], verify:[]}",
            "call_chain": "memo_cli.py init-report --data → memo_render.render_init_report → Base injector",
            "timestamp": d.get("generated_at") or "",
            "exception": "无",
        },
        extra={k: v for k, v in d.items()},
        message=payload.get("message") or "初始化报告已生成",
    )
    template = INIT_REPORT_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _write(name, _inject(template, envelope))


def _load_scenarios():
    """加载 references/scenarios.yaml(场景资产 = HELP 唯一事实源)"""
    if not SCENARIOS_PATH.exists():
        raise FileNotFoundError(f"场景资产缺失: {SCENARIOS_PATH}")
    try:
        import yaml
    except ImportError:
        raise RuntimeError("缺少 pyyaml,运行 `pip install pyyaml`")
    data = yaml.safe_load(SCENARIOS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "scenarios" not in data:
        raise ValueError(f"scenarios.yaml 格式错误: 缺少 'scenarios' 字段")
    return data


def _help_initialized():
    """初始化状态判定(承袭 v1.1.4):DB 文件存在 = 已初始化。
    env 覆盖:HELP_INITIALIZED=1/0 可强制指定(测试/镜像可重现性)。"""
    env = os.environ.get("HELP_INITIALIZED")
    if env is not None:
        return env.strip().lower() in ("1", "true", "yes")
    from memo_cli import DB_FILENAME, _find_db_path
    return _find_db_path(Path(__file__).parent.parent, DB_FILENAME).exists()


def _init_banner(scenarios_data):
    """init_banner(仅未初始化时输出 · 对齐 Base init_banner 结构)。

    Base 原生支持 init_banner;initialized 判定沿用 _help_initialized。
    """
    if _help_initialized():
        return None
    init_scene = next(
        (s for s in scenarios_data.get("scenarios", [])
         if s.get("scenario_id") == "memo_init_setup"),
        None,
    )
    if not init_scene:
        return None
    return {
        "title": "🚀 第一次用备忘录?",
        "subtitle": "从零搭建环境:检测 → 安装/配置 → 初始化数据库 → 生成报告,全程引导。",
        "button_text": "📋 复制",
        "prompt": init_scene.get("prompt", ""),
        "closable": True,
        "steps": [
            {"title": "检查并配置 Python", "desc": "版本与依赖检测"},
            {"title": "数据存储", "desc": "SQLite + FTS5 全文搜索"},
            {"title": "飞书 CLI", "desc": "安装并授权(核心联动)"},
            {"title": "环境变量", "desc": "SKILLS_DB_PATH / MEMO_MEDIA_DIR"},
            {"title": "初始化数据库", "desc": "建表 + 提醒调度"},
            {"title": "生成报告", "desc": "初始化报告页"},
        ],
    }


def _scenarios_to_contract_data(scenarios_data):
    """转换层:scenarios.yaml(SoT,不动) → scene-data 契约 v1 JSON(#295 决议)。

    映射:
      - categories → groups(id=key, icon, label);subfunction → subgroups;书写序 = 组内序
      - scenario_id→id / scenario_title→title / wake_word / status / prompt→prompt_template
      - type("采集+回执")按 + 拆成 types 数组(契约 §3.1 多徽章)
      - dimensions → editable_fields(name=键, label=中文映射, hint=原文, required=False)
      - result / dependencies 不展示(数据留 yaml · #295 决议)
      - memo_init_setup → init_banner(未初始化时);contact = GitHub/Issues
    """
    categories = scenarios_data.get("categories", [])
    scenarios = scenarios_data.get("scenarios", [])
    cat_key_to_name = {c.get("key"): c.get("name", c.get("key")) for c in categories}

    groups = []
    group_index = {}
    for cat in categories:
        key = cat.get("key")
        g = {"id": key, "icon": cat.get("icon", ""), "label": cat.get("name", key),
             "subgroups": []}
        groups.append(g)
        group_index[key] = g

    for s in scenarios:
        cat_key = s.get("category")
        g = group_index.get(cat_key)
        if g is None:
            continue
        sub_key = s.get("subfunction") or "基础"
        sub = next((sg for sg in g["subgroups"] if sg["label"] == sub_key), None)
        if sub is None:
            sub = {"id": f"{cat_key}_{len(g['subgroups'])}", "label": sub_key, "scenes": []}
            g["subgroups"].append(sub)

        dims = s.get("dimensions") or {}
        editable_fields = [
            {"name": k, "label": DIM_LABEL_MAP.get(k, k), "value": "",
             "hint": str(v), "required": False}
            for k, v in dims.items() if v
        ] or None

        scene = {
            "id": s.get("scenario_id"),
            "title": s.get("scenario_title", ""),
            "wake_word": s.get("wake_word", ""),
            "status": s.get("status", ""),
            "prompt_template": s.get("prompt", ""),
        }
        types = [t.strip() for t in str(s.get("type", "")).split("+") if t.strip()]
        if types:
            scene["types"] = types
        if editable_fields:
            scene["editable_fields"] = editable_fields
        sub["scenes"].append(scene)

    total = len(scenarios)
    available = sum(1 for s in scenarios if not s.get("status"))
    return {
        "skill_name": "备忘录",
        "title": "使用手册",
        "subtitle": (f"{len(categories)} 个分类 · {total} 个场景 · {available} 可用 · "
                     f"版本 {scenarios_data.get('version', '')}"),
        "version": scenarios_data.get("version", ""),
        "init_banner": _init_banner(scenarios_data),
        "contact": {
            "items": [
                {"label": "GitHub", "value": "https://github.com/FeatherHunter/SKILLS"},
                {"label": "Issues", "value": "https://github.com/FeatherHunter/SKILLS/issues"},
            ]
        },
        "groups": groups,
    }


def render_help(payload=None, name="备忘录_HELP", output_path=None):
    """渲染 HELP 使用手册页(v1.3.0 · Base help_template · 3 副本机制不变)

    路径形态(承袭 v1.1.4):
      1. 时间戳副本: $SKILLS_DATA_DIR/<skill>_html/<name>_<YYYYMMDD>_<HHMMSS>[_<N>].html
      2. Skill 根副本(**永远写**): <SKILL_DIR>/备忘录.html
      3. 额外副本(可选 · --output)

    payload 传入时视为已对齐的契约数据(测试用);缺省走转换层。
    """
    template = BASE_HELP_TEMPLATE_PATH.read_text(encoding="utf-8")
    scenarios_data = _load_scenarios()

    if payload is None:
        from validate_scenarios import validate_scenarios
        vres = validate_scenarios(scenarios_data)
        if not vres.ok:
            raise ValueError("场景资产校验失败: " + "; ".join(vres.errors[:5]))
        payload = _scenarios_to_contract_data(scenarios_data)

    # 1. 写时间戳副本
    help_path = _write(name, _inject(template, payload, help_mode=True))

    # 2. ★ 覆盖 skill 根目录 备忘录.html(用户额外要求 · 永远写)
    skill_root_help = SKILL_DIR / "备忘录.html"
    skill_root_help.write_text(
        Path(help_path).read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    # 3. 额外副本(可选 · --output)
    output_written = None
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            Path(help_path).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        output_written = str(output_path)

    scene_count = sum(len(sg["scenes"]) for g in payload.get("groups", [])
                      for sg in g.get("subgroups", []))
    return {
        "html_path": str(help_path),
        "skill_root_path": str(skill_root_help),
        "output_path": output_written,
        "scenario_count": scene_count,
    }


def main():
    payload = json.load(sys.stdin)
    path = render_query(payload)
    print(json.dumps({"status": "ok", "data": {"path": path}, "message": "HTML 已生成"},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""setup_scenarios.py — 作息管家 · 首次使用域(实施 T7 · 2026-08-09)

职责: 首次使用 + onboarding 的底层工作流 + 初始化报告 HTML 渲染。

场景资产: scenarios/setup.yaml(「首次使用」场景定义,合并写回由 T8 执行)

注册通道(实施 T1 · 渐进式注册通道契约):
    COMMANDS = {"<cmd>": handler}  → schedule_cli.py 自动发现 dispatch
    handler(args: list[str]) 签名与现有 cmd_* 一致

命令编排说明(票面「COMMANDS: check/init/status 编排」):
    - check(本模块新提供): 环境检测 → 结构化 JSON(OS/Python≥3.7/数据目录可写/
      DB 状态/分类白名单/飞书三档),供 AI 判定与报告组装
    - init / status(既有内置命令,不动): 建库(幂等,含迁移)与状态确认;
      首次使用流程按「check → 路径确认 → init → status → render-first-use」编排,
      本模块只补充缺失的 check 与报告渲染,不重定义内置命令(同名先到先得,内置优先)

6 步向导(规格 R3 · 首次使用工作流):
    ① 环境检测 → ② 路径确认(默认即确认,不静默) → ③ 建库+初始化(幂等)
    → ④ 状态确认 → ⑤ 初始化报告(本 HTML) → ⑥ 完成

飞书强引导(2026-08-09 人类修正 · 原「可选」升级):
    - 飞书联动是作息管家核心能力之一(计划双向同步飞书日历)
    - 报告页醒目标注「配合飞书效果最好」+ 安装命令 + 非阻塞授权说明
    - 只有用户明确拒绝才跳过,且标注「飞书同步不可用」;后续说「配置飞书」补装
    - 授权强制非阻塞(lark-cli config init --new --no-wait --json 拿 device_code
      → 发 QR/URL → 用户「好了」→ poll_auth),禁止同步阻塞 auth login

报告数据契约(对标备忘录 init-report · R3 §报告页内容):
    {"items":[{name,status(ok/warn/err),desc,action}],
     "todos":[{title,steps:[str]}],
     "verify":[str 或 {"text","status"}]}
    飞书项三态: {"text":"飞书同步已配置","status":"ok"} /
                {"text":"飞书同步未配置(强烈建议配置)","status":"skip"} /
                {"text":"飞书同步配置不完整","status":"fail"}

08-HTML 交互规范 v1:
    - 流程 5 向导(步骤条/阶段指示)+ 4 回执(成功/跳过/失败/错误)
    - 双按钮硬标准: 复制数据(5 段 JSON)+ 复制日志(6 段)
    - 单工闭环: 阶段动作 = 复制带参数 prompt → AI 执行 CLI → 重渲染
    - 双通道: 渲染后一句话文字总结(AI 交付时同步)

隔离契约: 本域只动 scripts/setup_scenarios.py + templates/开始使用/first_use_wizard.html
    + scenarios/setup.yaml + tests/test_setup_scenarios.py;不碰 schedule_cli.py /
    schedule_html_render.py / references/scenarios.yaml(T8 合并)。
    ⚠️ 模块级零副作用: 域注册通道会 exec 本模块,DB/飞书 import 一律延迟到函数内。
"""
import json
import platform
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "开始使用" / "first_use_wizard.html"
WHITELIST_PATH = SKILL_DIR / "category_whitelist.yaml"
DB_FILENAME = "schedule_data.db"

# 主库业务表(init_db 幂等创建): schedule_records / daily_summary /
# schedule_plans_legacy_2026_06_29 / schedule_plans(事件型新表)
EXPECTED_TABLES = 4
SKILL_VERSION = "v1.1.3-T7"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _module_ok(name: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(name) is not None


def _table_count(db_path: Path) -> int:
    """主库业务表数量(只读探测,不建库不写库)。文件不存在返回 0。"""
    if not db_path.exists():
        return 0
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            return len(rows)
        finally:
            conn.close()
    except sqlite3.OperationalError:
        return 0


def _dir_writable(d: Path) -> bool:
    """目录可写探针(创建 + 写删临时文件)"""
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / f".write_probe_{__import__('os').getpid()}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _is_wsl() -> bool:
    import os
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    if sys.platform.startswith("win"):
        return False
    try:
        return "microsoft" in Path("/proc/version").read_text(
            encoding="utf-8", errors="replace").lower()
    except OSError:
        return False


def _feishu_payload() -> dict:
    """飞书能力三档探测(只读;探测失败降级 unknown,不抛异常)"""
    try:
        from feishu_sync import is_feishu_available
        st = is_feishu_available()
        return {
            "tier": st.tier,
            "cli_installed": st.cli_installed,
            "authenticated": st.authenticated,
            "calendar_writable": st.calendar_writable,
            "last_error": st.last_error,
        }
    except Exception as e:
        return {"tier": "unknown", "cli_installed": False, "authenticated": False,
                "calendar_writable": False, "last_error": str(e)}


def _check_env() -> dict:
    """环境检测(步骤 ①): OS / Python(≥3.7)/ 数据目录可写 / DB 状态 / 白名单 / 飞书三档"""
    import os
    from schedule_db import get_db_base_dir

    os_name = "WSL" if _is_wsl() else platform.system()
    py_ver = platform.python_version()
    py_major, py_minor = platform.python_version_tuple()[:2]
    try:
        py_ok = (int(py_major), int(py_minor)) >= (3, 7)
    except ValueError:
        py_ok = True

    db_dir = get_db_base_dir()
    db_path = db_dir / DB_FILENAME
    tables = _table_count(db_path)
    feishu = _feishu_payload()

    return {
        "os": os_name,
        "python": py_ver,
        "python_ok": py_ok,
        "db_dir": str(db_dir),
        "db_dir_writable": _dir_writable(db_dir),
        "db_path": str(db_path),
        "db_exists": db_path.exists(),
        "db_tables": tables,
        "db_ready": tables >= EXPECTED_TABLES,
        "whitelist_ready": WHITELIST_PATH.exists(),
        "whitelist_path": str(WHITELIST_PATH),
        "env_skills_db_path": os.environ.get("SKILLS_DB_PATH") or "(未设置,走默认)",
        "feishu": feishu,
        "status": "ok",
    }


def _step_status(pred: bool, cur: bool) -> str:
    if pred:
        return "done"
    return "current" if cur else "pending"


def _feishu_item(fs: dict) -> dict:
    """飞书检查项三态(ok / warn-未配置 / fail-配置不完整)"""
    tier = fs.get("tier", "unknown")
    if tier == "full":
        return {"name": "飞书联动", "status": "ok",
                "desc": "飞书同步已配置(lark-cli 已授权,日历可写),配合飞书效果最好", "action": ""}
    if tier == "partial":
        return {"name": "飞书联动", "status": "fail",
                "desc": "飞书同步配置不完整(lark-cli 已装但未授权或日历不可写)", "action": "说「配置飞书」补全授权"}
    return {"name": "飞书联动", "status": "skip",
            "desc": "飞书同步未配置(强烈建议配置 · 配合飞书效果最好;不配则飞书同步不可用)",
            "action": "说「配置飞书」补装"}


def _feishu_section(fs: dict) -> dict:
    """飞书强引导区数据(仅非 full 时呈现)"""
    tier = fs.get("tier", "unknown")
    full = tier == "full"
    if full:
        return {"full": True}
    return {
        "full": False,
        "recommended": "飞书联动是作息管家核心能力:计划双向同步飞书日历,手机日历直接看作息安排,"
                       "配合飞书效果最好。不配置 = 飞书同步功能不可用(其余功能不受影响);"
                       "只有明确拒绝才跳过,后续想说「配置飞书」即可补装。",
        "install_cmds": [
            "npm install -g @larksuite/cli",
            "npx -y skills add https://open.feishu.cn --skill -y",
        ],
        "auth_note": "⚠️ 官方包是 @larksuite/cli(bin 名 lark-cli);npm 上 lark-cli 是僵尸包,严禁安装。"
                     "授权走强制非阻塞模式(lark-cli config init --new --no-wait --json 拿 device_code "
                     "→ 发二维码/链接 → 用户「好了」→ poll_auth),calendar 域必授;禁止同步阻塞 auth login(会卡死)。",
        "tier": tier,
        "cli_installed": fs.get("cli_installed", False),
    }


def _build_report(check: dict) -> tuple[list, list, list]:
    """报告数据契约(items/todos/verify,对标备忘录 init-report)"""
    db_ready = check["db_ready"]
    fs = check["feishu"]
    items = [
        {"name": "Python 可运行", "status": "ok" if check["python_ok"] else "err",
         "desc": f"{check['python']} (需 ≥3.7)", "action": ""},
        {"name": "数据位置可写", "status": "ok" if check["db_dir_writable"] else "err",
         "desc": check["db_dir"], "action": "" if check["db_dir_writable"] else "检查目录权限后重试"},
        {"name": "数据库已建", "status": "ok" if db_ready else "warn",
         "desc": f"{check['db_tables']}/{EXPECTED_TABLES} 表 · {check['db_path']}",
         "action": "" if db_ready else "待建库(开始初始化)"},
        {"name": "分类白名单就绪", "status": "ok" if check["whitelist_ready"] else "err",
         "desc": check["whitelist_path"], "action": "" if check["whitelist_ready"] else "缺失 category_whitelist.yaml,请检查技能目录完整性"},
    ]
    items.append(_feishu_item(fs))

    todos = []
    if not (fs.get("tier") == "full"):
        todos.append({
            "title": "飞书配置(可选 · 强烈建议)",
            "steps": ["npm install -g @larksuite/cli", "npx -y skills add https://open.feishu.cn --skill -y",
                      "说「配置飞书」走非阻塞授权(calendar 域必授)", "授权完成 → 重看本报告飞书项转 ✓"],
        })
    todos.append({
        "title": "自定义数据目录(可选)",
        "steps": ["说「配置数据目录」或自行设置 SKILLS_DB_PATH 环境变量",
                  f"Windows: setx SKILLS_DB_PATH \"自定义路径\" · 其他平台: export SKILLS_DB_PATH=自定义路径",
                  "新开终端后重跑「首次使用」,数据落到新目录"],
    })

    verify = ["Python 可运行", "数据库已建", "数据位置已确认(默认或自定义)", "HELP 页面可打开(说「作息管家 help」)"]
    if fs.get("tier") == "full":
        verify.append({"text": "飞书同步已配置", "status": "ok"})
    elif fs.get("tier") == "partial":
        verify.append({"text": "飞书同步配置不完整(未授权或日历不可写)", "status": "fail"})
    else:
        verify.append({"text": "飞书同步未配置(强烈建议配置 · 不配则飞书同步不可用)", "status": "skip"})
    return items, todos, verify


def _build_scene(check: dict) -> dict:
    """向导场景数据(6 步步骤条 + 阶段判定 + 检查项/待办/验证 + 下一步动作)"""
    db_ready = check["db_ready"]
    writable = check["db_dir_writable"]
    fs = check["feishu"]
    items, todos, verify = _build_report(check)

    if not check["python_ok"]:
        stage, hint = "error", "Python 版本过低(需 ≥3.7),无法运行本技能"
        steps = [{"title": "环境检测", "status": "fail"}, {"title": "路径确认", "status": "pending"},
                 {"title": "建库+初始化", "status": "pending"}, {"title": "状态确认", "status": "pending"},
                 {"title": "初始化报告", "status": "pending"}, {"title": "完成", "status": "pending"}]
        next_act = {"label": "一键重试(复制指令给 AI)",
                    "prompt": "作息管家首次使用向导: 环境异常(Python 需 ≥3.7)。请检查 Python 安装后重做环境检测。"}
    elif not writable:
        stage, hint = "error", "数据目录不可写,无法建库"
        steps = [{"title": "环境检测", "status": "fail"}, {"title": "路径确认", "status": "current"},
                 {"title": "建库+初始化", "status": "pending"}, {"title": "状态确认", "status": "pending"},
                 {"title": "初始化报告", "status": "pending"}, {"title": "完成", "status": "pending"}]
        next_act = {"label": "一键重试(复制指令给 AI)",
                    "prompt": f"作息管家首次使用向导: 数据目录不可写({check['db_dir']})。请检查目录权限后重做环境检测。"}
    elif not db_ready:
        stage = "need_init"
        hint = "数据库未初始化,确认路径后即可开始建库(幂等可重试)"
        steps = [{"title": "环境检测", "status": "done"}, {"title": "路径确认", "status": "current"},
                 {"title": "建库+初始化", "status": "current"}, {"title": "状态确认", "status": "pending"},
                 {"title": "初始化报告", "status": "pending"}, {"title": "完成", "status": "pending"}]
        next_act = {
            "label": "开始初始化(复制指令给 AI)",
            "prompt": (f"作息管家首次使用: 数据路径已确认 {check['db_dir']}(默认即确认;想自定义目录请先设置 "
                       f"SKILLS_DB_PATH 环境变量再执行)。请执行: python scripts/schedule_cli.py init 建库(幂等,"
                       f"已建自动跳过),完成后用 schedule_cli.py status 确认,再重新生成首次使用报告。"),
        }
    else:
        stage = "already"
        hint = "环境已就绪,数据库已初始化,可以开始使用了"
        steps = [{"title": "环境检测", "status": "done"}, {"title": "路径确认", "status": "done"},
                 {"title": "建库+初始化", "status": "done"}, {"title": "状态确认", "status": "done"},
                 {"title": "初始化报告", "status": "done"}, {"title": "完成", "status": "done"}]
        next_act = {"label": "开始使用(复制指令给 AI)",
                    "prompt": "首次使用已完成。我想看「作息管家 help」浏览全部功能(或直接说「记录」记第一条作息)。"}
    extra = []
    if stage == "already" and fs.get("tier") != "full":
        extra.append({"label": "配置飞书(复制指令给 AI)",
                      "prompt": "作息管家首次使用: 请引导我配置飞书联动(唤醒词:配置飞书)。"
                                "说明:配合飞书效果最好,计划双向同步飞书日历;授权走强制非阻塞模式(calendar 域必授)。"})

    init = {
        "db_path": check["db_path"],
        "db_status": ("✓ 已初始化" if db_ready else "未初始化"),
        "tables": f"{check['db_tables']}/{EXPECTED_TABLES} 表",
        "whitelist": "✓ 就绪" if check["whitelist_ready"] else "✗ 缺失",
        "feishu": _feishu_item(fs)["desc"],
    }

    return {
        "wizard": {"steps": steps, "stage": stage},
        "env": check,
        "init": init,
        "feishu": _feishu_section(fs),
        "items": items,
        "todos": todos,
        "verify": verify,
        "next": next_act,
        "next_extra": extra,
        "hint": hint,
    }


def _envelope(scene: dict, error: dict = None) -> dict:
    """08 信封: meta + scene + items/todos/verify + 复制数据 5 段 + 复制日志 6 段"""
    occurred = _now()
    stage = scene["wizard"]["stage"]
    env = scene["env"]
    cd_payload = {
        "scene_id": "first_use",
        "command_cn": "首次使用",
        "occurred_at": occurred,
        "target": "作息管家 · 首次使用初始化",
        "payload": {
            "stage": stage,
            "env": {k: env[k] for k in ("os", "python", "db_dir", "db_tables", "db_ready",
                                        "db_dir_writable", "whitelist_ready", "env_skills_db_path")},
            "feishu": env["feishu"],
            "items": scene["items"],
            "todos": scene["todos"],
            "verify": scene["verify"],
        },
    }
    copy_log = {
        "scene": "首次使用 · 唤醒词「首次使用」 · 场景「first_use」",
        "thinking": "意图理解: 首次使用初始化 → 决策点: 环境缺什么?库是否已初始化?飞书是否可配? → "
                    "关键判断: 幂等可重试,已有库不重置;飞书强引导(配合飞书效果最好,明确拒绝才跳过)",
        "data_structure": "payload JSON(env/items/todos/verify)· DB 操作类型: "
                          + ("只读检测(库未建,建库动作由 AI 经 init 命令执行:"
                             f"CREATE TABLE IF NOT EXISTS ×{EXPECTED_TABLES} 幂等)"
                             if stage != "already" else "只读检测(库已建,无需写库)"),
        "call_chain": "python scripts/schedule_cli.py check · python scripts/schedule_cli.py init(幂等) · "
                      "python scripts/schedule_cli.py status · python scripts/schedule_cli.py render-first-use",
        "timestamp": f"{occurred} · {SKILL_VERSION}",
        "exception": "",
    }
    data = {
        "meta": {
            "mode": "first-use",
            "title": "首次使用 · 初始化报告",
            "wake_word": "首次使用",
            "command_cn": "首次使用",
            "occurred_at": occurred,
            "generated_at": occurred,
            "skill_version": SKILL_VERSION,
        },
        "scene": scene,
        "items": scene["items"],
        "todos": scene["todos"],
        "verify": scene["verify"],
        "copy_data": {"label": "复制数据", "text": json.dumps(cd_payload, ensure_ascii=False, indent=2)},
        "copy_log": {"label": "复制日志", "text": json.dumps(copy_log, ensure_ascii=False, indent=2)},
    }
    if error:
        data["error"] = error
    return {"data": data}


def _inject_html(template_html: str, payload: dict, title: str) -> str:
    """占位符注入(对齐 schedule_html_render.inject_into_template 约定):
    <script id="payload" type="application/json"> 锚点 → 整段替换为「锚点 + JSON + </script>」"""
    payload_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    payload_str = payload_str.replace("</", "<\\/")
    anchor = '<script id="payload" type="application/json">'
    if anchor not in template_html:
        raise RuntimeError(f"模板缺少 {anchor} 锚点")
    close_tag = "</script>"
    start = template_html.find(anchor)
    end = template_html.find(close_tag, start)
    if end < 0:
        raise RuntimeError(f"模板缺少 {close_tag} 闭合")
    end += len(close_tag)
    html = template_html[:start] + anchor + payload_str + close_tag + template_html[end:]
    html = html.replace("{{ title }}", title).replace("{{ TITLE }}", title)
    html = html.replace("{{ template_name }}", "开始使用/first_use_wizard.html")
    return html


def _render_to(check: dict, error: dict = None) -> dict:
    """组装场景 + 信封 + 注入模板,返回 {path, stage, html_len, payload}"""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"模板不存在: {TEMPLATE_PATH}")
    scene = _build_scene(check)
    payload = _envelope(scene, error)
    title = payload["data"]["meta"]["title"]
    html = _inject_html(TEMPLATE_PATH.read_text(encoding="utf-8"), payload, title)
    return {"path": None, "stage": scene["wizard"]["stage"], "html": html, "payload": payload}


# ── COMMANDS(渐进式注册通道 · 实施 T1 契约)──────────────────────────────

def cmd_setup_check(args):
    """check — 环境检测(结构化 JSON,AI 解析执行)"""
    try:
        print(json.dumps(_check_env(), ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "error": "check_failed",
                          "reason": str(e), "suggest": "检查运行环境后重试"}, ensure_ascii=False, indent=2))
        sys.exit(1)


def cmd_render_first_use(args):
    """render-first-use — 渲染首次使用初始化报告 HTML(默认输出到
    $SKILLS_DB_PATH/schedule_html/setup/首次使用_<时间戳>.html;支持 --out 自定义)"""
    out_arg = None
    for i, a in enumerate(args):
        if a == "--out" and i + 1 < len(args):
            out_arg = args[i + 1]
    try:
        check = _check_env()
        result = _render_to(check)
    except Exception as e:
        print(f"❌ 渲染失败: {e}", file=sys.stderr)
        sys.exit(1)

    output = Path(out_arg) if out_arg else None
    if output is None:
        from schedule_db import get_db_base_dir
        setup_dir = get_db_base_dir() / "schedule_html" / "setup"
        output = setup_dir / f"首次使用_{_ts()}.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result["html"], encoding="utf-8")

    stage_cn = {"need_path": "待确认路径", "need_init": "待建库", "already": "已初始化",
                "done": "完成", "error": "异常"}.get(result["stage"], result["stage"])
    print(f"✅ 已渲染: {output} ({stage_cn} · {len(result['html'])} bytes)")
    print("首次使用初始化报告已生成,请打开 HTML 查看:环境检测 / 检查项 / 待办指引 / 完成验证清单。")


COMMANDS = {
    "check": cmd_setup_check,
    "render-first-use": cmd_render_first_use,
}


if __name__ == "__main__":
    # 直接运行支持: python scripts/setup_scenarios.py check|render-first-use [--out x]
    _cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    handler = COMMANDS.get(_cmd)
    if handler is None:
        print(f"未知命令: {_cmd}(可用: {', '.join(COMMANDS)})", file=sys.stderr)
        sys.exit(1)
    handler(sys.argv[2:])

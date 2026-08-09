# render_开始使用.py - 私家大厨 · 开始使用域(setup-1 首次使用 4 步向导)渲染器
#
# 数据流:
#     ops 环境检测/持久化引导/建库状态 ─┐
#                                      ├─→ 占位符注入(<!--INJECT-DATA--> → window.__DATA__)
#     templates/开始使用/first_use_wizard.html ─┘
#                                      ↓
#     $CHEF_OUTPUT_DIR/setup/首次使用_<YYYYMMDD_HHMMSS>.html
#
# 08-HTML 交互规范 v1:
#     - 流程 5 向导(步骤条/阶段指示)+ 4 回执(成功/跳过/迁移提示/错误)
#     - 双按钮硬标准: 复制数据(5 段 JSON)+ 复制日志(6 段)
#     - 单工闭环: 阶段动作 = 复制带参数 prompt → AI 执行 CLI → 重渲染
#     - 双通道: 本脚本输出一句话结果(AI 交付 HTML 时同步文字一句话)
import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from 开始使用 import ops
from output_config import get_output_root

SKILL_VERSION = "v4.0-T4"
SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "开始使用" / "first_use_wizard.html"


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── 向导场景 payload ───────────────────────────────────────────────────

def _step_status(pred: bool, cur: bool) -> str:
    if pred:
        return "done"
    return "current" if cur else "pending"


def _apply_target_overrides(env: dict, db_path=None, out_dir=None) -> dict:
    """目标路径覆盖(实施要点: 设 env 当前进程不生效 → 用目标路径;向导如实显示并进复制 prompt)"""
    if db_path:
        env["db_path"] = db_path
        env["db_target"] = db_path
    if out_dir:
        env["output_root"] = out_dir
        env["output_target"] = out_dir
    return env


def wizard_scene(db_path=None, out_dir=None) -> dict:
    """4 步向导场景数据(步骤条 + 阶段判定 + 下一步动作 prompt)"""
    env = _apply_target_overrides(ops.env_check_payload(), db_path, out_dir)
    persist = ops.env_persist_payload()
    install = ops.install_cmds_payload()
    tables = env.get("db_tables", 0)
    initialized = env.get("db_initialized", False)

    if env.get("output_root_error"):
        stage = "error"
        hint = env["output_root_error"]
        next_act = {
            "label": "一键重试(复制指令给 AI)",
            "prompt": f"私家大厨首次使用向导: 环境异常({hint})。请协助检查后重做环境检测。",
        }
    elif not env.get("pyyaml"):
        stage = "need_env"
        hint = "环境缺失 pyyaml(自动安装: 装前展示命令 → 确认 → 执行 → 重检)"
        next_act = {
            "label": "我已确认,执行安装(复制指令给 AI)",
            "prompt": f"私家大厨首次使用向导: 环境缺失 pyyaml,请执行自动安装: "
                      f"{install['pyyaml'].get('cmd') or 'pip install --user pyyaml'},完成后重新做环境检测。",
        }
    elif not initialized:
        stage = "need_init"
        hint = "库未初始化(17 表未齐全),可开始建库;环境变量未配置可跳过(非阻塞,走默认目录)"
        next_act = {
            "label": "开始初始化(复制指令给 AI)",
            "prompt": f"私家大厨首次使用向导: 请执行初始化(建库,幂等)。"
                      f"数据库路径: {env['db_path']},输出目录: {env.get('output_root') or '(走默认)'}。",
        }
    else:
        stage = "already"
        hint = "已初始化(17 表齐全),直接使用;老库仅提示迁移,不自动迁移"
        next_act = {
            "label": "开始使用(复制)",
            "prompt": "私家大厨首次使用已完成,直接使用。我想录入第一道菜(唤醒词:录入食谱)。",
        }

    steps = [
        {"title": "环境检测", "status": _step_status(env.get("pyyaml", False), stage == "need_env")},
        {"title": "环境变量配置", "status": _step_status(persist.get("configured", False), stage == "need_env" and env.get("pyyaml"))},
        {"title": "建库", "status": _step_status(initialized, stage == "need_init")},
        {"title": "完成回执", "status": "done" if stage in ("already", "done") else "pending"},
    ]

    return {
        "wizard": {"steps": steps, "stage": stage},
        "env": env,
        "persist": persist,
        "install": install,
        "init": None,
        "next": next_act,
        "hint": hint,
        "db_tables": tables,
    }


def receipt_scene(init_result: dict, db_path=None, out_dir=None) -> dict:
    """步骤 4 完成回执场景数据(基于 AI 刚执行的 init 结果)"""
    env = _apply_target_overrides(ops.env_check_payload(), db_path, out_dir)
    persist = ops.env_persist_payload()
    ok = init_result.get("status") == "ok"
    stage = "done" if ok else "error"
    if ok:
        if init_result.get("skipped"):
            hint = f"✅ 已完成回执: {init_result['skipped']}。老库仅提示迁移,不自动迁移。"
        else:
            hint = f"✅ 已完成回执: 建库成功(17 表齐全)。空库直接录第一道菜即 onboarding。"
    else:
        hint = f"❌ 建库失败: {init_result.get('reason') or '未知原因'}"
    steps = [
        {"title": "环境检测", "status": "done"},
        {"title": "环境变量配置", "status": "done"},
        {"title": "建库", "status": "done" if ok else "fail"},
        {"title": "完成回执", "status": "done" if ok else "fail"},
    ]
    next_act = {
        "label": "录入第一道菜(复制)",
        "prompt": "首次使用完成。我想录入第一道菜(唤醒词:录入食谱),请开始引导我。",
    } if ok else {
        "label": "一键重试(复制指令给 AI)",
        "prompt": f"私家大厨首次使用向导: 建库失败({init_result.get('reason') or '未知原因'}),"
                  f"建议: {init_result.get('suggest') or '检查数据库目录可写性后重试'}。",
    }
    return {
        "wizard": {"steps": steps, "stage": stage},
        "env": env,
        "persist": persist,
        "install": ops.install_cmds_payload(),
        "init": init_result,
        "next": next_act,
        "hint": hint,
        "db_tables": env.get("db_tables", 0),
    }


# ── 08 信封(复制数据 5 段 + 复制日志 6 段)──────────────────────────────

def build_envelope(scene: dict, stage: str) -> dict:
    occurred = now_str()
    copy_data = {
        "scene_id": "first_use",
        "command_cn": "首次使用",
        "occurred_at": occurred,
        "target": "私家大厨 · 首次使用初始化",
        "payload": {
            "stage": stage,
            "env": scene["env"],
            "persist": scene["persist"],
            "init": scene.get("init"),
        },
    }
    call_chain = (
        "python scripts/开始使用/cli.py check / env-config / init · "
        "python scripts/render_开始使用.py render [--init-json <json>]"
    )
    copy_log = {
        "scene": "首次使用 · 唤醒词「首次使用」 · 场景「first_use」",
        "thinking": "意图理解: 首次使用初始化 → 决策点: 环境缺失?库是否已初始化? → "
                    "关键判断: 幂等可重试,已有库不重置",
        "data_structure": f"payload JSON(env/persist/init)· DB 操作类型: "
                          f"{'CREATE TABLE IF NOT EXISTS ×17(幂等)' if scene.get('init') else '只读检测'}",
        "call_chain": call_chain,
        "timestamp": f"{occurred} · {SKILL_VERSION}",
        "exception": scene.get("init", {}).get("reason", "") if scene.get("init") else "",
    }
    return {
        "meta": {
            "scene_id": "first_use",
            "wake_word": "首次使用",
            "command_cn": "首次使用",
            "occurred_at": occurred,
            "skill_version": SKILL_VERSION,
        },
        "scene": scene,
        "reminders": [{"type": "next", "text": "空库直接录第一道菜即 onboarding(示例数据/偏好档案已砍除,G1 决策)"}],
        "copy_data": copy_data,
        "copy_log": copy_log,
    }


# ── 占位符注入(去 Jinja2 · T1 机制)────────────────────────────────────

def inject_data(template_html: str, payload: dict) -> str:
    placeholder = "<!--INJECT-DATA-->"
    count = template_html.count(placeholder)
    if count != 1:
        raise ValueError(f"占位符必须唯一 1 次,实际 {count} 次")
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    payload_json = payload_json.replace("</", "<\\/")
    script_tag = f'<script>window.__DATA__ = {payload_json};</script>'
    return template_html.replace(placeholder, script_tag, 1)


# ── 渲染主函数 ────────────────────────────────────────────────────────

def render(args) -> bool:
    """渲染首次使用向导(无 --init-json)或完成回执(带 --init-json)"""
    if not TEMPLATE_PATH.exists():
        print(f"❌ 模板不存在: {TEMPLATE_PATH}", file=sys.stderr)
        return False

    init_result = None
    if args.get("--init-json"):
        try:
            init_result = json.loads(args["--init-json"])
        except json.JSONDecodeError as e:
            print(f"❌ --init-json 解析失败: {e}", file=sys.stderr)
            return False

    try:
        scene = receipt_scene(init_result, args.get("--db-path"), args.get("--out-dir")) if init_result \
            else wizard_scene(args.get("--db-path"), args.get("--out-dir"))
    except Exception as e:
        print(f"❌ 场景数据组装失败: {e}", file=sys.stderr)
        return False

    payload = build_envelope(scene, scene["wizard"]["stage"])

    try:
        template_html = TEMPLATE_PATH.read_text(encoding="utf-8")
        html = inject_data(template_html, payload)
    except (ValueError, OSError) as e:
        print(f"❌ 注入失败: {e}", file=sys.stderr)
        return False

    output_arg = args.get("--out")
    if output_arg:
        output_path = Path(output_arg)
    else:
        # 默认:$CHEF_OUTPUT_DIR/setup/首次使用_<时间戳>.html
        # --out-dir: 显式目标输出根目录(对齐实施要点: 设 env 当前进程不生效 → 用目标路径)
        base_dir = Path(args["--out-dir"]) if args.get("--out-dir") else get_output_root()
        setup_dir = base_dir / "setup"
        setup_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = setup_dir / f"首次使用_{ts}.html"

    if output_path.exists() and args.get("--no-clobber"):
        print(f"⏭ 跳过(已存在):{output_path}", file=sys.stderr)
        return True

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    stage_cn = {"need_env": "环境缺失", "need_init": "待建库", "already": "已初始化",
                "done": "完成回执", "error": "异常"}.get(scene["wizard"]["stage"], scene["wizard"]["stage"])
    print(f"✅ 已渲染: {output_path} ({stage_cn} · {len(html)} bytes)")
    return True


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("""用法:
    python scripts/render_开始使用.py render [--init-json '<json>'] [--out <path>] [--out-dir <dir>] [--db-path <dir>]

示例:
    python scripts/render_开始使用.py render
    python scripts/render_开始使用.py render --out-dir D:/MyChef --db-path D:/MyChef/.db
    python scripts/render_开始使用.py render --init-json '{"status":"ok","db_path":"D:/CookHub/chef_data.db","tables":17}'
    python scripts/render_开始使用.py render --out ./preview.html

环境变量:
    CHEF_OUTPUT_DIR / SKILLS_DATA_DIR   HTML 输出目录(默认 D:/CookHub)
    输出子目录: $CHEF_OUTPUT_DIR/setup/
    --out-dir / --db-path 优先级最高(显式目标路径,设 env 当前进程不生效时使用;向导如实显示并进复制 prompt)
""")
        return

    action = sys.argv[1]
    args = {}
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith("--"):
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
                args[arg] = sys.argv[i + 1]
                i += 2
            else:
                args[arg] = True
                i += 1
        else:
            i += 1

    if action == "render":
        if not render(args):
            sys.exit(1)
    else:
        print(f"未知操作: {action}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

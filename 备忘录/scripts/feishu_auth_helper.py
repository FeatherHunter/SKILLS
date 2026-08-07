"""
飞书授权 helper —— 强制非阻塞,杜绝 AI 工具 timeout 卡死问题

【第一性原理】
AI 工具的 timeout 是秒级(2-5 分钟),用户浏览器操作是分钟级(1-10 分钟),
时间维度不匹配 → 同步阻塞命令必被强杀 → lark-cli 被 SIGKILL → 流程卡死。

【正解】
lark-cli 已提供非阻塞多轮协议:
  Step 1: 调 --no-wait --json 拿 device_code + verification_url (不阻塞,秒返)
  Step 2: 发 URL + QR 给用户 (AI 本轮回复,结束 turn)
  Step 3: 等用户回复"好了" (用户操作时间,不在 AI 工具控制范围)
  Step 4: 调 --device-code <code> 续轮询 (秒级,token response received)

【本模块设计】
- 物理上不暴露同步阻塞 API,只暴露 3 个非阻塞函数
- 任何 AI 走本模块都自动安全
- lark-cli 老版本(< 1.0.82)可能不支持 --no-wait,会报错提示升级
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

# lark-cli 路径(假定在 PATH)
LARK_CLI = "lark-cli"

# QR code 默认输出目录(通用临时目录,不绑定任何用户机器;AI 工作区可用 env 覆盖)
DEFAULT_QR_DIR = Path(tempfile.gettempdir()) / "memo_feishu_qr"


def init_app(brand: str = "feishu") -> Dict[str, Any]:
    """
    Step 1: 发起飞书 app 创建 (不阻塞)。

    Returns:
        {
          "ok": True/False,
          "device_code": "...",  # 续轮询要用
          "verification_url": "...",  # 发给用户
          "user_code": "...",  # 备用,显示用
          "expires_in": 600,  # device_code 有效期(秒)
          ...
        }

    注意:
        - 必须传 --no-wait --json,否则会同步阻塞直到用户授权完成
        - 同一个 device_code 只能轮询一次,重启会作废
        - 必须在 device_code expires_in 秒内完成用户操作
    """
    cmd = [
        LARK_CLI, "config", "init", "--new",
        "--brand", brand,
        "--no-wait",
        "--json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        # 老版本 lark-cli 不支持 --no-wait,提示升级
        if "--no-wait" in result.stderr or "unknown flag" in result.stderr:
            raise RuntimeError(
                f"lark-cli 版本太老,不支持 --no-wait。\n"
                f"请先升级: lark-cli update\n"
                f"原 stderr: {result.stderr}"
            )
        raise RuntimeError(f"lark-cli config init 失败:\n{result.stderr}\nstdout: {result.stdout}")
    return json.loads(result.stdout)


def generate_qr(verification_url: str, out_path: Optional[Path] = None) -> Path:
    """
    Step 2: 把 verification_url 转成 PNG 二维码(给用户手机扫)。

    Args:
        verification_url: init_app() 返回的 verification_url
        out_path: 自定义输出路径(默认 DEFAULT_QR_DIR/feishu_qr_<timestamp>.png)

    Returns:
        生成的 PNG 文件绝对路径

    注意:
        - lark-cli qrcode 要求 --output 是相对路径
        - 默认输出到 AI 的 scratch 目录,AI 读 QR 用 <media> 标签发给用户
    """
    DEFAULT_QR_DIR.mkdir(parents=True, exist_ok=True)
    if out_path is None:
        import time
        out_path = DEFAULT_QR_DIR / f"feishu_qr_{int(time.time())}.png"
    # lark-cli 要求 --output 是相对当前目录的相对路径
    rel_path = out_path.name
    cwd = out_path.parent
    cmd = [
        LARK_CLI, "auth", "qrcode", verification_url,
        "--output", rel_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(f"生成 QR 失败:\n{result.stderr}\nstdout: {result.stdout}")
    return out_path


def poll_auth(device_code: str, domain: str = "task") -> Dict[str, Any]:
    """
    Step 3: 续轮询(在用户回复"好了"后调)。

    Args:
        device_code: init_app() 返回的 device_code
        domain: 飞书权限域(task/calendar/drive/im/...)

    Returns:
        {
          "ok": True/False,
          "user": {"openId": "...", "userName": "...", ...},
          "expires_at": "...",
          ...
        }

    注意:
        - 必须传 --device-code,不能用同步阻塞的 --domain X (会卡死)
        - 如果 device_code 过期(用户太久没操作),init_app() 重新拿一个
        - 飞书 server 默认 10 分钟 device_code 过期
    """
    cmd = [
        LARK_CLI, "auth", "login",
        "--domain", domain,
        "--device-code", device_code,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    # poll_auth 可能返回 ok=false 表示还在等(用户还没授权),也可能是真错
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(
            f"poll_auth 返回非 JSON:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )


def check_status() -> Dict[str, Any]:
    """
    辅助:检查当前 lark-cli auth 状态(用于诊断)。
    """
    cmd = [LARK_CLI, "auth", "status"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw_stdout": result.stdout, "raw_stderr": result.stderr}


# === 4 轮交互标准流程(给 AI 看的"工作流"注释) ===
#
# 轮 1: AI 调 init_app() → 拿 device_code + verification_url
# 轮 1 输出: 告诉用户"在浏览器打开链接(或扫 QR)"
# 轮 1 结束: 把 verification_url 和 QR 图片用 <media> 发给用户
#
# [用户操作:1 秒 - 10 分钟,在飞书里点同意]
#
# 轮 2: AI 收到用户"好了" → 调 poll_auth(device_code, domain="task")
# 轮 2 输出: "OK: 授权成功! 用户: xxx" + auth status 校验
# 轮 2 结束: 后续 SKILL 操作可以用 lark-cli(飞书已就绪)
#
# 关键:不要在轮 1 调任何会阻塞的 lark-cli 命令!
# 不要 set timeout,不要 run_in_background + timeout,直接前台 subprocess.run
# subprocess.run 不会 timeout(默认等命令结束),lark-cli --no-wait --json 立即返
#
# === 完整示例(伪代码) ===
#
# from scripts.feishu_auth_helper import init_app, generate_qr, poll_auth
#
# # 轮 1
# init_result = init_app()
# device_code = init_result["device_code"]
# url = init_result["verification_url"]
# qr_path = generate_qr(url)
# # 发用户:URL + <media src=qr_path />
# # 等用户说"好了"
#
# # 轮 2 (用户说"好了"后)
# auth_result = poll_auth(device_code, domain="task")
# if auth_result.get("ok"):
#     print("飞书授权成功,可以用了")


if __name__ == "__main__":
    # CLI 入口:辅助调试 / 单步跑某一步
    import argparse
    parser = argparse.ArgumentParser(description="飞书授权 helper(非阻塞模式)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Step 1: 发起 app 创建(非阻塞)")
    p_init.add_argument("--brand", default="feishu", choices=["feishu", "lark"])

    p_poll = sub.add_parser("poll", help="Step 2: 续轮询(用户'好了'后)")
    p_poll.add_argument("--device-code", required=True)
    p_poll.add_argument("--domain", default="task")

    p_qr = sub.add_parser("qr", help="生成 QR code")
    p_qr.add_argument("--url", required=True)
    p_qr.add_argument("--out", default=None)

    p_status = sub.add_parser("status", help="查看当前 auth 状态")

    args = parser.parse_args()

    if args.cmd == "init":
        result = init_app(args.brand)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "poll":
        result = poll_auth(args.device_code, args.domain)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "qr":
        out = generate_qr(args.url, Path(args.out) if args.out else None)
        print(f"QR saved: {out}")
    elif args.cmd == "status":
        result = check_status()
        print(json.dumps(result, ensure_ascii=False, indent=2))

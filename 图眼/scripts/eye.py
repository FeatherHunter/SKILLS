#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图眼 (Eye) — 给无视觉模型装眼睛的细节保真管线 CLI。

用 mmx vision (MiniMax VLM) 当「眼睛」，把图片转成高保真文本描述；
可选接 deepseek-v4-flash / MiniMax-M3 当「大脑」做推理。

子命令:
  look   — 粗看:单次整体描述 (1 次 vision)
  scan   — 精扫:3x3 切片 + 放大 + 逐片审计 + 合并细节文档 (10 次 vision)
  ocr    — 读图:专项提取图中所有文字
  ask    — 问图:看图 + 问题 → 大脑推理 (默认走 scan 模式喂细节文档)
  audit  — 审图:审问循环,大脑生成追问 → 眼睛定向回答 → 收敛

输出契约:默认 text;--output json 时 stdout 输出 {"status","data","message"}。
进度/错误走 stderr;stdout 永远是干净数据。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import urllib.parse
from pathlib import Path

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
MMX_BIN = r"C:\Users\辰辰洋洋\AppData\Roaming\npm\mmx.cmd"
MMX_FALLBACKS = ["mmx.cmd", "mmx"]
DEEPSEEK_BASE = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"
MMX_BRAIN_MODEL = "MiniMax-M3"

DEFAULT_GRID = 3          # 切片网格 N x N
DEFAULT_TARGET = 1024     # 切片放大到的边长 (px)
DEFAULT_OVERLAP = 0.12    # 切片重叠比例,防物体被切边
DEFAULT_ROUNDS = 2        # 审问循环默认轮数
DEFAULT_ASK_TARGETS = 3   # 每轮审问的追问条数

# 审计 prompt(精扫核心,软规则模板见 references/prompts.md)
AUDIT_PROMPT = (
    "你是高精度图像审计员。这是原图放大后的局部区域。请逐项列出:"
    "1) 所有物体及其大致位置(左/中/右/上/下);"
    "2) 图中出现的所有文字,逐字输出,一个标点都不要漏;"
    "3) 数字、价格、日期等精确数值;"
    "4) 颜色、材质等视觉细节。宁多勿漏,宁可误报不可漏报。"
)
OCR_PROMPT = (
    "请提取这张图片里的所有文字内容,逐字输出,保留原文格式,"
    "不要翻译、不要解释、不要添加任何内容。"
)

# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
def _err(msg: str, code: int = 1) -> "NoReturn":
    sys.stderr.write(f"[图眼] {msg}\n")
    sys.exit(code)


def _find_mmx() -> str:
    if os.path.isfile(MMX_BIN):
        return MMX_BIN
    for name in MMX_FALLBACKS:
        p = shutil_which(name)
        if p:
            return p
    _err("找不到 mmx CLI。请先执行: npm install -g mmx-cli")


def shutil_which(name: str) -> str | None:
    import shutil
    return shutil.which(name)


def _run(args: list[str], timeout: int = 600) -> str:
    """跑外部命令,返回 stdout(UTF-8)。非零退出抛异常。"""
    try:
        r = subprocess.run(
            args, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout)
    except FileNotFoundError:
        _err(f"命令不存在: {args[0]}")
    except subprocess.TimeoutExpired:
        _err(f"命令超时({timeout}s): {args[0]}")
    if r.returncode != 0:
        msg = (r.stderr or r.stdout or "").strip()[-800:]
        _err(f"命令失败({r.returncode}): {' '.join(args[:4])}...\n{msg}")
    return r.stdout


def _out(data, fmt: str, message: str = "") -> None:
    """统一输出契约。"""
    if fmt == "json":
        print(json.dumps({"status": "ok" if message == "" else message,
                          "data": data, "message": message},
                         ensure_ascii=False, indent=2))
    else:
        if isinstance(data, str):
            print(data)
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))


def _log(msg: str) -> None:
    sys.stderr.write(f"[图眼] {msg}\n")


def _norm_input(src: str, workdir: str) -> str:
    """把输入归一化为本地图片路径:支持本地文件 / http(s) URL / file-id。"""
    if src.startswith(("http://", "https://")):
        _log(f"下载图片: {src[:80]}")
        name = "download_" + Path(urllib.parse.urlparse(src).path).name or "img.png"
        dest = os.path.join(workdir, name)
        try:
            urllib.request.urlretrieve(src, dest)
        except Exception as e:
            _err(f"图片下载失败: {e}")
        return dest
    if src.startswith("file-"):
        return src  # 已上传的 file-id,直接透传
    p = Path(src)
    if not p.is_file():
        _err(f"图片不存在: {src} (期望本地文件 / URL / file-id)")
    return str(p)


# ---------------------------------------------------------------------------
# 眼睛层: mmx vision
# ---------------------------------------------------------------------------
def vision_describe(image: str, prompt: str, timeout: int = 300) -> str:
    """单次看图。image: 本地路径 / URL / file-id。返回描述文本。"""
    out = _run([_find_mmx(), "vision", "describe",
                "--image", image, "--prompt", prompt,
                "--output", "json", "--quiet"], timeout=timeout)
    try:
        data = json.loads(out)
        return str(data.get("content", out))
    except json.JSONDecodeError:
        return out


# ---------------------------------------------------------------------------
# 切片层: PIL
# ---------------------------------------------------------------------------
def slice_image(img_path: str, out_dir: str,
                grid: int = DEFAULT_GRID,
                target: int = DEFAULT_TARGET,
                overlap: float = DEFAULT_OVERLAP) -> list[dict]:
    """把图片切成 grid x grid 带重叠的切片,每片放大到 target 边长。

    返回 [{name, path, x, y, w, h}] (x/y/w/h 为原图坐标)。
    """
    try:
        from PIL import Image
    except ImportError:
        _err("缺少 Pillow。请执行: pip install Pillow")

    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    if grid < 1 or grid > 8:
        _err(f"grid 取值范围 1-8,当前 {grid}")
    if not (0 <= overlap < 0.5):
        _err(f"overlap 取值范围 [0, 0.5),当前 {overlap}")

    step_x = w * (1 - overlap) / grid
    step_y = h * (1 - overlap) / grid
    tile_w = w / grid + w * overlap / grid * 2
    tile_h = h / grid + h * overlap / grid * 2

    tiles = []
    for r in range(grid):
        for c in range(grid):
            left = int(c * step_x)
            top = int(r * step_y)
            right = min(w, int(left + tile_w))
            bottom = min(h, int(top + tile_h))
            left = max(0, right - int(tile_w))
            top = max(0, bottom - int(tile_h))
            crop = img.crop((left, top, right, bottom))
            scale = target / max(crop.width, crop.height)
            crop = crop.resize(
                (max(1, int(crop.width * scale)),
                 max(1, int(crop.height * scale))), Image.LANCZOS)
            name = f"tile_{r+1}_{c+1}.png"
            path = os.path.join(out_dir, name)
            crop.save(path)
            tiles.append({"name": name, "path": path,
                          "x": left, "y": top, "w": right - left, "h": bottom - top})
    return tiles


def _region_label(tile: dict, grid: int) -> str:
    """把切片映射成人类可读区域名,用于合并文档的标题。"""
    r = int(tile["name"].split("_")[1]) - 1
    c = int(tile["name"].split("_")[2].split(".")[0]) - 1
    row = ["上", "中", "下"][min(r, 2)]
    col = ["左", "中", "右"][min(c, 2)]
    if grid == 1:
        return "全景"
    return f"{row}{col}区(第{r+1}行第{c+1}列)"


# ---------------------------------------------------------------------------
# 大脑层: deepseek / MiniMax-M3
# ---------------------------------------------------------------------------
def brain_ask(text: str, brain: str = "mmx",
              max_tokens: int = 4096, timeout: int = 600) -> str:
    """把文本发给无视觉大脑推理。brain: 'mmx'(MiniMax-M3) 或 'deepseek'。"""
    if brain == "deepseek":
        key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not key:
            _err("大脑=deepseek 需要环境变量 DEEPSEEK_API_KEY。"
                 "可设置后重试,或改用 --brain mmx(MiniMax-M3,零配置)")
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [{"role": "user", "content": text}],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        req = urllib.request.Request(
            f"{DEEPSEEK_BASE}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {key}"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return str(body["choices"][0]["message"]["content"])
        except Exception as e:
            _err(f"deepseek 调用失败: {e}")
    # 默认: mmx text chat (MiniMax-M3)
    # 注意:长文本不能塞命令行参数(Windows ~32KB 限制),走 --messages-file
    fd, msg_path = tempfile.mkstemp(suffix=".json", prefix="eye_msg_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump([{"role": "user", "content": text}], f, ensure_ascii=False)
        out = _run([_find_mmx(), "text", "chat",
                    "--messages-file", msg_path,
                    "--model", MMX_BRAIN_MODEL,
                    "--max-tokens", str(max_tokens),
                    "--output", "json", "--quiet"], timeout=timeout)
    finally:
        try:
            os.unlink(msg_path)
        except OSError:
            pass
    try:
        data = json.loads(out)
        return str(data.get("content", out))
    except json.JSONDecodeError:
        return out


# ---------------------------------------------------------------------------
# 精扫管线
# ---------------------------------------------------------------------------
def build_scan_doc(img_path: str, workdir: str, grid: int, target: int,
                   overlap: float, timeout: int) -> dict:
    """L1 全景 + L2 切片精扫,返回 {doc, tiles, calls}。"""
    calls = 0
    sections = []

    _log("L1 全景:整体结构...")
    overall = vision_describe(
        img_path,
        "描述整体场景、所有主要物体及其空间关系,按左上→右下扫描顺序。",
        timeout)
    calls += 1
    sections.append({"title": "全景", "text": overall})

    _log(f"L2 切片:切 {grid}x{grid} + 放大 {target}px...")
    tiles = slice_image(img_path, workdir, grid, target, overlap)
    for t in tiles:
        label = _region_label(t, grid)
        _log(f"  审计 {t['name']} ({label})...")
        text = vision_describe(t["path"], AUDIT_PROMPT, timeout)
        calls += 1
        sections.append({"title": label, "text": text})

    doc = "\n\n".join(f"### {s['title']}\n{s['text']}" for s in sections)
    return {"doc": doc, "tiles": tiles, "calls": calls}


def _extract_questions(brain_output: str, n: int = DEFAULT_ASK_TARGETS) -> list[dict]:
    """从大脑输出解析追问清单:支持 JSON 数组或行列表。

    每项: {"region": "全景" | 切片名 | "上左区"..., "question": "..."}
    """
    text = brain_output.strip()
    # 尝试 JSON
    try:
        arr = json.loads(text)
        if isinstance(arr, list):
            return [{"region": str(x.get("region", "全景")),
                     "question": str(x.get("question", ""))}
                    for x in arr if x.get("question")][:n]
    except json.JSONDecodeError:
        pass
    # 行列表: "区域 | 问题" 或 "区域: 问题" 或 "1. 问题"
    items = []
    for line in text.splitlines():
        line = line.strip().lstrip("0123456789.-) ")
        if not line:
            continue
        region = "全景"
        for sep in ("|", "：", ":", "->", "→"):
            if sep in line:
                region, q = line.split(sep, 1)
                region = region.strip().strip("【】[]()").strip()
                line = q.strip()
                break
        items.append({"region": region, "question": line})
        if len(items) >= n:
            break
    return items


def _resolve_region(region: str, tiles: list[dict], grid: int) -> dict:
    """把大脑说的区域名映射到切片/全景。找不到就回退全景。"""
    r0 = region.lower()
    for t in tiles:
        if t["name"] in region or t["name"].replace(".png", "") in region:
            return {"kind": "tile", "path": t["path"], "label": _region_label(t, grid)}
    for t in tiles:
        label = _region_label(t, grid)
        if label and (label[:-3] in region or label in region):
            return {"kind": "tile", "path": t["path"], "label": label}
    if "全景" in region or "整体" in region or "全图" in region:
        return {"kind": "overall", "path": None, "label": "全景"}
    return {"kind": "overall", "path": None, "label": "全景"}


def audit_round(doc: str, img_path: str, tiles: list[dict], grid: int,
                brain: str, round_no: int, timeout: int) -> tuple[str, int]:
    """单轮审问:大脑生成追问 → 眼睛定向回答 → 增量合并。"""
    prompt = (
        f"这是一张图片的多区域细节描述文档:\n\n{doc[:6000]}\n\n"
        f"你现在扮演审问者,找出信息最不足的区域。请输出 {DEFAULT_ASK_TARGETS} 条追问,"
        f"每条格式: 区域名(用 全景 / 上左区 / 上中区 / 上右区 / 中左区 / 中中区 / 中右区 / "
        f"下左区 / 下中区 / 下右区)|具体问题。不要问文档里已有答案的问题。"
    )
    q_text = brain_ask(prompt, brain=brain, max_tokens=1200, timeout=timeout)
    questions = _extract_questions(q_text, DEFAULT_ASK_TARGETS)

    addons = []
    for i, q in enumerate(questions):
        tgt = _resolve_region(q["region"], tiles, grid)
        qlog = f"审问#{round_no}.{i+1} [{tgt['label']}] {q['question']}"
        _log(qlog)
        if tgt["kind"] == "tile":
            ans = vision_describe(tgt["path"],
                                  f"针对这个局部区域回答:\n{q['question']}\n"
                                  "只输出与该问题相关的细节,精确具体。", timeout)
        else:
            ans = vision_describe(img_path,
                                  f"针对整张图片回答:\n{q['question']}\n"
                                  "只输出与该问题相关的细节,精确具体。", timeout)
        addons.append(f"\n\n### 审问#{round_no}.{i+1} [{tgt['label']}] 问:{q['question']}\n答:{ans}")
    return doc + "".join(addons), len(addons)


# ---------------------------------------------------------------------------
# 子命令
# ---------------------------------------------------------------------------
def cmd_look(args) -> None:
    workdir = tempfile.mkdtemp(prefix="eye_look_")
    img = _norm_input(args.image, workdir)
    _log("眼睛:单次整体描述...")
    text = vision_describe(img, args.prompt, args.timeout)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        _log(f"描述已保存: {args.out}")
        data = {"content": text, "saved": args.out}
    else:
        data = {"content": text}
    _out(data, args.output)


def cmd_scan(args) -> None:
    workdir = tempfile.mkdtemp(prefix="eye_scan_")
    img = _norm_input(args.image, workdir)
    res = build_scan_doc(img, workdir, args.grid, args.target, args.overlap,
                         args.timeout)
    if args.out:
        Path(args.out).write_text(res["doc"], encoding="utf-8")
        _log(f"细节文档已保存: {args.out}")
        saved = args.out
    else:
        saved = None
    _log(f"共 {res['calls']} 次 vision 调用")
    _out({"doc": res["doc"], "calls": res["calls"], "saved": saved,
          "tiles": [t["name"] for t in res["tiles"]]},
         args.output, "scan-ok")


def cmd_ocr(args) -> None:
    workdir = tempfile.mkdtemp(prefix="eye_ocr_")
    img = _norm_input(args.image, workdir)
    _log("眼睛:专项 OCR 提取...")
    text = vision_describe(img, OCR_PROMPT, args.timeout)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        _log(f"文字已保存: {args.out}")
        data = {"text": text, "saved": args.out}
    else:
        data = {"text": text}
    _out(data, args.output)


def cmd_ask(args) -> None:
    workdir = tempfile.mkdtemp(prefix="eye_ask_")
    img = _norm_input(args.image, workdir)
    _log(f"眼睛:模式={args.mode} 看图...")
    if args.mode == "look":
        vision_text = vision_describe(img, args.prompt, args.timeout)
        doc = vision_text
    else:
        res = build_scan_doc(img, workdir, args.grid, args.target, args.overlap,
                             args.timeout)
        doc = res["doc"]
    prompt = (f"以下是一张图片的描述:\n\n{doc[:15000]}\n\n"
              f"用户的问题:{args.question}\n\n请基于描述给出准确回答。"
              f"若描述信息不足,明确说明缺什么,不要编造。")
    _log(f"大脑:brain={args.brain} 推理...")
    answer = brain_ask(prompt, brain=args.brain, max_tokens=args.max_tokens,
                       timeout=args.timeout)
    if args.out:
        report = f"## 问题\n{args.question}\n\n## 图片描述\n{doc}\n\n## 回答\n{answer}\n"
        Path(args.out).write_text(report, encoding="utf-8")
        _log(f"问答报告已保存: {args.out}")
    _out({"question": args.question, "answer": answer, "doc_len": len(doc)},
         args.output, "ask-ok")


def cmd_audit(args) -> None:
    workdir = tempfile.mkdtemp(prefix="eye_audit_")
    img = _norm_input(args.image, workdir)
    _log("L1+L2:先精扫建基线文档...")
    res = build_scan_doc(img, workdir, args.grid, args.target, args.overlap,
                         args.timeout)
    doc = res["doc"]
    total = res["calls"]
    for round_no in range(1, args.rounds + 1):
        _log(f"L4 审问:第 {round_no}/{args.rounds} 轮...")
        doc, n = audit_round(doc, img, res["tiles"], args.grid,
                             args.brain, round_no, args.timeout)
        total += n
    if args.out:
        Path(args.out).write_text(doc, encoding="utf-8")
        _log(f"审问收敛文档已保存: {args.out}")
        saved = args.out
    else:
        saved = None
    _log(f"共 {total} 次 vision 调用 + {args.rounds} 轮大脑审问")
    _out({"doc": doc, "calls": total, "rounds": args.rounds, "saved": saved},
         args.output, "audit-ok")


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="eye.py", description="图眼 — mmx vision 细节保真管线 (给无视觉模型装眼睛)",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--output", choices=["text", "json"], default="text",
                   help="输出格式 (默认 text)")
    p.add_argument("--timeout", type=int, default=600,
                   help="外部调用超时秒数 (默认 600)")
    sub = p.add_subparsers(dest="command", required=True)

    def img_arg(sp):
        sp.add_argument("--image", required=True,
                        help="图片:本地路径 / URL / file-id")
        return sp

    sp = sub.add_parser("look", help="粗看:单次整体描述")
    img_arg(sp)
    sp.add_argument("--prompt", default="详细描述这张图片,列出所有物体和所有文字。",
                    help="自定义看图问题")
    sp.add_argument("--out", default=None, help="保存描述到文件")
    sp.set_defaults(func=cmd_look)

    sp = sub.add_parser("scan", help="精扫:切片 + 逐片审计 + 合并细节文档")
    img_arg(sp)
    sp.add_argument("--grid", type=int, default=DEFAULT_GRID,
                    help=f"切片网格 N x N (默认 {DEFAULT_GRID})")
    sp.add_argument("--target", type=int, default=DEFAULT_TARGET,
                    help=f"切片放大边长 px (默认 {DEFAULT_TARGET})")
    sp.add_argument("--overlap", type=float, default=DEFAULT_OVERLAP,
                    help=f"切片重叠比例 (默认 {DEFAULT_OVERLAP})")
    sp.add_argument("--out", default=None, help="保存细节文档到文件")
    sp.set_defaults(func=cmd_scan)

    sp = sub.add_parser("ocr", help="读图:提取图中所有文字")
    img_arg(sp)
    sp.add_argument("--out", default=None, help="保存文字到文件")
    sp.set_defaults(func=cmd_ocr)

    sp = sub.add_parser("ask", help="问图:看图 + 问题 → 大脑推理")
    img_arg(sp)
    sp.add_argument("--question", required=True, help="要问的问题")
    sp.add_argument("--mode", choices=["look", "scan"], default="scan",
                    help="看图模式:look=单次粗看 / scan=精扫(默认 scan)")
    sp.add_argument("--grid", type=int, default=DEFAULT_GRID)
    sp.add_argument("--target", type=int, default=DEFAULT_TARGET)
    sp.add_argument("--overlap", type=float, default=DEFAULT_OVERLAP)
    sp.add_argument("--brain", choices=["mmx", "deepseek"], default="mmx",
                    help="大脑: mmx=MiniMax-M3(默认,零配置) / deepseek=deepseek-v4-flash(需 DEEPSEEK_API_KEY)")
    sp.add_argument("--max-tokens", type=int, default=4096)
    sp.add_argument("--out", default=None, help="保存问答报告到文件")
    sp.set_defaults(func=cmd_ask)

    sp = sub.add_parser("audit", help="审图:审问循环收敛细节")
    img_arg(sp)
    sp.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS,
                    help=f"审问轮数 (默认 {DEFAULT_ROUNDS})")
    sp.add_argument("--grid", type=int, default=DEFAULT_GRID)
    sp.add_argument("--target", type=int, default=DEFAULT_TARGET)
    sp.add_argument("--overlap", type=float, default=DEFAULT_OVERLAP)
    sp.add_argument("--brain", choices=["mmx", "deepseek"], default="mmx",
                    help="审问大脑 (默认 mmx)")
    sp.add_argument("--out", default=None, help="保存收敛文档到文件")
    sp.set_defaults(func=cmd_audit)
    return p


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

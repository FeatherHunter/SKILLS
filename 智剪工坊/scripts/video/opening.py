# -*- coding: utf-8 -*-
"""
智剪工坊 · opening_text 子技能（v1.0 新增）
在视频指定区域叠加静态说明文字（ffmpeg drawtext 封装）

对应 op: opening-text（v0.6 SKILL 文档声明, v1.0 实现）
对应文档: references/06-text.md §G
对应触发词: "片头文字"、"场景说明"、"加个标题"、"视频前加 N 秒文字"

用法:
  # 1. 基础用法（视频开头 2 秒左下角加白色加粗文字）
  python scripts/video_opening.py add \\
      --input in.mp4 --output out.mp4 \\
      --text "晨间体重 新的一天" --region bottom-left --duration 2

  # 2. 顶部居中加大字号
  python scripts/video_opening.py add \\
      --input in.mp4 --output out.mp4 \\
      --text "汉堡减肥 163g / 450大卡" \\
      --region top-center --font-size 72 --font-color yellow --duration 3

  # 3. 精确坐标
  python scripts/video_opening.py add \\
      --input in.mp4 --output out.mp4 \\
      --text "DIET DAY 2" --x 100 --y 200 --duration 5

依赖: ffmpeg（drawtext filter, libx264）


📖 SKILL.md §14 索引 → REQUIRED: read references/06-text.md
"""
import argparse
import platform
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from common import (
    run_ffmpeg,
    get_duration,
    ensure_dir,
    log_info,
    log_warn,
    log_section,
    safe_run,
    require_file,
    ParamError,
)


# ============================================================
# 9 宫格区域（region 简写 → ffmpeg 表达式）
# ============================================================

REGIONS = {
    # 名称           # x 表达式              # y 表达式
    "top-left":      ("20",                   "20"),
    "top-center":    ("(w-text_w)/2",         "20"),
    "top-right":     ("w-text_w-20",          "20"),
    "middle-left":   ("20",                   "(h-text_h)/2"),
    "middle-center": ("(w-text_w)/2",         "(h-text_h)/2"),
    "middle-right":  ("w-text_w-20",          "(h-text_h)/2"),
    "bottom-left":   ("20",                   "h-text_h-20"),
    "bottom-center": ("(w-text_w)/2",         "h-text_h-20"),
    "bottom-right":  ("w-text_w-20",          "h-text_h-20"),
}


# ============================================================
# 字体自动探测（按平台给候选，失败报错）
# ============================================================

FONT_CANDIDATES_WIN = [
    r"C:\Windows\Fonts\msyhbd.ttc",   # 微软雅黑 Bold（醒目首选）
    r"C:\Windows\Fonts\msyh.ttc",     # 微软雅黑
    r"C:\Windows\Fonts\simhei.ttf",   # 黑体
    r"C:\Windows\Fonts\simsun.ttc",   # 宋体
]
FONT_CANDIDATES_LINUX = [
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
]
FONT_CANDIDATES_MAC = [
    "/System/Library/Fonts/PingFang.ttc",
    "/Library/Fonts/PingFang.ttc",
]


def detect_font() -> str:
    """自动探测系统中文字体路径"""
    candidates = {
        "Windows": FONT_CANDIDATES_WIN,
        "Linux":   FONT_CANDIDATES_LINUX,
        "Darwin":  FONT_CANDIDATES_MAC,
    }.get(platform.system(), FONT_CANDIDATES_LINUX)
    for p in candidates:
        if Path(p).exists():
            log_info(f"自动选用字体: {p}")
            return p
    raise FileNotFoundError(
        f"找不到中文字体。已尝试:\n  " + "\n  ".join(candidates)
        + "\n请用 --font 显式指定一个 .ttf / .ttc 字体路径"
    )


# ============================================================
# 字符串转义（drawtext text= 特殊字符）
# ============================================================

def escape_drawtext(s: str) -> str:
    """转义 drawtext text= 字符串里的特殊字符

    我们用 subprocess.run 传 list, 不经 shell, 所以 ffmpeg 收到的 filter 字符串
    就是 Python str 的字面值。drawtext 内部 eval 规则:
      - 1 个 \\  → 字面 1 个反斜杠
      - \\:     → 字面 1 个冒号（防止被解析为 key=value 分隔符）
      - \\%     → 字面 1 个百分号（防止被解析为时间格式 %{pts\\:hms}）
      - \\'     → 字面 1 个单引号（防止破坏 text='...' 的包裹）

    所以输入字符的转义写法:
      - \\  → \\\\(2 个)
      - :  → \\:
      - %  → \\%
      - '  → \\'
    """
    # 反斜杠必须先转义, 否则后续 : % ' 的转义会重复加 \\
    s = s.replace("\\", "\\\\")
    s = s.replace(":", "\\:")
    s = s.replace("%", "\\%")
    s = s.replace("'", "\\'")
    return s


def escape_filter_commas(s: str) -> str:
    """Escape ffmpeg -vf 表达式里的 , → \\,

    -vf 语法用 , 分隔多个 filter。drawtext 内部表达式（如 alpha=if(...), 
    enable=between(t,0,2)）用 , 分隔函数参数, 必须 escape 否则 ffmpeg 
    误以为是 filter 分隔符。

    注意: text='...' 和 fontfile='...' 内部不应有 , (我们已转义), 所以
    对整个 filter 字符串 escape , 是安全的。
    """
    return s.replace(",", "\\,")


def escape_fontpath(p: str) -> str:
    """转义 fontfile= 路径 (Windows 反斜杠 + 冒号)"""
    # Windows 路径: C:\Windows\Fonts\xxx → C\:/Windows/Fonts/xxx
    return p.replace("\\", "/").replace(":", r"\:")


# ============================================================
# 位置解析
# ============================================================

def resolve_position(region: str, x: str, y: str) -> tuple[str, str]:
    """根据 region 简写或自定义 x/y 返回 ffmpeg 表达式"""
    if region:
        if region not in REGIONS:
            valid = ", ".join(REGIONS.keys())
            raise ParamError(f"未知 region: {region}。可选: {valid}")
        return REGIONS[region]
    if x is None or y is None:
        raise ParamError("region 和 (--x, --y) 必须二选一")
    return x, y


# ============================================================
# alpha 表达式（控制淡入淡出）
# ============================================================

def alpha_expr(start: float, duration: float, fade_in: float, fade_out: float) -> str:
    """生成 drawtext alpha= 表达式

    时序:    [0, start) → 透明
             [start, start+fade_in) → 淡入 (0→1)
             [start+fade_in, end-fade_out) → 完全不透明
             [end-fade_out, end) → 淡出 (1→0)
             [end, ∞) → 透明
    """
    if fade_in < 0 or fade_out < 0:
        raise ParamError("fade_in / fade_out 必须 >= 0")
    if fade_in + fade_out > duration:
        fade_in = fade_out = duration / 3
        log_warn(f"fade_in+fade_out > duration, 自动设为 {fade_in:.2f}s")
    end = start + duration
    fade_out_start = end - fade_out
    return (
        f"if(lt(t,{start}),0,"
        f"if(lt(t,{start + fade_in}),(t-{start})/{fade_in},"
        f"if(lt(t,{fade_out_start}),1,"
        f"if(lt(t,{end}),({end}-t)/{fade_out},0))))"
    )


# ============================================================
# 构造 drawtext filter
# ============================================================

def build_drawtext(
    text: str,
    region: str = "bottom-left",
    x: str = None,
    y: str = None,
    start: float = 0.0,
    duration: float = 2.0,
    font: str = None,
    font_size: int = 56,
    font_color: str = "white",
    outline_color: str = "black",
    outline_width: int = 3,
    shadow: bool = True,
    fade_in: float = 0.3,
    fade_out: float = 0.3,
) -> str:
    """生成完整 drawtext filter 字符串（不含 [0:v] 前缀）

    用 -vf 单 filter 形式（不需要 [vout] label），
    用 : 分隔 key=value, 整个串直接传给 ffmpeg。
    """
    if not text:
        raise ParamError("--text 不能为空")
    if duration <= 0:
        raise ParamError(f"--duration 必须 > 0 (当前: {duration})")
    if start < 0:
        raise ParamError(f"--start 必须 >= 0 (当前: {start})")

    if font is None:
        font = detect_font()
    x_expr, y_expr = resolve_position(region, x, y)
    safe_text = escape_drawtext(text)
    safe_font = escape_fontpath(font)
    alpha = alpha_expr(start, duration, fade_in, fade_out)

    parts = [
        f"text='{safe_text}'",
        f"fontfile='{safe_font}'",
        f"fontsize={font_size}",
        f"fontcolor={font_color}",
        f"borderw={outline_width}",
        f"bordercolor={outline_color}",
        f"x={x_expr}",
        f"y={y_expr}",
        # alpha 控制淡入淡出, enable 限定时段（两个表达式里的 , 要 escape）
        f"alpha={escape_filter_commas(alpha)}",
        f"enable={escape_filter_commas(f'between(t,{start},{start + duration})')}",
    ]
    if shadow:
        # drawtext 的阴影是 shadowx/shadowy（默认 0 = 无阴影）
        parts.append("shadowcolor=black@0.5")
        parts.append("shadowx=2")
        parts.append("shadowy=2")
    return "drawtext=" + ":".join(parts)


# ============================================================
# 主入口
# ============================================================

def add_text(
    input_path,
    output_path,
    text,
    region="bottom-left",
    x=None,
    y=None,
    start=0.0,
    duration=2.0,
    font=None,
    font_size=56,
    font_color="white",
    outline_color="black",
    outline_width=3,
    shadow=True,
    fade_in=0.3,
    fade_out=0.3,
):
    """在视频指定区域叠加说明文字

    用 -vf（单 filter）而不是 -filter_complex，避免 drawtext 表达式里的
    单引号/逗号与 filter_complex parser 冲突。
    """
    log_section(f"叠加文字 → {Path(output_path).name}")
    require_file(input_path, hint="检查 --input 路径")

    # 时长检查
    in_dur = get_duration(input_path)
    if start >= in_dur:
        raise ParamError(
            f"--start ({start}s) >= 输入视频时长 ({in_dur:.2f}s)，没空间叠加"
        )
    if start + duration > in_dur + 0.5:
        log_warn(
            f"--start+duration ({start + duration:.2f}s) > 视频时长 ({in_dur:.2f}s), "
            f"会自动截断到视频结尾"
        )
        duration = in_dur - start

    ensure_dir(Path(output_path).parent)

    filter_str = build_drawtext(
        text=text, region=region, x=x, y=y,
        start=start, duration=duration,
        font=font, font_size=font_size,
        font_color=font_color, outline_color=outline_color,
        outline_width=outline_width, shadow=shadow,
        fade_in=fade_in, fade_out=fade_out,
    )
    log_info(f"drawtext filter: {filter_str}")

    cmd = [
        "-i", str(input_path),
        "-vf", filter_str,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "copy",            # 音频不重编, 保留原质量
        "-movflags", "+faststart",
        str(output_path),
    ]
    run_ffmpeg(cmd, timeout=600)
    log_info(f"输出: {output_path}")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · opening_text (v1.0): 在视频指定区域叠加静态说明文字",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""region 9 宫格简写:
  top-left      top-center      top-right
  middle-left   middle-center   middle-right
  bottom-left   bottom-center   bottom-right

示例:
  %(prog)s add --input in.mp4 --output out.mp4 \\
              --text "晨间体重" --region bottom-left --duration 2

  %(prog)s add --input in.mp4 --output out.mp4 \\
              --text "汉堡减肥 163g" --region top-center \\
              --font-size 72 --font-color yellow --duration 3

  %(prog)s add --input in.mp4 --output out.mp4 \\
              --text "DIET" --x 100 --y 200 --duration 5""",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add", help="叠加文字到视频指定区域")
    p.add_argument("-i", "--input",  required=True, help="输入视频")
    p.add_argument("-o", "--output", required=True, help="输出视频")
    p.add_argument("--text",   required=True, help="文字内容")
    p.add_argument("--region", choices=list(REGIONS.keys()),
                   help="9 宫格区域简写（与 --x/--y 互斥）")
    p.add_argument("--x", help="自定义 x 坐标（ffmpeg 表达式，与 --region 互斥）")
    p.add_argument("--y", help="自定义 y 坐标（ffmpeg 表达式，与 --region 互斥）")
    p.add_argument("--start",         type=float, default=0.0,  help="开始时间秒（默认 0）")
    p.add_argument("--duration",      type=float, default=2.0,  help="显示时长秒（默认 2）")
    p.add_argument("--font",          help="字体路径（默认自动找中文字体）")
    p.add_argument("--font-size",     type=int,   default=56,   help="字号（默认 56）")
    p.add_argument("--font-color",    default="white",         help="字色（默认 white）")
    p.add_argument("--outline-color", default="black",         help="描边色（默认 black）")
    p.add_argument("--outline-width", type=int,   default=3,    help="描边宽度（默认 3）")
    p.add_argument("--no-shadow",    dest="shadow", action="store_false",
                   help="关闭阴影（默认开启）")
    p.add_argument("--fade-in",       type=float, default=0.3,  help="淡入秒数（默认 0.3）")
    p.add_argument("--fade-out",      type=float, default=0.3,  help="淡出秒数（默认 0.3）")
    p.set_defaults(func=lambda a: add_text(
        a.input, a.output,
        text=a.text, region=a.region, x=a.x, y=a.y,
        start=a.start, duration=a.duration,
        font=a.font, font_size=a.font_size,
        font_color=a.font_color, outline_color=a.outline_color,
        outline_width=a.outline_width, shadow=a.shadow,
        fade_in=a.fade_in, fade_out=a.fade_out,
    ))

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    safe_run(main)()
"""
② 契约层(CLI 入口)

子命令:
- compose:    合成封面(手动挡:用户传参数)
- auto:       智能合成(自动挡:AI 决策)
- diagnose:   诊断图片问题(半透明黑/暗区/对称)
- presets:    输出平台/比例预设

双层 API 设计:
- compose 子命令(手动挡):用户传 --layout --aspect --text --bg,直接调 ③ pipeline.compose
- auto 子命令(自动挡):用户只传 --photos,auto.py 调 diagnostics 决策,
                   决定后调 ③ pipeline.compose
- 两者都通过 pipeline.compose() 落地(同样的"基础 API")

输出格式:统一 {status, data, message, warnings}
退出码: 0=ok, 1=error, 2=warn
"""
import argparse
import json
import sys
from pathlib import Path

# 兼容两种调用方式:
# 1) python -m cover_compose.cli ...  (包内运行, 相对导入)
# 2) python scripts/ai/cover_compose/cli.py ...  (直接运行, 绝对导入)
_SKILL_AI_DIR = str(Path(__file__).parent.parent)
if _SKILL_AI_DIR not in sys.path:
    sys.path.insert(0, _SKILL_AI_DIR)

try:
    # 优先相对导入(包内运行)
    from .pipeline import compose
    from .auto import auto_compose
    from .diagnose import diagnose_image
    from .presets import get_preset, list_presets
except ImportError:
    # 兜底: 绝对导入(直接 python cli.py)
    from cover_compose.pipeline import compose
    from cover_compose.auto import auto_compose
    from cover_compose.diagnose import diagnose_image
    from cover_compose.presets import get_preset, list_presets


def cmd_compose(args):
    """手动挡 compose:用户传完整参数,直接调 ③ compose"""
    text = None
    if args.text:
        text = args.text
    result = compose(
        photos=args.photos,
        layout=args.layout,
        aspect=args.aspect,
        text=text,
        bg=args.bg,
        output=args.output,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "error":
        sys.exit(1)
    elif result["status"] == "warn":
        sys.exit(2)
    sys.exit(0)


def cmd_auto(args):
    """自动挡 auto:用户只传 --photos,自动分析 + 决策 + 调 ③ compose"""
    hint = None
    if args.hint:
        # 尝试解析为 JSON
        try:
            hint = json.loads(args.hint)
        except json.JSONDecodeError:
            hint = args.hint  # 不是 JSON 当字符串用
    result = auto_compose(
        photos=args.photos,
        hint=hint,
        output=args.output,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "error":
        sys.exit(1)
    elif result["status"] == "warn":
        sys.exit(2)
    sys.exit(0)


def cmd_diagnose(args):
    """诊断子命令"""
    checks = args.check.split(",") if args.check else ["all"]
    result = diagnose_image(args.image, checks)
    # 转 numpy.bool_ 为 python bool,避免 json 序列化失败
    import numpy as np
    def _convert(o):
        if isinstance(o, dict):
            return {k: _convert(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_convert(v) for v in o]
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        return o
    result = _convert(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["status"] != "error" else 1)


def cmd_presets(args):
    """预设子命令"""
    if args.list:
        result = list_presets()
    elif args.platform or args.aspect:
        result = get_preset(platform=args.platform, aspect=args.aspect)
    else:
        # 默认列出所有
        result = list_presets()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        prog="cover-composer",
        description="封面合成:多图旋转叠加 + 文字水印 + 半透明黑防御",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
双层 API 设计:
  手动挡 compose:  传 --layout --aspect --text --bg 完全控制
  自动挡 auto:     只传 --photos,AI 自动分析决策

示例:
  cover-composer auto --photos a.jpg b.jpg c.jpg -o cover.jpg
  cover-composer compose --photos a.jpg b.jpg c.jpg --layout polaroid --text '{"main":"14 天","sub":"-7 斤"}' -o cover.jpg
  cover-composer diagnose cover.jpg
  cover-composer presets --platform douyin
  cover-composer presets --list
        """,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # 自动挡 auto
    a = sub.add_parser("auto", help="智能合成(只传 --photos,AI 自动分析决策)")
    a.add_argument("--photos", nargs="+", required=True, help="图片路径(1+ 张)")
    a.add_argument("--hint", help="文字提示(字符串或 JSON,可选)")
    a.add_argument("--output", "-o", required=True, help="输出路径(.jpg/.png)")
    a.set_defaults(func=cmd_auto)

    # 手动挡 compose
    c = sub.add_parser("compose", help="手动合成(用户传完整参数)")
    c.add_argument("--photos", nargs="+", required=True, help="2+ 张图片路径")
    c.add_argument("--layout", choices=["symmetric-cascade", "cascade", "polaroid", "grid"],
                   default="symmetric-cascade", help="布局类型(默认 symmetric-cascade)")
    c.add_argument("--aspect", default="16:9", help="画布比例(默认 16:9)")
    c.add_argument("--text", help="文字层 JSON(详见 SKILL.md)")
    c.add_argument("--bg", default="#000000", help="画布背景色(默认纯黑)")
    c.add_argument("--output", "-o", required=True, help="输出路径(.jpg/.png)")
    c.set_defaults(func=cmd_compose)

    # diagnose
    d = sub.add_parser("diagnose", help="诊断图片问题")
    d.add_argument("--image", required=True, help="图片路径")
    d.add_argument("--check", default="all",
                   help="检查项(transparency,darkness,symmetry,all)")
    d.set_defaults(func=cmd_diagnose)

    # presets
    p = sub.add_parser("presets", help="平台/比例预设")
    p.add_argument("--platform", help="平台名(douyin/bilibili/...)")
    p.add_argument("--aspect", help="比例(16:9/9:16/4:3/1:1)")
    p.add_argument("--list", action="store_true", help="列出所有预设")
    p.set_defaults(func=cmd_presets)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "message": f"未捕获异常:{e}",
            "data": {},
        }, ensure_ascii=False))
        sys.exit(1)

"""
③ 业务核心:主流程编排 — 多图旋转叠加 + 文字水印 + 半透明黑防御

这是 cover_compose 的"基础 API",手动挡 compose() 和自动挡 auto_compose()
都最终调到这里。

双层 API 设计:
- 手动挡 compose(用户传参数):直接调本文件 compose()
- 自动挡 auto(用户只传 --photos):auto.py 调 diagnostics 决策,再调 compose()
"""
import json
from typing import Dict, Any, List

from .canvas import make_canvas, safe_save
from .diagnostics import full_diagnose
from .layout import get_layout
from .layers import rotate_hard, place, text_layer
from .validators import validate_all


ASPECT_RATIOS = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "4:3": (1440, 1080),
    "3:4": (1080, 1440),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "5:4": (1350, 1080),
}


def parse_text_spec(text_spec):
    """text_spec 可以是 JSON 字符串 或 dict

    支持两种格式:
    1. 简单: {"main": "14 天", "sub": "-7 斤"}
    2. 完整: {"lines": [{"text": "14 天", "position": "top-center", "size": 64, ...}]}
    """
    if isinstance(text_spec, str):
        try:
            text_spec = json.loads(text_spec)
        except json.JSONDecodeError as e:
            return None, f"text JSON 解析失败:{e}"
    if not isinstance(text_spec, dict):
        return None, f"text 必须是 dict 或 JSON 字符串,收到 {type(text_spec).__name__}"

    # 简单格式自动转换
    if "lines" not in text_spec:
        lines = []
        if "main" in text_spec:
            lines.append({"text": text_spec["main"], "position": "middle-center", "size": 200})
        if "sub" in text_spec:
            lines.append({"text": text_spec["sub"], "position": "top-center", "size": 80})
        if "tags" in text_spec:
            tags = text_spec["tags"]
            if isinstance(tags, str):
                tags = [tags]
            lines.append({"text": "\n".join(tags), "position": "bottom-center", "size": 50})
        return {"lines": lines}, None

    return text_spec, None


def compose(photos: List[str], layout: str = "symmetric-cascade",
           aspect: str = "16:9", text: Any = None, bg: str = "#000000",
           output: str = None) -> Dict[str, Any]:
    """主入口

    Returns:
        {
          "status": "ok" | "warn" | "error",
          "data": {"path": ..., "size": (W, H), "applied_layers": [...]},
          "message": "...",
          "warnings": [...]
        }
    """
    args = {"photos": photos, "aspect": aspect, "layout": layout, "bg": bg, "output": output}

    # 1. 校验
    ok, errors = validate_all(args)
    if not ok:
        return {
            "status": "error",
            "message": "参数校验失败",
            "errors": errors,
            "data": {},
        }

    # 2. 解析 text
    text_spec, text_err = parse_text_spec(text)
    if text_err:
        return {"status": "error", "message": text_err, "data": {}}

    # 3. 创建画布
    W, H = ASPECT_RATIOS[aspect]
    canvas = make_canvas(W, H, bg_color=bg)

    # 4. 算布局
    layout_fn = get_layout(layout)
    layers = layout_fn(W, H, photos)

    # 5. 按 z 顺序处理图层
    layers_sorted = sorted(layers, key=lambda l: l.z)
    applied = []
    for spec in layers_sorted:
        try:
            img = rotate_hard(spec.path, spec.target_w, spec.target_h, spec.angle)
            place(canvas, img, spec.x, spec.y)
            applied.append({
                "path": spec.path, "x": spec.x, "y": spec.y,
                "w": spec.target_w, "h": spec.target_h,
                "angle": spec.angle, "z": spec.z,
            })
        except Exception as e:
            return {
                "status": "error",
                "message": f"图层处理失败:{spec.path} - {e}",
                "data": {"applied": applied},
            }

    # 6. 烧文字
    if text_spec and "lines" in text_spec:
        for line in text_spec["lines"]:
            text_layer(
                canvas,
                content=line["text"],
                position=line.get("position", "middle-center"),
                font_size=line.get("size", 64),
                font_color=tuple(line.get("font_color", [255, 215, 0])),
                outline_color=tuple(line.get("outline_color", [0, 0, 0])),
                outline_width=line.get("outline_width", 4),
                font_path=line.get("font_path"),
            )

    # 7. 自检诊断
    diag = full_diagnose(canvas)

    # 8. 保存
    try:
        saved_path = safe_save(canvas, output)
    except Exception as e:
        return {
            "status": "error",
            "message": f"保存失败:{e}",
            "data": {"applied": applied, "diagnosis": diag},
        }

    # 9. 返回结果
    result = {
        "status": "warn" if (diag["status"] == "warn" or text_err) else "ok",
        "data": {
            "path": saved_path,
            "size": [W, H],
            "applied_layers": applied,
            "text_lines": len(text_spec.get("lines", [])) if text_spec else 0,
        },
        "message": f"合成完成:共 {len(applied)} 个图层",
        "warnings": diag["issues"],
    }
    if text_err:
        result["warnings"].append({"type": "text_parse", "message": text_err})
    return result

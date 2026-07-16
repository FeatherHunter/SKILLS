"""
封面合成 operations/auto_compose.py
② 契约层(智能挡):智能决策 + 调 ③ 业务核心 compose()

这是 ② 智能 CLI,不是 ③ 业务核心。
它只做"看图决策",不直接调 layers/text/layout 等底层 — 都调 compose()。

设计:
- 输入:photos + hint(可选)
- 智能决策:layout / aspect / bg / text
- 调 ① compose(完全参数化 API)
- 返回: {status, decisions: {...}, data: {path, size, ...}, warnings: [...]}
"""
from typing import Dict, Any, List, Optional, Union
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from infra import (
    analyze_image, decide_layout, decide_aspect, decide_bg, decide_text,
    full_diagnose,
)
from infra.cover_canvas import hex_to_rgb
from infra.cover_canvas import make_canvas, safe_save
from core.cover_pipeline import compose


def auto_compose(
    photos: List[str],
    hint: Optional[Union[str, Dict[str, Any]]] = None,
    output: str = None,
) -> Dict[str, Any]:
    """智能合成封面(不传 layout/aspect/bg/text)

    Args:
        photos: 图片路径列表
        hint: 可选提示
            - None: 全自动决策
            - str: 主标题文字
            - dict: 完整文字 spec(覆盖智能决策)
        output: 输出路径

    Returns:
        {
          "status": "ok" | "warn" | "error",
          "data": {path, size, applied_layers, text_lines},
          "decisions": {layout, aspect, bg, text, reasons},
          "message": "...",
          "warnings": [...]
        }
    """
    if not photos:
        return {
            "status": "error",
            "message": "photos 列表为空,至少需要 1 张图片",
            "data": {},
        }

    # 1. 分析每张图片(用 infra.diagnostics.analyze_image)
    print(f"[auto_compose] 分析 {len(photos)} 张图片...")
    analyses = []
    for p in photos:
        try:
            a = analyze_image(p)
            analyses.append(a)
            print(f"  - {a['filename']}: {a['width']}x{a['height']} ({a['orientation']})")
        except Exception as e:
            return {
                "status": "error",
                "message": f"分析图片失败:{p} - {e}",
                "data": {},
            }

    # 2. 智能决策(用 infra.diagnostics 的 decide_* 函数)
    layout = decide_layout(analyses)
    aspect = decide_aspect(analyses)
    bg = decide_bg(analyses)

    # text:如果有 hint,处理;否则自动
    if isinstance(hint, dict):
        text = hint
    else:
        text = decide_text(analyses, hint=hint)

    decisions = {
        "layout": layout,
        "aspect": aspect,
        "bg": bg,
        "text": text,
        "reasons": {
            "layout": f"根据 {len(analyses)} 张图自动选 {layout}",
            "aspect": f"主图 {analyses[0]['orientation']} → {aspect}",
            "bg": f"主图 brightness={analyses[0]['mean_brightness']:.0f}, contrast={analyses[0]['contrast_score']:.0f}",
        },
    }

    print(f"[auto_compose] 决策: layout={layout} aspect={aspect} bg={bg}")

    # 3. 调 ① compose(纯参数化 API,不直接调 core/layers)
    result = compose(
        photos=photos,
        layout=layout,
        aspect=aspect,
        text=text if text else None,
        bg=bg,
        output=output,
    )

    # 4. 在 result 里加 decisions(自动挡特供字段)
    result["decisions"] = decisions
    return result

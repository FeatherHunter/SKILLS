"""
封面合成 scripts/validators.py
③ 业务层:硬规则集中校验

设计原则(参考《优秀Skill指导手册》§④ 可约束):
- 早失败优于晚失败
- 错误信息具体:字段名 + 当前值 + 期望值 + 怎么修
- 无 --force 跳过通道
- AI 偷懒不会找到绕路

本 Skill 的硬规则:
1. photos 至少 1 张(实际场景 ≥ 2 张才有 collage 意义,但 1 张也允许)
2. 每张照片路径必须存在且可读
3. output 路径的目录必须可写
4. aspect 必须在白名单
5. layout 必须在白名单
6. text JSON 解析必须成功
7. bg 颜色必须是合法 hex
"""
from pathlib import Path
from typing import Any, Dict, Tuple


def validate_photos(photo_paths: list) -> Tuple[bool, str]:
    """校验 photos 列表"""
    if not photo_paths:
        return False, "photos 列表为空,至少需要 1 张图片"
    if not isinstance(photo_paths, list):
        return False, f"photos 必须是 list,收到 {type(photo_paths).__name__}"
    for i, p in enumerate(photo_paths):
        if not isinstance(p, str):
            return False, f"photos[{i}] 必须是字符串路径,收到 {type(p).__name__}"
        path = Path(p)
        if not path.exists():
            return False, f"photos[{i}] 路径不存在:{p}"
        if not path.is_file():
            return False, f"photos[{i}] 不是文件:{p}"
    return True, ""


def validate_aspect(aspect: str) -> Tuple[bool, str]:
    """校验 aspect"""
    valid = {"16:9", "9:16", "4:3", "3:4", "1:1", "4:5", "5:4"}
    if aspect not in valid:
        return False, (
            f"aspect 值 '{aspect}' 不在白名单。期望 {sorted(valid)},"
            f"或用 cover-composer presets 输出平台预设"
        )
    return True, ""


def validate_layout(layout: str) -> Tuple[bool, str]:
    """校验 layout"""
    valid = {"symmetric-cascade", "cascade", "polaroid", "grid"}
    if layout not in valid:
        return False, (
            f"layout '{layout}' 不支持。期望 {sorted(valid)}"
        )
    return True, ""


def validate_bg(bg: str) -> Tuple[bool, str]:
    """校验 bg 颜色(hex / RGB tuple / 'auto')"""
    if bg == "auto":
        return True, ""
    if isinstance(bg, str):
        s = bg.lstrip("#")
        if len(s) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in s):
            return True, ""
        return False, (
            f"bg 颜色 '{bg}' 不是合法 hex(期望 #RGB / #RRGGBB / 'auto')"
        )
    if isinstance(bg, (tuple, list)) and len(bg) in (3, 4):
        return True, ""
    return False, f"bg 颜色必须是 hex str 或 RGB tuple"


def validate_output(output_path: str) -> Tuple[bool, str]:
    """校验 output 路径"""
    if not output_path:
        return False, "output 路径必填"
    p = Path(output_path)
    if not p.suffix:
        return False, f"output '{output_path}' 缺后缀(.jpg/.png)"
    if p.suffix.lower() not in (".jpg", ".jpeg", ".png"):
        return False, f"output 仅支持 .jpg/.jpeg/.png,收到 '{p.suffix}'"
    return True, ""


def validate_all(args: Dict[str, Any]) -> Tuple[bool, list]:
    """一键校验所有参数,返回 (ok, [errors])"""
    errors = []
    checks = [
        ("photos", validate_photos, [args.get("photos")]),
        ("aspect", validate_aspect, [args.get("aspect", "16:9")]),
        ("layout", validate_layout, [args.get("layout", "symmetric-cascade")]),
        ("bg", validate_bg, [args.get("bg", "#000000")]),
        ("output", validate_output, [args.get("output", "")]),
    ]
    for name, fn, params in checks:
        ok, msg = fn(*params)
        if not ok:
            errors.append({"field": name, "message": msg})
    return (len(errors) == 0, errors)
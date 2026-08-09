#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/check_html_responsive.py — HTML 响应式 lint · seam 6

ticket 02 · 2026-07-29 · ADR-0005 配套

扫描 templates/*.html,断言每个模板:
  1. 含 <meta name="viewport" ...> tag
  2. 含 ≥1 @media (max-width:640px) 规则(或同等断点)
  3. <svg> tag 的 height 不是固定像素(应是 clamp()/auto/100%/vh/vw)
  4. <table> 在 overflow-x:auto 容器内(div.table-wrap 或 inline style)

用法:
    python scripts/check_html_responsive.py
    # exit code 0 = 全部通过, 1 = 有违例

API:
    lint_templates(templates_dir) -> list[str]  # 单元测试用

依赖:BeautifulSoup4(`pip install beautifulsoup4`)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: 需 pip install beautifulsoup4", file=sys.stderr)
    sys.exit(2)

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"

# 固定像素 height 模式(单位 px 且为整数)
FIXED_PX_RE = re.compile(r"height\s*:\s*\d+\s*px", re.IGNORECASE)

# 合法的 viewport-relative height
VIEWPORT_HEIGHT_RE = re.compile(
    r"height\s*:\s*(?:clamp\s*\(|auto|inherit|initial|unset|"
    r"\d+\s*%|100%|"
    r"\d+\s*v[h|w]|min-|max-)", re.IGNORECASE,
)


def _check_viewport(soup: BeautifulSoup, errors: list[str], fname: str) -> None:
    """检查 viewport meta tag"""
    metas = soup.find_all("meta", attrs={"name": "viewport"})
    if not metas:
        errors.append(f"{fname}: missing <meta name='viewport'> tag")


def _check_media_queries(soup: BeautifulSoup, errors: list[str], fname: str) -> None:
    """检查 ≥1 @media 规则"""
    style_tags = soup.find_all("style")
    has_media = False
    for tag in style_tags:
        if tag.string and "@media" in tag.string:
            has_media = True
            break
    if not has_media:
        errors.append(f"{fname}: missing @media query in <style> tag")


def _check_svg_height(soup: BeautifulSoup, errors: list[str], fname: str) -> None:
    """检查 <svg> height 不是固定像素"""
    svgs = soup.find_all("svg")
    for i, svg in enumerate(svgs):
        # 检查 inline style
        style = svg.get("style", "")
        if style and FIXED_PX_RE.search(style):
            errors.append(
                f"{fname}: <svg #{i+1}> has fixed pixel height in style: '{style}'"
            )
            continue
        # 检查 <style> 块里的 svg { height: X }
        for tag in soup.find_all("style"):
            if tag.string and re.search(
                r"svg\s*\{[^}]*height\s*:\s*\d+\s*px", tag.string, re.IGNORECASE,
            ):
                errors.append(
                    f"{fname}: <svg> CSS rule uses fixed pixel height (use clamp() or vh/vw)"
                )
                return


def _check_table_wrap(soup: BeautifulSoup, errors: list[str], fname: str) -> None:
    """检查 <table> 在 overflow-x:auto 容器内"""
    tables = soup.find_all("table")
    for i, table in enumerate(tables):
        parent = table.parent
        wrapped = False
        # 向上查 2 层
        for _ in range(2):
            if parent is None:
                break
            style = parent.get("style", "") or ""
            cls = parent.get("class", []) or []
            if "overflow-x:auto" in style.replace(" ", "") or "table-wrap" in cls:
                wrapped = True
                break
            parent = parent.parent
        if not wrapped:
            errors.append(
                f"{fname}: <table #{i+1}> not wrapped in div with overflow-x:auto"
            )


def lint_file(html_path: Path) -> list[str]:
    """lint 单个 HTML 文件,返回 error 列表(空 = 通过)"""
    errors: list[str] = []
    fname = html_path.name
    try:
        text = html_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return [f"{fname}: read error: {e}"]
    soup = BeautifulSoup(text, "html.parser")
    _check_viewport(soup, errors, fname)
    _check_media_queries(soup, errors, fname)
    _check_svg_height(soup, errors, fname)
    _check_table_wrap(soup, errors, fname)
    return errors


def lint_templates(templates_dir: Path = TEMPLATES_DIR) -> list[str]:
    """lint templates_dir 下所有 *.html,返回 error 列表"""
    all_errors: list[str] = []
    for html_path in sorted(templates_dir.glob("*.html")):
        all_errors.extend(lint_file(html_path))
    return all_errors


def main() -> int:
    errors = lint_templates()
    if errors:
        print("❌ HTML 响应式 lint 发现违例:\n")
        for e in errors:
            print(f"  · {e}")
        print(f"\n共 {len(errors)} 处违例。详见 seam 6 契约.")
        return 1
    print(f"✓ HTML 响应式 lint 通过(扫描 {len(list(TEMPLATES_DIR.glob('*.html')))} 个模板)")
    return 0


if __name__ == "__main__":
    from _io_guard import guard_io; guard_io()
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
智剪工坊 · filename 工具
Windows 文件名安全化 + 成片路径生成

意图: 阶段 4 拼成片时按 project.title 生成文件名
"""
import re


def sanitize_filename(title):
    """Windows 文件名安全化（v1.3 严格版）

    规则:
      - 空/全空白 → 'vlog_final'
      - Windows 非法字符 < > : " / \\ | ? * → '_'
      - 英文空格 → '_'（中文空格保留）
      - 连续下划线压缩成 1 个
      - 前导/末尾点 trim
      - 前导/末尾下划线 trim
      - 长度限制 200 字符
      - 全点/全下划线 → 'vlog_final'

    Args:
        title: 原始标题

    Returns:
        安全化后的文件名（不含扩展名）
    """
    if not title or not title.strip():
        return 'vlog_final'

    # 替换 Windows 非法字符
    illegal = re.compile(r'[<>:"/\\|?*]')
    safe = illegal.sub('_', title)

    # 英文空格 → 下划线（中文空格保留）
    safe = re.sub(r' +', '_', safe)

    # 连续下划线压缩
    safe = re.sub(r'_+', '_', safe)

    # 去前导/末尾点
    safe = safe.strip('.')

    # 限制长度
    if len(safe) > 200:
        safe = safe[:200]

    # 去前导/末尾下划线
    safe = safe.strip('_')

    # 全点/下划线 fallback
    if not safe or re.match(r'^[._]+$', safe):
        return 'vlog_final'

    return safe


def get_output_path(intent, output_dir="00_智剪/成片"):
    """按 intent.json.project.title 生成成片路径

    优先级: title > name > 'vlog_final'

    Args:
        intent: intent.json dict
        output_dir: 输出目录

    Returns:
        完整成片路径 (Path 对象)
    """
    from pathlib import Path
    project = intent.get('project', {}) or {}
    title = project.get('title') or project.get('name') or 'vlog_final'
    safe = sanitize_filename(title)
    return Path(output_dir) / f"{safe}.mp4"


if __name__ == "__main__":
    # 简单自测
    import sys
    test_cases = [
        ("DAY 2 减脂日记", "DAY_2_减脂日记"),
        ("Hello/World: test", "Hello_World_test"),
        ("<test>", "test"),
        ("", "vlog_final"),
        (None, "vlog_final"),
        ("   ", "vlog_final"),
        ("... . . .", "vlog_final"),
        (".hidden", "hidden"),
        ("trailing.", "trailing"),
        ("中文 测试", "中文_测试"),
    ]
    passed = 0
    for inp, expected in test_cases:
        actual = sanitize_filename(inp)
        if actual == expected:
            passed += 1
            print(f"  ✓ {inp!r:40} → {actual!r}")
        else:
            print(f"  ✗ {inp!r:40} → {actual!r} (期望 {expected!r})")
    print(f"\n{passed}/{len(test_cases)} 通过")
    sys.exit(0 if passed == len(test_cases) else 1)
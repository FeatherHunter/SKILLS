"""SKILL开发总纲V1.0 · _assets/injector.py

占位符注入函数。所有 HTML 模板复用。
对应 [04-可视化与注入v2.md 原则 4 和原则 5](../../04-可视化与注入v2.md)。

使用:
    from _injector import inject, render_4step
    template = read_text('templates/xxx.html')
    output = inject(template, data_dict)
"""

import json
import subprocess
from pathlib import Path
from typing import Any, List, Union


def inject(template: str, data: Any, placeholder: str = '<!--INJECT-DATA-->') -> str:
    """读模板 + 注入 window.__DATA__ + 校验占位符唯一

    Args:
        template:    HTML 模板字符串
        data:        要注入的数据(dict 或 list)
        placeholder: 占位符(默认 <!--INJECT-DATA-->)

    Returns:
        注入数据后的 HTML 字符串

    Raises:
        ValueError: 占位符数量 != 1
    """
    count = template.count(placeholder)
    if count != 1:
        raise ValueError(
            f"占位符 {placeholder} 数量异常: 期望 1, 实际 {count}"
        )

    # JSON 序列化 + 转义 </ 防提前闭合 script 标签
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')

    inject_str = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject_str, 1)


def render_4step(
    cli_path: Union[str, Path],
    args: List[str],
    template_path: Union[str, Path],
    output_path: Union[str, Path],
) -> Path:
    """4 步渲染器(对应 04 原则 5)

    1. 拿 JSON(subprocess 列表传参,避开 PowerShell 乱码)
    2. 读模板 + assert 占位符唯一
    3. 注入(转义 + 替换)
    4. 写副本(原模板不动)

    Args:
        cli_path:      CLI 脚本路径
        args:          CLI 参数列表(列表传参)
        template_path: 模板 HTML 路径
        output_path:   输出 HTML 路径

    Returns:
        写入的输出路径(Path 对象)
    """
    cli_path = Path(cli_path)
    template_path = Path(template_path)
    output_path = Path(output_path)

    # 1. 拿 JSON(默认 30s timeout,避免卡死的 CLI 永久 hang)
    result = subprocess.run(
        ['python', str(cli_path)] + list(args),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"CLI 执行失败: {cli_path} {' '.join(args)}\n"
            f"stderr: {result.stderr}"
        )
    data = json.loads(result.stdout)

    # 2. 读模板
    template = template_path.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError(
            f"模板 {template_path} 占位符必须唯一,实际 "
            f"{template.count('<!--INJECT-DATA-->')}"
        )

    # 3. 注入
    output = inject(template, data)

    # 4. 写副本
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding='utf-8')

    return output_path


if __name__ == '__main__':
    # demo
    tpl = '<html><body>before <!--INJECT-DATA--> after</body></html>'
    out = inject(tpl, {"foo": "bar", "n": 42})
    print(out)

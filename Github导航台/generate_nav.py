#!/usr/bin/env python3
"""
generate_nav.py — 扫描 docs/ 目录，生成 structure.json 导航数据
依赖环境变量 STUDYNOTES_DOCS 指定 docs 根目录路径
"""
import json
import os
import sys
from pathlib import Path


def get_docs_path() -> Path:
    """获取 docs 目录路径，优先读取环境变量"""
    docs_path = os.environ.get("STUDYNOTES_DOCS")
    if docs_path:
        path = Path(docs_path).resolve()
        if not path.exists():
            print(f"[ERROR] 环境变量 STUDYNOTES_DOCS 指向的路径不存在: {path}")
            sys.exit(1)
        return path

    # 环境变量未设置，提示用户
    print("[INFO] 未检测到环境变量 STUDYNOTES_DOCS，正在引导配置...")
    # 向上两级到项目根目录，再进入 docs
    default_path = Path(__file__).parent.parent.parent / "docs"
    current_value = os.environ.get("STUDYNOTES_DOCS", str(default_path))

    print(f"\n[PROMPT] 请输入 docs 目录的绝对路径（直接回车使用默认值）:")
    print(f"  默认值: {default_path}")

    # 检测是否交互式终端
    import sys
    if sys.stdin.isatty():
        try:
            user_input = input(f"  输入路径: ").strip()
        except (EOFError, OSError):
            user_input = ""
    else:
        print("[INFO] 非交互环境，自动使用默认路径")
        user_input = ""

    docs_path_str = user_input if user_input else str(default_path)
    docs_path = Path(docs_path_str).resolve()

    if not docs_path.exists():
        print(f"[ERROR] 路径不存在: {docs_path}")
        sys.exit(1)

    # 写入环境变量（仅本次会话）
    os.environ["STUDYNOTES_DOCS"] = str(docs_path)
    _save_env_config(docs_path)
    print(f"[OK] docs 路径已配置为: {docs_path}")
    return docs_path


def _save_env_config(path: Path):
    """将环境变量配置持久化到 .env 文件"""
    env_file = Path(__file__).parent / ".env"
    try:
        env_file.write_text(f"STUDYNOTES_DOCS={path}\n", encoding="utf-8")
        print(f"[OK] 路径已保存到 {env_file}（下次运行自动加载）")
    except Exception as e:
        print(f"[WARN] 无法保存配置到 .env: {e}")


def load_env_config():
    """尝试从 .env 文件加载环境变量"""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def scan_docs_structure(docs_path: Path) -> dict:
    """扫描 docs 目录，返回子目录和根文件结构"""
    subdirs = []
    root_files = []

    # 扫描直接子目录
    for subdir in sorted(docs_path.iterdir()):
        if not subdir.is_dir():
            continue
        # 跳过隐藏目录和特殊目录
        if subdir.name.startswith(".") or subdir.name in ("node_modules", "__pycache__"):
            continue

        html_files = []
        for f in sorted(subdir.glob("*.html")):
            if f.name == "index.html":
                # 子目录的 index.html 用目录名作为标签
                label = subdir.name
            else:
                label = _generate_label(f.stem)
            html_files.append({
                "name": f.name,
                "label": label
            })

        if html_files:
            subdirs.append({
                "name": subdir.name,
                "path": subdir.name + "/",
                "files": html_files
            })

    # 扫描根目录 HTML 文件
    for f in sorted(docs_path.glob("*.html")):
        if f.name in ("index.html", "structure.json"):
            continue
        label = _generate_label(f.stem)
        root_files.append({
            "name": f.name,
            "label": label,
            "isEntry": False
        })

    # 检查根目录是否有 index.html
    index_file = docs_path / "index.html"
    if index_file.exists():
        root_files.insert(0, {
            "name": "index.html",
            "label": "本导航台",
            "isEntry": True
        })

    return {
        "subdirs": subdirs,
        "rootFiles": root_files
    }


def _generate_label(stem: str) -> str:
    """从文件名生成人类可读标签"""
    # 移除常见前缀后缀
    label = stem
    label = label.replace("_", " ").replace("-", " ")
    label = label.replace("2Study_StudyNotes", "目录树")
    label = label.replace("StudyNotes", "StudyNotes")
    # 保留大小写
    return label.strip()


def main():
    # 1. 加载 .env 配置
    load_env_config()

    # 2. 获取 docs 路径
    docs_path = get_docs_path()
    print(f"[INFO] 扫描目录: {docs_path}")

    # 3. 扫描结构
    structure = scan_docs_structure(docs_path)
    total_subdirs = len(structure["subdirs"])
    total_root = len(structure["rootFiles"])
    print(f"[INFO] 扫描完成: {total_subdirs} 个子目录, {total_root} 个根文件")

    # 4. 生成 structure.json
    output_file = docs_path / "structure.json"
    output_file.write_text(json.dumps(structure, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] structure.json 已生成: {output_file}")

    return structure


if __name__ == "__main__":
    main()

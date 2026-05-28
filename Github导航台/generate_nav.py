#!/usr/bin/env python3
"""
generate_nav.py — 扫描 $STUDYNOTES_DOCS 目录，在 SKILL 目录下生成 structure.json
依赖环境变量 STUDYNOTES_DOCS 和 GITHUB_PAGES_BASE
"""
import json
import os
import re
import sys
from pathlib import Path


def get_docs_path() -> Path:
    """获取导航台目录路径，优先读取环境变量"""
    docs_path = os.environ.get("STUDYNOTES_DOCS")
    if docs_path:
        path = Path(docs_path).resolve()
        if not path.exists():
            print(f"[ERROR] 环境变量 STUDYNOTES_DOCS 指向的路径不存在: {path}")
            sys.exit(1)
        return path

    # 环境变量未设置，提示用户
    print("[INFO] 未检测到环境变量 STUDYNOTES_DOCS，正在引导配置...")
    # 向上三级到 SKILL 所在项目根目录，作为兜底默认值
    default_path = Path(__file__).parent.parent.parent

    print(f"\n[PROMPT] 请输入导航台根目录的绝对路径（直接回车使用默认值）:")
    print(f"  默认值: {default_path}")

    # 检测是否交互式终端
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

    # 写入环境变量（仅本次会话），等待 GITHUB_PAGES_BASE 配置后一起保存
    os.environ["STUDYNOTES_DOCS"] = str(docs_path)
    print(f"[OK] 导航台路径已配置为: {docs_path}")
    return docs_path


def get_github_pages_base() -> str:
    """获取 GitHub Pages 根地址，优先读取环境变量"""
    base = os.environ.get("GITHUB_PAGES_BASE")
    if base:
        if not base.endswith("/"):
            print("[WARN] GITHUB_PAGES_BASE 应以 / 结尾，已自动添加")
            base += "/"
            os.environ["GITHUB_PAGES_BASE"] = base
        return base

    # 环境变量未设置，提示用户
    print("[INFO] 未检测到环境变量 GITHUB_PAGES_BASE，正在引导配置...")

    print(f"\n[PROMPT] 请输入 GitHub Pages 根地址（必须以 / 结尾）:")
    print(f"  示例: https://<用户名>.github.io/<仓库名>/")
    print(f"  注意: 末尾必须有斜杠 /")

    if sys.stdin.isatty():
        try:
            user_input = input(f"  输入地址: ").strip()
        except (EOFError, OSError):
            user_input = ""
    else:
        print("[ERROR] 非交互环境无法引导 GITHUB_PAGES_BASE，请先设置环境变量")
        sys.exit(1)

    if not user_input:
        print("[ERROR] GITHUB_PAGES_BASE 不能为空")
        sys.exit(1)

    if not user_input.startswith(("http://", "https://")):
        print("[ERROR] GITHUB_PAGES_BASE 必须是以 http:// 或 https:// 开头的有效 URL")
        sys.exit(1)

    if not user_input.endswith("/"):
        user_input += "/"

    os.environ["GITHUB_PAGES_BASE"] = user_input
    print(f"[OK] GITHUB_PAGES_BASE 已配置为: {user_input}")
    return user_input


def _save_env_config(docs_path: Path, github_pages_base: str):
    """将环境变量配置持久化到 .env 文件"""
    env_file = Path(__file__).parent / ".env"
    try:
        lines = [f"STUDYNOTES_DOCS={docs_path}", f"GITHUB_PAGES_BASE={github_pages_base}"]
        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[OK] 配置已保存到 {env_file}（下次运行自动加载）")
    except Exception as e:
        print(f"[WARN] 无法保存配置到 .env: {e}")


def _is_wsl() -> bool:
    """检测是否在 WSL 环境中运行"""
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except Exception:
        return False


def _win_to_wsl_path(path: str) -> str:
    """将 Windows 路径 (D:\\xxx) 转换为 WSL 路径 (/mnt/d/xxx)"""
    m = re.match(r"^([A-Za-z]):\\(.*)$", path)
    if m:
        drive = m.group(1).lower()
        rest = m.group(2).replace("\\", "/")
        return f"/mnt/{drive}/{rest}"
    return path


def load_env_config():
    """尝试从 .env 文件加载环境变量"""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

    # WSL 兼容：将 Windows 路径自动转为 /mnt/ 格式
    if _is_wsl():
        for key in ("STUDYNOTES_DOCS",):
            val = os.environ.get(key)
            if val and re.match(r"^[A-Za-z]:\\", val):
                converted = _win_to_wsl_path(val)
                os.environ[key] = converted
                print(f"[INFO] WSL 路径转换: {key} {val} -> {converted}")


def scan_docs_structure(docs_path: Path) -> dict:
    """扫描 $STUDYNOTES_DOCS 目录，返回子目录和根文件结构"""
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
    label = stem
    label = label.replace("_", " ").replace("-", " ")
    return label.strip()


def main():
    # 1. 加载 .env 配置
    load_env_config()

    # 2. 获取导航台目录路径
    docs_path = get_docs_path()

    # 3. 获取 GitHub Pages 根地址
    github_pages_base = get_github_pages_base()

    # 4. 保存环境变量到 .env
    _save_env_config(docs_path, github_pages_base)

    # 5. 扫描结构
    structure = scan_docs_structure(docs_path)
    total_subdirs = len(structure["subdirs"])
    total_root = len(structure["rootFiles"])
    print(f"[INFO] 扫描完成: {total_subdirs} 个子目录, {total_root} 个根文件")

    # 6. 生成 structure.json 到 SKILL 目录下
    structure["githubPagesBase"] = github_pages_base
    output_file = Path(__file__).parent / "structure.json"
    output_file.write_text(json.dumps(structure, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] structure.json 已生成: {output_file}")

    return structure


if __name__ == "__main__":
    main()

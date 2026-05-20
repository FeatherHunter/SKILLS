#!/usr/bin/env python3
"""
deploy.py — 部署导航台到 $STUDYNOTES_DOCS 目录
依赖: STUDYNOTES_DOCS, GITHUB_PAGES_BASE
流程: 1) 运行 generate_nav.py 在 SKILL 目录生成 structure.json
      2) 复制 index.html 和 structure.json 到 $STUDYNOTES_DOCS/ 目录
      3) 自动 git commit + push（如有变化）
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

# 添加 SKILL 目录到路径，引用同级模块
SKILL_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SKILL_DIR))


def run_generate_nav():
    """运行 generate_nav.py 生成 structure.json"""
    gen_script = SKILL_DIR / "generate_nav.py"
    print("\n[STEP 1/3] 运行 generate_nav.py 扫描 $STUDYNOTES_DOCS 目录...")
    result = subprocess.run(
        [sys.executable, str(gen_script)],
        capture_output=False
    )
    if result.returncode != 0:
        print("[ERROR] generate_nav.py 执行失败")
        sys.exit(1)
    print("[OK] structure.json 生成完成")


def copy_files_to_docs():
    """复制 index.html 和 structure.json 到 $STUDYNOTES_DOCS/ 目录"""
    print("\n[STEP 2/3] 复制文件到 $STUDYNOTES_DOCS/ 目录...")

    # 从环境变量或 .env 获取导航台路径
    from generate_nav import load_env_config
    load_env_config()
    docs_path = Path(os.environ.get("STUDYNOTES_DOCS")).resolve()

    src_html = SKILL_DIR / "index.html"
    dst_html = docs_path / "index.html"
    src_json = SKILL_DIR / "structure.json"  # generate_nav.py 输出到 SKILL 目录

    if not src_html.exists():
        print(f"[ERROR] 源文件不存在: {src_html}")
        sys.exit(1)
    if not src_json.exists():
        print(f"[ERROR] structure.json 未生成，请先运行 generate_nav.py")
        sys.exit(1)

    # 备份 index.html（如果存在）
    if dst_html.exists():
        backup = dst_html.with_suffix(".html.bak")
        shutil.copy2(dst_html, backup)
        print(f"[INFO] 已备份原 index.html -> {backup.name}")

    # 复制文件
    shutil.copy2(src_html, dst_html)
    print(f"[OK] index.html -> {dst_html}")

    print(f"[OK] 文件复制完成")
    return docs_path


def git_commit_push(docs_path: Path):
    """检查 git 变化，如有变化则 commit + push"""
    print("\n[STEP 3/3] 检查 git 变化并推送...")

    os.chdir(docs_path)

    # 检查状态
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True
    )
    changed = result.stdout.strip()

    if not changed:
        print("[INFO] $STUDYNOTES_DOCS 已是最新，无需推送")
        return

    print(f"[INFO] 检测到变化:\n{changed}")

    # Stage 所有更改
    subprocess.run(["git", "add", "."], check=True)

    # 获取变更文件列表用于 commit message
    changed_files = [line.strip().split(maxsplit=1)[1] for line in changed.splitlines()]
    file_summary = ", ".join(changed_files[:5])
    if len(changed_files) > 5:
        file_summary += f" (+{len(changed_files) - 5} more)"

    commit_msg = f"chore: 更新导航台 {file_summary}"

    subprocess.run(
        ["git", "commit", "-m", commit_msg],
        check=True
    )
    print(f"[OK] 已提交: {commit_msg}")

    # Push
    push_result = subprocess.run(["git", "push"], capture_output=True, text=True)
    if push_result.returncode != 0:
        print(f"[ERROR] push 失败: {push_result.stderr}")
        sys.exit(1)

    print("[OK] 已推送到远程仓库，GitHub Pages 将自动更新")


def main():
    print("=" * 50)
    print("  文档导航台 · 部署脚本")
    print("=" * 50)

    # Step 1: 生成结构数据
    run_generate_nav()

    # Step 2: 复制文件
    docs_path = copy_files_to_docs()

    # Step 3: Git 推送
    git_commit_push(docs_path)

    print("\n" + "=" * 50)
    print("  部署完成!")
    print("=" * 50)


if __name__ == "__main__":
    main()

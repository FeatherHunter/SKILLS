#!/bin/bash
# scripts/install_hooks.sh
# SKILLS/ 仓库钩子安装器: 设 core.hooksPath 指向 SKILLS/.githooks
# (不是居家管家/.githooks, 因为 git 仓库根是 SKILLS/)

set -e

# 找 git 仓库根 (向上递归)
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$REPO_ROOT" ]; then
    echo "❌ 不在 git 仓库中"
    exit 1
fi

# 找 .githooks (可能在仓库根, 也可能在 skill 内, 优先仓库根)
HOOKS_DIR=""
if [ -d "$REPO_ROOT/.githooks" ]; then
    HOOKS_DIR="$REPO_ROOT/.githooks"
elif [ -d "../.githooks" ]; then
    HOOKS_DIR="$(cd ../ && pwd)/.githooks"
fi

if [ -z "$HOOKS_DIR" ] || [ ! -d "$HOOKS_DIR" ]; then
    echo "❌ 未找到 .githooks 目录"
    echo "   应位于: $REPO_ROOT/.githooks/"
    exit 1
fi

git config core.hooksPath "$HOOKS_DIR"
chmod +x "$HOOKS_DIR/"* 2>/dev/null || true

CURRENT=$(git config core.hooksPath)
echo ""
echo "✓ SKILLS 仓库 git hooks 已安装"
echo "  仓库根:    $REPO_ROOT"
echo "  hooks 目录: $CURRENT"
echo "  pre-commit: $HOOKS_DIR/pre-commit"
echo ""
echo "📋 后续行为"
echo "  - 每次 commit 前自动检测改动"
echo "  - 改居家管家/* → 跑居家管家 pytest"
echo "  - 改卡路里/*    → 跑卡路里 pytest"
echo "  - 其他 skill/ 文档改动 → 跳过测试"
echo "  - 失败 → commit 拒绝"
echo ""
echo "🔍 验证"
echo "  bash $HOOKS_DIR/pre-commit"

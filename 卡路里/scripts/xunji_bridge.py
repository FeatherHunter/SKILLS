#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xunji_bridge CLI shim 入口。

让 `python scripts/xunji_bridge.py <子命令>` 这种调用形式能跑通
(等价于 `python -m xunji_bridge`,但不需要 cwd 在 scripts/)。

实际逻辑在 xunji_bridge/__main__.py。
"""
from __future__ import annotations

import sys
from pathlib import Path

# 确保 scripts/ 在 sys.path(让 import xunji_bridge 能找到)
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from xunji_bridge.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())

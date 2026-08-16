# -*- coding: utf-8 -*-
"""iso_db · production DB isolation for SKILLS multi-skill repo (#400 / #386 C1.9)

⚠️ pytest plugin 形式在 pytest 9.x 不可靠(hook 注册问题),#400 实施采用
**内联到 conftest.py**方案(参见 卡路里/tests/conftest.py L17-145)。

保留 cwd_sentry 子模块供 #404 L3 复用(可被卡路里 scripts/db.py import)。

模块清单:
- cwd_sentry: cwd 哨兵 + CALORIE_FORCE_PROD opt-in(给 #404 L3 用)
- plugin: 已弃用,仅作参考实现
"""

__version__ = "1.0.0"

from iso_db import cwd_sentry  # 暴露给调用方

__all__ = ["cwd_sentry"]

"""
智剪工坊 · cover_compose 包入口
=================================

封面合成子模块(多图旋转叠加 + 文字水印 + 半透明黑防御)

5 层架构定位(5 层是逻辑职责,不是物理目录 — 物理按 5 大功能组织):
- ② 契约层(CLI):     cli.py / auto.py / diagnose.py / presets.py
- ③ 业务核心:        pipeline.py / layers.py / layout.py / text.py / validators.py
- ④ 基础设施:        canvas.py / diagnostics.py / presets_data.py

包内用相对导入(`.pipeline`/`.canvas`),包外用 `from cover_compose import compose`。
其他模块调用前需 sys.path.insert(0, <智剪工坊>/scripts/ai)。

详细:见 references/封面合成-多图拼版PIL.md
"""
from .pipeline import compose, parse_text_spec, ASPECT_RATIOS

__all__ = ["compose", "parse_text_spec", "ASPECT_RATIOS"]
__version__ = "1.0.0"

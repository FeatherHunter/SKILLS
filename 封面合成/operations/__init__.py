"""operations/ ② 契约层入口

子命令:
- cli.py:  统一 CLI 入口(argparse)
- auto_compose.py: 智能挡(分析图片 + 决策 + 调 compose)
- diagnose.py: 诊断子命令
- presets.py: 预设查询

按手册 ② 契约层职责,这里只做:
- 接收参数
- 调度 core/ 业务核心
- 格式化输出
"""

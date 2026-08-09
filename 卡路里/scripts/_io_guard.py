#!/usr/bin/env python3
"""_io_guard.py — 全技能统一 stdout/stderr 编码防护(跨机器兼容 · #242)

第一性原理:
  1. 输出通道永远不许杀死进程。GBK/cp1252/Latin-1 等非 UTF-8 控制台 print emoji
     (✅❌⚠️) 会抛 UnicodeEncodeError → 进程非零退出 → AI 误判"渲染失败"。
  2. 成败判据 = 退出码 + 产物文件,不是 stdout 里的 emoji。guard 保证输出永不崩,
     不可编码字符以替换符输出,不干扰判据。
  3. 幂等:重复调用无副作用(TextIOWrapper.reconfigure 天然幂等)。

用法(入口脚本 __main__ 块第一行):
    from _io_guard import guard_io; guard_io()

说明:
  - 仅改输出编码与 errors 策略,不改变写入内容本身;
  - reconfigure 不存在(非常规流/被关闭)时静默跳过,不抛异常;
  - 本模块被 scripts/ 同目录所有入口脚本共享,单点维护。
"""
import sys


def guard_io():
    """把 stdout/stderr 重配为 UTF-8 + errors='replace'(永不因编码崩溃)。"""
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError, OSError):
            # 非常规流(如已关闭/自定义对象)没有 reconfigure,静默跳过
            pass
    return 0

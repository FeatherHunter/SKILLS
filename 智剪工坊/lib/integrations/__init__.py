# -*- coding: utf-8 -*-
"""
智剪工坊 · 对外集成层（v1.21 新建）

集中管理 7+ 个外部集成点（原散落在 scripts/ 各处）：
  - matrix MCP（AI 生图 / TTS / 视频生成 / 翻译 / 数字人）
  - HuggingFace（Whisper / pyannote / demucs）
  - 模型下载（Whisper / face_landmarker / ffprobe）

规范依据：
  《SKILL五层架构规范》② 操作层（对外部分）"≥2 集成点必须抽 integrations/"

设计原则：
  1. 箭头向下：integrations/* 只 import lib/common.py，不 import scripts/*
  2. 失败降级：调外部失败 → 本地照常工作，stderr 记录（业务方继续）
  3. 幂等性：所有写操作支持 client_request_id（P1-4 Sprint 实现）
  4. 零依赖：只用 stdlib + 现有 lib/common

调用方式（业务脚本）：
    from integrations.matrix import MatrixClient
    from integrations.huggingface import HuggingFaceClient
    from integrations.model_download import ModelDownloader

当前状态：骨架阶段（Sprint P0-1 step 1/7）
  - 接口签名已定
  - 实现待 Sprint P0-1 step 2-4
  - 不引入新依赖
  - 现有 scripts/ 不动一行

Sprint 计划：
  P0-1 step 2  实现 MatrixClient.call / call_with_retry
  P0-1 step 3  实现 HuggingFaceClient.transcribe / diarize / separate
  P0-1 step 4  实现 ModelDownloader.download（SSL EOF + 镜像切换）
  P0-1 step 5  改 5 个 matrix 调用脚本 import 新模块
  P0-1 step 6  改 3 个 HF 调用脚本 import 新模块
  P0-1 step 7  跑 verify.py 验证全链路通
"""
# 显式 re-export 子模块（避免循环导入）
# 注：业务脚本用法 `from integrations.matrix import MatrixClient`

__all__ = ["matrix", "huggingface", "model_download"]
# -*- coding: utf-8 -*-
"""
智剪工坊 · LLM 客户端
统一封装 Mavis daemon 的 LLM 调用,所有需要 LLM 的子技能都 import 这个。

设计原则:
  - 零配置:从 mavis config.yaml 读 provider,直接用
  - 简单:一个 call() 函数,传 prompt 返回文本
  - 稳定:失败抛 LLMError,带可读错误信息
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# 找 mavis llm_call.py
def _find_llm_call_script() -> Optional[Path]:
    """找 mavis 内置的 llm-call skill 脚本"""
    candidates = [
        # Windows mavis 内置
        Path(os.environ.get("USERPROFILE", "")) / ".mavis" / ".builtin-skills" / "llm-call" / "scripts" / "llm_call.py",
        Path("C:/Users") / os.environ.get("USERNAME", "") / ".mavis" / ".builtin-skills" / "llm-call" / "scripts" / "llm_call.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


_LLM_CALL_SCRIPT = _find_llm_call_script()
DEFAULT_MODEL = "minimax/MiniMax-M3"


class LLMError(Exception):
    """LLM 调用失败"""
    pass


def call(prompt: str, system: str = None, model: str = DEFAULT_MODEL,
         max_tokens: int = 2000, temperature: float = 0.1,
         timeout: int = 120) -> str:
    """
    调 LLM 返回文本。

    Args:
        prompt: 用户 prompt
        system: system prompt(可选,用于角色设定)
        model: 模型名,默认 MiniMax-M3
        max_tokens: 最大输出 token
        temperature: 0-1,越低越确定
        timeout: 秒

    Returns:
        模型输出文本

    Raises:
        LLMError: 调失败
    """
    if _LLM_CALL_SCRIPT is None:
        raise LLMError(
            "找不到 mavis llm-call skill 脚本(llm_call.py)。\n"
            "  修复: 确认 Mavis 已正确安装,内置 skill 没被删"
        )

    cmd = [
        sys.executable,
        str(_LLM_CALL_SCRIPT),
        "--model", model,
        "--max-tokens", str(max_tokens),
        "--temperature", str(temperature),
        "--timeout", str(timeout),
        "--prompt", prompt,
    ]
    if system:
        cmd.extend(["--system", system])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout + 30,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            raise LLMError(f"LLM 调用失败 (exit {result.returncode}):\n{err[:500]}")
        return (result.stdout or "").strip()
    except subprocess.TimeoutExpired:
        raise LLMError(f"LLM 调用超时 ({timeout}s)")
    except FileNotFoundError as e:
        raise LLMError(f"找不到 Python 或 llm_call.py: {e}")


def is_filler(text: str, prev_text: str = "", next_text: str = "") -> bool:
    """
    用 LLM 判断一句话是不是"无意义水词"。

    Args:
        text: 当前句
        prev_text: 上一句(给 LLM 上下文)
        next_text: 下一句

    Returns:
        True = 无意义水词(该删),False = 有实际内容(该留)
    """
    system = (
        "你是中文口播剪辑助手。你的任务是判断一句话是不是'无意义水词'。"
        "水词定义:对话中无实际信息量的填充词、犹豫词、习惯性口头禅。"
        "比如'嗯''啊''呃''那个''然后''就是''其实'等单独出现或明显无意义时。"
        "但如果是表达肯定/确认/有实义(如'嗯,好的''对,没错''就是那个东西'),不是水词。"
        "请严格区分这两种情况。"
    )
    context_parts = []
    if prev_text:
        context_parts.append(f"上一句: {prev_text}")
    context_parts.append(f"当前句: {text}")
    if next_text:
        context_parts.append(f"下一句: {next_text}")
    prompt = "\n".join(context_parts) + "\n\n请只回答 'YES'(是水词,该删)或 'NO'(不是水词,该留),不要其他内容。"

    try:
        result = call(prompt, system=system, max_tokens=10, temperature=0.0)
        result = result.strip().upper()
        # 抽取 YES/NO
        if "YES" in result:
            return True
        if "NO" in result:
            return False
        # 模糊匹配
        if any(c in result for c in ["是", "该删", "水词"]):
            return True
        return False
    except LLMError:
        # 失败默认保留(保守策略:宁可漏删不错删)
        return False

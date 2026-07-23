# -*- coding: utf-8 -*-
"""
智剪工坊 · matrix MCP 集成层（v1.21 新建）

封装 5 个 matrix MCP 调用点（原散落在 5 个 scripts/ai/*.py）：

  | # | 工具名                       | 原调用脚本                          | 用途          |
  |---|------------------------------|-------------------------------------|---------------|
  | 1 | matrix_generate_image        | scripts/ai/cover.py                | AI 生图封面   |
  | 2 | matrix_gen_videos            | scripts/ai/text_to_video.py        | 文字成片      |
  | 3 | matrix_gen_videos (subject)  | scripts/ai/digital_human.py        | 数字人讲解    |
  | 4 | matrix_synthesize_speech     | scripts/ai/rewrite.py              | TTS 改词配音  |
  | 5 | matrix_translate             | scripts/ai/translate.py            | 视频翻译      |

现有调用模板（5 处高度一致）：
    mavis_bin = shutil.which("mavis") or r"C:/Users/辰辰洋洋/.mavis/bin/mavis.cmd"
    subprocess.run([mavis_bin, "mcp", "call", "matrix", TOOL_NAME, "--file", tmp_json],
                   capture_output=True, text=True, encoding="utf-8")

设计要点：
  - 统一 mavis 路径探测（shutil.which + Windows/macOS/Linux fallback）
  - 统一 payload JSON 临时文件处理（避免 shell 转义陷阱）
  - 统一 stdout/stderr 解析（matrix 返回 dict，部分有 output_url）
  - 统一失败降级（返回 None + log_warn，业务方继续）
  - 统一超时与重试（P1-4 加 client_request_id 幂等键）

对外接口：
    MatrixClient().call(tool_name, payload, timeout=...)
    MatrixClient().call_with_retry(tool_name, payload, max_retries=2)
    MatrixClient().call_with_idempotency(tool_name, payload, client_request_id, ttl=86400)

骨架状态（Sprint P0-1 step 1/7）：
  - 类与函数签名已定
  - 实现细节待 P0-1 step 2/7 填充
"""
from pathlib import Path
import sys
import json
import os
import re
import shutil
import subprocess
import tempfile
import time

# 引导：保证 lib/common.py 可被找到
_LIB_DIR = Path(__file__).parent.parent
if str(_LIB_DIR) not in sys.path:
    sys.path.append(str(_LIB_DIR))

from common import SkillError, log_info, log_warn, log_error, log_section  # noqa: E402


# ============================================================
# mavis CLI 路径探测（5 处现有脚本均硬编码此 fallback）
# ============================================================

# Windows 默认安装路径（5 个现有脚本的 hardcode）
MAVIS_BIN_FALLBACK_WIN = r"C:/Users/辰辰洋洋/.mavis/bin/mavis.cmd"


def _find_mavis_bin() -> str:
    """探测 mavis 可执行文件路径

    优先级：
      1. shutil.which("mavis") 优先（PATH 中的版本）
      2. Windows fallback 到 MAVIS_BIN_FALLBACK_WIN（用户特定路径）
      3. macOS/Linux fallback 到 ~/.local/bin/mavis

    Returns:
        mavis 可执行文件的完整路径

    Raises:
        FileNotFoundError: 找不到 mavis（带 hint）
    """
    # 1. PATH 中优先
    p = shutil.which("mavis")
    if p:
        return p

    # 2. Windows fallback（5 个现有脚本的硬编码路径）
    if sys.platform == "win32":
        if Path(MAVIS_BIN_FALLBACK_WIN).exists():
            return MAVIS_BIN_FALLBACK_WIN

    # 3. Unix fallback
    unix_default = os.path.expanduser("~/.local/bin/mavis")
    if Path(unix_default).exists():
        return unix_default

    # 4. 都找不到:抛 FileNotFoundError（含 hint 让上层包成 MatrixError）
    raise FileNotFoundError(
        f"找不到 mavis CLI:\n"
        f"  - PATH 中:shutil.which('mavis') = None\n"
        f"  - Windows fallback:{MAVIS_BIN_FALLBACK_WIN} (不存在)\n"
        f"  - Unix fallback:{unix_default} (不存在)\n"
        f"  修复:1) npm install -g @anthropic-ai/mavis (Windows 装 mavis.cmd)\n"
        f"        2) 或手动下载 mavis 放到 PATH\n"
        f"        3) 或显式传 MatrixClient(mavis_bin='/your/path')"
    )


# ============================================================
# 异常类型
# ============================================================

class MatrixError(SkillError):
    """matrix MCP 调用失败"""
    def __init__(self, cmd, stderr, stdout="", hint=None):
        self.cmd = cmd
        self.stderr = stderr
        self.stdout = stdout
        self.hint = hint
        msg = f"matrix 调用失败\n命令: {' '.join(str(x) for x in cmd[:6])}\nstderr: {(stderr or '无输出')[-300:]}"
        if hint:
            msg += f"\n提示: {hint}"
        super().__init__(msg)


# ============================================================
# 内部辅助函数（业务方法用）
# ============================================================

# 可重试错误模式（网络/临时性）
_RETRYABLE_PATTERNS = (
    "timeout", "timed out", "connection", "unreachable", "refused", "reset",
    "broken pipe", "temporarily", "try again", "internal server",
    "service unavailable", "502", "503", "504",
)

# 不可重试错误模式（业务错）
_NON_RETRYABLE_PATTERNS = (
    "invalid", "unauthorized", "forbidden", "401", "403",
    "rate limit", "quota", "argument", "parameter", "api key",
    "not allowed", "bad request",
)


def _is_retryable_error(error):
    """判断 MatrixError 是否可重试

    优先级：非重试模式 > 重试模式
    （先排除明确不该重试的，再判断是否属于临时性错误）
    """
    text = ((error.stderr or "") + " " + (getattr(error, "stdout", "") or "")).lower()
    for pattern in _NON_RETRYABLE_PATTERNS:
        if pattern in text:
            return False
    # 默认按可重试处理（重试不会让情况更糟，业务错会被模式拦住）
    return True


def _extract_matrix_error_hint(stderr):
    """从 stderr 推断修复建议（与 common._extract_hint 风格一致）"""
    s = (stderr or "").lower()
    if "no such file" in s or "not found" in s:
        return "检查 mavis 路径 / 文件路径"
    if "timeout" in s or "timed out" in s:
        return "加大 timeout 或拆小任务"
    if "connection" in s or "unreachable" in s or "refused" in s:
        return "检查网络/代理/防火墙"
    if "unauthorized" in s or "401" in s:
        return "检查 mavis 登录状态（mavis auth login）"
    if "rate" in s or "quota" in s:
        return "调用频率过高,稍后重试或换 API"
    if "invalid" in s or "argument" in s:
        return "检查参数（payload 字段名/类型与 matrix 工具要求是否一致）"
    return None


def _parse_matrix_output(stdout, tool_name):
    """解析 matrix MCP stdout

    3 段 fallback（按现有 5 个脚本实测情况）:
      1. 整段 JSON（rewrite.py L111 模式:json.loads(stdout.strip())）
      2. regex 提取第一个 JSON object（text 包裹 JSON 模式）
      3. 提取 output_url（cover.py L58 模式:"output_url":"..."）

    Returns:
        dict: 解析结果

    Raises:
        MatrixError: 3 段都失败
    """
    if not stdout or not stdout.strip():
        raise MatrixError(
            cmd=[],
            stderr=f"matrix {tool_name} 返回空 stdout",
            hint="可能 matrix 服务异常或 CLI 输出被截断"
        )

    text = stdout.strip()

    # 尝试 1: 整段 JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试 2: regex 提取首个 JSON object
    match = re.search(r'(\{[\s\S]*?\})', text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试 3: 提取 output_url
    match = re.search(r'"output_url"\s*:\s*"([^"]+)"', text)
    if match:
        return {
            "output_url": match.group(1),
            "status": "ok",
            "tool": tool_name,
        }

    # 全部失败
    raise MatrixError(
        cmd=[],
        stderr=f"无法解析 matrix {tool_name} 输出（不是 JSON）",
        stdout=text[:500],
        hint="matrix 返回格式异常,可能是新工具返回非标准格式"
    )


# ============================================================
# 客户端类
# ============================================================

class MatrixClient:
    """matrix MCP 统一客户端

    用法：
        client = MatrixClient()
        result = client.call("matrix_generate_image",
                             {"prompt": "sunset", "aspect_ratio": "16:9"})
        # result = {"status": "ok", "output_url": "C:\\..."}

        result = client.call_with_retry("matrix_synthesize_speech",
                                        {"text": "你好", "voice_id": "male-qn-jingying"},
                                        max_retries=2)
    """

    def __init__(self, mavis_bin=None, default_timeout=1500):
        """初始化 MatrixClient

        Args:
            mavis_bin: mavis 可执行文件路径（None=自动探测 _find_mavis_bin）
            default_timeout: 默认超时秒数
                - matrix_generate_image: ~30s
                - matrix_synthesize_speech: ~10s
                - matrix_gen_videos: 可达 1500s（25 分钟）
                默认 1500 取最大安全值
        """
        self.mavis_bin = mavis_bin or _find_mavis_bin()
        self.default_timeout = default_timeout

    # -------- 基础调用 --------

    def call(self, tool_name, payload, timeout=None):
        """基础调用 matrix MCP

        Args:
            tool_name: 工具名（如 "matrix_generate_image"）
            payload: 参数 dict（会被序列化为 JSON 临时文件传给 --file）
            timeout: 超时秒数（None=用 default_timeout）

        Returns:
            dict: 解析后的返回值（如 {"status": "ok", "output_url": "..."}）

        Raises:
            MatrixError: 调用失败 / 返回非 JSON / 超时
        """
        if timeout is None:
            timeout = self.default_timeout

        tmp_path = None
        try:
            # 1. 写 payload 到 tempfile JSON
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False,
                prefix=f"matrix_{tool_name}_",
                encoding="utf-8",
            ) as f:
                json.dump(payload, f, ensure_ascii=False)
                tmp_path = f.name

            # 2. 构造命令
            cmd = [self.mavis_bin, "mcp", "call", "matrix", tool_name, "--file", tmp_path]
            log_info(f"matrix call: {tool_name} timeout={timeout}s payload_keys={list(payload.keys())[:5]}...")

            # 3. subprocess 调用
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                raise MatrixError(
                    cmd=cmd,
                    stderr=f"matrix {tool_name} timeout ({timeout}s)",
                    hint="加大 timeout 或拆小任务（matrix 视频生成耗时长）",
                )
            except FileNotFoundError:
                raise MatrixError(
                    cmd=cmd,
                    stderr=f"mavis CLI not found: {self.mavis_bin}",
                    hint="检查 mavis 路径或重装 mavis",
                )

            # 4. returncode 检查
            if result.returncode != 0:
                hint = _extract_matrix_error_hint(result.stderr or "")
                raise MatrixError(
                    cmd=cmd,
                    stderr=result.stderr or "",
                    stdout=result.stdout or "",
                    hint=hint,
                )

            # 5. 解析 stdout
            return _parse_matrix_output(result.stdout or "", tool_name)

        finally:
            # 6. 清理临时文件（即使中途出错也清理）
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)

    # -------- 重试 --------

    def call_with_retry(self, tool_name, payload, max_retries=2, timeout=None):
        """带指数退避的重试调用

        适用：网络抖动 / 临时性 5xx 错误
        不适用：参数错误 / 鉴权失败 / 配额耗尽（这些应该立刻报错）

        Args:
            tool_name: 工具名
            payload: 参数 dict
            max_retries: 最大重试次数（默认 2，加上首次共 3 次）
            timeout: 单次超时秒数

        Returns:
            dict: 同 call()

        Raises:
            MatrixError: 重试耗尽仍失败
        """
        retry_delays = [1, 2, 4]  # 第 1/2/3 次失败后的等待（秒）
        last_error = None

        for attempt in range(max_retries + 1):  # 0=首次,1/2=重试
            try:
                return self.call(tool_name, payload, timeout)
            except MatrixError as e:
                last_error = e

                # 业务错误(参数/鉴权/配额):立即报错,不浪费 3 次重试
                if not _is_retryable_error(e):
                    log_warn(f"matrix {tool_name} 不可重试,立即报错")
                    raise

                # 已达最大次数
                if attempt >= max_retries:
                    log_error(
                        f"matrix {tool_name} 重试 {max_retries} 次仍失败"
                        f"（最后错误:{e}）"
                    )
                    raise

                # 等待后重试
                delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                log_warn(
                    f"matrix {tool_name} 第 {attempt + 1} 次失败({type(e).__name__}),"
                    f"{delay}s 后重试 ({attempt + 1}/{max_retries})"
                )
                time.sleep(delay)

        # 实际不可达(循环总会 raise 或 return)
        if last_error:
            raise last_error

    # -------- 幂等 --------

    def call_with_idempotency(self, tool_name, payload,
                              client_request_id, ttl=86400, timeout=None):
        """带幂等键的调用（避免重试产生重复数据）

        幂等键格式（与 SKILL.md §5.2 备份命名规则一致）：
            {date}_{task_slug}_{step}_{uuid8}
        示例: "2026-07-23_fitness-vlog_step9_cover_a1b2c3d4"

        Args:
            tool_name: 工具名
            payload: 参数 dict
            client_request_id: 幂等键（同 key 在 ttl 内复用上次结果）
            ttl: 缓存秒数（默认 86400=24h）

        Returns:
            dict: 同 call()

        Sprint P1-4 待实现：
          - 内存 cache + 文件 cache（防止进程重启丢）
          - cache key = f"{client_request_id}:{tool_name}"
          - cache 路径: <skill_root>/.cache/matrix_idempotency/<hash>.json
        """
        raise NotImplementedError("Sprint P1-4 实现 MatrixClient.call_with_idempotency")


__all__ = [
    "MatrixClient",
    "MatrixError",
    "MAVIS_BIN_FALLBACK_WIN",
    "_find_mavis_bin",
]
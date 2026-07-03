# scripts/

这里放**可执行的 Python 脚本**,封装 ffmpeg 命令,提供 CLI 接口。

## 命名规范

`{子技能名}.py`,例如:
- `cut.py` —— 剪切 + 拼接
- `xfade.py` —— 转场
- `effect_slowmo.py` —— 慢动作
- `effect_zoom.py` —— 推镜头
- `color_lut.py` —— 调色
- `text_anim.py` —— 文字动画
- `cover_ai.py` —— AI 封面
- `bgm_loop.py` —— BGM 循环
- `pipeline_vlog.py` —— 大流程

## 标准接口

每个脚本应支持:

```bash
python {script}.py --input in.mp4 --output out.mp4 --param1 value1
```

## 调用 ffmpeg

统一通过 Python `subprocess` 调用:

```python
import subprocess

def run_ffmpeg(cmd_args):
    cmd = ["ffmpeg", "-y"] + cmd_args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")
    return result
```

## 公共工具

可以创建 `_common.py`,放共享函数:
- `run_ffmpeg()`
- `get_duration()`
- `validate_output()`

## 当前状态

🚧 **空目录,待填充**

阶段 2 计划填入:
- `cut.py`(剪切 + 拼接)
- `xfade.py`(转场)
- `bgm_loop.py`(BGM 循环混音)
- `cover_ai.py`(AI 封面)

后续阶段填入其余子技能的脚本。
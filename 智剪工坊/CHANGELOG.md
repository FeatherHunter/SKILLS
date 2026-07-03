# 智剪工坊 · 变更日志

## v0.3 (2026-07-03) - 美颜 L2 + 重大 bug 修复

### ✨ 新增
- **`scripts/beauty.py`** —— 美颜 L2 标准版
  - 4 个独立子能力:磨皮 + 美白 + 瘦脸 + 大眼
  - 5 个 preset:`off` / `slight` / `natural` / `strong` / `max`
  - 底层:mediapipe 0.10 tasks.FaceLandmarker(478 关键点)
  - 算法:脸部 oval mask + 三角剖分 + 仿射变形
  - 自动下载模型(3.7MB 一次性)
  - 视频逐帧处理 + 音频自动 mux
  - 图片 + 视频双模式

### 🐛 修过的关键 Bug
1. **全局 27 脚本 `safe_run(main)` 缺 `()`** —— 最严重!
   - 现象:全部 27 个脚本入口实际不调 main(),Python 加载完模块后正常退出(返回 0)
   - 影响:之前 verify.py 报告的 "6/6 冒烟测试通过" 实际啥也没跑,只是退出了
   - 修法:批量 `safe_run(main)` → `safe_run(main)()`(全 27 个脚本)
2. **mediapipe 0.10.35 移除 `solutions` API**
   - 现象:`mp.solutions.face_mesh` 不存在了
   - 修法:改用 `mp.tasks.vision.FaceLandmarker` task-based API
3. **mediapipe 0.10.35 Windows 中文路径 bug**
   - 现象:模型路径含非 ASCII 字符(如 `智剪工坊`)→ `FileNotFoundError`
   - 修法:自动 fallback 复制到 `C:\zhijian_models\`(纯 ASCII 路径)
4. **color_style.py 用 `curves=preset=X`**
   - 现象:ffmpeg 7.1 不支持 `curves` 的 `preset` 选项
   - 修法:批量移除 `curves=preset=X` 段
5. **fx.py intensity blend 语法错**
   - 现象:`split[orig];[orig][orig]blend=...` 写法错,ffmpeg 报"input/output 数量不对"
   - 修法:简化为静态效果,intensity 改成"提示"信息

### 📦 验证状态(2026-07-03 实测)
- ✅ 27/27 脚本 import 通过(新增 beauty.py)
- ✅ 6/6 核心脚本冒烟测试真正通过(修了 safe_run bug 后)
- ✅ 10/10 Python 依赖就位
- ✅ beauty 4 个 preset 真实人脸图测试通过(biden + two_people)
- ✅ 解决 mediapipe Windows 中文路径 bug

### ⚠️ 已知小问题
- mediapipe 0.10.35 在 Windows 上对非 ASCII 路径有 bug,本系统通过自动 fallback 解决
- beauty 视频处理 ~5-10x 实时(1080p CPU),生产用可考虑 GPU 版

---

## v0.2 (2026-07-03) - 可发布版本

### ✨ 新增
- `setup.bat`(Windows)+ `setup.sh`(Mac/Linux)—— 一键安装脚本
- `verify.py`—— 环境验证脚本
- 产品级 `README.md`

### 🔧 升级
- `lib/common.py`:读 config.json + 跨平台 ffmpeg + 友好错误
- `requirements.txt`:9 个实依赖全开

---

## v0.1 (2026-07-03) - 骨架完成

- 11 个子技能文档 + 5 个核心脚本

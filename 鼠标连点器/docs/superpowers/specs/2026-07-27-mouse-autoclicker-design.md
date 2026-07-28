# 鼠标连点器 — 设计文档

| 项目 | 值 |
|------|-----|
| 文档日期 | 2026-07-27 |
| 平台 | Windows 10 / 11 |
| 技术栈 | Python 3.11 + PySide6 (Qt6) + ctypes |
| 打包 | PyInstaller `--onefile --windowed` |
| 目标产物 | `dist/鼠标连点器.exe`（~30 MB，单文件，免安装） |

---

## 1. 用户目标（first principles）

1. 启动软件 → 在鼠标当前位置持续点击，无需多看一眼。
2. 可调节间隔、按键、位置策略。
3. 软件本身不抢焦点、不弹窗、不抢键盘——其他工作流不被它打断。
4. UI 看上去"高级、大气"（已选定 Fluent 亚克力风格）。

**非目标（YAGNI）**：随机间隔、点击次数上限、延时启动、定时停止、悬浮指示圈、点击录制、多点序列、统计图表、皮肤切换、联网、i18n。

---

## 2. 行为规约

### 2.1 启停
- **启动**：用户按主界面"启动"按钮 / 全局热键 F6。
- **停止**：用户按"停止"按钮 / F6（toggle）/ 全局热键 Esc / 关闭主窗（仅最小化到托盘，不停止当前运行）。

> Esc 永远能停，无论 UI 在哪。这是保护性硬性需求。

### 2.2 参数默认值与范围
| 参数 | 默认 | 范围 | 控件 |
|------|------|------|------|
| 间隔 | 100 ms | 10 ~ 10000 ms | 滑杆 + QSpinBox 双向绑定 |
| 鼠标按键 | 左键 | 左/右/中 | Segmented control |
| 点击类型 | 单击 | 单击 / 双击 | Segmented control |
| 位置策略 | 当前位置 | 当前位置 / 锁定坐标 / 跟随鼠标 | Segmented control |
| 锁定坐标 | — | 全屏像素 | "取点"按钮，按下后 3 秒内按 F6 取当前鼠标位置 |

### 2.3 全局热键
| 热键 | 功能 | 默认 | 可改？ |
|------|------|------|--------|
| F6 | 启停 toggle | ✓ | ✓ |
| Esc | 强制急停 | ✓ | ✗（永远是 Esc） |
| Ctrl+Shift+A | 显示/隐藏主窗 | ✓ | ✓ |

热键冲突（例如 F6 被占用）：弹 toast "F6 已被占用，已自动改为 Ctrl+Alt+Q"，写入日志，不报错退出。

### 2.4 位置策略细节
- **当前位置**：按"启动"瞬间记录 `(x, y)`，循环里固定点这个坐标直到停止。
- **锁定坐标**：进入"取点"模式 → 用户移动鼠标到目标位置 → 在 3 秒内按下 F6 → 记录坐标。
- **跟随鼠标**：每次循环重新读取当前鼠标位置点。

### 2.5 托盘行为
- 主窗关闭（×）→ 隐藏窗口至托盘，**不退出进程，连点继续**。
- 托盘图标左键单击 → 显示主窗。
- 托盘右键菜单：显示主窗 / 启停 / 退出。
- "退出"才真正杀进程，保存配置。

### 2.6 配置持久化
- 路径：`%USERPROFILE%/.autoclicker/config.json`
- 保存时机：每次参数变更（debounce 500ms）、退出前、托盘"退出"前。
- 内容：`interval_ms`, `button`, `click_type`, `position_mode`, `locked_x`, `locked_y`, `hotkey_toggle`, `hotkey_show_window`
- 不保存的：密码、统计、状态。

### 2.7 单实例
- 启动时尝试创建命名互斥体 `Local\AutoClickerSingleInstance`。
- 已存在 → 通过 Win32 `FindWindowW` + `SetForegroundWindow` 唤起既有窗口，不报错。

### 2.8 自启动时机
- 程序启动后延迟 200ms 才显示窗口（避免抢启动瞬间焦点）。
- 启动时自动从 config.json 恢复最后参数。

---

## 3. 架构

### 3.1 进程 / 线程模型

```
主进程 (Qt 主线程 / GUI 线程)
  ├─ QApplication event loop
  ├─ MainWindow (UI)
  ├─ QSystemTrayIcon
  ├─ GlobalHotkeyManager (在主线程的 Qt event loop 里处理 OS 热键消息)
  └─ ClickerEngine (派生 QObject，使用 moveToThread + QThread)
        └─ 内部一个 while self._running: click + sleep 循环
```

线程通信：ClickerEngine 通过 `Signal(tuple)` 回传 `(count, elapsed_ms, last_pos)` 给 UI；UI 通过 `Signal(bool)` 通知 engine 启动/停止。不允许直接跨线程操作 QWidget。

### 3.2 文件布局

```
鼠标连点器/
├─ src/
│  ├─ app.py              入口 (QApplication、单实例锁、组件组合)
│  ├─ main_window.py      UI（PySide6 widget tree）
│  ├─ clicker.py          ClickerEngine + SendInput ctypes 包装
│  ├─ hotkeys.py          GlobalHotkeyManager (Win32 RegisterHotKey)
│  ├─ config.py           JSON 持久化
│  ├─ styles.py           QSS 字符串 + Windows 11 亚克力启用代码
│  └─ tray.py             QSystemTrayIcon 封装
├─ assets/
│  ├─ icon.ico            托盘图标 (256×256，含 multi-resolution)
│  └─ icon-running.ico    运行中状态
├─ tests/
│  └─ test_config.py      配置读写
│  └─ test_clicker.py     SendInput 结构布局校验（不实际点击）
├─ build.spec             PyInstaller 配置
├─ requirements.txt       PySide6, pyinstaller
└─ docs/superpowers/specs/2026-07-27-mouse-autoclicker-design.md
```

**YAGNI 检查**：7 个 .py 文件不算多，但都是单一职责，无 god class 无 god module。

### 3.3 关键代码骨架（不写实现，先定接口）

```python
# clicker.py
class ClickerEngine(QObject):
    state_changed = Signal(bool)          # running / stopped
    stats_updated = Signal(int, int)      # total_clicks, elapsed_ms
    error = Signal(str)

    def configure(self, interval_ms, button, click_type, pos_mode, locked_xy):
        ...

    def start(self) -> bool: ...
    def stop(self) -> None: ...

# hotkeys.py
class GlobalHotkeyManager(QObject):
    activated = Signal(str)  # 'toggle' | 'panic' | 'show'

    def __init__(self, on_activate: Callable[[str], None]): ...
    def register(self) -> bool: ...
    def unregister(self): ...

# config.py
@dataclass
class AppConfig:
    interval_ms: int = 100
    button: str = 'left'        # 'left' | 'right' | 'middle'
    click_type: str = 'single'  # 'single' | 'double'
    position_mode: str = 'current'  # 'current' | 'locked' | 'follow'
    locked_x: int = 0
    locked_y: int = 0
    hotkey_toggle: str = 'F6'
    hotkey_show: str = 'Ctrl+Shift+A'

    @classmethod
    def load(cls) -> 'AppConfig': ...
    def save(self): ...
```

---

## 4. UI（已定：Fluent 亚克力）

主窗 380 × 480，无标题栏（自定义拖拽区），固定不放大。

```
┌──────────────────────────────┐
│ ⚙  AutoClicker       ─ □ ✕ │  ← 18px 高的自定义标题栏（拖拽区）
├──────────────────────────────┤
│                              │
│  ⬤ 运行中  100ms · 当前位置 │  ← 状态徽章 + 当前参数
│                              │
│   ┌────────────────────┐    │
│   │      ▶ 启 动        │    │  ← 大 CTA 按钮，蓝色渐变
│   └────────────────────┘    │
│                              │
│   间隔  100 ms               │
│   ●━━━━━━━━━━○━━━━━━━━━━     │  ← 滑杆 (10-10000)
│                              │
│   按键  ◉左  ○右  ○中       │  ← Segmented
│   类型  ◉单  ○双            │
│   位置  ◉当前 ○锁定 ○跟随   │
│                              │
│   已点击 1,284   02:14       │
│                              │
│   F6 启停 · Esc 急停 · ...  │  ← 底部 footer（热键提示）
└──────────────────────────────┘
```

**亚克力实现**：
- Windows 11：调用 DWM API 设 `DWMWA_SYSTEMBACKDROP_TYPE` = `DWMSBT_MAINWINDOW` (transient) → 真亚克力。
- Windows 10 fallback：用 `Qt.WA_TranslucentBackground` + 自定义 QSS 渐变 + 30px 圆角，自制"伪亚克力"。

**启动/停止颜色切换**：停止时 CTA 是蓝紫渐变（`linear-gradient(135deg, #0067c0, #4a6ee0)`）+ 显示"▶ 启 动"；运行时 CTA 变红橙（`linear-gradient(135deg, #e81123, #c00)`）+ 显示"■ 停 止"，加柔和阴影发光。

---

## 5. 容错

| 场景 | 处理 |
|------|------|
| `SendInput` 调用失败 | 日志 + 重试 1 次；连续 3 次失败 → 弹 toast + 自动停 |
| 坐标越界（> 屏幕宽高 / < 0） | 强制 clamp 到屏幕范围 |
| 热键被占用 | toast 提示，自动改备用（toggle 改 `Ctrl+Alt+Q`），允许用户在设置里手动改 |
| 单实例冲突 | 唤起既有窗口，不报错 |
| config.json 损坏 | 备份 .bak + 用默认值启动 |
| 配置文件权限不足 | 用 `%LOCALAPPDATA%/AutoClicker/` 兜底 |
| 关闭主窗→托盘后用户不点击托盘而注销 | OK，下次开机重新启动即可（无系统服务） |

---

## 6. 测试

| 类型 | 内容 |
|------|------|
| 单元 | `config` round-trip；`SendInput` 结构体 `sizeof` == Windows 期望值；坐标 clamp 边界 |
| 集成 | 在本地打开记事本，设 200ms 左键当前位置，跑 3 秒，统计点击数和记事本进程是否收到点击 |
| 手动 | 启动 → F6 → 看另一窗口被点击 → Esc → 停止；关闭主窗 → 托盘图标还在；双击 exe 唤起既有窗 |
| 验收 (面对用户的需求映射) | 见 §7 |

**不测**：跨 Win10/11 的 100% 像素级 UI 一致性（退化为"在两平台上都能识别为亚克力风"）。

---

## 7. 验收映射（用户原话 → 可验证行为）

| 用户原话 | 验收测试 |
|----------|----------|
| "启动后在鼠标的位置 一直模拟点击" | 按 F6；鼠标放在另一窗口的某个按钮上；3 秒后该按钮被点 ~30 次（间隔 100ms） |
| "可以设置参数" | 调间隔滑杆到 500ms → F6 → 另窗口按钮被点 ~6 次/3 秒 |
| "UI 要好看，设计要大气" | 主窗在 Windows 11 上呈现真亚克力；在 Win10 上呈现类亚克力 fallback；视觉通过用户目检 |
| "不能妨碍用户的正常其他软件使用" | 启动后无焦点抢占；运行中可正常切换/操作其他软件；热键 Esc 任何时候能停 |

---

## 8. 打包 & 分发

- `pyinstaller --onefile --windowed --icon assets/icon.ico --name 鼠标连点器 src/app.py`
- 产物 `dist/鼠标连点器.exe`，~30 MB，免安装双击即跑。
- 文档：附一个 5 行 README.md 说明用法：F6 启停 / Esc 急停 / 参数持久化。

---

## 9. 风险 & 待确认

- **Win10 真亚克力**：API 不存在，已设计 fallback（伪亚克力 QSS）。可接受。
- **PyInstaller 误报**：少数杀毒软件对打包的 PyInstaller exe 误报。可接受（README 里备注）。
- **3 秒倒计时取点**：本机调试 3 秒够用，未来可配置。先不变。

# stdout/stderr 编码防护(_io_guard · 跨机器兼容)

Status: accepted

Issue #242 表面症状:GBK 控制台(cp936)下 `render_help_center.py` L335 `print(f'✅ {out_path}')` 抛 `UnicodeEncodeError`,进程崩溃。根因:全技能 65/66 render 脚本、207 处 emoji print,stdout 编码继承环境(GBK/cp1252/UTF-8 因机器而异),任何非 UTF-8 环境 print emoji 即崩。**且崩溃发生在 HTML 文件写盘之后** → 非零退出 + traceback → AI 误判渲染失败 → 手写 HTML 兜底(正是 #235 的触发链)。

我们决定:**所有入口脚本启动时把 stdout/stderr 重配为 UTF-8 + errors='replace'**(共享模块 `scripts/_io_guard.py`,99 个入口脚本 main 块首行注入)。第一性原理:
1. **输出通道永远不许杀死进程**——成败判据 = 退出码 + 产物文件存在,不是 stdout 里的 emoji。
2. **消费端编码对齐**——opencode 子进程输出按 UTF-8 解码(源码实证),guard 强制 UTF-8 字节恰好对齐;改动前 GBK 字节经 PowerShell 转发后中文路径乱码,guard 顺带修复。
3. **幂等容错**——reconfigure 天然幂等;非常规流(已关闭/自定义对象)静默跳过,不抛异常。

考虑过的选项:
- **只改 errors 不改 encoding**(保留 GBK 输出)——在 opencode 消费端(UTF-8 解码)下中文乱码,否决。
- **全量去 emoji 改 ASCII 标记**——改动面过大(207 处),且 emoji 有语义提示价值,否决。
- **当前方案**——单点维护(_io_guard.py)+ 机械注入 + check 防回归(对照 4),改动小、可回滚。

后果:
- 输出恒为 UTF-8:UTF-8 消费端(opencode)完整正确;GBK 终端人类直接看会乱码但文件已生成,AI 链路不受影响。
- Mavis(MiniMaxCode)消费端编码闭源未验证——若其按 GBK 解码需再适配(遗留项)。
- Python 版本声明同步 >=3.7 → >=3.10(实际代码已用 PEP 604/generic 语法)。
- db.py:Windows 保持 D:/.db(用户规定),macOS/Linux fallback ~/.db。

详见:`scripts/_io_guard.py` + `scripts/check_trigger_consistency.py`(对照 4)+ GitHub #242。

# 05 — 伪代码与实现对齐:§04 原则 5 补 timeout/5MB/二次校验 + CSS 路径说明

**What to build:** §04 原则 5 伪代码(line 91-115)与 _assets/injector.py 字字对应,消除"文档与实现不同步":(1) 伪代码补 timeout=30(injector.py:87 有)(2) 补 5MB 数据大小警告(injector.py:42-50 有)(3) 补占位符二次校验(injector.py:98-102 有 count != 1 抛 ValueError)。形式:4 步主体保持 + 每步下方加 `# 生产防护:` 注释行,既字字对应实现又保留主次。同时在 §04 原则 5 SOP 步骤 5(引用 style.css 处)补 CSS 路径处理说明:三选一(拷贝 _assets/style.css 到 Skill 的 templates/ / 软链 / 内联到 <style> 标签)。这一步落实 A 坐标"伪代码与实现零缝隙"。

**Blocked by:** None — 可立即开始

**Status:** ready-for-agent

- [ ] §04 原则 5 伪代码含 "timeout=30"
- [ ] §04 原则 5 伪代码含 "5MB" 或 "5 MB"(数据大小警告)
- [ ] §04 原则 5 伪代码含二次校验(count != 1 抛 ValueError)
- [ ] §04 原则 5 SOP 步骤 5 含 CSS 路径三选一说明(拷贝 / 软链 / 内联)
- [ ] 伪代码与 injector.py 的关键参数字字对应(grep 比对 timeout / 5MB / count)

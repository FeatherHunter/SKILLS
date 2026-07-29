Status: ready-for-agent

# 09 — 主页 dashboard quick commands = prompts

**What to build:** 主页 dashboard 底部 "快捷命令" 区域复制的不是 shell script,而是自然语言 prompt(从 `_triggers.py` 来),用户可直接粘到 AI 聊天框。

依据:D3 + D7(spec 实现细节)。

**Blocked by:** None — can start immediately

- [ ] `render_home.py` 增加 `quick_actions` 组装:从 `_triggers.py` 按 `wake_word` 查 `main_prompt.text`,作为 `quick_actions[i].prompt`(原 `a.command` 仍保留 fallback 字段供调试)
- [ ] `home_dashboard.html` `.cmd-row .cmd` 文本渲染 `a.prompt`(优先)或 `a.command`(fallback)
- [ ] `.copy-mini` 复制 `a.prompt`;若空,降级复制 `a.command`(避免破坏旧用户习惯)
- [ ] 测试:每个 quick_action 在 mock 下产生的 prompt 与 `_triggers.py` 中对应 main_prompt.text 字节相同
- [ ] 桌面 + 手机都验:copy 按钮可见 + 复制内容是自然语言
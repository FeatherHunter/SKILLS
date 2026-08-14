# dsh-opencode-tui-theme

DSH（DeepSeek Harness）Web 界面的 **opencode TUI 风格主题**（Client 插件）。

让整个对话界面复刻 opencode TUI 的观感：

- 统一深黑背景 `#0a0a0a`（像素采样自 opencode TUI 截图）
- 正文浅灰 `#d4d4d4`、全等宽终端字体、13px 紧凑字号
- 标题淡紫 `#c084fc`、内联代码翠绿 `#4ade80`（无背景芯片）
- 代码块柔和亮度分层（`#131316` / 横幅 `#19191d`）+ One Dark 语法高亮
- 输入框深灰卡片 `#1c1c1e`，与聊天内容明显分层

## 安装（正式 · 开机自启）

```bash
npm install dsh-opencode-tui-theme
```

然后在本机 DSH profile 的 `cordis.patch.yml` 追加：

```yaml
- insert:
    - id: opencode-tui-theme
      name: 'dsh-opencode-tui-theme'
```

刷新浏览器页面即可生效（配置热加载，无需重启 DSH）。之后每次启动自动生效，无需审批。

> 注意：npm 安装的包要能被 DSH 找到，需装在 DSH profile 的依赖树里
> （`~/.dsh/profiles` 下执行 `npm install`，或在 profile 的 package.json 中声明）。

## 卸载

删除 `cordis.patch.yml` 中的 insert 行，然后 `npm uninstall dsh-opencode-tui-theme`。

## 工作原理

- `dsh.client: { platform: 'web' }` 声明自己是浏览器端插件；
- DSH 的 `dsh-client-modules` 扫描组合条目，把 `exports["./client"]` 指向的
  bundle 伺服为 `/plugins/<id>/client.js` 并注入 `window.__DSH_BOOT__`；
- 浏览器内核启动时自动挂载，`theme.overrideTokens` 覆盖 13 个注册主题 token，
  并注入 `<style>` 覆盖 CSS 层变量（输入框/按钮/代码块/shiki 高亮/字体/字号）。

## License

MIT

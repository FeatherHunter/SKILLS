/**
 * dsh-Opencode TUI 主题（pluginId: ocode-2）
 *
 * 将 DSH 对话界面复刻为 opencode TUI 风格：
 *   - 整个界面背景统一为截图背景色 #0a0a0a（不追随系统外观）
 *   - 标题淡紫 #c084fc、内联代码翠绿 #4ade80
 *   - 默认正文为全等宽终端样式，13px 紧凑字号
 *   - 代码块深底 + One Dark 语法高亮（--shiki-token-*）
 *   - 输入框 / 按钮 / 菜单等全部组件强制深色体系
 *
 * 本文件内容 = cordis_define 的 code.client（纯 JS 函数体，返回 Cordis Plugin）。
 * 加载方式：在 DSH 会话中 cordis_define -> cordis_run（首次需批准）。
 */
return {
  apply(ctx) {
    const theme = ctx.get('theme')
    const slots = ctx.get('slots')
    if (theme === undefined) return

    let disposers = []
    let enabled = false
    let mode = 'mono' // mono=全等宽终端(默认) tui=无衬线忠实
    let size = 13     // 正文基础字号 12/13/14
    let fontKey = 'JetBrains Mono'

    const SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif"

    // 截图背景色（像素采样 #0A0A0A）：整个界面背景统一
    const BG = '#0a0a0a'
    const BG_RAISE = '#101014' // 悬停/浮起略亮
    const BG_OVER = '#16161a'  // 浮层/选中
    const INPUT_BG = '#1c1c1e' // 截图底部输入框背景（macOS 深灰卡片，与内容区明显分层）
    // 代码块柔和亮度阶梯（opencode TUI 风格：无硬边框、无芯片，靠柔和表面差 + 圆角）：
    //   L0 聊天画布 #0a0a0a < L1 代码块 #131316 < L2 横幅(复制按钮) #19191d
    const CODE_BG = '#131316'   // 代码块浮起面：柔和亮一级，不刺眼
    const BANNER_BG = '#19191d' // 代码块横幅（文件名+复制按钮）：再柔和亮一级

    // 等宽代码字体预设（尾部保留 CJK 字体，避免 Windows 中文回退 SimSun）
    const FONTS = {
      'JetBrains Mono': "'JetBrains Mono', 'SF Mono', 'Cascadia Code', 'Fira Code', 'Menlo', Consolas, 'Liberation Mono', 'Courier New', 'PingFang SC', 'Microsoft YaHei'",
      'Cascadia Code': "'Cascadia Code', 'JetBrains Mono', 'SF Mono', 'Fira Code', Consolas, 'Courier New', 'PingFang SC', 'Microsoft YaHei'",
      'Fira Code': "'Fira Code', 'JetBrains Mono', 'Cascadia Code', Consolas, 'Courier New', 'PingFang SC', 'Microsoft YaHei'",
      'SF Mono': "'SF Mono', 'JetBrains Mono', 'Fira Code', Consolas, 'Courier New', 'PingFang SC', 'Microsoft YaHei'",
      'Consolas': "Consolas, 'JetBrains Mono', 'Cascadia Code', 'Courier New', 'PingFang SC', 'Microsoft YaHei'",
    }

    // 注册主题 token：全部背景层统一为截图背景色 #0a0a0a
    const TOKENS = {
      '--dsw-alias-bg-base': { light: BG, dark: BG },
      '--dsw-alias-bg-layer-1': { light: BG, dark: BG },
      '--dsw-alias-bg-layer-2': { light: BG, dark: BG },
      '--dsw-alias-bg-overlay': { light: BG, dark: BG },
      '--dsw-alias-border-l1': { light: '#27272a', dark: '#27272a' },
      '--dsw-alias-border-l2': { light: '#333338', dark: '#333338' },
      '--dsw-alias-brand-primary': { light: '#c084fc', dark: '#c084fc' },
      '--dsw-alias-label-primary': { light: '#d4d4d4', dark: '#d4d4d4' },
      '--dsw-alias-label-secondary': { light: '#a1a1aa', dark: '#a1a1aa' },
      '--dsw-alias-state-error-primary': { light: '#f87171', dark: '#f87171' },
      '--dsw-alias-state-success-primary': { light: '#4ade80', dark: '#4ade80' },
      '--dsw-alias-state-warn-primary': { light: '#f59e0b', dark: '#f59e0b' },
      '--dsw-specific-sidebar-fill': { light: BG, dark: BG },
    }

    // 生成完整样式：统一深色体系（不追随系统外观）+ 文字层级 + 代码块 + 语法高亮 + 字号 + 字体 + 标题紫色
    const buildCss = () => {
      const bodyFont = mode === 'mono' ? FONTS[fontKey] : SANS
      const codeFont = FONTS[fontKey]
      const lh = size + 9 // 13px → 22px 行高，约 1.7
      const small = size - 1
      return [
        'body, body[data-ds-dark-theme]{',
        // 文字颜色层级
        '--dsw-alias-label-tertiary:#8b8b95;',
        '--dsw-alias-label-caption:#8b8b95;',
        '--dsw-alias-label-dimmed:#52525b;',
        // 背景：所有表面统一深黑（输入框/按钮/菜单/选择器/弹层等）
        '--dsw-alias-bg-layer-3:' + BG + ';',
        '--dsw-alias-bg-module-platform:' + BG + ';',
        '--dsw-alias-bg-multi-select:' + BG + ';',
        // 输入框：截图同款深灰卡片 #1c1c1e，与聊天内容分层
        '--dsw-specific-input-major:' + INPUT_BG + ';',
        '--dsw-specific-login-input:' + INPUT_BG + ';',
        '--dsw-alias-border-l2-darkmode-thin:#333338;',
        '--dsw-specific-menu:' + BG + ';',
        '--dsw-specific-selector:' + BG + ';',
        '--dsw-specific-tip:' + BG + ';',
        '--dsw-alias-toast-bg:' + BG_OVER + ';',
        '--dsw-alias-tooltip-bg:' + BG_OVER + ';',
        // 按钮与交互态（深色体系）
        '--dsw-alias-button-elevated-fill:' + BG + ';',
        '--dsw-alias-button-floating-fill:' + BG + ';',
        '--dsw-alias-button-floating-hover:' + BG_RAISE + ';',
        '--dsw-alias-button-ghost-active-border:#52525b;',
        '--dsw-alias-button-ghost-active-fill:' + BG + ';',
        '--dsw-alias-button-ghost-active-hover:' + BG_RAISE + ';',
        '--dsw-alias-button-primary-dimmed:' + BG + ';',
        '--dsw-alias-button-primary-fill:#c084fc;',
        '--dsw-alias-button-primary-hover:#d09cff;',
        '--dsw-alias-button-info-fill:#3b82f6;',
        '--dsw-alias-button-info-hover:#4d94ff;',
        '--dsw-alias-button-contrast-fill:#f4f4f5;',
        '--dsw-alias-button-tool-bar-fill:rgba(255,255,255,0.1);',
        '--dsw-alias-button-tool-bar-hover:rgba(255,255,255,0.16);',
        '--dsw-alias-button-tool-bar-fill-invisible:rgba(255,255,255,0.04);',
        // 交互背景
        '--dsw-alias-interactive-bg-active:rgba(255,255,255,0.14);',
        '--dsw-alias-interactive-bg-hover:rgba(255,255,255,0.08);',
        '--dsw-alias-interactive-bg-hover-accent:rgba(192,132,252,0.2);',
        '--dsw-alias-interactive-bg-hover-danger:rgba(248,113,113,0.15);',
        '--dsw-alias-interactive-bg-hover-solid:' + BG_RAISE + ';',
        // 反色边框与滚动条
        '--dsw-alias-border-inverted:rgba(255,255,255,0.06);',
        '--dsw-alias-border-inverted2:rgba(255,255,255,0.08);',
        '--dsw-alias-scrollbar-bg-l1:#1e1e22;',
        '--dsw-alias-scrollbar-bg-l2:#1e1e22;',
        '--dsw-alias-scrollbar-hover-l1:#333338;',
        '--dsw-alias-scrollbar-hover-l2:#333338;',
        // 主按钮文字（紫底深字）
        '--dsw-alias-label-primary-foreground:#140a1e;',
        '--dsw-alias-label-primary-inverted:#e5e5e5;',
        '--dsw-alias-label-primary-dimmed:#f4f4f5;',
        '--dsw-alias-brand-primary-invert:#e5e5e5;',
        // 代码风格：柔和分层（L1 #131316 / 横幅 L2 #19191d），无硬边框
        '--dsw-alias-markdown-code-block:' + CODE_BG + ';',
        '--dsw-alias-markdown-code-block-banner:' + BANNER_BG + ';',
        // 内联代码：opencode TUI 同款无背景芯片，纯翠绿文字
        '--dsw-alias-markdown-inline-code:transparent;',
        '--dsw-alias-markdown-tag:' + BG + ';',
        '--dsw-alias-markdown-placeholder:' + BG_OVER + ';',
        '--dsw-alias-markdown-citation:' + BG_OVER + ';',
        '--dsw-alias-markdown-code-segment-selected:' + BG_OVER + ';',
        '--dsw-alias-markdown-code-segment-unselected:' + BG + ';',
        '--dsw-specific-bubble:' + BG + ';',
        '--dsw-specific-bubble-highlight:' + BG + ';',
        // 代码语法高亮（One Dark 系）
        '--shiki-foreground:#d4d4d4;',
        '--shiki-token-constant:#d19a66;',
        '--shiki-token-string:#98c379;',
        '--shiki-token-comment:#7f848e;',
        '--shiki-token-keyword:#c678dd;',
        '--shiki-token-parameter:#e06c75;',
        '--shiki-token-function:#61afef;',
        '--shiki-token-string-expression:#98c379;',
        '--shiki-token-punctuation:#abb2bf;',
        '--shiki-token-link:#61afef;',
        // 字体
        '--dsw-font-family:' + bodyFont + ';',
        '--ds-font-family-code:' + codeFont + ';',
        // 字号层级（markdown）
        '--dsw-font-markdown-base:' + size + 'px/' + lh + 'px var(--dsw-font-family);',
        '--dsw-font-markdown-base-font-size:' + size + 'px;',
        '--dsw-font-markdown-base-line-height:' + lh + 'px;',
        '--dsw-font-markdown-h1:700 16px/24px var(--dsw-font-family);',
        '--dsw-font-markdown-h1-font-size:16px;',
        '--dsw-font-markdown-h1-line-height:24px;',
        '--dsw-font-markdown-h2:700 15px/22px var(--dsw-font-family);',
        '--dsw-font-markdown-h2-font-size:15px;',
        '--dsw-font-markdown-h2-line-height:22px;',
        '--dsw-font-markdown-h3:600 14px/21px var(--dsw-font-family);',
        '--dsw-font-markdown-h3-font-size:14px;',
        '--dsw-font-markdown-h3-line-height:21px;',
        '--dsw-font-markdown-small:' + small + 'px/' + (small + 8) + 'px var(--dsw-font-family);',
        '--dsw-font-markdown-small-font-size:' + small + 'px;',
        '--dsw-font-markdown-small-line-height:' + (small + 8) + 'px;',
        '}',
        // 内联代码：opencode 风格翠绿等宽
        'code:not(pre code){color:#4ade80 !important;}',
        // markdown 标题：opencode 淡紫色（截图「Commit 历史」同款）
        'body h1,body h2,body h3,body h4,body h5,body h6{color:#c084fc;}',
        // 正文基础字号
        'body{font-size:' + size + 'px;}',
        // 有意不加代码块描边：opencode TUI 无硬边框，靠亮度阶梯 + 12px 圆角定义模块
      ].join('')
    }

    const applyStyle = () => {
      const d1 = theme.overrideTokens('opencode-tui-style', TOKENS)
      const d2 = styles.insert(buildCss())
      disposers = [d1, d2]
    }

    const clearStyle = () => {
      disposers.forEach(function (d) { if (typeof d === 'function') d() })
      disposers = []
    }

    applyStyle()
    enabled = true

    if (slots === undefined) return
    slots.inject('tool.view.cordis', function () {
      return slots.register(
        { name: 'tool.view.cordis', key: 'self' },
        function (props) {
          const [on, setOn] = React.useState(enabled)
          const [curMode, setMode] = React.useState(mode)
          const [curSize, setSize] = React.useState(size)
          const [curFont, setFont] = React.useState(fontKey)

          const refresh = (nextMode, nextSize, nextFont) => {
            mode = nextMode
            size = nextSize
            fontKey = nextFont
            if (enabled) {
              clearStyle()
              applyStyle()
            }
          }

          const toggle = function () {
            if (on) {
              clearStyle()
              enabled = false
            } else {
              applyStyle()
              enabled = true
            }
            setOn(!on)
          }

          const labelStyle = { color: 'var(--dsw-alias-label-secondary)', fontSize: 12 }
          const controlStyle = {
            background: 'var(--dsw-alias-bg-layer-2)',
            color: 'var(--dsw-alias-label-primary)',
            border: '1px solid var(--dsw-alias-border-l1)',
            borderRadius: 4,
            padding: '3px 6px',
            fontFamily: 'var(--dsw-font-family)',
            fontSize: 12,
            cursor: 'pointer',
          }
          const field = function (label, select) {
            return React.createElement('label', { style: { display: 'inline-flex', alignItems: 'center', gap: 4 } }, [
              React.createElement('span', { style: labelStyle }, label),
              select,
            ])
          }

          return React.createElement('div', {
            style: {
              border: '1px solid var(--dsw-alias-border-l1)',
              borderRadius: 8,
              padding: '10px 12px',
              background: 'var(--dsw-alias-bg-layer-1)',
              fontFamily: 'var(--dsw-font-family)',
              fontSize: 13,
              color: 'var(--dsw-alias-label-primary)',
              lineHeight: 1.6,
            },
          }, [
            React.createElement('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' } }, [
              React.createElement('strong', null, '🖥 Opencode TUI 主题'),
              React.createElement('span', { style: { color: on ? 'var(--dsw-alias-state-success-primary)' : 'var(--dsw-alias-label-secondary)', fontSize: 12 } }, on ? '● 已启用' : '○ 已停用'),
            ]),
            React.createElement('div', { style: { ...labelStyle, margin: '6px 0' } }, '复刻 opencode TUI：统一深黑背景 + 全等宽终端正文 + One Dark 语法高亮'),
            React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 10, marginTop: 4, flexWrap: 'wrap' } }, [
              field('正文', React.createElement('select', { value: curMode, onChange: function (e) { const v = e.target.value; setMode(v); refresh(v, size, fontKey) }, style: controlStyle }, [
                React.createElement('option', { value: 'mono' }, '全等宽(终端)'),
                React.createElement('option', { value: 'tui' }, '无衬线(忠实)'),
              ])),
              field('字号', React.createElement('select', { value: curSize, onChange: function (e) { const v = Number(e.target.value); setSize(v); refresh(mode, v, fontKey) }, style: controlStyle }, [12, 13, 14].map(function (s) {
                return React.createElement('option', { key: s, value: s }, s + 'px')
              }))),
              field('代码字体', React.createElement('select', { value: curFont, onChange: function (e) { const v = e.target.value; setFont(v); refresh(mode, size, v) }, style: controlStyle }, Object.keys(FONTS).map(function (k) {
                return React.createElement('option', { key: k, value: k }, k)
              }))),
              React.createElement('button', { onClick: toggle, style: { ...controlStyle, borderColor: on ? 'var(--dsw-alias-state-warn-primary)' : 'var(--dsw-alias-state-success-primary)', color: on ? 'var(--dsw-alias-state-warn-primary)' : 'var(--dsw-alias-state-success-primary)' } }, on ? '停用风格' : '启用风格'),
            ]),
          ])
        },
      )
    })
  },
}

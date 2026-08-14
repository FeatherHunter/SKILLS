/**
 * dsh-opencode-tui-theme 浏览器半（Client bundle）v1.1.0
 *
 * 格式：DSH client-modules 的惰性 CJS bundle —— 经典脚本执行时只注册 factory，
 * 由浏览器内核（vendored Cordis Loader）在挂载该插件条目时物化执行。
 * 导出形状与官方 client 包一致：named exports { inject, apply }。
 *
 * v1.1.0 变更：
 *   1. 修复 v1.0.0 致命 bug：ctx.effect(fn) 的 fn 是「立即执行」、返回值才是
 *      卸载清理器。旧代码把清理动作直接写进 effect 体，导致样式注入后
 *      在同一瞬间被移除（插件 active 但界面毫无变化）。
 *   2. 新增控制面板：设置 → 插件 → 「Opencode 主题」标签页 ——
 *      ● 已启用/○ 已停用 状态、启用/停用开关、正文模式/字号/代码字体调节、
 *      以及 getComputedStyle 实测生效自检（背景/字体/字号）。
 */
window.__ModuleLoader__.load({
  id: 'dsh-opencode-tui-theme',
  factory: (require) => {
    var module = { exports: {} }
    var exports = module.exports
    Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' })

    let react = require('react')

    // ── 主题常量（与动态版 client.js 同一套配色）──
    const BG = '#0a0a0a' // 截图背景色（像素采样 #0A0A0A）：整个界面背景统一
    const BG_RAISE = '#101014' // 悬停/浮起略亮
    const BG_OVER = '#16161a' // 浮层/选中
    const INPUT_BG = '#1c1c1e' // 截图底部输入框背景（深灰卡片，与内容区分层）
    // 代码块柔和亮度阶梯（无硬边框、无芯片，靠柔和表面差 + 圆角）：
    //   L0 聊天画布 #0a0a0a < L1 代码块 #131316 < L2 横幅(复制按钮) #19191d
    const CODE_BG = '#131316'
    const BANNER_BG = '#19191d'

    // 运行时可调参数（控制面板修改；默认值 = v1.0.0 固定参数）
    let mode = 'mono' // mono=全等宽终端(默认) tui=无衬线忠实
    let size = 13 // 正文基础字号 12/13/14
    let fontKey = 'JetBrains Mono'

    const SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif"

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

    // 生成完整样式：统一深色体系 + 文字层级 + 代码块分层 + 语法高亮 + 字号 + 字体 + 标题紫色
    function buildCss() {
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
        // markdown 标题：opencode 淡紫色
        'body h1,body h2,body h3,body h4,body h5,body h6{color:#c084fc;}',
        // 正文基础字号
        'body{font-size:' + size + 'px;}',
        // 有意不加代码块描边：opencode TUI 无硬边框，靠亮度阶梯 + 12px 圆角定义模块
      ].join('')
    }

    exports.inject = ['theme', 'slots']

    exports.apply = function (ctx) {
      const theme = ctx.get('theme')
      const slots = ctx.get('slots')

      let tokenDispose = null
      let styleTag = null
      let enabled = false

      // 应用样式：token 层（13 个注册 token）+ <style> 层（其余 CSS 变量）
      function applyStyle() {
        if (!theme) return
        if (tokenDispose) { try { tokenDispose() } catch (error) {} }
        tokenDispose = theme.overrideTokens('opencode-tui-style-boot', TOKENS)
        if (styleTag === null && typeof document !== 'undefined') {
          styleTag = document.createElement('style')
          styleTag.dataset.plugin = 'dsh-opencode-tui-theme'
          document.head.appendChild(styleTag)
        }
        if (styleTag) styleTag.textContent = buildCss()
      }
      function clearStyle() {
        if (tokenDispose) { try { tokenDispose() } catch (error) {} tokenDispose = null }
        if (styleTag !== null && styleTag.parentNode) styleTag.parentNode.removeChild(styleTag)
        styleTag = null
      }

      // 面板动作（与 React 组件共享的闭包）
      function getState() { return { enabled, mode, size, fontKey } }
      function toggle() {
        if (enabled) { clearStyle(); enabled = false }
        else { applyStyle(); enabled = true }
      }
      function refresh(nextMode, nextSize, nextFont) {
        mode = nextMode
        size = nextSize
        fontKey = nextFont
        if (enabled) { clearStyle(); applyStyle() }
      }

      // 默认启用（与 v1.0.0 行为一致）
      applyStyle()
      enabled = true

      // ── 控制面板：设置 → 插件 → 「Opencode 主题」标签页 ──
      let disposePanel = null
      if (slots !== undefined && typeof document !== 'undefined') {
        const Panel = function (props) {
          const init = props.getState()
          const [on, setOn] = react.useState(init.enabled)
          const [curMode, setMode] = react.useState(init.mode)
          const [curSize, setSize] = react.useState(init.size)
          const [curFont, setFont] = react.useState(init.fontKey)
          const [tick, setTick] = react.useState(0)

          const change = function (nextMode, nextSize, nextFont) {
            props.refresh(nextMode, nextSize, nextFont)
            setMode(nextMode); setSize(nextSize); setFont(nextFont)
          }
          const flip = function () {
            props.toggle()
            setOn(!on)
            setTick(tick + 1)
          }

          // 生效自检：getComputedStyle 实测 body（每次渲染重算）
          let evidence = null
          try {
            if (typeof getComputedStyle !== 'undefined' && document.body) {
              const cs = getComputedStyle(document.body)
              evidence = {
                bg: cs.backgroundColor,
                font: (cs.fontFamily || '').split(',')[0] || '',
                size: cs.fontSize,
              }
            }
          } catch (error) { /* 忽略自检失败 */ }

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
          const field = function (labelText, select) {
            return react.createElement('label', { style: { display: 'inline-flex', alignItems: 'center', gap: 4 } }, [
              react.createElement('span', { style: labelStyle }, labelText),
              select,
            ])
          }
          const select = function (value, options, onChange) {
            return react.createElement('select', { value: String(value), onChange: onChange, style: controlStyle },
              options.map(function (opt) {
                return react.createElement('option', { key: String(opt.value), value: String(opt.value) }, opt.label)
              }))
          }

          return react.createElement('div', { style: { display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 720 } }, [
            react.createElement('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' } }, [
              react.createElement('strong', null, '🖥 Opencode TUI 主题'),
              react.createElement('span', { style: { color: on ? 'var(--dsw-alias-state-success-primary)' : 'var(--dsw-alias-label-secondary)', fontSize: 12 } },
                on ? '● 已启用' : '○ 已停用'),
            ]),
            react.createElement('div', { style: labelStyle }, '复刻 opencode TUI：统一深黑背景 #0a0a0a + 全等宽终端正文 + One Dark 语法高亮'),
            react.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' } }, [
              field('正文', select(curMode, [
                { value: 'mono', label: '全等宽(终端)' },
                { value: 'tui', label: '无衬线(忠实)' },
              ], function (e) { change(e.target.value, curSize, curFont) })),
              field('字号', select(curSize, [12, 13, 14].map(function (s) { return { value: s, label: s + 'px' } }),
                function (e) { change(curMode, Number(e.target.value), curFont) })),
              field('代码字体', select(curFont, Object.keys(FONTS).map(function (k) { return { value: k, label: k } }),
                function (e) { change(curMode, curSize, e.target.value) })),
              react.createElement('button', {
                onClick: flip,
                style: {
                  ...controlStyle,
                  borderColor: on ? 'var(--dsw-alias-state-warn-primary)' : 'var(--dsw-alias-state-success-primary)',
                  color: on ? 'var(--dsw-alias-state-warn-primary)' : 'var(--dsw-alias-state-success-primary)',
                },
              }, on ? '停用风格' : '启用风格'),
            ]),
            evidence === null ? null : react.createElement('div', { style: { ...labelStyle, fontFamily: 'monospace', marginTop: 4 } },
              '实测 body → 背景 ' + evidence.bg + ' · 字体 ' + evidence.font + ' · ' + evidence.size),
          ])
        }
        disposePanel = slots.inject('settings.plugins.tab', function () {
          return slots.register({
            name: 'settings.plugins.tab',
            id: 'opencode-tui-theme',
            order: 30,
            label: function () { return 'Opencode 主题' },
            inject: function () { return { getState, toggle, refresh } },
          }, Panel)
        })
      }

      // 卸载清理（v1.1.0 修复：fn 立即执行建立 effect，RETURN 的函数才是清理器）
      ctx.effect(function () {
        return function () {
          try { clearStyle() } catch (error) { /* 忽略清理期错误 */ }
          try { if (disposePanel) disposePanel() } catch (error) { /* 忽略清理期错误 */ }
        }
      }, 'dsh-opencode-tui-theme: styles')
    }

    return module.exports
  },
})

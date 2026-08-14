/**
 * dsh-opencode-tui-theme 宿主半（no-op）
 *
 * 主题的全部工作在浏览器端（./client.js）完成：
 *   - theme.overrideTokens 覆盖 13 个注册主题 token
 *   - 注入 <style> 覆盖 CSS 层变量（输入框/按钮/代码块/shiki/字体/字号）
 * 宿主半只保证 loader 条目可解析、可挂载。
 */
export const name = 'dsh-opencode-tui-theme'

export function apply() {
  // no-op：客户端半负责一切
}

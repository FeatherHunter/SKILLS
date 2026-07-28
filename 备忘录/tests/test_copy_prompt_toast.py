"""v1.1.5 · HELP HTML 复制 prompt 反馈 UI 守护

学习卡路里 HELP(help_center.html)的 toast 反馈模式,
升级备忘录 HELP(memo_help.html)的 copyPrompt 体验:

卡路里模式(参考):
  - iOS 通知风格 toast 浮层(底部 fixed + 毛玻璃 + 4.5s 自动消失)
  - 3 段内容:📋 icon + "已复制 <em>唤醒词</em>" 标题 + "粘贴给 AI..." 详情
  - "✓ 知道了" 关闭按钮(绿色,可手动关闭)
  - 按钮自身也变 "✓ 已复制" 2s(双反馈)
  - 复制时从场景卡片提取唤醒词显示在 toast(确认复制对了)

备忘录语境适配:
  - 文案改"备忘录"语境(不是"卡路里")
  - 提取 scenario.wake_word 显示在 toast
"""
from pathlib import Path

TEMPLATE = Path(__file__).parent.parent / "templates" / "memo_help.html"


class TestCopyPromptToastFeedback:
    """学习卡路里 HELP 的 toast 反馈 UI,移植到备忘录 HELP。"""

    def test_has_toast_element(self):
        """toast 浮层元素存在(id="toast")。"""
        text = TEMPLATE.read_text(encoding="utf-8")
        assert 'id="toast"' in text, "memo_help.html 缺 toast 浮层元素"

    def test_has_toast_css(self):
        """toast CSS 样式存在(.toast + .toast.show)。"""
        text = TEMPLATE.read_text(encoding="utf-8")
        assert ".toast" in text, "memo_help.html 缺 .toast CSS"
        assert ".toast.show" in text or ".toast.show{" in text, "memo_help.html 缺 .toast.show CSS"

    def test_has_toast_icon_and_title_structure(self):
        """toast 含 📋 icon + "已复制" + <em id="toastWake"> 标题结构。"""
        text = TEMPLATE.read_text(encoding="utf-8")
        assert "📋" in text, "toast 缺 📋 icon"
        assert "已复制" in text, "toast 缺 '已复制' 标题"
        assert 'id="toastWake"' in text or 'toastWake' in text, "toast 缺 <em id=\"toastWake\"> 元素(显示唤醒词)"

    def test_has_toast_detail_text_with_memo_context(self):
        """toast 详情文案含"粘贴给 AI" + "微信/飞书" + "备忘录" + "HTML"(备忘录语境)。"""
        text = TEMPLATE.read_text(encoding="utf-8")
        assert "粘贴给 AI" in text or "粘贴给" in text, "toast 缺'粘贴给 AI'文案"
        assert "微信" in text and "飞书" in text, "toast 缺'微信/飞书'消息工具提及"
        assert "备忘录" in text, "toast 缺'备忘录'语境词"
        assert "HTML" in text, "toast 缺'HTML'结果承诺"

    def test_has_toast_close_button(self):
        """toast 含"✓ 知道了"关闭按钮。"""
        text = TEMPLATE.read_text(encoding="utf-8")
        assert "知道了" in text, "toast 缺'✓ 知道了'关闭按钮"

    def test_copy_prompt_calls_show_toast(self):
        """copyPrompt 函数调用 showToast(触发 toast 显示)。"""
        text = TEMPLATE.read_text(encoding="utf-8")
        assert "showToast" in text, "copyPrompt 缺 showToast 调用"
        # showToast 函数定义存在
        assert "function showToast" in text or "showToast=function" in text or "const showToast" in text, \
            "缺 showToast 函数定义"

    def test_toast_auto_dismiss_and_manual_close(self):
        """toast 自动消失(setTimeout) + 手动关闭(addEventListener click)。"""
        text = TEMPLATE.read_text(encoding="utf-8")
        assert "setTimeout" in text, "toast 缺自动消失 setTimeout"
        assert "toastClose" in text or "addEventListener" in text, "toast 缺手动关闭逻辑"

    def test_toast_mobile_adaptive(self):
        """toast 移动端适配(@media 段含 .toast 规则)。"""
        text = TEMPLATE.read_text(encoding="utf-8")
        # 检查 @media 段内含 .toast(允许嵌套 },用简单 substring 检查)
        # 找所有 @media 起始位置,看后续 500 字符内是否有 .toast
        import re
        media_starts = [m.start() for m in re.finditer(r"@media", text)]
        found_in_media = False
        for start in media_starts:
            chunk = text[start:start+600]  # 取 @media 后 600 字符
            if ".toast" in chunk:
                found_in_media = True
                break
        assert found_in_media, "@media 段缺 .toast 移动端适配"

    def test_button_text_changes_too(self):
        """按钮自身文案也变 '✓ 已复制'(双反馈 · 保留原行为)。"""
        text = TEMPLATE.read_text(encoding="utf-8")
        assert "✓ 已复制" in text, "copyPrompt 按钮文案缺 '✓ 已复制' 反馈"

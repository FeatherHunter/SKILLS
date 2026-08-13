"""v1.1.3 复制按钮改造守护

测试 templates/memo_query.html 的复制按钮和函数必须:
- 按钮文案 "复制" (不是 "复制ID")
- copyInfo 函数存在且含 #ID/content/category/created_at 字段
- 反馈 "✓ 已复制" 字面存在
- copyReceipt 含每条 item 详情

来源:用户反馈 "复制的内容不是单纯 ID · 应含相关信息(用户看内容确认是否复制错)"

边界说明(诚实):
- 文档层测试(字面/regex),不验证 JS 运行时
- 不能防:JS 语法错 / 按钮点击无反应 / navigator.clipboard 改 API
- 能防:文案回退 / 函数删 / 字段缺 / 反馈消 / 详情降级
"""
import re
from pathlib import Path
import pytest

TEMPLATE = Path(__file__).parent.parent / "templates" / "memo_query.html"


def _extract_function_body(text, name):
    """提取 function NAME(...) { body } 的 body,正确处理嵌套 {}"""
    m = re.search(r'function\s+' + re.escape(name) + r'\s*\([^)]*\)\s*\{', text)
    if not m:
        return None
    start = m.end() - 1  # '{' 位置
    depth = 0
    i = start
    in_string = False
    string_char = None
    while i < len(text):
        c = text[i]
        if not in_string and c in ('"', "'", '`'):
            in_string = True
            string_char = c
        elif in_string and c == string_char and (i == 0 or text[i-1] != '\\'):
            in_string = False
        elif not in_string:
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return text[start + 1:i]
        i += 1
    return None


class TestCopyButtonV113:
    """v1.1.3 复制按钮 + 函数 + 反馈守护"""

    @pytest.fixture
    def text(self):
        return TEMPLATE.read_text(encoding="utf-8")

    # ---- 1. 按钮文案(简化)----

    def test_copy_button_label_simplified(self, text):
        """按钮文案是'复制'(不是'复制ID')· #299 Base ghost 样式"""
        m = re.search(
            r'renderItem\([^{]*\{.*?<button[^>]*class="copy ghost"[^>]*>([^<]+)</button>',
            text, re.DOTALL,
        )
        assert m, "renderItem 缺 class='copy ghost' 按钮(#299 Base 复制按钮样式)"
        assert m.group(1).strip() == "复制", \
            f"按钮文案应为'复制',实际: {m.group(1).strip()!r}"

    def test_no_old_copy_id_label(self, text):
        """不应有 '复制 ID' / '复制ID' 字样(防回退)"""
        bad = re.findall(r'>\s*复制\s*ID\s*<', text)
        assert not bad, f"模板不应有'复制 ID'旧按钮文案: {bad}"

    def test_copy_button_exists_per_item(self, text):
        """renderItem 含 copy ghost 按钮(每条 item 都有)"""
        m = re.search(r'renderItem\([^{]*\{.*?class="copy ghost".*?</button>', text, re.DOTALL)
        assert m, "renderItem 缺复制按钮(#299 ghost)"

    # ---- 2. copyInfo 函数(单条复制)----

    def test_copy_info_function_exists(self, text):
        """字面含 'function copyInfo'(单条复制函数)"""
        assert "function copyInfo" in text, "缺 copyInfo 函数(用户期望新增)"

    def test_copy_info_includes_id_with_hash(self, text):
        """copyInfo 含 '#'+id 形式(AI 能解析的格式)"""
        body = _extract_function_body(text, "copyInfo")
        assert body is not None, "copyInfo 函数体未找到"
        has_hash = '#' in body
        has_id_ref = ('x.id' in body) or ('checkin_note_id' in body) or ('reminder_id' in body)
        assert has_hash and has_id_ref, \
            "copyInfo 应含 '#'+id 形式(AI 可解析)"

    def test_copy_info_includes_content(self, text):
        """copyInfo 含 content 字段引用(用户看内容确认复制正确)"""
        body = _extract_function_body(text, "copyInfo")
        assert body is not None
        assert "content" in body, \
            "copyInfo 应含 content 字段引用(用户关键诉求:复制内容含信息)"

    def test_copy_info_includes_category(self, text):
        """copyInfo 含 category 字段引用"""
        body = _extract_function_body(text, "copyInfo")
        assert body is not None
        assert "category" in body and "cat" in body, \
            "copyInfo 应引用 category 字段(用户看分类确认)"

    def test_copy_info_includes_created_at(self, text):
        """copyInfo 含 created_at 字段引用(用户看时间确认)"""
        body = _extract_function_body(text, "copyInfo")
        assert body is not None
        assert ("created_at" in body) or ("checkin_at" in body), \
            "copyInfo 应含 created_at/checkin_at 字段引用(用户看时间)"

    # ---- 3. 复制反馈(用户体验)----

    def test_copy_feedback_label_exists(self, text):
        """字面含自定义 toast 反馈文案(#299:按钮文字恒定,反馈走 Base toast)"""
        assert "已复制这条备忘" in text, \
            "缺'已复制这条备忘'taost 反馈文案(#295 文案表定稿)"

    # ---- 4. copyReceipt 改造(整批复制含详情)----

    def test_copy_receipt_includes_item_details(self, text):
        """snapshotText 含每条 item 详情(不是纯 ID 列表)
        #299:回执 → 筛选快照,receiptText → snapshotText,4 部分格式
        """
        body = _extract_function_body(text, "snapshotText")
        assert body is not None, "snapshotText 函数未找到"
        has_detail_keywords = any(
            kw in body for kw in ["详情", "content", "forEach", "【", "① 场景", "② 数据"]
        )
        assert has_detail_keywords, \
            "snapshotText 应含每条 item 详情处理(不是纯 ID 列表)"

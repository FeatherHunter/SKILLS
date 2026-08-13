"""T15 · 备忘录.html surrogates 钉死测试。

HEAD 中 备忘录/备忘录.html blob 含 GBK surrogates 异常(bad decode
遗留) · 任何跑 memo_cli.py help 后应重生成干净版本。
未来 CI 失败时不要 commit broken 版。
"""
from pathlib import Path

# HEAD 中 备忘录.html 路径(镜像 · memo_cli.py help 生成)
HELP_HTML = Path(__file__).parent.parent / "备忘录.html"


class TestMemoHtmlSurrogateGuard:
    def test_no_utf16_surrogates(self):
        """HEAD 副本不应含 UTF-16 高/低代理字符"""
        if not HELP_HTML.exists():
            return  # 工作区无 · 让 pre-commit hook 还原
        text = HELP_HTML.read_text(encoding="utf-8")
        SURROGATE_LOW = 0xD800
        SURROGATE_HIGH = 0xDFFF
        for i, ch in enumerate(text):
            code = ord(ch)
            assert not (SURROGATE_LOW <= code <= SURROGATE_HIGH), (
                "备忘录.html 第 " + str(i) + " 字符含 UTF-16 surrogate "
                "(U+" + format(code, "04X") + ")"
                "· 通常 GBK 误解码 UTF-8 字节序列导致 · 跑 memo_cli.py help 重生成"
            )

    def test_no_gbk_artifacts(self):
        """不应含 GBK 误解码的乱码字符(典型:鍚屾 / 缁撴 / 椤圭)"""
        if not HELP_HTML.exists():
            return
        text = HELP_HTML.read_text(encoding="utf-8")
        gbk_artifacts = ["鍚", "缁", "椤", "鐢", "閫", "鏍", "鏂"]
        for art in gbk_artifacts:
            assert art not in text, (
                f"备忘录.html 含 GBK 误解码字符 {art!r} · 跑 `memo_cli.py help` 重生成"
            )

    def test_html_well_formed(self):
        """基本 HTML 结构 · doctype + html + body 必须存在"""
        if not HELP_HTML.exists():
            return
        text = HELP_HTML.read_text(encoding="utf-8")
        assert text.lower().startswith("<!doctype"), "备忘录.html 缺 doctype"
        assert "<html" in text, "备忘录.html 缺 <html>"
        assert "</html>" in text, "备忘录.html 缺 </html>"
        assert "<body>" in text, "备忘录.html 缺 <body>"

    def test_injects_help_data(self):
        """#299:必含 Base help-data 注入(memo_cli.py help 标准输出)"""
        if not HELP_HTML.exists():
            return
        text = HELP_HTML.read_text(encoding="utf-8")
        assert 'id="help-data"' in text, (
            "备忘录.html 缺 help-data 注入 · HELP 未正确生成"
        )
        assert "function copyText" in text, (
            "备忘录.html 缺 Base base.js · HELP 管线未接"
        )
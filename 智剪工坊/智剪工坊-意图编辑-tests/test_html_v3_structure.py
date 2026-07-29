"""
智剪工坊-意图编辑.html v3.0 静态结构测试
"""
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(r"D:\2Study\StudyNotes\SKILLS\智剪工坊")
HTML_PATH = SKILL_ROOT / "智剪工坊-意图编辑.html"

RESULTS = []
TESTS = []


def test(name):
    def decorator(fn):
        TESTS.append((name, fn))
        return fn
    return decorator


def run_all():
    for name, fn in TESTS:
        try:
            fn()
            RESULTS.append((name, True, ""))
        except AssertionError as e:
            RESULTS.append((name, False, str(e)))
        except Exception as e:
            RESULTS.append((name, False, f"{type(e).__name__}: {e}"))

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n{'='*60}\nResults: {passed}/{total} PASS\n{'='*60}\n")
    for name, ok, detail in RESULTS:
        marker = "PASS" if ok else "FAIL"
        line = f"  [{marker}] {name}"
        if not ok and detail:
            line += f"\n         {detail}"
        print(line)
    if passed != total:
        sys.exit(1)


# 读取 HTML
HTML = HTML_PATH.read_text(encoding="utf-8")


@test("H1 · _meta.schema_version='3.0' 已写入 collectFormData")
def h1():
    assert "schema_version: '3.0'" in HTML, "_meta.schema_version 应写入"
    assert "schema_version 必须" in HTML or "必须写" in HTML, "应加注释"


@test("H2 · _meta.tool_version 已写入")
def h2():
    assert "tool_version: '2.135'" in HTML, "_meta.tool_version 应写入"


@test("H3 · _meta.history 已删除")
def h3():
    # 查找 legacyOps 周围代码,确认没有 history 写入
    # 注释可保留(说明已删除),但不应有 history: newHistory 逻辑
    assert "const oldHistory" not in HTML, "_meta.history 数组写入代码应删除"
    assert "history: newHistory" not in HTML, "_meta.history 应删除"


@test("H4 · cover.type 含 image 选项(D1)")
def h4():
    assert '<option value="image">多图拼版' in HTML, "cover.type 应增加 image 选项"


@test("H5 · cover.images[] 上传器已加")
def h5():
    assert "data-cover-img-pick" in HTML, "cover.images[] 上传器 picker 应有"
    assert "data-path=\"cover.images-json\"" in HTML or 'data-path="cover.images-json"' in HTML, "cover.images[] hidden input 应有"


@test("H6 · ending select 改用 template 字段(D2 + D3)")
def h6():
    # ending.type select 应删除,但允许在注释/历史说明中出现
    # 真实的数据路径 data-path="ending.type" 不应存在
    assert 'data-path="ending.type"' not in HTML, "ending.type select 应删除"
    assert 'data-path="ending.template"' in HTML, "ending.template select 应有"
    # 10 个模板 emoji 检查
    emojis = ['🎵', '🖼️', '⬛', '⏱️', '📋', '🎙️', '🙏']
    for e in emojis:
        assert e in HTML, f"模板 emoji {e} 应出现"


@test("H7 · legacyOps 数组不含 5 个 deprecated op")
def h7():
    # 检查所有 legacyOps 数组定义
    matches = re.findall(r"const legacyOps = \[(.*?)\];", HTML, re.DOTALL)
    assert matches, "应至少有一个 legacyOps 数组"
    for ops_str in matches:
        for deprecated in ['trim-head', 'trim-tail', 'cut-middle', 'pin-range', 'target-duration']:
            # 检查 deprecated op 不在数组里(作为独立元素)
            # 注意:可能出现在 'trim-head' 这种字符串里,但要看完整 token
            tokens = [t.strip().strip("'") for t in ops_str.split(',')]
            assert deprecated not in tokens, f"legacyOps 仍含 deprecated op {deprecated}"


@test("H8 · addOrSplit 移除 user op 注入")
def h8():
    # 之前 mid 段注入 ops: { user: { on: true, note: '' } }
    assert "ops: { user: { on: true, note: '' } }" not in HTML, "mid 段不应注入 user op"
    # 找 addOrSplit 函数体
    fn_idx = HTML.find("addOrSplit(videoIndex, start, end)")
    if fn_idx < 0:
        fn_idx = HTML.find("function addOrSplit")
    assert fn_idx >= 0, "应找到 addOrSplit"
    # 找下一个 function 边界
    fn_end = HTML.find("\n    function ", fn_idx + 10)
    if fn_end < 0:
        fn_end = HTML.find("\n    // ===", fn_idx + 10)
    fn_body = HTML[fn_idx:fn_end] if fn_end > 0 else HTML[fn_idx:fn_idx + 3000]
    assert "ops: { user:" not in fn_body, "addOrSplit 内不应注入 user op"


@test("H9 · collectFormData 过滤 excluded 段")
def h9():
    # 找到 time_segments.map 周围代码
    ts_idx = HTML.find("st.segments.map")
    if ts_idx >= 0:
        # 看前面 100 字是否含 filter
        before = HTML[max(0, ts_idx - 300):ts_idx]
        assert "filter" in before and "excluded" in before, "应加 filter(!excluded)"


@test("H10 · 加载老 schema 报错逻辑已加")
def h10():
    assert 'schema_version !== ' in HTML or 'schema_version !=' in HTML, "应加 schema_version 检查"
    assert '只支持 schema_version="3.0"' in HTML or '只支持' in HTML, "应明确只支持 v3.0"


@test("H11 · validateIntent 增强:含 schema_version/ending.template/cover.images 检查")
def h11():
    # 找 validateIntent 函数
    fn_idx = HTML.find("function validateIntent(")
    assert fn_idx >= 0, "应有 validateIntent 函数"
    fn_end = HTML.find("\n    }\n", fn_idx)
    fn_body = HTML[fn_idx:fn_end]
    assert "_meta.schema_version" in fn_body, "validateIntent 应检查 schema_version"
    assert "ending.template" in fn_body, "validateIntent 应检查 ending.template"
    assert "cover.images" in fn_body, "validateIntent 应检查 cover.images"
    assert "trim-head" in fn_body, "validateIntent 应检查 5 个 deprecated op"


@test("H12 · JS 语法正确(node --check)")
def h12():
    import subprocess
    import tempfile
    # 提取 <script>...</script> 内容
    script_start = HTML.find("<script>")
    script_end = HTML.rfind("</script>")
    if script_start < 0 or script_end < 0:
        assert False, "未找到 <script> 块"
    js_content = HTML[script_start + len("<script>"):script_end]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js_content)
        tmp_path = f.name
    try:
        result = subprocess.run(
            ["node", "--check", tmp_path],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, f"JS 语法错: {result.stderr}"
    finally:
        import os
        os.unlink(tmp_path)


if __name__ == "__main__":
    print(f"HTML: {HTML_PATH} ({len(HTML)} bytes)")
    run_all()
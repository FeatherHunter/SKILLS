"""HELP 端到端 Playwright 验证 + 截图闭环
用户要求: 任何问题用 Playwright + 截图,LLM 看图定位 bug
闭环: 实测 → 截图 → 报告失败 → 落盘修复
"""
import asyncio
import subprocess
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright


SKILL = Path("/mnt/d/2Study/StudyNotes/SKILLS/居家管家")
SHOTS_DIR = SKILL / ".notes" / "HELP_shots"
SHOTS_DIR.mkdir(parents=True, exist_ok=True)


async def run():
    # 1. 实际跑 help 命令生成 HTML(隔离 temp DB,不污染生产)
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    env = {
        "HOME": "/tmp",
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "SKILLS_DB_PATH": str(tmp),
    }
    out = tmp / "help.html"
    r = subprocess.run(
        ["python3", str(SKILL / "scripts" / "home_manager.py"), "help", "--output", str(out)],
        capture_output=True, text=True, env=env, cwd=str(SKILL / "scripts"),
        timeout=60,
    )
    assert r.returncode == 0, f"help 命令失败: {r.stderr}"

    issues = []
    passed = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # 收集 console 错误
        console_errors = []
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))
        page.on("console", lambda msg: console_errors.append(f"console.{msg.type}: {msg.text}") if msg.type == "error" else None)

        # ===== Step 1: 加载页面 =====
        await page.goto(f"file://{out}")
        await page.wait_for_load_state("networkidle")

        # 截图 1: 初始状态
        shot1 = SHOTS_DIR / "01_initial.png"
        await page.screenshot(path=str(shot1), full_page=True)

        # 验证 1: h1
        h1 = await page.locator("h1").text_content()
        if "居家管家" in h1 and "能力速查" in h1:
            passed.append(f"✓ h1 渲染: {h1}")
        else:
            issues.append(f"✗ h1 缺失或错: {h1!r}")

        # 验证 2: groups 数量
        groups = await page.locator(".group").count()
        if groups == 31:
            passed.append(f"✓ groups 渲染: {groups} 个")
        else:
            issues.append(f"✗ groups 数量: 预期 31,实际 {groups}")

        # 验证 3: 默认第一组展开
        open_count = await page.locator(".group.open").count()
        if open_count == 1:
            passed.append("✓ 默认第一组展开")
        else:
            issues.append(f"✗ 默认展开数: 预期 1,实际 {open_count}")

        # 验证 4: 第一个 group 是修物品(scenarios.yaml 顺序)
        first_group_h2 = await page.locator(".group").first.locator("h2").text_content()
        # 期望:查物品(用户视角高频优先),实际可能是修物品
        issues.append(f"⚠ 第一个 group 是 {first_group_h2!r}(scenarios.yaml 首项,非用户视角高频)")

        # 验证 5: 场景渲染数
        scenarios = await page.locator(".scenario").count()
        if scenarios == 34:
            passed.append(f"✓ scenarios 渲染: {scenarios} 个")
        else:
            issues.append(f"✗ scenarios 数量: 预期 34,实际 {scenarios}")

        # 验证 6: 复制按钮
        copy_btns = await page.locator(".copy-btn").count()
        if copy_btns == 34:
            passed.append(f"✓ copy buttons: {copy_btns} 个")
        else:
            issues.append(f"✗ copy buttons: 预期 34,实际 {copy_btns}")

        # 验证 7: prompt textContent 是否被注入
        first_prompt = await page.locator(".s-prompt").first.text_content()
        if first_prompt and first_prompt.strip():
            passed.append(f"✓ prompt 注入 OK: {first_prompt[:30]!r}...")
        else:
            issues.append("✗ prompt textContent 为空!")
            shot_empty = SHOTS_DIR / "07_prompt_empty.png"
            await page.locator(".group").first.screenshot(path=str(shot_empty))

        # ===== Step 2: 点 group[0] 折叠/展开切换 =====
        first_gh = page.locator(".group-h").first
        was_open = "open" in (await first_gh.evaluate("el => el.closest('.group').className"))
        await first_gh.click()
        await page.wait_for_timeout(200)
        now_open = "open" in (await first_gh.evaluate("el => el.closest('.group').className"))
        if was_open != now_open:
            passed.append(f"✓ 折叠切换: {was_open} → {now_open}")
        else:
            issues.append(f"✗ 折叠切换失败: {was_open} → {now_open}")

        shot2 = SHOTS_DIR / "02_after_toggle.png"
        await page.screenshot(path=str(shot2), full_page=True)

        # ===== Step 3: 点 TOC 链接跳转 =====
        toc_links = await page.locator(".toc a").count()
        if toc_links >= 30:
            passed.append(f"✓ TOC 链接: {toc_links} 个")
        # 点第 5 个 TOC
        if toc_links >= 5:
            await page.locator(".toc a").nth(4).click()
            await page.wait_for_timeout(500)
            # 检查 URL 变化
            url = page.url
            if "#g-" in url:
                passed.append(f"✓ TOC 跳转: {url[-20:]}")
            else:
                issues.append(f"✗ TOC 跳转 URL 未变: {url}")

        shot3 = SHOTS_DIR / "03_after_toc_jump.png"
        await page.screenshot(path=str(shot3), full_page=True)

        # ===== Step 4: 测试 copy 按钮 =====
        await context.grant_permissions(["clipboard-read", "clipboard-write"])
        # 展开所有 group 以便点 copy
        await page.evaluate("document.querySelectorAll('.group').forEach(g => g.classList.add('open'))")
        await page.wait_for_timeout(200)
        # 点第 0 个 copy 按钮
        await page.locator(".copy-btn").first.click()
        await page.wait_for_timeout(500)
        try:
            clip = await page.evaluate("navigator.clipboard.readText()")
            if clip and clip.strip() and clip != "undefined":
                passed.append(f"✓ copy 成功: {clip[:40]!r}...")
            else:
                issues.append(f"✗ copy 内容无效: {clip!r}")
        except Exception as e:
            issues.append(f"✗ clipboard.readText 异常: {e}")

        shot4 = SHOTS_DIR / "04_after_copy.png"
        await page.screenshot(path=str(shot4), full_page=True)

        # ===== Step 5: 测试 XSS 防护 =====
        xss_test = await page.evaluate("""
            (() => {
                const result = {};
                if (typeof esc !== 'function') {
                    result.error = 'esc is not defined!';
                    return result;
                }
                const input = '<script>alert(1)</script>';
                const output = esc(input);
                result.input = input;
                result.output = output;
                result.encoded_lt = output.includes('&lt;');
                result.encoded_gt = output.includes('&gt;');
                result.raw_script = output.includes('<script>');
                return result;
            })()
        """)
        if "error" in xss_test:
            issues.append(f"✗ XSS 测试失败: {xss_test['error']}")
        elif not xss_test.get("encoded_lt"):
            issues.append(f"❌ XSS 严重: {xss_test}")
        elif xss_test.get("raw_script"):
            issues.append(f"❌ XSS 严重: raw <script> 未转义: {xss_test}")
        else:
            passed.append(f"✓ XSS 防护 OK: {xss_test['output']}")

        # ===== Step 6: 移动端视口测试 =====
        await page.set_viewport_size({"width": 375, "height": 812})
        await page.wait_for_timeout(200)
        shot5 = SHOTS_DIR / "05_mobile.png"
        await page.screenshot(path=str(shot5), full_page=True)
        # 检查移动端是否正常
        h1_visible = await page.locator("h1").is_visible()
        if h1_visible:
            passed.append("✓ 移动端视口 h1 可见")
        else:
            issues.append("✗ 移动端 h1 不可见")

        # ===== Step 7: console 错误检查 =====
        await page.set_viewport_size({"width": 1280, "height": 900})
        await page.wait_for_timeout(200)
        if console_errors:
            # 截 console 错误时的图
            shot6 = SHOTS_DIR / "06_console_error.png"
            await page.screenshot(path=str(shot6), full_page=True)
            for e in console_errors[:5]:
                issues.append(f"⚠ Console 错误: {e}")
        else:
            passed.append("✓ 无 console 错误")

        # ===== Step 8: 缩放/截全图 =====
        shot_full = SHOTS_DIR / "00_full_page.png"
        await page.screenshot(path=str(shot_full), full_page=True)

        await browser.close()

    # 写报告
    report = SHOTS_DIR / "REPORT.md"
    with open(report, "w", encoding="utf-8") as f:
        f.write("# HELP Playwright 端到端验证报告\n\n")
        f.write(f"## 截图清单\n\n")
        for shot in sorted(SHOTS_DIR.glob("*.png")):
            f.write(f"- `{shot.name}` ({shot.stat().st_size} bytes)\n")
        f.write(f"\n## 通过项 ({len(passed)})\n\n")
        for p in passed:
            f.write(f"- {p}\n")
        f.write(f"\n## 问题项 ({len(issues)})\n\n")
        for i in issues:
            f.write(f"- {i}\n")
    print(f"\n=== REPORT WRITTEN: {report} ===\n")
    print(f"passed: {len(passed)}, issues: {len(issues)}")
    if issues:
        print("\nISSUES:")
        for i in issues:
            print(f"  - {i}")
    return issues, [str(p) for p in SHOTS_DIR.glob("*.png")]


if __name__ == "__main__":
    issues, shots = asyncio.run(run())
    sys.exit(0 if not issues else 1)

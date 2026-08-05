# -*- coding: utf-8 -*-
"""HTML 双浏览器审查(G6 #63 技术 · 跨技能通用工具)

桌面窗口 1280x900(电脑)+ 手机窗口 390x844(is_mobile + has_touch,触发移动端渲染)
同一 HTML 双窗口同时打开,用户一眼对比桌面/手机呈现。任何技能生成的 HTML 均可审查。

- 每 5 秒客观测量一次(横向溢出 / 场景数 / 模块数 / 初始化横幅),结束时报汇总
- 捕获 JS 报错与 console 错误
- 用户审完直接关掉两个窗口 → 脚本自动结束,报告写入报告文件
- 最长 20 分钟兜底

用法:
    python 双浏览器审查.py <html路径> [报告路径]
    例:python 双浏览器审查.py "D:/.../居家管家_HELP_20260805_193000.html"
        python 双浏览器审查.py "D:/.../home.html" "D:/.../我的审查报告.txt"
    (报告路径省略时,默认写到 HTML 同目录下的 <文件名>.审查报告.txt)
"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

if len(sys.argv) < 2:
    print("用法: python 双浏览器审查.py <html路径> [报告路径]")
    sys.exit(1)

HTML = Path(sys.argv[1])
if not HTML.exists():
    print(f"HTML 不存在: {HTML}")
    sys.exit(1)
LOG_FILE = Path(sys.argv[2]) if len(sys.argv) > 2 else HTML.with_name(HTML.stem + ".审查报告.txt")
URL = HTML.resolve().as_uri()
MAX_SECONDS = 20 * 60


def log(msg):
    print(msg, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")


def measure(page):
    try:
        return page.evaluate("""() => {
          const de = document.documentElement;
          return {
            scrollW: de.scrollWidth, clientW: de.clientWidth,
            overflow: de.scrollWidth > de.clientWidth + 1,
            scenes: document.querySelectorAll('.scene').length,
            modules: document.querySelectorAll('.module').length,
            subs: document.querySelectorAll('.sub-module').length,
            cards: document.querySelectorAll('details').length
          };
        }""")
    except Exception:
        return None


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False)
        errors = []
        reports = {"桌面": {}, "手机": {}}
        state = {"d": True, "m": True}

        desktop_ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        mobile_ctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True, has_touch=True, user_agent=MOBILE_UA,
            device_scale_factor=2,
        )

        d_page = desktop_ctx.new_page()
        d_page.on("pageerror", lambda e: errors.append(f"[桌面] JS 报错: {e}"))
        d_page.on("console", lambda m: errors.append(f"[桌面] console.{m.type}: {m.text}")
                  if m.type in ("error", "warning") else None)
        d_page.on("close", lambda: state.update(d=False))

        m_page = mobile_ctx.new_page()
        m_page.on("pageerror", lambda e: errors.append(f"[手机] JS 报错: {e}"))
        m_page.on("console", lambda m: errors.append(f"[手机] console.{m.type}: {m.text}")
                  if m.type in ("error", "warning") else None)
        m_page.on("close", lambda: state.update(m=False))

        d_page.goto(URL)
        m_page.goto(URL)
        d_page.wait_for_timeout(800)
        m_page.wait_for_timeout(800)

        log(f"URL: {URL}")
        log("双窗口已打开:窗口 1 = 电脑 1280x900 · 窗口 2 = 手机 390x844(触屏)")
        log("审完关闭两个窗口即自动结束,报告写入 " + str(LOG_FILE))
        sys.stdout.flush()

        start = time.time()
        while (state["d"] or state["m"]) and (time.time() - start) < MAX_SECONDS:
            for name, page in (("桌面", d_page), ("手机", m_page)):
                data = measure(page)
                if data:
                    reports[name]["B"] = data
            time.sleep(5)

        log("---- 最终测量报告 ----")
        all_ok = True
        for name in ("桌面", "手机"):
            data = reports[name].get("B")
            if not data:
                continue
            flag = "PASS" if not data["overflow"] else "FAIL"
            if data["overflow"]:
                all_ok = False
            print(f"[{name}] 域={data['modules']} 子功能={data['subs']} 场景={data['scenes']} "
                  f"details={data['cards']} 横向溢出={data['overflow']} "
                  f"(scrollW={data['scrollW']} clientW={data['clientW']}) {flag}")
        if errors:
            all_ok = False
            log("---- 审查期间捕获 ----")
            for e in errors:
                log(e)
        else:
            log("无 JS 报错 / console 错误")
        log("结论: " + ("PASS(无横向溢出,无 JS 报错)" if all_ok else "FAIL(见上)"))

        try:
            desktop_ctx.close()
        except Exception:
            pass
        try:
            mobile_ctx.close()
        except Exception:
            pass
        browser.close()


if __name__ == "__main__":
    main()

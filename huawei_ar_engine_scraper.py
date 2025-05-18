from playwright.sync_api import sync_playwright
from markdownify import markdownify as md
import os

url = "https://developer.huawei.com/consumer/cn/doc/harmonyos-references/ar-engine-overview"

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"正在导航到: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000) # 增加超时并等待DOM加载
        print("页面DOM加载完成")

        # 尝试更通用的选择器或直接获取body内容
        # 首先尝试之前使用的选择器，但增加等待时间
        try:
            page.wait_for_selector("div.doc-content", timeout=30000) # 增加等待时间
            main_content_html = page.locator("div.doc-content").inner_html()
            print("通过 'div.doc-content' 获取到内容")
        except Exception:
            print("'div.doc-content' 未找到或超时，尝试获取整个body内容")
            # 如果特定选择器失败，尝试获取整个 body 的 HTML
            # 等待 body 元素确保页面已基本加载
            page.wait_for_selector("body", timeout=30000)
            main_content_html = page.locator("body").inner_html()
            print("已获取整个body的HTML内容")

        if main_content_html:
            markdown_content = md(main_content_html)
            markdown_content = os.linesep.join([s for s in markdown_content.splitlines() if s.strip()])

            file_name = "ar-engine-overview.md"
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            print(f"成功抓取内容并保存到 {file_name}")
            print(f"Markdown文件大小: {len(markdown_content)} 字符")
        else:
            print("未能获取到任何HTML内容")
            
        browser.close()
        print("浏览器已关闭")

except Exception as e:
    print(f"发生错误: {e}")
    if 'browser' in locals() and browser.is_connected():
        browser.close()
        print("发生错误后，浏览器已关闭")

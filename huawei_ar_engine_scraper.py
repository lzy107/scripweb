from playwright.sync_api import sync_playwright
from markdownify import markdownify as md
import os
import re

def scrape_url(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            print(f"正在导航到: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)  # 增加超时并等待DOM加载
            print("页面DOM加载完成")

            # 尝试更通用的选择器或直接获取body内容
            # 首先尝试之前使用的选择器，但增加等待时间
            try:
                page.wait_for_selector("div.doc-content", timeout=30000)  # 增加等待时间
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

                # 从URL中提取文件名
                file_name = url.split('/')[-1]
                if not file_name.endswith('.md'):
                    file_name = file_name + ".md"
                
                with open(file_name, "w", encoding="utf-8") as f:
                    f.write(markdown_content)

                print(f"成功抓取内容并保存到 {file_name}")
                print(f"Markdown文件大小: {len(markdown_content)} 字符")
            else:
                print("未能获取到任何HTML内容")
                
            browser.close()
            print("浏览器已关闭")
            return True

    except Exception as e:
        print(f"发生错误: {e}")
        if 'browser' in locals() and browser.is_connected():
            browser.close()
            print("发生错误后，浏览器已关闭")
        return False

def update_config_status(config_file, url, new_status):
    """
    更新配置文件中指定URL的状态
    """
    # 读取配置文件内容
    with open(config_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # 修改对应URL的状态
    updated_lines = []
    for line in lines:
        if url in line:
            # 使用@作为分隔符替换状态部分
            parts = line.split("@")
            if len(parts) >= 1:
                updated_line = parts[0] + f"@{new_status}\n"
                updated_lines.append(updated_line)
                print(f"已将URL {url} 的状态更新为: {new_status}")
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)
    
    # 写回配置文件
    with open(config_file, "w", encoding="utf-8") as f:
        f.writelines(updated_lines)

def main():
    config_file = "config.txt"
    
    # 检查配置文件是否存在
    if not os.path.exists(config_file):
        print(f"错误：找不到配置文件 {config_file}")
        return
    
    # 读取配置文件
    with open(config_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        try:
            # 使用正则表达式匹配URL和状态，使用@作为分隔符
            match = re.match(r'(https?://[^\s@]+)@(yes|no)', line)
            if match:
                url = match.group(1)
                status = match.group(2)
                
                if status.lower() == "yes":
                    print(f"跳过URL: {url}，配置为: {status}")
                    continue
                elif status.lower() == "no":
                    print(f"处理URL: {url}，配置为: {status}")
                    success = scrape_url(url)
                    
                    # 如果成功处理了URL，则更新配置文件中的状态
                    if success:
                        update_config_status(config_file, url, "yes")
                else:
                    print(f"无效的状态值: {status}，应为 'yes' 或 'no'")
            else:
                print(f"无效的配置行: {line}")
        except Exception as e:
            print(f"处理配置行时出错: {line}")
            print(f"错误信息: {e}")

if __name__ == "__main__":
    main()

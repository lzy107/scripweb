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
                
                # 使用正则表达式查找"展开章节"位置，只保留该位置之后的内容
                content_start_pattern = r"展开章节"
                match = re.search(content_start_pattern, markdown_content)
                if match:
                    start_index = match.start()
                    # 只保留从"展开章节"开始的内容
                    markdown_content = markdown_content[start_index:]
                    print(f"已找到实际内容起始位置，过滤前{start_index}个字符")
                else:
                    print("未找到内容起始标记'展开章节'，保留全部内容")
                
                # 删除空行
                markdown_content = os.linesep.join([s for s in markdown_content.splitlines() if s.strip()])

                # 确保docs目录存在
                docs_dir = "docs"
                if not os.path.exists(docs_dir):
                    os.makedirs(docs_dir)
                    print(f"创建目录: {docs_dir}")

                # 从URL中提取文件名
                file_name = url.split('/')[-1]
                if not file_name.endswith('.md'):
                    file_name = file_name + ".md"
                
                # 设置文件保存路径到docs子目录
                file_path = os.path.join(docs_dir, file_name)
                
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(markdown_content)

                print(f"成功抓取内容并保存到 {file_path}")
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
            # 去除可能存在的旧状态标记
            line_without_status = re.sub(r'@(yes|no).*$', '', line.strip())
            # 添加新状态标记
            updated_line = f"{line_without_status}@{new_status}\n"
            updated_lines.append(updated_line)
            print(f"已将URL {url} 的状态更新为: {new_status}")
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
            # 检查行是否包含URL
            url_match = re.search(r'(https?://[^\s]+)', line)
            if not url_match:
                print(f"无效的配置行，未找到URL: {line}")
                continue
                
            url = url_match.group(1)
            
            # 检查是否明确标记为yes
            if "@yes" in line:
                print(f"跳过URL: {url}，配置为: yes")
                continue
            
            # 处理URL（无论是否标记为no或没有标记）
            print(f"处理URL: {url}")
            success = scrape_url(url)
            
            # 如果成功处理了URL，则更新配置文件中的状态
            if success:
                update_config_status(config_file, url, "yes")
            
        except Exception as e:
            print(f"处理配置行时出错: {line}")
            print(f"错误信息: {e}")

if __name__ == "__main__":
    main()

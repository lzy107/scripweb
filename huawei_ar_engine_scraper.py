from playwright.sync_api import sync_playwright
from markdownify import markdownify as md
import os
import re
import datetime

def scrape_url(url):
    # 确保URL不包含@yes或@no部分
    url = re.sub(r'@(yes|no).*$', '', url)
    
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
                
                # 定义可能的内容起始标记，按优先级排序
                possible_markers = [
                    "展开章节",
                    "本文导读",
                    "导入模块"
                ]
                
                # 尝试查找任何一个标记
                found_marker = False
                for marker in possible_markers:
                    match = re.search(marker, markdown_content)
                    if match:
                        start_index = match.start()
                        # 只保留从标记位置开始的内容
                        markdown_content = markdown_content[start_index:]
                        print(f"已找到实际内容起始位置('{marker}')，过滤前{start_index}个字符")
                        found_marker = True
                        break
                
                if not found_marker:
                    print(f"未找到任何内容起始标记{possible_markers}，保留全部内容")
                
                # 删除空行
                markdown_content = os.linesep.join([s for s in markdown_content.splitlines() if s.strip()])

                # 确保docs目录存在
                docs_dir = "docs"
                if not os.path.exists(docs_dir):
                    os.makedirs(docs_dir)
                    print(f"创建目录: {docs_dir}")

                # 从URL中提取文件名，确保不包含@yes或@no部分
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
                file_path = None
                
            browser.close()
            print("浏览器已关闭")
            return file_path  # 返回创建的文件路径，如果失败则返回None

    except Exception as e:
        print(f"发生错误: {e}")
        if 'browser' in locals() and browser.is_connected():
            browser.close()
            print("发生错误后，浏览器已关闭")
        return None

def update_config_status(config_file, url, new_status):
    """
    更新配置文件中指定URL的状态，保留特殊标记行
    """
    # 读取配置文件内容
    with open(config_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # 修改对应URL的状态
    updated_lines = []
    for line in lines:
        line_stripped = line.strip()
        # 保留特殊标记行(#begin::和#end::)和注释行
        if line_stripped.startswith('#'):
            updated_lines.append(line)
            continue
            
        if url in line:
            # 去除可能存在的旧状态标记
            line_without_status = re.sub(r'@(yes|no).*$', '', line_stripped)
            # 添加新状态标记
            updated_line = f"{line_without_status}@{new_status}\n"
            updated_lines.append(updated_line)
            print(f"已将URL {url} 的状态更新为: {new_status}")
        else:
            updated_lines.append(line)
    
    # 写回配置文件
    with open(config_file, "w", encoding="utf-8") as f:
        f.writelines(updated_lines)

def combine_markdown_files(file_paths, output_file_path):
    """
    合并多个markdown文件内容到一个文件中
    
    Args:
        file_paths: 要合并的markdown文件路径列表
        output_file_path: 输出的合并文件路径
    """
    combined_content = []
    successful_files = 0
    
    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # 添加文件名作为标题
                    file_name = os.path.basename(file_path)
                    header = f"\n\n## {file_name}\n\n"
                    
                    # 添加分隔线
                    divider = "\n\n" + "-" * 80 + "\n\n"
                    
                    combined_content.append(header + content + divider)
                    successful_files += 1
            except Exception as e:
                print(f"合并文件时出错 '{file_path}': {e}")
        else:
            print(f"警告: 文件不存在或路径无效: {file_path}")
    
    if combined_content:
        # 添加合并文件的标题和信息
        title = os.path.basename(output_file_path)
        header = f"# {title}\n\n"
        timestamp = f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        info = f"本文件包含 {successful_files} 个markdown文件的合并内容。\n\n"
        
        # 写入合并文件
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(header + timestamp + info + "".join(combined_content))
        print(f"成功合并 {successful_files} 个文件到 {output_file_path}")
        return True
    else:
        print("没有找到要合并的文件")
        return False

def main():
    config_file = "config.txt"
    
    # 检查配置文件是否存在
    if not os.path.exists(config_file):
        print(f"错误：找不到配置文件 {config_file}")
        return
    
    # 读取配置文件
    with open(config_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # 初始化变量，用于跟踪#begin::#end区域
    in_group = False
    group_name = ""
    group_files = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        try:
            # 检查是否是#begin::标记
            begin_match = re.match(r'#begin::\s*(\S+)', line)
            if begin_match:
                group_name = begin_match.group(1)
                in_group = True
                group_files = []
                print(f"开始处理文件组: {group_name}")
                continue
                
            # 检查是否是#end::标记
            end_match = re.match(r'#end::\s*(\S+)', line)
            if end_match:
                end_group_name = end_match.group(1)
                if in_group and end_group_name == group_name:
                    # 检查是否有文件需要合并
                    if group_files:
                        docs_dir = "docs"
                        combined_file = os.path.join(docs_dir, f"combined--{group_name}.md")
                        
                        # 检查合并文件是否已存在
                        if os.path.exists(combined_file):
                            print(f"合并文件已存在: {combined_file}，跳过合并过程")
                        else:
                            combine_markdown_files(group_files, combined_file)
                    
                    # 重置状态
                    in_group = False
                    group_name = ""
                    group_files = []
                    print(f"结束处理文件组: {end_group_name}")
                continue
            
            # 跳过注释行
            if line.startswith('#'):
                continue
                
            # 检查行是否包含URL
            url_match = re.search(r'(https?://[^\s@]+)', line)
            if not url_match:
                print(f"无效的配置行，未找到URL: {line}")
                continue
                
            url = url_match.group(1)
            
            # 从URL中提取文件名，确保不包含@yes或@no部分
            file_name = url.split('/')[-1]
            if not file_name.endswith('.md'):
                file_name = file_name + ".md"
            docs_dir = "docs"
            file_path = os.path.join(docs_dir, file_name)
            
            # 检查是否明确标记为yes
            if "@yes" in line:
                print(f"URL已处理: {url}，配置为: yes")
                
                # 如果在组内且该URL已经处理过，检查是否存在对应的markdown文件
                if in_group:
                    if os.path.exists(file_path):
                        print(f"找到已存在的markdown文件: {file_path}")
                        group_files.append(file_path)
                    else:
                        print(f"警告: 标记为@yes但未找到对应的markdown文件: {file_path}")
                        
                continue
            
            # 处理URL（无论是否标记为no或没有标记）
            print(f"处理URL: {url}")
            processed_file_path = scrape_url(url)
            
            # 如果在组内且成功抓取了文件，添加到组文件列表
            if in_group and processed_file_path:
                group_files.append(processed_file_path)
            
            # 如果成功处理了URL，则更新配置文件中的状态
            if processed_file_path:
                update_config_status(config_file, url, "yes")
            
        except Exception as e:
            print(f"处理配置行时出错: {line}")
            print(f"错误信息: {e}")

if __name__ == "__main__":
    main()

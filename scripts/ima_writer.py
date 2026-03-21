#!/usr/bin/env python3
"""
IMA Note Writer for Macro Economic Data
复用到 macro-archiver 的缓存和日期识别逻辑，输出到 IMA 笔记
"""

import json
import os
import sys
import hashlib
from datetime import datetime

# 国家笔记本映射（从 list_note_folder_by_cursor 获取）
COUNTRY_FOLDERS = {
    "US": "folder6fd7dfe4c3d88488",
    "China": "folder22193d7fb7e55cc8",
    "Japan": "folder8e94e3efca419294",
    "EuroArea": "folder653cfbe69cd7475b",
    "Bangladesh": "folder8356d626be25a385",
    "SouthAfrica": "folder33c2f9d193273d27",
    "Global": "folder693ab9c25455821f"
}

# 本地存储根目录
LOCAL_STORAGE_ROOT = os.path.expanduser("~/workspace/macro_data")

def get_ima_credentials():
    """获取 IMA API 凭证"""
    client_id = os.environ.get('IMA_OPENAPI_CLIENTID')
    api_key = os.environ.get('IMA_OPENAPI_APIKEY')
    
    if not client_id or not api_key:
        print("❌ 缺少 IMA 凭证，请配置环境变量:")
        print("   export IMA_OPENAPI_CLIENTID='your_client_id'")
        print("   export IMA_OPENAPI_APIKEY='your_api_key'")
        print("获取地址：https://ima.qq.com/agent-interface")
        sys.exit(1)
    
    return client_id, api_key

def ima_api_call(endpoint, body):
    """调用 IMA API"""
    import urllib.request
    import urllib.error
    
    client_id, api_key = get_ima_credentials()
    
    url = f"https://ima.qq.com/openapi/note/v1/{endpoint}"
    headers = {
        'ima-openapi-clientid': client_id,
        'ima-openapi-apikey': api_key,
        'Content-Type': 'application/json'
    }
    
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"❌ API 请求失败：{e.code} {e.reason}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 请求错误：{e}")
        sys.exit(1)

def list_note_folders():
    """列出所有笔记本，获取 folder_id"""
    result = ima_api_call("list_note_folder_by_cursor", {
        "cursor": "0",
        "limit": 20
    })
    
    if result.get('code') == 0 or result.get('is_end') is not None:
        folders = result.get('note_book_folders', [])
        folder_map = {}
        for item in folders:
            folder_info = item.get('folder', {}).get('basic_info', {})
            folder_id = folder_info.get('folder_id')
            folder_name = folder_info.get('name')
            if folder_id and folder_name:
                folder_map[folder_name] = folder_id
        return folder_map
    return {}

def search_note(title):
    """搜索笔记"""
    result = ima_api_call("search_note_book", {
        "search_type": 0,
        "query_info": {"title": title},
        "start": 0,
        "end": 20
    })
    
    if result.get('code') == 0 and result.get('docs'):
        return result['docs'][0]['doc']['basic_info']
    return None

def create_note(content, title=None, folder_id=None):
    """新建笔记
    
    Args:
        content: 笔记内容
        title: 笔记标题（可选，从内容第一行提取）
        folder_id: 笔记本 ID（可选，指定存储位置）
    """
    body = {
        "content_format": 1,  # Markdown
        "content": content
    }
    
    # 如果指定了 folder_id，添加到请求中
    if folder_id:
        body["folder_id"] = folder_id
    
    result = ima_api_call("import_doc", body)
    
    if result.get('code') == 0:
        return result.get('doc_id')
    else:
        print(f"❌ 创建笔记失败：{result}")
        return None

def append_note(doc_id, content):
    """追加内容到笔记"""
    result = ima_api_call("append_doc", {
        "doc_id": doc_id,
        "content_format": 1,  # Markdown
        "content": content
    })
    
    if result.get('code') == 0:
        return True
    else:
        print(f"❌ 追加内容失败：{result}")
        return False

def format_macro_data(country, indicator, year, data_entries):
    """
    格式化宏观经济数据为 Markdown
    
    Args:
        country: 国家代码 (US, China, etc.)
        indicator: 指标名称 (PMI, GDP, etc.)
        year: 年份
        data_entries: 数据条目列表，每项为 {'sub_indicator': 'Composite PMI', 'month': 'YYYY-MM', 'content': '...'}
                      如果 sub_indicator 为空，则直接写入内容
    """
    markdown = f"# {country} - {indicator} - {year}\n\n"
    markdown += f"## 📊 {indicator}\n\n"
    
    # 按子指标分组
    sub_indicators = {}
    for entry in data_entries:
        sub = entry.get('sub_indicator', '')
        if sub not in sub_indicators:
            sub_indicators[sub] = []
        sub_indicators[sub].append(entry)
    
    # 遍历每个子指标
    for sub_name, entries in sub_indicators.items():
        # 如果有子指标名称，添加标题
        if sub_name:
            markdown += f"### {sub_name}\n\n"
        
        # 写入该子指标的所有月份数据
        for entry in entries:
            month = entry.get('month', 'Unknown')
            content = entry.get('content', '')
            markdown += f"**{month}**. {content}\n\n"
    
    markdown += "---\n\n"
    markdown += f"*数据来源：Trading Economics | 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}*\n"
    markdown += f"*国家：{country} | 指标：{indicator} | 年份：{year}*"
    
    return markdown

def save_to_local(country, indicator, year, content, append_mode=True):
    """
    保存数据到本地文件系统
    
    Args:
        country: 国家代码 (US, China, etc.)
        indicator: 指标名称 (PMI, GDP, etc.)
        year: 年份
        content: 要写入的内容
        append_mode: True=追加模式，False=创建新文件
    """
    # 确保国家文件夹存在
    country_folder = os.path.join(LOCAL_STORAGE_ROOT, country)
    os.makedirs(country_folder, exist_ok=True)
    
    # 确定文件路径
    file_path = os.path.join(country_folder, f"{indicator}.md")
    
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    if append_mode and os.path.exists(file_path):
        # 追加模式：直接在文件末尾添加内容
        with open(file_path, 'a', encoding='utf-8') as f:
            # 添加更新时间和分隔符
            separator = "\n\n---\n\n## 更新时间：" + now_str + "\n\n"
            f.write(separator)
            f.write(content)
        print(f"✅ 数据已追加到本地文件：{file_path}")
    else:
        # 创建模式：写入完整文档结构
        header = f"# {country} - {indicator}\n\n## 📊 {indicator}\n\n"
        footer = f"\n\n---\n*数据来源：Trading Economics | 更新时间：{now_str}*\n*国家：{country} | 指标：{indicator} | 年份：{year}*"
        full_content = header + content + footer
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        print(f"✅ 已创建本地文件：{file_path}")
    
    return file_path

def write_to_ima(country, indicator, year, data_entries, append_mode=True):
    """
    写入数据到 IMA 笔记
    
    Args:
        country: 国家代码
        indicator: 指标名称
        year: 年份
        data_entries: 数据条目列表
        append_mode: 是否追加模式（True=追加，False=新建）
    """
    note_title = f"{country} - {indicator} - {year}"
    
    # 获取国家笔记本 folder_id
    folder_id = COUNTRY_FOLDERS.get(country)
    if not folder_id:
        # 尝试动态获取
        folders = list_note_folders()
        folder_id = folders.get(country)
        
        if not folder_id:
            print(f"⚠️ 警告：未找到 '{country}' 笔记本，将创建到默认位置")
            print(f"   可用笔记本：{list(folders.keys())}")
    
    # 搜索是否已有笔记
    existing_note = search_note(note_title)
    
    if existing_note and append_mode:
        # 找到已有笔记，追加新数据
        doc_id = existing_note['docid']
        print(f"✓ 找到已有笔记：{note_title} (doc_id: {doc_id})")
        
        # 格式化新数据
        new_content = "\n\n---\n\n## 最新数据\n\n"
        for entry in data_entries:
            month = entry.get('month', 'Unknown')
            content = entry.get('content', '')
            new_content += f"**{month}**. {content}\n\n"
        
        # 追加内容
        if append_note(doc_id, new_content):
            print(f"✅ 数据已追加到 IMA 笔记：{note_title}")
            # 同步保存到本地（append 模式）
            save_to_local(country, indicator, year, new_content, append_mode=True)
            return doc_id
        else:
            return None
    else:
        # 未找到笔记或新建模式，创建新笔记
        print(f"ℹ 未找到已有笔记，将创建新笔记：{note_title}")
        
        # 格式化完整内容
        full_content = format_macro_data(country, indicator, year, data_entries)
        
        # 创建笔记（指定 folder_id）
        doc_id = create_note(full_content, note_title, folder_id)
        if doc_id:
            print(f"✅ 已创建 IMA 笔记：{note_title} (doc_id: {doc_id})")
            # 同步保存到本地
            save_to_local(country, indicator, year, full_content, append_mode=False)
            return doc_id
        else:
            return None

def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法：python3 ima_writer.py <command> [args]")
        print("命令:")
        print("  search <title>           搜索笔记")
        print("  create <content_file>    从文件创建笔记")
        print("  append <doc_id> <content_file>  追加内容到笔记")
        print("  test                     测试 API 连通性")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "test":
        # 测试 API 连通性
        result = ima_api_call("list_note_folder_by_cursor", {
            "cursor": "0",
            "limit": 1
        })
        if result.get('code') == 0:
            print("✅ IMA API 连通性测试通过")
        else:
            print(f"❌ IMA API 测试失败：{result}")
            sys.exit(1)
    
    elif command == "search":
        if len(sys.argv) < 3:
            print("❌ 请提供搜索关键词")
            sys.exit(1)
        title = sys.argv[2]
        result = search_note(title)
        if result:
            print(f"找到笔记:")
            print(f"  标题：{result.get('title')}")
            print(f"  doc_id: {result.get('docid')}")
            print(f"  文件夹：{result.get('folder_name')}")
        else:
            print("未找到匹配的笔记")
    
    elif command == "create":
        if len(sys.argv) < 3:
            print("❌ 请提供内容文件路径")
            sys.exit(1)
        content_file = sys.argv[2]
        with open(content_file, 'r', encoding='utf-8') as f:
            content = f.read()
        doc_id = create_note(content)
        if doc_id:
            print(f"✅ 笔记已创建，doc_id: {doc_id}")
        else:
            sys.exit(1)
    
    elif command == "append":
        if len(sys.argv) < 4:
            print("❌ 请提供 doc_id 和内容文件路径")
            sys.exit(1)
        doc_id = sys.argv[2]
        content_file = sys.argv[3]
        with open(content_file, 'r', encoding='utf-8') as f:
            content = f.read()
        if append_note(doc_id, content):
            print(f"✅ 内容已追加到笔记 {doc_id}")
        else:
            sys.exit(1)
    
    else:
        print(f"❌ 未知命令：{command}")
        sys.exit(1)

if __name__ == "__main__":
    main()

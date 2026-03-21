#!/usr/bin/env python3
"""
Feishu Wiki Hierarchy Manager for macro economic data archiver.
Creates and manages parent-child document relationships in JVS knowledge base.
"""

import json
from pathlib import Path

# JVS Knowledge Base configuration
JVS_SPACE_ID = "7618982188336876498"
MACRO_INDEX_NODE_TOKEN = "Nku3wbMnTigBAikD0wAcj5bLnZe"  # "Macro - 宏观经济数据索引"

def get_parent_doc_title(country: str, year: int) -> str:
    """Get parent document title."""
    return f"{country} - {year}"

def get_child_doc_title(country: str, indicator: str, year: int) -> str:
    """Get child document title."""
    return f"{country} - {indicator} - {year}"

def generate_index_template(country: str, year: int, indicator_hierarchy: dict) -> str:
    """
    Generate index document template with indicator hierarchy.
    
    Args:
        country: Country name (US, China, etc.)
        year: Year (2026, 2027, etc.)
        indicator_hierarchy: Dict from indicator-hierarchy.json
    
    Returns:
        Markdown template for index document
    """
    template = f"# {country} - {year}\n\n"
    template += f"## 📊 经济指标数据\n\n"
    template += f"*宏观经济数据按指标分类，点击指标名称查看详情。*\n\n"
    template += "---\n\n"
    
    for category, info in indicator_hierarchy.items():
        display_name = info.get('display_name', category)
        sub_indicators = info.get('sub_indicators', [])
        
        if info['type'] == 'single':
            # Single indicator (no sub-indicators)
            link_text = f"[{display_name}](#{display_name.lower().replace(' ', '-')})"
            template += f"### {display_name}\n- {link_text}\n\n"
        else:
            # Group with sub-indicators
            template += f"### {display_name}\n\n"
            for sub in sub_indicators:
                link_text = f"[{sub}](#{sub.lower().replace(' ', '-').replace('&', '')})"
                template += f"- {link_text}\n"
            template += "\n"
    
    template += "---\n\n"
    template += f"*最后更新：{year}-03-20*\n"
    
    return template

def generate_child_doc_template(country: str, indicator: str, year: int) -> str:
    """
    Generate child document template.
    
    Args:
        country: Country name
        indicator: Indicator name
        year: Year
    
    Returns:
        Markdown template for child document
    """
    template = f"# {country} - {indicator} - {year}\n\n"
    template += f"## {indicator}\n\n"
    template += f"*数据来源：Trading Economics*\n\n"
    template += "---\n\n"
    
    return template

def update_index_with_links(index_content: str, child_links: dict, indicator_hierarchy: dict) -> str:
    """
    Update index document with actual child document links.
    
    Args:
        index_content: Current index document content
        child_links: Dict mapping indicator names to node tokens
                     e.g., {"PMI": "node_token_123", "GDP": "node_token_456"}
        indicator_hierarchy: Hierarchy definition
    
    Returns:
        Updated index content with working links
    """
    # For each indicator that has a child doc, update the link
    for indicator, node_token in child_links.items():
        # Feishu wiki link format
        wiki_link = f"https://www.feishu.cn/wiki/{node_token}"
        
        # Find and replace placeholder link
        # This is simplified - in practice, you'd parse the markdown properly
        placeholder = f"(#{indicator.lower().replace(' ', '-').replace('&', '')})"
        actual_link = f"({wiki_link})"
        
        index_content = index_content.replace(placeholder, actual_link)
    
    return index_content

# CLI usage
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: wiki_hierarchy.py <command> [args]")
        print("Commands:")
        print("  template <country> <year>        - Generate index template")
        print("  child <country> <indicator> <year> - Generate child template")
        print("  hierarchy                        - Show indicator hierarchy")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    # Load hierarchy
    hierarchy_file = Path(__file__).parent.parent / "references" / "indicator-hierarchy.json"
    indicator_hierarchy = json.load(open(hierarchy_file))
    
    if cmd == 'template':
        country, year = sys.argv[2], int(sys.argv[3])
        template = generate_index_template(country, year, indicator_hierarchy)
        print(template)
    
    elif cmd == 'child':
        country, indicator, year = sys.argv[2], sys.argv[3], int(sys.argv[4])
        template = generate_child_doc_template(country, indicator, year)
        print(template)
    
    elif cmd == 'hierarchy':
        print("Indicator Hierarchy:")
        for category, info in indicator_hierarchy.items():
            print(f"\n{category} ({info['type']}):")
            if info.get('sub_indicators'):
                for sub in info['sub_indicators']:
                    print(f"  - {sub}")

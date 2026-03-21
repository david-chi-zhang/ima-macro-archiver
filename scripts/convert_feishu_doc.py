#!/usr/bin/env python3
"""
Convert Feishu doc month headings to bold format.
### 2026-01 or #### 2026-02 → **2026-01**
"""
import re
import sys

def convert_to_bold(text):
    # Pattern 1: ### 2026-01 (3-4 hashes, YYYY-MM format)
    text = re.sub(r'^#{3,4}\s+(\d{4}-\d{2})\s*$', r'**\1**', text, flags=re.MULTILINE)
    # Pattern 2: #### 2026-02 (Non-Farm Payrolls) → **2026-02** (Non-Farm Payrolls)
    text = re.sub(r'^#{3,4}\s+(\d{4}-\d{2})\s*(\([^)]+\))?\s*$', r'**\1**\2', text, flags=re.MULTILINE)
    return text

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: convert_feishu_doc.py '<markdown text>'")
        sys.exit(1)
    
    text = ' '.join(sys.argv[1:])
    converted = convert_to_bold(text)
    print(converted)

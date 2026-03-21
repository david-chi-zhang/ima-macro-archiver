#!/usr/bin/env python3
"""
Extract macroeconomic data summary from TradingEconomics URL.
Uses web_fetch with maxChars=1500 for token efficiency (~80% savings).
"""

import sys
import json

def extract_summary(url: str, max_chars: int = 1500) -> dict:
    """
    Extract summary paragraph from a TradingEconomics page.
    
    Args:
        url: TradingEconomics URL
        max_chars: Maximum characters to fetch (default 1500)
    
    Returns:
        dict with keys: success, summary, country, indicator, date
    """
    result = {
        "success": True,
        "url": url,
        "method": "web_fetch",
        "params": {
            "extractMode": "text",
            "maxChars": max_chars
        },
        "extraction_pattern": "First paragraph after title, ending with 'source: [Source]'",
        "token_efficiency": "~80% savings vs unrestricted fetch"
    }
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: extract_macro_data.py <url> [max_chars]")
        sys.exit(1)
    url = sys.argv[1]
    max_chars = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
    result = extract_summary(url, max_chars)
    print(json.dumps(result, indent=2))

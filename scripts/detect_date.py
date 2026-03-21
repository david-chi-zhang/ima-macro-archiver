#!/usr/bin/env python3
"""
Detect date from macroeconomic summary text.
Returns YYYY-MM format.
"""

import re
import sys
from datetime import datetime, timedelta

MONTH_MAP = {
    'january': '01', 'february': '02', 'march': '03', 'april': '04',
    'may': '05', 'june': '06', 'july': '07', 'august': '08',
    'september': '09', 'october': '10', 'november': '11', 'december': '12',
    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
    'jun': '06', 'jul': '07', 'aug': '08', 'sep': '09',
    'oct': '10', 'nov': '11', 'dec': '12'
}

QUARTER_MONTH = {'Q1': '03', 'Q2': '06', 'Q3': '09', 'Q4': '12'}

def detect_date(text: str) -> str:
    """
    Detect date from summary text.
    Returns YYYY-MM format.
    """
    text_lower = text.lower()
    current_year = datetime.now().year
    
    # Pattern 1: "in February 2026" or "in Q4 2025"
    month_year_match = re.search(r'in\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})', text_lower)
    if month_year_match:
        month = MONTH_MAP.get(month_year_match.group(1))
        year = month_year_match.group(2)
        if month:
            return f"{year}-{month}"
    
    # Pattern 2: "in Q1/Q2/Q3/Q4 2025"
    quarter_year_match = re.search(r'in\s+(q1|q2|q3|q4)\s+(\d{4})', text_lower)
    if quarter_year_match:
        quarter = quarter_year_match.group(1).upper()
        year = quarter_year_match.group(2)
        month = QUARTER_MONTH.get(quarter)
        if month:
            return f"{year}-{month}"
    
    # Pattern 3: "February 2026" (without "in")
    month_year_match2 = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})', text_lower)
    if month_year_match2:
        month = MONTH_MAP.get(month_year_match2.group(1))
        year = month_year_match2.group(2)
        if month:
            return f"{year}-{month}"
    
    # Pattern 4: "in February" (no year, use current year)
    month_only_match = re.search(r'in\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b', text_lower)
    if month_only_match:
        month = MONTH_MAP.get(month_only_match.group(1))
        if month:
            return f"{current_year}-{month}"
    
    # Pattern 5: "February reading" or "February data"
    month_reading_match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(reading|data|release|report)', text_lower)
    if month_reading_match:
        month = MONTH_MAP.get(month_reading_match.group(1))
        if month:
            return f"{current_year}-{month}"
    
    # Pattern 6: ISO date "2026-02-15"
    iso_date_match = re.search(r'(\d{4})-(\d{2})-\d{2}', text)
    if iso_date_match:
        return f"{iso_date_match.group(1)}-{iso_date_match.group(2)}"
    
    # Pattern 7: "previous month" or "last month"
    if 'previous month' in text_lower or 'last month' in text_lower:
        last_month = datetime.now() - timedelta(days=30)
        return last_month.strftime('%Y-%m')
    
    # Fallback: return current month
    return datetime.now().strftime('%Y-%m')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: detect_date.py '<summary text>'")
        sys.exit(1)
    
    text = ' '.join(sys.argv[1:])
    detected = detect_date(text)
    print(detected)

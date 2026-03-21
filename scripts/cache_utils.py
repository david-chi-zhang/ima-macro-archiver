#!/usr/bin/env python3
"""
Cache utilities for macro economic data archiver.
Implements cache check, validation, and update with head-100-chars verification.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "temp" / "macro_cache"

def get_cache_path(country: str, indicator: str) -> Path:
    """Get cache file path for a country-indicator pair."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{country}_{indicator}.json"

def load_cache(country: str, indicator: str) -> dict | None:
    """Load cache if exists."""
    cache_path = get_cache_path(country, indicator)
    if cache_path.exists():
        with open(cache_path, 'r') as f:
            return json.load(f)
    return None

def save_cache(country: str, indicator: str, data: dict, head_100_chars: str):
    """Save data to cache with head-100-chars for validation."""
    cache_path = get_cache_path(country, indicator)
    cache = {
        "country": country,
        "indicator": indicator,
        "fetched_at": datetime.now().isoformat(),
        "head_100_chars": head_100_chars,
        "data": data
    }
    with open(cache_path, 'w') as f:
        json.dump(cache, f, indent=2)
    print(f"✅ Cache saved: {cache_path}")

def is_cache_fresh(cache: dict, max_age_hours: int = 24) -> bool:
    """Check if cache is fresh (within max_age_hours)."""
    fetched_at = datetime.fromisoformat(cache['fetched_at'])
    age = datetime.now() - fetched_at
    return age < timedelta(hours=max_age_hours)

def validate_cache(cache: dict, fresh_head: str) -> bool:
    """
    Validate cache by comparing head-100-chars.
    
    Args:
        cache: Loaded cache dict
        fresh_head: Freshly fetched first 100 chars from URL
    
    Returns:
        True if cache is valid (data unchanged), False if needs refresh
    """
    cached_head = cache.get('head_100_chars', '')
    
    # Normalize whitespace for comparison
    cached_head_norm = ' '.join(cached_head.split())
    fresh_head_norm = ' '.join(fresh_head.split())
    
    # Compare first 100 chars (normalized)
    is_valid = cached_head_norm[:100] == fresh_head_norm[:100]
    
    if is_valid:
        print(f"✅ Cache validated: Data unchanged, using cached data")
    else:
        print(f"⚠️  Cache stale: Data changed, will re-fetch")
    
    return is_valid

def get_or_fetch(country: str, indicator: str, url: str, web_fetch_func) -> tuple[dict, bool]:
    """
    Get data from cache or fetch fresh.
    
    Args:
        country: Country code (US, China, etc.)
        indicator: Indicator name (PMI, GDP, etc.)
        url: URL to fetch from
        web_fetch_func: Function to call for web fetching (signature: url, maxChars)
    
    Returns:
        tuple: (data_dict, used_cache_bool)
    """
    cache = load_cache(country, indicator)
    
    if cache and is_cache_fresh(cache):
        # Cache exists and is fresh, validate with head-100-chars
        print(f"📦 Cache found (age: {datetime.now() - datetime.fromisoformat(cache['fetched_at'])})")
        
        # Fetch first 100 chars for validation
        fresh_head = web_fetch_func(url, maxChars=100)
        
        if validate_cache(cache, fresh_head):
            return cache['data'], True
    
    # Cache miss or stale, fetch full data
    print(f"🌐 Fetching fresh data from {url}")
    full_data = web_fetch_func(url, maxChars=1500)
    
    # Save to cache
    save_cache(country, indicator, full_data, full_data[:100])
    
    return full_data, False

# CLI usage
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: cache_utils.py <command> [args]")
        print("Commands:")
        print("  check <country> <indicator>  - Check cache status")
        print("  clear <country> <indicator>  - Clear cache")
        print("  list                         - List all cached data")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'check':
        country, indicator = sys.argv[2], sys.argv[3]
        cache = load_cache(country, indicator)
        if cache:
            print(f"Cache for {country}_{indicator}:")
            print(f"  Fetched at: {cache['fetched_at']}")
            print(f"  Fresh: {is_cache_fresh(cache)}")
            print(f"  Head: {cache['head_100_chars'][:50]}...")
        else:
            print(f"No cache found for {country}_{indicator}")
    
    elif cmd == 'clear':
        country, indicator = sys.argv[2], sys.argv[3]
        cache_path = get_cache_path(country, indicator)
        if cache_path.exists():
            cache_path.unlink()
            print(f"✅ Cache cleared: {cache_path}")
        else:
            print(f"No cache to clear for {country}_{indicator}")
    
    elif cmd == 'list':
        if CACHE_DIR.exists():
            print("Cached data:")
            for f in CACHE_DIR.glob("*.json"):
                cache = json.load(open(f))
                print(f"  {f.stem}: {cache['fetched_at']}")
        else:
            print("No cache directory found")

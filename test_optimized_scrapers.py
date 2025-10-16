#!/usr/bin/env python3
"""
Test the optimized scraping approach based on your test results:
- StockTitan: Use requests (fast, reliable)
- HedgeFollow: Use Selenium (required for JavaScript)
"""

import sys
import time
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_optimized_approach():
    """Test the optimized scraping methods"""
    print("="*80)
    print("TESTING OPTIMIZED SCRAPING APPROACH")
    print("="*80)
    print("Based on your test results:")
    print("✓ StockTitan: requests + BeautifulSoup (0.36s response time)")
    print("✗ HedgeFollow: Selenium required (JavaScript content)")
    print("="*80)
    
    total_start_time = time.time()
    
    # Test optimized StockTitan (requests)
    print(f"\n1. Testing StockTitan with requests method...")
    try:
        from table_scrapers import scrape_stock_titan_requests
        
        st_start = time.time()
        recent_splits, all_splits = scrape_stock_titan_requests()
        st_end = time.time()
        
        print(f"✓ StockTitan SUCCESS:")
        print(f"  - Time: {st_end - st_start:.2f} seconds")
        print(f"  - Recent splits: {len(recent_splits)}")
        print(f"  - Total splits: {len(all_splits)}")
        print(f"  - Method: requests + BeautifulSoup")
        
        if recent_splits:
            print(f"  - Sample split: {recent_splits[0]['symbol']} - {recent_splits[0]['ratio']}")
        
    except Exception as e:
        print(f"✗ StockTitan FAILED: {e}")
    
    # Test HedgeFollow (Selenium)
    print(f"\n2. Testing HedgeFollow with Selenium method...")
    try:
        from table_scrapers import scrape_hedge_follow
        
        hf_start = time.time()
        future_splits, past_splits = scrape_hedge_follow()
        hf_end = time.time()
        
        print(f"✓ HedgeFollow SUCCESS:")
        print(f"  - Time: {hf_end - hf_start:.2f} seconds")
        print(f"  - Future splits: {len(future_splits)}")
        print(f"  - Past splits: {len(past_splits)}")
        print(f"  - Method: Selenium (required)")
        
        if future_splits:
            print(f"  - Sample split: {future_splits[0]['symbol']} - {future_splits[0]['ratio']}")
        
    except Exception as e:
        print(f"✗ HedgeFollow FAILED: {e}")
    
    # Test the smart fallback method
    print(f"\n3. Testing StockTitan with smart fallback...")
    try:
        from table_scrapers import scrape_stock_titan_with_fallback
        
        fb_start = time.time()
        recent_splits, all_splits = scrape_stock_titan_with_fallback()
        fb_end = time.time()
        
        print(f"✓ StockTitan Fallback SUCCESS:")
        print(f"  - Time: {fb_end - fb_start:.2f} seconds")
        print(f"  - Recent splits: {len(recent_splits)}")
        print(f"  - Total splits: {len(all_splits)}")
        print(f"  - Method: Smart fallback (requests → Selenium if needed)")
        
    except Exception as e:
        print(f"✗ StockTitan Fallback FAILED: {e}")
    
    total_end_time = time.time()
    
    print(f"\n{'='*80}")
    print("SUMMARY")
    print("="*80)
    print(f"Total test time: {total_end_time - total_start_time:.2f} seconds")
    print()
    print("✓ BENEFITS OF OPTIMIZED APPROACH:")
    print("  1. StockTitan is ~27x faster (0.36s vs ~10s with Selenium)")
    print("  2. Reduced Chrome browser usage (only for HedgeFollow)")
    print("  3. More reliable for StockTitan (no browser dependencies)")
    print("  4. Smart fallback ensures reliability")
    print()
    print("✓ RECOMMENDED USAGE:")
    print("  - Use scrape_stock_titan_requests() for StockTitan")
    print("  - Use scrape_hedge_follow() for HedgeFollow (Selenium required)")
    print("  - Use scrape_stock_titan_with_fallback() for maximum reliability")
    print()
    print("✓ TO IMPLEMENT IN YOUR MAIN CODE:")
    print("  Replace scrape_stock_titan() calls with scrape_stock_titan_with_fallback()")
    print("  This will give you the speed benefit with automatic fallback")


def compare_methods():
    """Compare the old vs new methods side by side"""
    print(f"\n{'='*80}")
    print("PERFORMANCE COMPARISON")
    print("="*80)
    
    # Test old Selenium method
    print(f"\nTesting ORIGINAL StockTitan (Selenium)...")
    try:
        from table_scrapers import scrape_stock_titan
        
        old_start = time.time()
        old_recent, old_all = scrape_stock_titan()
        old_end = time.time()
        old_time = old_end - old_start
        
        print(f"✓ Original method: {old_time:.2f}s, {len(old_recent)} recent, {len(old_all)} total")
        
    except Exception as e:
        print(f"✗ Original method failed: {e}")
        old_time = None
    
    # Test new requests method
    print(f"\nTesting NEW StockTitan (requests)...")
    try:
        from table_scrapers import scrape_stock_titan_requests
        
        new_start = time.time()
        new_recent, new_all = scrape_stock_titan_requests()
        new_end = time.time()
        new_time = new_end - new_start
        
        print(f"✓ New method: {new_time:.2f}s, {len(new_recent)} recent, {len(new_all)} total")
        
        if old_time and new_time:
            speedup = old_time / new_time
            print(f"\n🚀 SPEED IMPROVEMENT: {speedup:.1f}x faster!")
            print(f"   Old: {old_time:.2f}s → New: {new_time:.2f}s")
        
    except Exception as e:
        print(f"✗ New method failed: {e}")


if __name__ == "__main__":
    print(f"Optimized Scraper Test - {datetime.now()}")
    
    test_optimized_approach()
    compare_methods()
    
    print(f"\nTest completed at: {datetime.now()}")
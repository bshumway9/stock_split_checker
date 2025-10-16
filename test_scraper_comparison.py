#!/usr/bin/env python3
"""
Simple test script to compare Selenium vs requests scraping methods.
"""

import sys
import time
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_requests_method():
    """Test the requests-based scrapers"""
    print("="*60)
    print("TESTING REQUESTS + BEAUTIFULSOUP METHOD")
    print("="*60)
    
    try:
        from alternative_scrapers import scrape_hedge_follow_requests, scrape_stock_titan_requests
        
        # Test HedgeFollow
        print("\n1. Testing HedgeFollow (requests)...")
        start_time = time.time()
        try:
            splits, past_splits = scrape_hedge_follow_requests()
            end_time = time.time()
            print(f"✓ SUCCESS: {len(splits)} future splits, {len(past_splits)} past splits")
            print(f"✓ Time taken: {end_time - start_time:.2f} seconds")
            
            if splits:
                print("Sample future split:")
                sample = splits[0]
                print(f"  Symbol: {sample['symbol']}")
                print(f"  Ratio: {sample['ratio']}")
                print(f"  Date: {sample['effective_date']}")
                print(f"  Company: {sample['company']}")
                
        except Exception as e:
            print(f"✗ FAILED: {e}")
        
        # Test StockTitan
        print("\n2. Testing StockTitan (requests)...")
        start_time = time.time()
        try:
            recent_splits, all_splits = scrape_stock_titan_requests()
            end_time = time.time()
            print(f"✓ SUCCESS: {len(recent_splits)} recent splits, {len(all_splits)} total splits")
            print(f"✓ Time taken: {end_time - start_time:.2f} seconds")
            
            if recent_splits:
                print("Sample recent split:")
                sample = recent_splits[0]
                print(f"  Symbol: {sample['symbol']}")
                print(f"  Ratio: {sample['ratio']}")
                print(f"  Date: {sample['effective_date']}")
                print(f"  Title: {sample['title'][:80]}...")
                
        except Exception as e:
            print(f"✗ FAILED: {e}")
            
    except ImportError as e:
        print(f"✗ Could not import alternative scrapers: {e}")


def test_selenium_method():
    """Test the existing Selenium scrapers"""
    print("\n" + "="*60)
    print("TESTING SELENIUM METHOD (FOR COMPARISON)")
    print("="*60)
    
    try:
        from table_scrapers import scrape_hedge_follow, scrape_stock_titan
        
        # Test HedgeFollow Selenium
        print("\n1. Testing HedgeFollow (Selenium)...")
        start_time = time.time()
        try:
            splits, past_splits = scrape_hedge_follow()
            end_time = time.time()
            print(f"✓ SUCCESS: {len(splits)} future splits, {len(past_splits)} past splits")
            print(f"✓ Time taken: {end_time - start_time:.2f} seconds")
            
        except Exception as e:
            print(f"✗ FAILED: {e}")
        
        # Test StockTitan Selenium
        print("\n2. Testing StockTitan (Selenium)...")
        start_time = time.time()
        try:
            recent_splits, all_splits = scrape_stock_titan()
            end_time = time.time()
            print(f"✓ SUCCESS: {len(recent_splits)} recent splits, {len(all_splits)} total splits")
            print(f"✓ Time taken: {end_time - start_time:.2f} seconds")
            
        except Exception as e:
            print(f"✗ FAILED: {e}")
            
    except ImportError as e:
        print(f"✗ Could not import Selenium scrapers: {e}")


def main():
    print("Stock Split Scraper Comparison Test")
    print(f"Started at: {datetime.now()}")
    print("\nThis script compares requests+BeautifulSoup vs Selenium scraping methods")
    
    # Test requests method first (usually faster)
    test_requests_method()
    
    # Test Selenium method
    test_selenium_method()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("✓ requests + BeautifulSoup:")
    print("  - Faster and uses less memory")
    print("  - More reliable for simple HTML parsing")
    print("  - No browser dependencies")
    print("  - May not work if sites use heavy JavaScript")
    print()
    print("✓ Selenium:")
    print("  - Handles JavaScript-rendered content")
    print("  - More resource intensive")
    print("  - Requires Chrome browser")
    print("  - Better for complex dynamic sites")
    print()
    print("Recommendation: Try requests method first, fallback to Selenium if needed")
    print(f"\nCompleted at: {datetime.now()}")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Test script for the HedgeFollow scraper
Tests the hybrid Selenium + BeautifulSoup approach
"""
import logging
import json
import time
from table_scrapers import scrape_hedge_follow

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    print("=" * 80)
    print("Testing HedgeFollow stock split scraper (Selenium + BeautifulSoup)")
    print("=" * 80)
    
    start_time = time.time()
    
    try:
        # The function now returns a tuple: (upcoming_splits, past_splits)
        upcoming_splits, past_splits = scrape_hedge_follow()
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        print(f"\n✓ Scraping completed in {elapsed:.2f} seconds")
        print(f"✓ Found {len(upcoming_splits)} upcoming splits")
        print(f"✓ Found {len(past_splits)} past splits")
        
        if upcoming_splits:
            print("\n" + "=" * 80)
            print("UPCOMING SPLITS:")
            print("=" * 80)
            for split in upcoming_splits:
                split_type = "Reverse" if split.get('is_reverse', False) else "Forward"
                print(f"  • {split['symbol']:6} | {split['company']:30.30} | {split_type:7} | {split['ratio']:10} | {split['effective_date']}")
            
            print("\n" + "-" * 80)
            print("First upcoming split (detailed):")
            print("-" * 80)
            print(json.dumps(upcoming_splits[0], indent=2))
        else:
            print("\n⚠ No upcoming splits found.")
        
        if past_splits:
            print("\n" + "=" * 80)
            print("PAST SPLITS (for reference):")
            print("=" * 80)
            for split in past_splits[:5]:  # Show only first 5
                split_type = "Reverse" if split.get('is_reverse', False) else "Forward"
                print(f"  • {split['symbol']:6} | {split['company']:30.30} | {split_type:7} | {split['ratio']:10} | {split['effective_date']}")
            
            if len(past_splits) > 5:
                print(f"  ... and {len(past_splits) - 5} more past splits")
        
        # Summary statistics
        print("\n" + "=" * 80)
        print("SUMMARY:")
        print("=" * 80)
        upcoming_forward = sum(1 for s in upcoming_splits if not s.get('is_reverse', False))
        upcoming_reverse = sum(1 for s in upcoming_splits if s.get('is_reverse', False))
        past_forward = sum(1 for s in past_splits if not s.get('is_reverse', False))
        past_reverse = sum(1 for s in past_splits if s.get('is_reverse', False))
        
        print(f"  Upcoming: {upcoming_forward} forward, {upcoming_reverse} reverse")
        print(f"  Past:     {past_forward} forward, {past_reverse} reverse")
        print(f"  Total:    {len(upcoming_splits) + len(past_splits)} splits found")
        print(f"  Time:     {elapsed:.2f}s")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n✗ Error during scraping: {e}")
        logging.exception("Full error details:")
        raise

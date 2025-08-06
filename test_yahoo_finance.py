#!/usr/bin/env python3
"""
Test script for the Yahoo Finance scraper using Selenium
"""
from table_scrapers import scrape_yahoo_finance_selenium
import json
from datetime import datetime

if __name__ == "__main__":
    print(f"Testing Yahoo Finance stock split scraper at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    splits = scrape_yahoo_finance_selenium()
    
    print(f"Found {len(splits)} splits")
    
    if splits:
        # Group splits by date
        splits_by_date = {}
        for split in splits:
            date = split['effective_date']
            if date not in splits_by_date:
                splits_by_date[date] = []
            splits_by_date[date].append(split)
        
        # Display splits by date
        print("\nUpcoming splits by date:")
        for date in sorted(splits_by_date.keys()):
            date_splits = splits_by_date[date]
            print(f"\n{date} - {len(date_splits)} splits:")
            for split in date_splits:
                split_type = "Reverse" if split.get('is_reverse', False) else "Forward"
                print(f"- {split['symbol']}: {split_type} split {split['ratio']}")
        
        print("\nFirst split details:")
        print(json.dumps(splits[0], indent=2))
    else:
        print("No splits found.")

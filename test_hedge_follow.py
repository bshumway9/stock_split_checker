#!/usr/bin/env python3
"""
Test script for the HedgeFollow scraper
"""
from reverse_split_checker import scrape_hedge_follow
import json

if __name__ == "__main__":
    print("Testing HedgeFollow stock split scraper...")
    splits = scrape_hedge_follow()
    
    print(f"Found {len(splits)} splits")
    
    if splits:
        print("\nUpcoming splits:")
        for split in splits:
            split_type = "Reverse" if split.get('is_reverse', False) else "Forward"
            print(f"- {split['symbol']}: {split_type} split {split['ratio']} on {split['effective_date']}")
        
        print("\nFirst split details:")
        print(json.dumps(splits[0], indent=2))
    else:
        print("No splits found.")

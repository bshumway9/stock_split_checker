#!/usr/bin/env python3

import logging
from table_scrapers import scrape_stock_titan

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def test_stock_titan_scraper():
    """Test the StockTitan scraper."""
    print("Testing StockTitan scraper...")
    
    try:
        splits = scrape_stock_titan()
        
        print(f"\nFound {len(splits)} stock splits from StockTitan:")
        print("=" * 80)
        
        for i, split in enumerate(splits, 1):
            print(f"\n{i}. {split['symbol']} ({split.get('exchange', 'Unknown')})")
            print(f"   Type: {'Reverse Split' if split.get('is_reverse') else 'Forward Split'}")
            print(f"   Ratio: {split['ratio']}")
            print(f"   Effective Date: {split['effective_date']}")
            print(f"   Source: {split['source']}")
            if 'title' in split:
                print(f"   Title: {split['title']}")
        
        if not splits:
            print("No stock splits found.")
            
    except Exception as e:
        print(f"Error testing StockTitan scraper: {e}")
        logging.error(f"Error testing StockTitan scraper: {e}")

if __name__ == "__main__":
    test_stock_titan_scraper()

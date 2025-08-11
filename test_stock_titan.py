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
        recent_splits, all_splits_with_links = scrape_stock_titan()
        
        print(f"\nFound {len(recent_splits)} recent stock splits from StockTitan:")
        print(f"Found {len(all_splits_with_links)} total splits with article links:")
        print("=" * 80)
        
        print("\n--- RECENT SPLITS (last week) ---")
        for i, split in enumerate(recent_splits, 1):
            print(f"\n{i}. {split['symbol']} ({split.get('exchange', 'Unknown')})")
            print(f"   Type: {'Reverse Split' if split.get('is_reverse') else 'Forward Split'}")
            print(f"   Ratio: {split['ratio']}")
            print(f"   Effective Date: {split['effective_date']}")
            print(f"   Source: {split['source']}")
            print(f"   Article Links: {len(split.get('article_link', []))}")
            if split.get('article_link'):
                for link in split['article_link']:
                    print(f"     - {link}")
            if 'title' in split:
                print(f"   Title: {split['title']}")
        
        print("\n--- ALL SPLITS WITH LINKS ---")
        for i, split in enumerate(all_splits_with_links, 1):
            print(f"\n{i}. {split['symbol']} ({split.get('exchange', 'Unknown')})")
            print(f"   Type: {'Reverse Split' if split.get('is_reverse') else 'Forward Split'}")
            print(f"   Ratio: {split['ratio']}")
            print(f"   Effective Date: {split['effective_date']}")
            print(f"   Source: {split['source']}")
            print(f"   Article Links: {len(split.get('article_link', []))}")
            if split.get('article_link'):
                for link in split['article_link']:
                    print(f"     - {link}")
            if 'title' in split:
                print(f"   Title: {split['title']}")
        
        if not recent_splits and not all_splits_with_links:
            print("No stock splits found.")
            
    except Exception as e:
        print(f"Error testing StockTitan scraper: {e}")
        logging.error(f"Error testing StockTitan scraper: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_stock_titan_scraper()

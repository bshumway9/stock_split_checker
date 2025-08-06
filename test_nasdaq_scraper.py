#!/usr/bin/env python3

import logging
import json
from datetime import datetime
from reverse_split_checker import scrape_nasdaq

# Set up logging to console for testing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Log to console
    ]
)

def main():
    """Test the Nasdaq stock split scraper function."""
    print("Starting Nasdaq scraper test...")
    
    # Record start time
    start_time = datetime.now()
    print(f"Test started at: {start_time}")
    
    # Run the scraper
    results = scrape_nasdaq()
    
    # Record end time
    end_time = datetime.now()
    duration = end_time - start_time
    print(f"Test completed at: {end_time}")
    print(f"Total execution time: {duration}")
    
    # Print results summary
    print(f"\nFound {len(results)} stock splits on Nasdaq")
    
    # Print results in formatted JSON
    if results:
        print("\nStock Split Results:")
        print(json.dumps(results, indent=2, default=str))
        
        # Count forward vs reverse splits
        reverse_splits = [split for split in results if split.get('is_reverse', False)]
        forward_splits = [split for split in results if not split.get('is_reverse', False)]
        
        print(f"\nReverse Splits: {len(reverse_splits)}")
        print(f"Forward Splits: {len(forward_splits)}")
        
        # Print upcoming splits by date
        print("\nUpcoming Splits by Date:")
        dates = {}
        for split in results:
            date = split['effective_date']
            if date not in dates:
                dates[date] = []
            dates[date].append(split['symbol'])
        
        for date in sorted(dates.keys()):
            print(f"{date}: {', '.join(dates[date])}")
    else:
        print("No results found. Check if there are any issues with the scraper.")

if __name__ == "__main__":
    main()

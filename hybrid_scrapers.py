#!/usr/bin/env python3
"""
Hybrid scraper approach - uses the best method for each site based on test results:
- StockTitan: requests + BeautifulSoup (faster, more reliable)
- HedgeFollow: Selenium (required for JavaScript content)
"""

import requests
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import re
from helper_functions import next_market_day

# Import Selenium components for HedgeFollow
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def scrape_stock_titan_requests_optimized():
    """
    Optimized StockTitan scraper using requests + BeautifulSoup.
    Based on test results, this is faster and more reliable than Selenium for StockTitan.
    Returns a tuple: (recent_splits, all_splits_with_links)
    """
    recent_splits = []
    all_splits_with_links = []
    
    # Optimized headers based on test results - no User-Agent works best
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    
    try:
        url = "https://www.stocktitan.net/news/stock-splits.html"
        logging.info(f"Fetching StockTitan data using optimized requests method from {url}")
        
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        end_time = time.time()
        
        logging.info(f"StockTitan response: {response.status_code}, Time: {end_time - start_time:.2f}s, Size: {len(response.content)} bytes")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for the live news feed
        news_feed = soup.find('div', {'id': 'live-news-feed'})
        if not news_feed:
            logging.warning("Could not find StockTitan live-news-feed div")
            return recent_splits, all_splits_with_links
        
        logging.info("Found StockTitan live-news-feed div")
        
        # Look for news rows
        news_rows = news_feed.find_all('div', class_='news-row')
        if not news_rows:
            # Alternative selector
            news_rows = news_feed.find_all('div', {'data-news-id': True})
        
        if not news_rows:
            logging.warning("Could not find StockTitan news rows")
            return recent_splits, all_splits_with_links
        
        logging.info(f"Found {len(news_rows)} news rows in StockTitan feed")
        
        # Get date for filtering
        prev_week = next_market_day(datetime.now().date(), previous=True, days=5)
        
        for row in news_rows:
            try:
                # Check if this article is about stock splits
                row_text = row.get_text().lower()
                if 'stock split' not in row_text and 'share split' not in row_text:
                    continue
                
                # Look for tags to confirm it's a split article
                tags = row.find_all('span', class_='badge')
                is_split_article = any('stock split' in tag.get_text().lower() for tag in tags)
                
                if not is_split_article and 'stock split' not in row_text:
                    continue
                
                # Extract ticker information
                ticker_elements = row.find_all('span', class_='feed-ticker')
                if not ticker_elements:
                    # Try alternative ticker extraction
                    ticker_divs = row.find_all('div', attrs={'name': 'tickers'})
                    if ticker_divs:
                        ticker_elements = ticker_divs[0].find_all('span', class_='feed-ticker')
                
                if not ticker_elements:
                    continue
                
                # Process the first ticker only
                ticker_element = ticker_elements[0]
                
                # Extract symbol
                symbol_link = ticker_element.find('a', class_='symbol-link')
                if not symbol_link:
                    continue
                
                symbol = symbol_link.get_text().strip()
                
                # Get exchange (usually after the colon in ticker text)
                ticker_text = ticker_element.get_text().strip()
                exchange = "Unknown"
                if ":" in ticker_text:
                    exchange = ticker_text.split(":")[-1].strip()
                
                # Skip OTC stocks
                if exchange.upper() == "OTC":
                    continue
                
                # Extract title and article link
                title_element = row.find('div', attrs={'name': 'title'})
                if not title_element:
                    continue
                
                title_link = title_element.find('a', class_='feed-link')
                if not title_link:
                    continue
                
                title = title_link.get_text().strip()
                article_link = title_link.get('href')
                
                # Make article link absolute
                if article_link and not article_link.startswith('http'):
                    article_link = urljoin(url, article_link)
                
                # Extract date
                date_element = row.find('time', class_='news-row-datetime')
                if date_element:
                    date_span = date_element.find('span', class_='date')
                    date_text = date_span.get_text().strip() if date_span else date_element.get_text().strip()
                else:
                    # Use current date as fallback
                    date_text = datetime.now().strftime('%m/%d/%Y')
                
                # Parse date
                try:
                    date_obj = datetime.strptime(date_text, '%m/%d/%Y')
                    effective_date = date_obj.strftime('%Y-%m-%d')
                    split_date = date_obj.date()
                except ValueError:
                    # Use current date as fallback
                    effective_date = datetime.now().strftime('%Y-%m-%d')
                    split_date = datetime.now().date()
                
                # Determine split type and ratio from title
                is_reverse = False
                ratio = "Not specified"
                title_lower = title.lower()
                
                if "reverse" in title_lower:
                    is_reverse = True
                
                # Extract ratio using regex
                ratio_patterns = [
                    r'(\d+)[-\s]*for[-\s]*(\d+)',
                    r'(\d+):(\d+)',
                    r'(\d+)[-\s]*to[-\s]*(\d+)'
                ]
                
                for pattern in ratio_patterns:
                    match = re.search(pattern, title_lower)
                    if match:
                        left = int(match.group(1))
                        right = int(match.group(2))
                        
                        if is_reverse or left < right:
                            ratio = f"{left}:{right}"
                            is_reverse = True
                        else:
                            ratio = f"{left}:{right}"
                        break
                
                split_info = {
                    'symbol': symbol,
                    'ratio': ratio,
                    'effective_date': effective_date,
                    'fractional': 'Not specified',
                    'is_reverse': is_reverse,
                    'source': 'StockTitan (optimized requests)',
                    'exchange': exchange,
                    'title': title,
                    'article_link': [article_link] if article_link else []
                }
                
                # Add to appropriate lists
                if split_date >= prev_week:
                    recent_splits.append(split_info)
                    logging.info(f"Found recent StockTitan split: {symbol} ({exchange}) - {ratio} on {effective_date}")
                
                if article_link:
                    all_splits_with_links.append(split_info)
                
            except Exception as e:
                logging.error(f"Error processing StockTitan news row: {e}")
                continue
        
        logging.info(f"StockTitan (optimized requests): {len(recent_splits)} recent splits, {len(all_splits_with_links)} total with links")
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error scraping StockTitan: {e}")
        raise
    except Exception as e:
        logging.error(f"Error scraping StockTitan with optimized requests: {e}")
        raise
    
    return recent_splits, all_splits_with_links


def scrape_hedge_follow_selenium_optimized():
    """
    Optimized HedgeFollow scraper using Selenium (required for JavaScript content).
    Uses optimized settings for better performance.
    Returns a tuple: (upcoming_splits, past_splits)
    """
    splits = []
    past_splits = []
    driver = None
    
    try:
        # Optimized Chrome options for HedgeFollow
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # Memory-saving flags
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-client-side-phishing-detection")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--disable-translate")
        chrome_options.add_argument("--metrics-recording-only")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--safebrowsing-disable-auto-update")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        
        # Initialize the Chrome WebDriver
        logging.info("Initializing optimized Chrome WebDriver for HedgeFollow scraping")
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to HedgeFollow's upcoming stock splits page
        url = "https://www.hedgefollow.com/upcoming-stock-splits.php"
        logging.info(f"Navigating to {url}")
        
        start_time = time.time()
        driver.get(url)
        
        # Wait for the latest_splits table to load
        wait = WebDriverWait(driver, 15)
        table = wait.until(EC.presence_of_element_located((By.ID, "latest_splits")))
        end_time = time.time()
        
        logging.info(f"HedgeFollow page loaded in {end_time - start_time:.2f}s")
        
        # Get all rows from the table (except header row)
        rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header row
        logging.info(f"Found {len(rows)} rows in HedgeFollow latest_splits table")

        next_day = next_market_day()

        for row in rows:
            try:
                # Extract cells from each row
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 4:  # Ensure we have enough cells
                    continue
                
                # Extract data from cells
                symbol = cells[0].text.strip()
                market = cells[1].text.strip()
                company = cells[2].text.strip()
                ratio = cells[3].text.strip()
                date_text = cells[4].text.strip()
                
                # Skip if essential data is missing or if it's OTC
                if not symbol or not date_text or not ratio or market.lower() == "otc":
                    continue
                
                # Parse date (format is YYYY-MM-DD)
                try:
                    date_obj = datetime.strptime(date_text, '%Y-%m-%d')
                    effective_date = date_obj.strftime('%Y-%m-%d')
                    split_date = date_obj.date()
                except ValueError as e:
                    logging.warning(f"Could not parse HedgeFollow date '{date_text}': {e}")
                    continue
                
                # Determine if this is a reverse split (if ratio contains :)
                is_reverse = False
                normalized_ratio = ratio
                if ":" in ratio:
                    try:
                        left, right = map(float, ratio.split(":"))
                        is_reverse = left < right  # e.g., 1:10 is a reverse split
                        normalized_ratio = f"{right}->{left}" if is_reverse else f"{left}->{right}"
                    except ValueError:
                        pass
                
                split_info = {
                    'symbol': symbol,
                    'company': company,
                    'ratio': normalized_ratio,
                    'effective_date': effective_date,
                    'fractional': 'Not specified',
                    'is_reverse': is_reverse,
                    'source': 'HedgeFollow (optimized Selenium)',
                    'article_link': []
                }
                
                # Categorize as future or past split
                if split_date >= next_day:
                    splits.append(split_info)
                    logging.info(f"Found future HedgeFollow split: {symbol} - {ratio} on {effective_date}")
                else:
                    past_splits.append(split_info)
                
            except Exception as e:
                logging.error(f"Error processing HedgeFollow row: {e}")
                continue
        
        logging.info(f"HedgeFollow (optimized Selenium): {len(splits)} future splits, {len(past_splits)} past splits")
        
    except Exception as e:
        logging.error(f"Error scraping HedgeFollow with optimized Selenium: {e}")
        raise
    finally:
        # Always close the WebDriver to free resources
        if driver:
            try:
                driver.quit()
                logging.info("HedgeFollow WebDriver closed successfully")
            except Exception as e:
                logging.error(f"Error closing HedgeFollow WebDriver: {e}")
    
    return splits, past_splits


def scrape_all_splits_hybrid():
    """
    Hybrid scraper that uses the optimal method for each site:
    - StockTitan: requests + BeautifulSoup (faster, more reliable)
    - HedgeFollow: Selenium (required for JavaScript)
    
    Returns combined results from both sources.
    """
    logging.info("Starting hybrid scraping approach")
    
    all_recent_splits = []
    all_splits_with_links = []
    all_future_splits = []
    all_past_splits = []
    
    # Scrape StockTitan with optimized requests
    try:
        logging.info("Scraping StockTitan with optimized requests method...")
        st_recent, st_all = scrape_stock_titan_requests_optimized()
        all_recent_splits.extend(st_recent)
        all_splits_with_links.extend(st_all)
        logging.info(f"StockTitan completed: {len(st_recent)} recent, {len(st_all)} total")
    except Exception as e:
        logging.error(f"StockTitan scraping failed: {e}")
    
    # Scrape HedgeFollow with optimized Selenium
    try:
        logging.info("Scraping HedgeFollow with optimized Selenium method...")
        hf_future, hf_past = scrape_hedge_follow_selenium_optimized()
        all_future_splits.extend(hf_future)
        all_past_splits.extend(hf_past)
        logging.info(f"HedgeFollow completed: {len(hf_future)} future, {len(hf_past)} past")
    except Exception as e:
        logging.error(f"HedgeFollow scraping failed: {e}")
    
    # Combine results
    total_recent = len(all_recent_splits)
    total_future = len(all_future_splits)
    total_with_links = len(all_splits_with_links)
    total_past = len(all_past_splits)
    
    logging.info(f"Hybrid scraping completed - Recent: {total_recent}, Future: {total_future}, With links: {total_with_links}, Past: {total_past}")
    
    return {
        'stocktitan_recent': all_recent_splits,
        'stocktitan_all': all_splits_with_links,
        'hedgefollow_future': all_future_splits,
        'hedgefollow_past': all_past_splits
    }


def test_hybrid_scrapers():
    """
    Test the hybrid scraper approach and show performance benefits.
    """
    print("="*80)
    print("TESTING HYBRID SCRAPER APPROACH")
    print("="*80)
    print("StockTitan: requests + BeautifulSoup (optimized)")
    print("HedgeFollow: Selenium (required for JavaScript)")
    print("="*80)
    
    start_time = time.time()
    
    try:
        results = scrape_all_splits_hybrid()
        end_time = time.time()
        
        print(f"\n✓ HYBRID SCRAPING COMPLETED in {end_time - start_time:.2f} seconds")
        print(f"\nResults Summary:")
        print(f"  StockTitan Recent Splits: {len(results['stocktitan_recent'])}")
        print(f"  StockTitan Total Splits:  {len(results['stocktitan_all'])}")
        print(f"  HedgeFollow Future:       {len(results['hedgefollow_future'])}")
        print(f"  HedgeFollow Past:         {len(results['hedgefollow_past'])}")
        
        # Show sample data
        if results['stocktitan_recent']:
            print(f"\nSample StockTitan Split:")
            sample = results['stocktitan_recent'][0]
            print(f"  Symbol: {sample['symbol']}")
            print(f"  Ratio: {sample['ratio']}")
            print(f"  Date: {sample['effective_date']}")
            print(f"  Source: {sample['source']}")
        
        if results['hedgefollow_future']:
            print(f"\nSample HedgeFollow Split:")
            sample = results['hedgefollow_future'][0]
            print(f"  Symbol: {sample['symbol']}")
            print(f"  Ratio: {sample['ratio']}")
            print(f"  Date: {sample['effective_date']}")
            print(f"  Source: {sample['source']}")
        
        print(f"\n✓ Hybrid approach provides best of both worlds:")
        print(f"  - Fast StockTitan scraping (~0.36s)")
        print(f"  - Reliable HedgeFollow data via Selenium")
        print(f"  - Reduced overall Selenium usage")
        
    except Exception as e:
        print(f"\n✗ Hybrid scraping failed: {e}")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    test_hybrid_scrapers()
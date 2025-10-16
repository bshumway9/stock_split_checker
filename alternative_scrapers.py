#!/usr/bin/env python3
"""
Alternative scraper implementations for StockTitan and HedgeFollow.
These functions use requests + BeautifulSoup instead of Selenium for better reliability.
"""

import requests
import json
import re
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from helper_functions import next_market_day


def scrape_hedge_follow_requests():
    """
    Alternative HedgeFollow scraper using requests + BeautifulSoup.
    More reliable than Selenium for simple HTML parsing.
    Returns a tuple: (upcoming_splits, past_splits)
    """
    splits = []
    past_splits = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        # Use the same URL as in table_scrapers.py
        url = "https://www.hedgefollow.com/upcoming-stock-splits.php"
        logging.info(f"Fetching HedgeFollow data from {url}")
        
        session = requests.Session()
        session.headers.update(headers)
        
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        logging.info(f"HedgeFollow response: {response.status_code}, Content length: {len(response.content)}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for the latest_splits table
        table = soup.find('table', {'id': 'latest_splits'})
        if not table:
            # Try alternative selectors
            table = soup.find('table', class_=re.compile(r'splits|latest'))
            if not table:
                # Look for any table that might contain split data
                all_tables = soup.find_all('table')
                for t in all_tables:
                    table_text = t.get_text().lower()
                    if 'symbol' in table_text and 'ratio' in table_text and 'date' in table_text:
                        table = t
                        break
        
        if not table:
            logging.warning("Could not find HedgeFollow splits table")
            return splits, past_splits
        
        logging.info("Found HedgeFollow splits table")
        
        rows = table.find_all('tr')
        if len(rows) <= 1:
            logging.info("No data rows found in HedgeFollow table")
            return splits, past_splits
        
        # Skip header row
        data_rows = rows[1:]
        logging.info(f"Found {len(data_rows)} data rows in HedgeFollow table")
        
        next_day = next_market_day(datetime.now().date())
        
        for row in data_rows:
            try:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 4:
                    continue
                
                # Extract data - HedgeFollow format: Symbol, Market, Company, Ratio, Date
                cell_data = [cell.get_text().strip() for cell in cells]
                
                if len(cell_data) >= 5:
                    symbol = cell_data[0]
                    market = cell_data[1]
                    company = cell_data[2]
                    ratio = cell_data[3]
                    date_text = cell_data[4]
                else:
                    # Fallback if column structure is different
                    continue
                
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
                
                # Determine if this is a reverse split
                is_reverse = False
                normalized_ratio = ratio
                if ":" in ratio:
                    try:
                        parts = ratio.split(":")
                        left = float(parts[0].strip())
                        right = float(parts[1].strip())
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
                    'source': 'HedgeFollow (requests)',
                    'article_link': []
                }
                
                # Categorize as future or past split
                if split_date >= next_day:
                    splits.append(split_info)
                    logging.info(f"Found future HedgeFollow split: {symbol} - {ratio} on {effective_date}")
                else:
                    past_splits.append(split_info)
                    # logging.info(f"Found past HedgeFollow split: {symbol} - {ratio} on {effective_date}")
                
            except Exception as e:
                logging.error(f"Error processing HedgeFollow row: {e}")
                continue
        
        logging.info(f"HedgeFollow (requests): {len(splits)} future splits, {len(past_splits)} past splits")
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error scraping HedgeFollow: {e}")
        raise
    except Exception as e:
        logging.error(f"Error scraping HedgeFollow with requests: {e}")
        raise
    
    return splits, past_splits


def scrape_stock_titan_requests():
    """
    Alternative StockTitan scraper using requests + BeautifulSoup.
    Attempts to parse the live news feed directly from HTML.
    Returns a tuple: (recent_splits, all_splits_with_links)
    """
    recent_splits = []
    all_splits_with_links = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        # Use the same URL as in table_scrapers.py
        url = "https://www.stocktitan.net/news/stock-splits.html"
        logging.info(f"Fetching StockTitan data from {url}")
        
        session = requests.Session()
        session.headers.update(headers)
        
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        logging.info(f"StockTitan response: {response.status_code}, Content length: {len(response.content)}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for the live news feed
        news_feed = soup.find('div', {'id': 'live-news-feed'})
        if not news_feed:
            # Try alternative selectors
            news_feed = soup.find('div', class_=re.compile(r'news.+feed|feed.+news'))
            if not news_feed:
                logging.warning("Could not find StockTitan news feed container")
                return recent_splits, all_splits_with_links
        
        logging.info("Found StockTitan news feed container")
        
        # Look for news rows
        news_rows = news_feed.find_all('div', class_='news-row') or news_feed.find_all('div', {'data-news-id': True})
        
        if not news_rows:
            # Try to find any divs that might contain news articles
            news_rows = news_feed.find_all('div', class_=re.compile(r'row|item|article'))
        
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
                tags = row.find_all('span', class_='badge') or row.find_all('a', href=re.compile(r'stock.?split'))
                is_split_article = any('stock split' in tag.get_text().lower() for tag in tags)
                
                if not is_split_article and 'stock split' not in row_text:
                    continue
                
                # Extract ticker information
                ticker_elements = row.find_all('span', class_='feed-ticker') or row.find_all('div', attrs={'name': 'tickers'})
                
                if not ticker_elements:
                    # Try alternative ticker extraction
                    symbol_links = row.find_all('a', class_='symbol-link')
                    if symbol_links:
                        ticker_elements = [link.parent for link in symbol_links if link.parent]
                
                if not ticker_elements:
                    continue
                
                # Process the first ticker only
                ticker_element = ticker_elements[0]
                
                # Extract symbol
                symbol_link = ticker_element.find('a', class_='symbol-link')
                if not symbol_link:
                    symbol_links = ticker_element.find_all('a')
                    symbol_link = symbol_links[0] if symbol_links else None
                
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
                title_element = row.find('div', attrs={'name': 'title'}) or row.find('a', class_='feed-link')
                if not title_element:
                    title_elements = row.find_all('a', href=True)
                    title_element = next((elem for elem in title_elements if elem.get_text().strip()), None)
                
                if not title_element:
                    continue
                
                if title_element.name == 'div':
                    title_link = title_element.find('a', class_='feed-link') or title_element.find('a')
                else:
                    title_link = title_element
                
                if not title_link:
                    continue
                
                title = title_link.get_text().strip()
                article_link = title_link.get('href')
                
                # Make article link absolute
                if article_link and not article_link.startswith('http'):
                    article_link = urljoin(url, article_link)
                
                # Extract date
                date_element = row.find('time', class_='news-row-datetime') or row.find('span', class_='date')
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
                    'source': 'StockTitan (requests)',
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
        
        logging.info(f"StockTitan (requests): {len(recent_splits)} recent splits, {len(all_splits_with_links)} total with links")
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error scraping StockTitan: {e}")
        raise
    except Exception as e:
        logging.error(f"Error scraping StockTitan with requests: {e}")
        raise
    
    return recent_splits, all_splits_with_links


def test_alternative_scrapers():
    """
    Test the alternative scrapers and compare with Selenium versions.
    """
    print("=== Testing Alternative Scrapers ===")
    
    # Test HedgeFollow
    print("\n--- Testing HedgeFollow (requests) ---")
    try:
        splits, past_splits = scrape_hedge_follow_requests()
        print(f"✓ HedgeFollow (requests): {len(splits)} future splits, {len(past_splits)} past splits")
        
        if splits:
            print("Sample split:")
            sample = splits[0]
            for key, value in sample.items():
                print(f"  {key}: {value}")
                
    except Exception as e:
        print(f"✗ HedgeFollow (requests) error: {e}")
    
    # Test StockTitan
    print("\n--- Testing StockTitan (requests) ---")
    try:
        recent_splits, all_splits = scrape_stock_titan_requests()
        print(f"✓ StockTitan (requests): {len(recent_splits)} recent splits, {len(all_splits)} total")
        
        if recent_splits:
            print("Sample split:")
            sample = recent_splits[0]
            for key, value in sample.items():
                print(f"  {key}: {value}")
                
    except Exception as e:
        print(f"✗ StockTitan (requests) error: {e}")
    
    print("\n--- Comparison with Selenium (if available) ---")
    try:
        from table_scrapers import scrape_hedge_follow, scrape_stock_titan
        
        # Test Selenium HedgeFollow
        try:
            selenium_splits, selenium_past = scrape_hedge_follow()
            print(f"HedgeFollow Selenium: {len(selenium_splits)} future, {len(selenium_past)} past")
        except Exception as e:
            print(f"HedgeFollow Selenium error: {e}")
        
        # Test Selenium StockTitan
        try:
            selenium_recent, selenium_all = scrape_stock_titan()
            print(f"StockTitan Selenium: {len(selenium_recent)} recent, {len(selenium_all)} total")
        except Exception as e:
            print(f"StockTitan Selenium error: {e}")
            
    except ImportError:
        print("Could not import Selenium scrapers for comparison")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    test_alternative_scrapers()
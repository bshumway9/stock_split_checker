#!/usr/bin/env python3
"""
Alternative scraper test file for StockTitan and HedgeFollow.
This file tests different approaches to scraping without using Selenium,
including requests + BeautifulSoup, API endpoints, and RSS feeds.
"""

import requests
import json
import re
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import xml.etree.ElementTree as ET
from helper_functions import next_market_day

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_stocktitan_requests():
    """
    Test scraping StockTitan using requests and BeautifulSoup instead of Selenium.
    """
    print("\n=== Testing StockTitan with requests + BeautifulSoup ===")
    
    # Headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        # Use the same URL as in table_scrapers.py
        url = "https://www.stocktitan.net/news/stock-splits.html"
        print(f"Fetching: {url}")
        
        session = requests.Session()
        session.headers.update(headers)
        
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        print(f"Status Code: {response.status_code}")
        print(f"Content Length: {len(response.content)}")
        print(f"Content Type: {response.headers.get('content-type', 'Unknown')}")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        print(f"Page title: {soup.title.string if soup.title else 'No title'}")
        
        # Look for the live news feed
        news_feed = soup.find('div', {'id': 'live-news-feed'})
        if news_feed:
            print("✓ Found live-news-feed div")
            
            # Look for news rows
            news_rows = news_feed.find_all('div', class_='news-row')
            print(f"Found {len(news_rows)} news rows")
            
            if news_rows:
                for i, row in enumerate(news_rows[:3]):  # Check first 3 rows
                    print(f"\n--- Row {i+1} ---")
                    
                    # Look for stock split tags
                    tags = row.find_all('span', class_='badge')
                    tag_texts = [tag.get_text().strip() for tag in tags]
                    print(f"Tags: {tag_texts}")
                    
                    # Look for ticker information
                    ticker_divs = row.find_all('div', attrs={'name': 'tickers'})
                    if ticker_divs:
                        ticker_spans = ticker_divs[0].find_all('span', class_='feed-ticker')
                        for ticker_span in ticker_spans:
                            symbol_link = ticker_span.find('a', class_='symbol-link')
                            if symbol_link:
                                symbol = symbol_link.get_text().strip()
                                print(f"Symbol: {symbol}")
                    
                    # Look for title
                    title_div = row.find('div', attrs={'name': 'title'})
                    if title_div:
                        title_link = title_div.find('a', class_='feed-link')
                        if title_link:
                            title = title_link.get_text().strip()
                            article_url = title_link.get('href')
                            print(f"Title: {title}")
                            print(f"Article URL: {article_url}")
                    
                    # Look for date
                    time_elem = row.find('time', class_='news-row-datetime')
                    if time_elem:
                        date_span = time_elem.find('span', class_='date')
                        if date_span:
                            date_text = date_span.get_text().strip()
                            print(f"Date: {date_text}")
            else:
                print("No news rows found")
        else:
            print("✗ live-news-feed div not found")
            
            # Try alternative approaches
            print("\nTrying alternative selectors...")
            
            # Look for any divs with news-related classes
            news_elements = soup.find_all('div', class_=re.compile(r'news|feed|article'))
            print(f"Found {len(news_elements)} elements with news/feed/article classes")
            
            # Look for any elements containing "stock split"
            split_elements = soup.find_all(text=re.compile(r'stock split', re.IGNORECASE))
            print(f"Found {len(split_elements)} elements containing 'stock split'")
            
            if split_elements:
                for i, elem in enumerate(split_elements[:3]):
                    parent = elem.parent if hasattr(elem, 'parent') else None
                    print(f"Split mention {i+1}: {elem.strip()[:100]}...")
                    if parent:
                        print(f"  Parent tag: {parent.name}")
        
        # Save HTML for debugging
        with open('/tmp/stocktitan_requests.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("HTML saved to /tmp/stocktitan_requests.html")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Request error: {e}")
        return False
    except Exception as e:
        print(f"✗ Other error: {e}")
        return False


def test_stocktitan_api_endpoints():
    """
    Test for potential API endpoints or AJAX calls that StockTitan might use.
    """
    print("\n=== Testing StockTitan API Endpoints ===")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://www.stocktitan.net/news/stock-splits.html'
    }
    
    # Common API endpoint patterns to try
    api_endpoints = [
        "https://www.stocktitan.net/api/news/splits",
        "https://www.stocktitan.net/api/news/feed",
        "https://www.stocktitan.net/ajax/news/splits",
        "https://www.stocktitan.net/ajax/live-feed",
        "https://api.stocktitan.net/news/splits",
        "https://api.stocktitan.net/v1/news/splits",
        "https://www.stocktitan.net/feed/stock-splits.json",
        "https://www.stocktitan.net/data/splits.json"
    ]
    
    session = requests.Session()
    session.headers.update(headers)
    
    for endpoint in api_endpoints:
        try:
            print(f"Trying: {endpoint}")
            response = session.get(endpoint, timeout=10)
            
            if response.status_code == 200:
                print(f"✓ Success! Status: {response.status_code}")
                content_type = response.headers.get('content-type', '')
                print(f"Content-Type: {content_type}")
                
                if 'json' in content_type:
                    try:
                        data = response.json()
                        print(f"JSON data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        print(f"Sample content: {str(data)[:200]}...")
                    except json.JSONDecodeError:
                        print("Invalid JSON response")
                else:
                    print(f"Text content (first 200 chars): {response.text[:200]}...")
                
                # Save successful response
                filename = f"/tmp/stocktitan_{endpoint.split('/')[-1].replace('.', '_')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"Response saved to {filename}")
                
            else:
                print(f"✗ Status: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Error: {e}")
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
        
        time.sleep(0.5)  # Be respectful


def test_stocktitan_rss():
    """
    Test for RSS feeds that might contain stock split information.
    """
    print("\n=== Testing StockTitan RSS Feeds ===")
    
    rss_urls = [
        "https://www.stocktitan.net/rss/stock-splits.xml",
        "https://www.stocktitan.net/feed/stock-splits.xml",
        "https://www.stocktitan.net/feeds/splits.xml",
        "https://feeds.stocktitan.net/stock-splits.xml",
        "https://www.stocktitan.net/rss/news.xml",
        "https://www.stocktitan.net/feed.xml"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; RSS Reader)',
        'Accept': 'application/rss+xml, application/xml, text/xml'
    }
    
    for rss_url in rss_urls:
        try:
            print(f"Trying RSS: {rss_url}")
            response = requests.get(rss_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                print(f"✓ RSS feed found! Status: {response.status_code}")
                
                # Try to parse as XML
                try:
                    root = ET.fromstring(response.content)
                    print(f"XML root tag: {root.tag}")
                    
                    # Look for RSS or Atom elements
                    items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
                    print(f"Found {len(items)} items/entries")
                    
                    if items:
                        for i, item in enumerate(items[:3]):
                            title_elem = item.find('title') or item.find('.//{http://www.w3.org/2005/Atom}title')
                            if title_elem is not None:
                                title = title_elem.text or ''
                                print(f"Item {i+1} title: {title}")
                                
                                if 'split' in title.lower():
                                    print(f"  ✓ Contains 'split'!")
                    
                    # Save RSS content
                    filename = f"/tmp/stocktitan_rss_{rss_url.split('/')[-1]}.xml"
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    print(f"RSS saved to {filename}")
                    
                except ET.ParseError as e:
                    print(f"✗ XML parse error: {e}")
            else:
                print(f"✗ Status: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Request error: {e}")
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
        
        time.sleep(0.5)


def test_hedgefollow_requests():
    """
    Test scraping HedgeFollow using requests and BeautifulSoup.
    """
    print("\n=== Testing HedgeFollow with requests + BeautifulSoup ===")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    
    try:
        # Use the same URL as in table_scrapers.py
        url = "https://www.hedgefollow.com/upcoming-stock-splits.php"
        print(f"Fetching: {url}")
        
        session = requests.Session()
        session.headers.update(headers)
        
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        print(f"Status Code: {response.status_code}")
        print(f"Content Length: {len(response.content)}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        print(f"Page title: {soup.title.string if soup.title else 'No title'}")
        
        # Look for the latest_splits table
        table = soup.find('table', {'id': 'latest_splits'})
        if table:
            print("✓ Found latest_splits table")
            
            rows = table.find_all('tr')
            print(f"Found {len(rows)} rows in table")
            
            if len(rows) > 1:  # Should have header + data rows
                # Check header row
                header_row = rows[0]
                headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]
                print(f"Table headers: {headers}")
                
                # Process data rows
                splits_found = 0
                for i, row in enumerate(rows[1:6]):  # Check first 5 data rows
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 4:
                        cell_data = [cell.get_text().strip() for cell in cells]
                        print(f"Row {i+1}: {cell_data}")
                        
                        # Try to extract split information
                        if len(cell_data) >= 5:
                            symbol = cell_data[0]
                            market = cell_data[1]
                            company = cell_data[2]
                            ratio = cell_data[3]
                            date = cell_data[4]
                            
                            if symbol and ratio and date:
                                splits_found += 1
                                print(f"  ✓ Split found: {symbol} ({market}) - {ratio} on {date}")
                
                print(f"Total splits identified: {splits_found}")
            else:
                print("No data rows found in table")
        else:
            print("✗ latest_splits table not found")
            
            # Try alternative approaches
            print("\nLooking for alternative table structures...")
            
            # Look for any tables
            all_tables = soup.find_all('table')
            print(f"Found {len(all_tables)} total tables")
            
            for i, table in enumerate(all_tables):
                table_id = table.get('id', f'table_{i}')
                table_class = table.get('class', [])
                rows = table.find_all('tr')
                print(f"Table {i+1} (id='{table_id}', class={table_class}): {len(rows)} rows")
                
                # Check if this table might contain split data
                table_text = table.get_text().lower()
                if any(keyword in table_text for keyword in ['split', 'ratio', 'symbol', 'ticker']):
                    print(f"  ✓ Table {i+1} might contain split data")
                    
                    if rows and len(rows) > 1:
                        # Show first data row
                        first_data_row = rows[1] if len(rows) > 1 else rows[0]
                        cells = [cell.get_text().strip() for cell in first_data_row.find_all(['td', 'th'])]
                        print(f"    Sample row: {cells}")
        
        # Save HTML for debugging
        with open('/tmp/hedgefollow_requests.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("HTML saved to /tmp/hedgefollow_requests.html")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Request error: {e}")
        return False
    except Exception as e:
        print(f"✗ Other error: {e}")
        return False


def test_hedgefollow_api():
    """
    Test for potential API endpoints for HedgeFollow.
    """
    print("\n=== Testing HedgeFollow API Endpoints ===")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://www.hedgefollow.com/upcoming-stock-splits.php'
    }
    
    api_endpoints = [
        "https://www.hedgefollow.com/api/stock-splits.php",
        "https://www.hedgefollow.com/ajax/splits.php",
        "https://www.hedgefollow.com/data/splits.json",
        "https://api.hedgefollow.com/splits",
        "https://www.hedgefollow.com/feeds/splits.json"
    ]
    
    session = requests.Session()
    session.headers.update(headers)
    
    for endpoint in api_endpoints:
        try:
            print(f"Trying: {endpoint}")
            response = session.get(endpoint, timeout=10)
            
            if response.status_code == 200:
                print(f"✓ Success! Status: {response.status_code}")
                content_type = response.headers.get('content-type', '')
                print(f"Content-Type: {content_type}")
                print(f"Content preview: {response.text[:200]}...")
                
                # Save response
                filename = f"/tmp/hedgefollow_{endpoint.split('/')[-1].replace('.', '_')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"Response saved to {filename}")
            else:
                print(f"✗ Status: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Error: {e}")
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
        
        time.sleep(0.5)


def compare_with_existing_selenium():
    """
    Run the existing Selenium scrapers for comparison.
    """
    print("\n=== Running Existing Selenium Scrapers for Comparison ===")
    
    try:
        from table_scrapers import scrape_stock_titan, scrape_hedge_follow
        
        print("Testing StockTitan Selenium scraper...")
        try:
            recent_splits, all_splits = scrape_stock_titan()
            print(f"StockTitan Selenium: {len(recent_splits)} recent splits, {len(all_splits)} total")
            
            if recent_splits:
                print("Sample StockTitan split:")
                sample = recent_splits[0]
                for key, value in sample.items():
                    print(f"  {key}: {value}")
        except Exception as e:
            print(f"StockTitan Selenium error: {e}")
        
        print("\nTesting HedgeFollow Selenium scraper...")
        try:
            splits, past_splits = scrape_hedge_follow()
            print(f"HedgeFollow Selenium: {len(splits)} future splits, {len(past_splits)} past splits")
            
            if splits:
                print("Sample HedgeFollow split:")
                sample = splits[0]
                for key, value in sample.items():
                    print(f"  {key}: {value}")
        except Exception as e:
            print(f"HedgeFollow Selenium error: {e}")
            
    except ImportError as e:
        print(f"Could not import existing scrapers: {e}")
    except Exception as e:
        print(f"Error running existing scrapers: {e}")


def test_network_diagnostics():
    """
    Test basic network connectivity and response times.
    """
    print("\n=== Network Diagnostics ===")
    
    test_urls = [
        "https://www.stocktitan.net",
        "https://www.hedgefollow.com",
        "https://finance.yahoo.com",
        "https://httpbin.org/get"  # Test endpoint
    ]
    
    for url in test_urls:
        try:
            print(f"\nTesting {url}...")
            start_time = time.time()
            
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            end_time = time.time()
            response_time = end_time - start_time
            
            print(f"✓ Status: {response.status_code}")
            print(f"✓ Response time: {response_time:.2f}s")
            print(f"✓ Content length: {len(response.content)} bytes")
            print(f"✓ Server: {response.headers.get('server', 'Unknown')}")
            
        except requests.exceptions.Timeout:
            print(f"✗ Timeout after 10 seconds")
        except requests.exceptions.ConnectionError:
            print(f"✗ Connection error")
        except Exception as e:
            print(f"✗ Error: {e}")


def main():
    """
    Run all alternative scraping tests.
    """
    print("=== Alternative Scraping Methods Test Suite ===")
    print(f"Test started at: {datetime.now()}")
    
    # Run network diagnostics first
    test_network_diagnostics()
    
    # Test StockTitan alternatives
    print("\n" + "="*60)
    test_stocktitan_requests()
    test_stocktitan_api_endpoints()
    test_stocktitan_rss()
    
    # Test HedgeFollow alternatives
    print("\n" + "="*60)
    test_hedgefollow_requests()
    test_hedgefollow_api()
    
    # Compare with existing Selenium methods
    print("\n" + "="*60)
    compare_with_existing_selenium()
    
    print(f"\nTest completed at: {datetime.now()}")
    print("\nCheck /tmp/ directory for saved HTML and response files")
    print("\nRecommendations will be based on which methods successfully retrieved data.")


if __name__ == "__main__":
    main()
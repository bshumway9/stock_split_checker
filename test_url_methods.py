#!/usr/bin/env python3
"""
Enhanced URL fetching test - tests multiple methods for the exact same URLs used in table_scrapers.py
"""

import requests
import time
import logging
from datetime import datetime
from bs4 import BeautifulSoup
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# URLs from table_scrapers.py
HEDGEFOLLOW_URL = "https://www.hedgefollow.com/upcoming-stock-splits.php"
STOCKTITAN_URL = "https://www.stocktitan.net/news/stock-splits.html"

def test_different_user_agents(url, site_name):
    """Test different User-Agent strings to see what works best"""
    print(f"\n=== Testing Different User Agents for {site_name} ===")
    
    user_agents = [
        # Chrome on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        # Firefox on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        # Safari on macOS
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Version/17.1 Safari/537.36',
        # Edge on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        # Simple bot user agent
        'python-requests/2.31.0',
        # No user agent
        None
    ]
    
    results = []
    
    for i, ua in enumerate(user_agents):
        try:
            headers = {}
            if ua:
                headers['User-Agent'] = ua
                print(f"\nTesting UA {i+1}: {ua[:50]}{'...' if len(ua) > 50 else ''}")
            else:
                print(f"\nTesting UA {i+1}: No User-Agent header")
            
            start_time = time.time()
            response = requests.get(url, headers=headers, timeout=15)
            end_time = time.time()
            
            result = {
                'user_agent': ua or 'None',
                'status_code': response.status_code,
                'response_time': end_time - start_time,
                'content_length': len(response.content),
                'success': response.status_code == 200
            }
            
            results.append(result)
            
            if response.status_code == 200:
                print(f"✓ SUCCESS - Status: {response.status_code}, Time: {result['response_time']:.2f}s, Size: {result['content_length']} bytes")
            else:
                print(f"✗ FAILED - Status: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"✗ TIMEOUT after 15 seconds")
            results.append({'user_agent': ua or 'None', 'status_code': 'TIMEOUT', 'success': False})
        except requests.exceptions.RequestException as e:
            print(f"✗ REQUEST ERROR: {e}")
            results.append({'user_agent': ua or 'None', 'status_code': f'ERROR: {e}', 'success': False})
        except Exception as e:
            print(f"✗ OTHER ERROR: {e}")
            results.append({'user_agent': ua or 'None', 'status_code': f'EXCEPTION: {e}', 'success': False})
        
        # Small delay between requests
        time.sleep(1)
    
    # Summary
    successful = [r for r in results if r.get('success', False)]
    print(f"\n--- {site_name} User Agent Test Summary ---")
    print(f"Successful requests: {len(successful)}/{len(results)}")
    
    if successful:
        fastest = min(successful, key=lambda x: x.get('response_time', float('inf')))
        print(f"Fastest successful UA: {fastest['user_agent'][:60]}{'...' if len(fastest['user_agent']) > 60 else ''}")
        print(f"  Time: {fastest.get('response_time', 'N/A'):.2f}s")
    
    return results


def test_different_headers(url, site_name):
    """Test different combinations of HTTP headers"""
    print(f"\n=== Testing Different Header Combinations for {site_name} ===")
    
    header_combinations = [
        # Minimal headers
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        },
        
        # Standard browser headers
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        },
        
        # Full browser headers with cache control
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        },
        
        # Mobile browser headers
        {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br'
        }
    ]
    
    results = []
    
    for i, headers in enumerate(header_combinations):
        try:
            print(f"\nTesting header combination {i+1}:")
            for key, value in headers.items():
                print(f"  {key}: {value[:60]}{'...' if len(value) > 60 else ''}")
            
            start_time = time.time()
            response = requests.get(url, headers=headers, timeout=15)
            end_time = time.time()
            
            result = {
                'combination': i+1,
                'headers': headers,
                'status_code': response.status_code,
                'response_time': end_time - start_time,
                'content_length': len(response.content),
                'success': response.status_code == 200
            }
            
            results.append(result)
            
            if response.status_code == 200:
                print(f"✓ SUCCESS - Status: {response.status_code}, Time: {result['response_time']:.2f}s, Size: {result['content_length']} bytes")
                
                # Quick check if we can find expected content
                soup = BeautifulSoup(response.content, 'html.parser')
                if site_name == "HedgeFollow":
                    table = soup.find('table', {'id': 'latest_splits'})
                    print(f"  Found latest_splits table: {'✓' if table else '✗'}")
                elif site_name == "StockTitan":
                    news_feed = soup.find('div', {'id': 'live-news-feed'})
                    print(f"  Found live-news-feed div: {'✓' if news_feed else '✗'}")
            else:
                print(f"✗ FAILED - Status: {response.status_code}")
                
        except Exception as e:
            print(f"✗ ERROR: {e}")
            results.append({'combination': i+1, 'status_code': f'ERROR: {e}', 'success': False})
        
        time.sleep(1)
    
    return results


def test_sessions_vs_single_requests(url, site_name):
    """Test whether using sessions vs single requests makes a difference"""
    print(f"\n=== Testing Sessions vs Single Requests for {site_name} ===")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive'
    }
    
    results = []
    
    # Test single request
    print("\n1. Testing single request...")
    try:
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=15)
        end_time = time.time()
        
        results.append({
            'method': 'Single Request',
            'status_code': response.status_code,
            'response_time': end_time - start_time,
            'content_length': len(response.content),
            'success': response.status_code == 200
        })
        
        print(f"Status: {response.status_code}, Time: {end_time - start_time:.2f}s")
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        results.append({'method': 'Single Request', 'status_code': f'ERROR: {e}', 'success': False})
    
    time.sleep(2)
    
    # Test with session
    print("\n2. Testing with session...")
    try:
        session = requests.Session()
        session.headers.update(headers)
        
        start_time = time.time()
        response = session.get(url, timeout=15)
        end_time = time.time()
        
        results.append({
            'method': 'Session',
            'status_code': response.status_code,
            'response_time': end_time - start_time,
            'content_length': len(response.content),
            'success': response.status_code == 200
        })
        
        print(f"Status: {response.status_code}, Time: {end_time - start_time:.2f}s")
        session.close()
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        results.append({'method': 'Session', 'status_code': f'ERROR: {e}', 'success': False})
    
    return results


def test_content_parsing(url, site_name):
    """Test if we can successfully parse the expected content from the URL"""
    print(f"\n=== Testing Content Parsing for {site_name} ===")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    
    try:
        print(f"Fetching {url}...")
        response = requests.get(url, headers=headers, timeout=20)
        
        if response.status_code != 200:
            print(f"✗ Failed to fetch page: Status {response.status_code}")
            return False
        
        print(f"✓ Page fetched successfully: {len(response.content)} bytes")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        print(f"✓ Page parsed with BeautifulSoup")
        print(f"  Page title: {soup.title.string if soup.title else 'No title'}")
        
        if site_name == "HedgeFollow":
            return test_hedgefollow_parsing(soup)
        elif site_name == "StockTitan":
            return test_stocktitan_parsing(soup)
        
    except Exception as e:
        print(f"✗ Error during content parsing test: {e}")
        return False


def test_hedgefollow_parsing(soup):
    """Test parsing HedgeFollow content"""
    print("\n--- HedgeFollow Content Analysis ---")
    
    # Look for the expected table
    table = soup.find('table', {'id': 'latest_splits'})
    if table:
        print("✓ Found 'latest_splits' table")
        
        rows = table.find_all('tr')
        print(f"✓ Found {len(rows)} rows in table")
        
        if len(rows) > 1:
            # Check header row
            header_row = rows[0]
            headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]
            print(f"✓ Table headers: {headers}")
            
            # Check first few data rows
            for i, row in enumerate(rows[1:3]):
                cells = row.find_all(['td', 'th'])
                cell_data = [cell.get_text().strip() for cell in cells]
                print(f"  Row {i+1}: {cell_data}")
            
            return True
        else:
            print("✗ No data rows found")
            return False
    else:
        print("✗ 'latest_splits' table not found")
        
        # Look for alternative table structures
        all_tables = soup.find_all('table')
        print(f"  Found {len(all_tables)} total tables on page")
        
        for i, table in enumerate(all_tables):
            table_id = table.get('id', f'no-id-{i}')
            rows = table.find_all('tr')
            print(f"  Table {i+1} (id='{table_id}'): {len(rows)} rows")
        
        return False


def test_stocktitan_parsing(soup):
    """Test parsing StockTitan content"""
    print("\n--- StockTitan Content Analysis ---")
    
    # Look for the live news feed
    news_feed = soup.find('div', {'id': 'live-news-feed'})
    if news_feed:
        print("✓ Found 'live-news-feed' div")
        
        # Look for news rows
        news_rows = news_feed.find_all('div', class_='news-row')
        print(f"✓ Found {len(news_rows)} news rows")
        
        if news_rows:
            # Analyze first few rows
            split_articles = 0
            for i, row in enumerate(news_rows[:5]):
                row_text = row.get_text().lower()
                has_split = 'stock split' in row_text or 'share split' in row_text
                
                if has_split:
                    split_articles += 1
                    print(f"  Row {i+1}: Contains split content ✓")
                    
                    # Try to extract ticker
                    ticker_elements = row.find_all('span', class_='feed-ticker')
                    if ticker_elements:
                        symbol_link = ticker_elements[0].find('a', class_='symbol-link')
                        if symbol_link:
                            symbol = symbol_link.get_text().strip()
                            print(f"    Symbol found: {symbol}")
                else:
                    print(f"  Row {i+1}: No split content")
            
            print(f"✓ Found {split_articles} articles mentioning splits out of {min(5, len(news_rows))} checked")
            return split_articles > 0
        else:
            print("✗ No news rows found in feed")
            return False
    else:
        print("✗ 'live-news-feed' div not found")
        
        # Look for alternative structures
        news_divs = soup.find_all('div', id=lambda x: x and 'news' in x.lower())
        print(f"  Found {len(news_divs)} divs with 'news' in id")
        
        feed_divs = soup.find_all('div', id=lambda x: x and 'feed' in x.lower())
        print(f"  Found {len(feed_divs)} divs with 'feed' in id")
        
        return False


def main():
    """Run all URL fetching tests"""
    print("="*80)
    print("ENHANCED URL FETCHING TEST SUITE")
    print("Testing multiple methods for the exact URLs from table_scrapers.py")
    print("="*80)
    print(f"Started at: {datetime.now()}")
    
    sites_to_test = [
        (HEDGEFOLLOW_URL, "HedgeFollow"),
        (STOCKTITAN_URL, "StockTitan")
    ]
    
    all_results = {}
    
    for url, site_name in sites_to_test:
        print(f"\n{'='*20} TESTING {site_name.upper()} {'='*20}")
        print(f"URL: {url}")
        
        site_results = {}
        
        # Test 1: Different User Agents
        site_results['user_agents'] = test_different_user_agents(url, site_name)
        
        # Test 2: Different Headers
        site_results['headers'] = test_different_headers(url, site_name)
        
        # Test 3: Sessions vs Single Requests
        site_results['sessions'] = test_sessions_vs_single_requests(url, site_name)
        
        # Test 4: Content Parsing
        site_results['parsing_success'] = test_content_parsing(url, site_name)
        
        all_results[site_name] = site_results
        
        print(f"\n--- {site_name} Summary ---")
        ua_success = len([r for r in site_results['user_agents'] if r.get('success', False)])
        header_success = len([r for r in site_results['headers'] if r.get('success', False)])
        session_success = len([r for r in site_results['sessions'] if r.get('success', False)])
        
        print(f"User Agent tests successful: {ua_success}/{len(site_results['user_agents'])}")
        print(f"Header tests successful: {header_success}/{len(site_results['headers'])}")
        print(f"Session tests successful: {session_success}/{len(site_results['sessions'])}")
        print(f"Content parsing successful: {'✓' if site_results['parsing_success'] else '✗'}")
    
    # Final recommendations
    print(f"\n{'='*80}")
    print("FINAL RECOMMENDATIONS")
    print("="*80)
    
    for site_name, results in all_results.items():
        print(f"\n{site_name}:")
        
        if results['parsing_success']:
            print(f"  ✓ Content can be successfully parsed with requests + BeautifulSoup")
            print(f"  ✓ Recommended approach: Use requests instead of Selenium")
        else:
            print(f"  ✗ Content parsing failed - may require Selenium for JavaScript rendering")
            print(f"  ✗ Recommended approach: Stick with Selenium or investigate further")
        
        # Find best performing configuration
        successful_ua = [r for r in results['user_agents'] if r.get('success', False)]
        if successful_ua:
            fastest_ua = min(successful_ua, key=lambda x: x.get('response_time', float('inf')))
            print(f"  ✓ Best User Agent: {fastest_ua['user_agent'][:50]}...")
            print(f"    Response time: {fastest_ua.get('response_time', 'N/A'):.2f}s")
    
    print(f"\nTest completed at: {datetime.now()}")


if __name__ == "__main__":
    main()
import logging
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
from helper_functions import next_market_day


def scrape_yahoo_finance_selenium():
    """
    Scrape upcoming stock splits from Yahoo Finance calendar using Selenium for the next 3 market days.
    Handles JavaScript-rendered content and dynamic tables.
    Implements retry logic with up to 2 additional attempts if table container approach fails.
    Saves screenshots and HTML to logs/ directory before each refresh attempt for debugging.
    Returns a list of dictionaries containing split information.
    """
    splits = []
    driver = None
    
    try:
        # Set up Chrome options for headless browsing
        chrome_options = Options()
        # Use new headless mode for better memory efficiency (Chrome 109+)
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # Memory-saving Chrome flags
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
        # Block images to save memory
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        
        # Initialize the Chrome WebDriver
        logging.info("Initializing Chrome WebDriver for Yahoo Finance scraping")
        driver = webdriver.Chrome(options=chrome_options)
        
        # Get the next 3 market days
        current_date = datetime.now().date()
        market_days = []
        for i in range(3):
            if i == 0:
                market_day = next_market_day(current_date)
            else:
                market_day = next_market_day(market_days[-1])
            market_days.append(market_day)
        
        logging.info(f"Scraping Yahoo Finance for 3 market days: {[day.strftime('%Y-%m-%d') for day in market_days]}")
        
        # Loop through each market day
        for day_index, market_day in enumerate(market_days):
            day_str = market_day.strftime('%Y-%m-%d')
            logging.info(f"Scraping day {day_index + 1}/3: {day_str}")

            # Yahoo Finance splits calendar URL for the current market day
            url = f"https://finance.yahoo.com/calendar/splits?day={day_str}&size=100"
            logging.info(f"Navigating to Yahoo Finance splits calendar: {url}")
            driver.get(url)
            
            # Give the page a moment to load all JavaScript content
            time.sleep(2)
            
            # Log the page title to help with debugging
            logging.info(f"Page title for {day_str}: {driver.title}")
            
            # Check if we need to handle consent dialogs or other overlays (only on first day)
            if day_index == 0:
                try:
                    consent_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Consent') or contains(text(), 'I agree')]")
                    if consent_buttons:
                        logging.info("Found consent dialog, attempting to accept")
                        for button in consent_buttons:
                            if button.is_displayed():
                                button.click()
                                time.sleep(1)
                                logging.info("Clicked consent button")
                                break
                except Exception as e:
                    logging.warning(f"Error handling consent dialog: {e}")
            
            # Wait for the page to load and the table to be present
            wait = WebDriverWait(driver, 15)
            
            # Try up to 3 times (initial attempt + 2 retries)
            max_retries = 2
            retries = 0
            table = None
            
            while retries <= max_retries:
                try:
                    # First try to find the table container div
                    logging.info(f"Looking for table container div for {day_str} (attempt {retries + 1}/{max_retries + 1})")
                    table_container = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "table-container")))
                    logging.info(f"Table container div found for {day_str}")
                    
                    # Then find the table inside the container
                    table = table_container.find_element(By.TAG_NAME, "table")
                    logging.info(f"Yahoo Finance splits table found inside table-container for {day_str}")
                    
                    # If we found the table, break out of the retry loop
                    break
                    
                except TimeoutException:
                    logging.info(f"Table container approach failed on attempt {retries + 1} for {day_str}")
                    if retries < max_retries:
                        # Save screenshot and HTML before reloading
                        try:
                            # Ensure logs directory exists
                            import os
                            logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
                            os.makedirs(logs_dir, exist_ok=True)
                            
                            # Generate timestamp for unique filenames
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            
                            # Save screenshot
                            screenshot_path = os.path.join(logs_dir, f"yahoo_finance_{day_str}_before_refresh_{timestamp}_attempt{retries+1}.png")
                            driver.save_screenshot(screenshot_path)
                            logging.info(f"Screenshot saved to {screenshot_path}")
                            
                            # Save HTML
                            html_path = os.path.join(logs_dir, f"yahoo_finance_{day_str}_before_refresh_{timestamp}_attempt{retries+1}.html")
                            with open(html_path, "w", encoding="utf-8") as f:
                                f.write(driver.page_source)
                            logging.info(f"HTML saved to {html_path}")
                        except Exception as e:
                            logging.error(f"Error saving debug files: {e}")
                        
                        # Reload the page and try again
                        logging.info(f"Reloading page and retrying (retry {retries + 1}/{max_retries}) for {day_str}")
                        driver.refresh()
                        time.sleep(3)  # Give the page time to reload
                        retries += 1
                    else:
                        # If we've exhausted retries, try alternative selectors
                        logging.info(f"All retries failed for {day_str}, trying alternative selectors")
                        try:
                            # Try the data-test attribute
                            table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table[data-test='splits-table']")))
                            logging.info(f"Yahoo Finance splits table found by data-test attribute for {day_str}")
                        except TimeoutException:
                            # As a last resort, try any table
                            try:
                                table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
                                logging.info(f"Found generic table on Yahoo Finance for {day_str}")
                            except TimeoutException:
                                logging.warning(f"No tables found on Yahoo Finance page for {day_str}")
                                continue  # Skip to next day
            
            if not table:
                logging.warning(f"Could not find table for {day_str}, skipping to next day")
                continue
            
            # Log the table HTML for debugging
            table_html = table.get_attribute('outerHTML')
            logging.info(f"Table HTML structure for {day_str} (first 500 chars): {table_html[:500]}")
            
            # Extract the table rows
            rows = table.find_elements(By.TAG_NAME, "tr")
            if len(rows) <= 1:  # Only header row exists
                logging.info(f"Yahoo Finance splits table has no data rows for {day_str}")
                
                # Check if there might be a "No results" message
                try:
                    no_results = driver.find_elements(By.XPATH, "//*[contains(text(), 'No results') or contains(text(), 'no data')]")
                    if no_results:
                        logging.info(f"Found 'No results' message on the page for {day_str}")
                except Exception:
                    pass
                    
                continue  # Skip to next day
            
            # Log the header row to understand the column structure
            try:
                header_row = rows[0]
                header_cells = header_row.find_elements(By.TAG_NAME, "th")
                header_texts = [cell.text.strip() for cell in header_cells]
                logging.info(f"Table header columns for {day_str}: {header_texts}")
            except Exception as e:
                logging.warning(f"Error processing header row for {day_str}: {e}")
            
            # Skip the header row
            rows = rows[1:]
            logging.info(f"Found {len(rows)} rows in Yahoo Finance splits table for {day_str}")
            
            day_splits_count = 0
            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 4:  # Need Symbol, Name, Date, Ratio
                        logging.warning(f"Row has insufficient cells: {len(cells)} for {day_str}")
                        logging.warning(f"Row content: {row.text}")
                        continue
                    
                    # Log the row content to help debug
                    # row_text = row.text
                    # logging.info(f"Processing row: {row_text[:100]}")
                    
                    # Extract data from cells - using adaptive approach based on header
                    cell_texts = [cell.text.strip() for cell in cells]
                    logging.debug(f"Cell texts for {day_str}: {cell_texts}")
                    # logging.info("-------------------------------------")
                    # for i, cell_text in enumerate(cell_texts):
                    #     logging.info(f"Cell {i}: {cell_text}")
                    # Standard Yahoo Finance format
                    symbol = cells[0].text.strip()
                    if "." in symbol:
                        continue  # Skip rows with dots in ticker (unbuyable stocks)
                    company = cells[1].text.strip()
                    date_text = cells[2].text.strip()
                    ratio = cells[4].text.strip()
                    
                    # If the format doesn't match what we expect, try to adapt
                    if not symbol or not date_text or not ratio:
                        logging.warning(f"Standard column format doesn't seem right for {day_str}, trying to identify columns by content")
                        
                        # Try to identify columns by looking at the content pattern
                        for i, cell_text in enumerate(cell_texts):
                            # Symbol is typically 1-5 uppercase letters, possibly with a period
                            if re.match(r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$', cell_text) and not symbol:
                                symbol = cell_text
                                logging.info(f"Identified symbol '{symbol}' at position {i} for {day_str}")
                            
                            # Date typically contains a month abbreviation and numbers
                            elif re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', cell_text) and not date_text:
                                date_text = cell_text
                                logging.info(f"Identified date '{date_text}' at position {i} for {day_str}")
                            
                            # Ratio typically contains a colon or 'for' or numbers
                            elif ((':' in cell_text or 'for' in cell_text.lower() or 
                                  re.search(r'\d+\s*:\s*\d+', cell_text)) and not ratio):
                                ratio = cell_text
                                logging.info(f"Identified ratio '{ratio}' at position {i} for {day_str}")
                    
                    # Skip if essential data is missing
                    if not symbol or not date_text or not ratio:
                        continue
                    
                    # Parse date (Yahoo format is typically "Aug 04, 2025")
                    try:
                        date_obj = datetime.strptime(date_text, '%b %d, %Y')
                        effective_date = date_obj.strftime('%Y-%m-%d')
                        split_date = date_obj.date()
                        
                        # Only include splits from the current market day or future dates
                        # (since we're scraping specific days, we want all splits from those days)
                        current_market_day = market_day
                        if split_date < current_market_day:
                            # logging.info(f"Skipping past Yahoo Finance split: {symbol} on {effective_date}")
                            continue
                            
                    except ValueError as e:
                        logging.warning(f"Could not parse Yahoo Finance date '{date_text}' for {day_str}: {e}")
                        continue
                    
                    # Determine if this is a reverse split
                    is_reverse = False
                    # Handle "250.00 - 1.00" or "1:10" or "1-for-10" formats
                    if "-" in ratio:
                        parts = ratio.split("-")
                        if len(parts) == 2:
                            try:
                                left = float(parts[0].strip())
                                right = float(parts[1].strip())
                                is_reverse = right < left  # e.g., 10.00 - 1.00 is a reverse split
                                ratio = f"{left}->{right}"  # Normalize to "10.00->1.00" format
                            except ValueError:
                                pass
                    elif ":" in ratio:
                        parts = ratio.split(":")
                        if len(parts) == 2:
                            try:
                                left = float(parts[0].strip())
                                right = float(parts[1].strip())
                                is_reverse = left < right
                            except ValueError:
                                pass
                    elif "for" in ratio.lower():
                        match = re.search(r'(\d+(?:\.\d+)?)\s*for\s*(\d+(?:\.\d+)?)', ratio.lower())
                        if match:
                            left = float(match.group(1))
                            right = float(match.group(2))
                            is_reverse = left < right
                    
                    split_type = "Reverse Split" if is_reverse else "Forward Split"
                    
                    split_info = {
                        'symbol': symbol,
                        'company': company,
                        'ratio': ratio,
                        'effective_date': effective_date,
                        'fractional': 'Not specified',
                        'is_reverse': is_reverse,
                        'source': 'Yahoo Finance',
                        'article_link': []
                    }
                    
                    splits.append(split_info)
                    day_splits_count += 1
                    logging.info(f"Found Yahoo Finance split for {day_str}: {symbol} - {ratio} on {effective_date}")
                    
                except Exception as e:
                    logging.error(f"Error processing Yahoo Finance row for {day_str}: {e}")
                    continue
            
            logging.info(f"Found {day_splits_count} splits for {day_str}")
        
        logging.info(f"Successfully scraped {len(splits)} total splits from Yahoo Finance across 3 market days")
        
    except Exception as e:
        logging.error(f"Error scraping Yahoo Finance with Selenium: {e}")
        raise  # Raise so retry logic can catch
    finally:
        # Always close the WebDriver to free resources
        if driver:
            try:
                driver.quit()
                logging.info("Yahoo Finance WebDriver closed successfully")
            except Exception as e:
                logging.error(f"Error closing Yahoo Finance WebDriver: {e}")
    return splits







def scrape_hedge_follow():
    """
    Scrape upcoming stock splits from HedgeFollow.com using Selenium.
    Returns a list of dictionaries containing split information.
    """
    splits = []
    past_splits = []
    driver = None
    
    try:
        # Set up Chrome options for headless browsing
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
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
        logging.info("Initializing Chrome WebDriver for HedgeFollow scraping")
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to HedgeFollow's upcoming stock splits page
        url = "https://www.hedgefollow.com/upcoming-stock-splits.php"
        logging.info(f"Navigating to {url}")
        driver.get(url)
        
        # Wait for the latest_splits table to load
        wait = WebDriverWait(driver, 10)
        table = wait.until(EC.presence_of_element_located((By.ID, "latest_splits")))
        
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
                past_split = False
                # Extract data from cells
                company = cells[2].text.strip()
                market = cells[1].text.strip()
                symbol = cells[0].text.strip()
                date_text = cells[4].text.strip()
                ratio = cells[3].text.strip()
                
                # Skip if essential data is missing
                if not symbol or not date_text or not ratio or market.lower() == "otc":
                    continue
                
                # Parse date (format is YYYY-MM-DD)
                try:
                    date_obj = datetime.strptime(date_text, '%Y-%m-%d')
                    effective_date = date_obj.strftime('%Y-%m-%d')
                    split_date = date_obj.date()
                    
                    # Skip past splits
                    if split_date < next_day:
                        past_split = True
                        # logging.info(f"Skipping past split: {symbol} on {effective_date}")
                        # continue
                        
                except ValueError as e:
                    logging.warning(f"Could not parse HedgeFollow date '{date_text}': {e}")
                    continue
                
                # Determine if this is a reverse split (if ratio contains :)
                is_reverse = False
                if ":" in ratio:
                    try:
                        left, right = map(float, ratio.split(":"))
                        is_reverse = left < right  # e.g., 1:10 is a reverse split
                        ratio = f"{right}->{left}"  # Normalize to "10->1" format
                    except ValueError:
                        pass
                
                split_type = "Reverse Split" if is_reverse else "Forward Split"
                
                split_info = {
                    'symbol': symbol,
                    'company': company,
                    'ratio': ratio,
                    'effective_date': effective_date,
                    'fractional': 'Not specified',
                    'is_reverse': is_reverse,
                    'article_link': []
                }
                if past_split:
                    past_splits.append(split_info)
                else:
                    splits.append(split_info)
                    logging.info(f"Found HedgeFollow split: {symbol} - {ratio} on {effective_date}")
                
            except Exception as e:
                logging.error(f"Error processing HedgeFollow row: {e}")
                continue
        
        logging.info(f"Successfully scraped {len(splits)} splits from HedgeFollow")
        
    except Exception as e:
        logging.error(f"Error scraping HedgeFollow: {e}")
        raise
    finally:
        # Always close the WebDriver to free resources
        if driver:
            try:
                driver.quit()
                logging.info("WebDriver closed successfully")
            except Exception as e:
                logging.error(f"Error closing WebDriver: {e}")
    return splits, past_splits






def scrape_stock_titan(max_retries=3, retry_delay=5):
    """
    Scrape upcoming stock splits from StockTitan.net using Selenium with retry logic.
    Returns a tuple: (recent_splits, all_splits_with_links) where recent_splits contains
    only splits from the last week, and all_splits_with_links contains all splits with
    article links for potential matching with existing data.
    
    Args:
        max_retries (int): Maximum number of retry attempts (default: 3)
        retry_delay (int): Delay in seconds between retries (default: 5)
    """
    recent_splits = []
    all_splits_with_links = []
    driver = None
    
    for attempt in range(max_retries + 1):  # +1 because we want max_retries actual retries after the first attempt
        try:
            logging.info(f"StockTitan scraping attempt {attempt + 1}/{max_retries + 1}")
            
            # Set up Chrome options for headless browsing
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
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
            # Only run one Chrome WebDriver at a time for lowest memory usage
            
            # Initialize the Chrome WebDriver
            logging.info("Initializing Chrome WebDriver for StockTitan scraping")
            driver = webdriver.Chrome(options=chrome_options)
            
            # Navigate to StockTitan stock splits page
            url = "https://www.stocktitan.net/news/stock-splits.html"
            logging.info(f"Navigating to {url}")
            driver.get(url)
            
            # Give the page a moment to load JavaScript content
            time.sleep(3)
            
            # Log the page title for debugging
            logging.info(f"Page title: {driver.title}")
            
            # Wait for the live news feed to be present
            wait = WebDriverWait(driver, 15)
            
            # Find the live news feed container
            news_feed = wait.until(EC.presence_of_element_located((By.ID, "live-news-feed")))
            logging.info("StockTitan live news feed found")
            
            # Get all news rows from the feed
            news_rows = news_feed.find_elements(By.CSS_SELECTOR, "div.news-row[data-news-id]")
            logging.info(f"Found {len(news_rows)} news articles in StockTitan feed")
            
            # If we successfully got this far, break out of the retry loop
            break
            
        except Exception as e:
            logging.warning(f"StockTitan scraping attempt {attempt + 1} failed: {e}")
            
            # Close the driver if it was created
            if driver:
                try:
                    driver.quit()
                    driver = None
                except Exception as cleanup_error:
                    logging.warning(f"Error closing driver during retry: {cleanup_error}")
            
            # If this was the last attempt, re-raise the exception
            if attempt == max_retries:
                logging.error(f"All {max_retries + 1} StockTitan scraping attempts failed")
                raise e
            
            # Wait before retrying
            logging.info(f"Waiting {retry_delay} seconds before retry...")
            time.sleep(retry_delay)
            continue
    
    try:
        # Get today's date for filtering
        prev_week = next_market_day(datetime.now().date(), previous=True, days=5)

        # Process each news row
        for row in news_rows:
            try:
                # Check if this article is about stock splits by looking for stock split tag
                tags = row.find_elements(By.CSS_SELECTOR, "span.badge.tag a")
                is_split_article = any("stock split" in tag.text.lower() for tag in tags)
                
                if not is_split_article:
                    continue
                
                # Extract the ticker information (only process the first ticker)
                ticker_elements = row.find_elements(By.CSS_SELECTOR, "div[name='tickers'] span.feed-ticker")
                if not ticker_elements:
                    continue
                
                # Only process the first ticker in the article
                ticker_element = ticker_elements[0]
                try:
                    # Extract symbol and exchange
                    symbol_link = ticker_element.find_element(By.CSS_SELECTOR, "a.symbol-link")
                    symbol = symbol_link.text.strip()
                    
                    # Get the exchange text (appears after the colon)
                    ticker_text = ticker_element.text.strip()
                    if ":" in ticker_text:
                        exchange = ticker_text.split(":")[-1].strip()
                    else:
                        exchange = "Unknown"
                    
                    # Skip OTC stocks as requested
                    if exchange.upper() == "OTC":
                        # logging.info(f"Skipping OTC stock: {symbol}")
                        continue
                    
                    # Extract the title
                    title_element = row.find_element(By.CSS_SELECTOR, "div[name='title'] a.feed-link")
                    title = title_element.text.strip()
                    
                    # Extract the date
                    date_element = row.find_element(By.CSS_SELECTOR, "time.news-row-datetime span.date")
                    date_text = date_element.text.strip()
                    
                    # Parse date (format is MM/DD/YYYY)
                    try:
                        date_obj = datetime.strptime(date_text, '%m/%d/%Y')
                        effective_date = date_obj.strftime('%Y-%m-%d')
                        split_date = date_obj.date()
                        
                        # Skip past splits
                        if split_date < prev_week:
                            # logging.info(f"Skipping past StockTitan split: {symbol} on {effective_date}")
                            continue
                            
                    except ValueError as e:
                        logging.warning(f"Could not parse StockTitan date '{date_text}': {e}")
                        # Use current date as fallback
                        effective_date = datetime.now().strftime('%Y-%m-%d')
                    
                    # Determine split type and ratio from title
                    is_reverse = False
                    ratio = "Not specified"
                    
                    title_lower = title.lower()
                    
                    # Look for reverse split indicators
                    if "reverse" in title_lower:
                        is_reverse = True
                        
                        # Try to extract ratio from common patterns
                        import re
                        # Pattern like "1-for-10", "1:10", "1 for 10"
                        ratio_patterns = [
                            r'(\d+)[-\s]*for[-\s]*(\d+)',
                            r'(\d+):(\d+)',
                            r'(\d+)[-\s]*to[-\s]*(\d+)'
                        ]
                        
                        for pattern in ratio_patterns:
                            match = re.search(pattern, title_lower)
                            if match:
                                left = match.group(1)
                                right = match.group(2)
                                ratio = f"{left}:{right}"
                                break
                    
                    # Look for forward split indicators
                    elif any(keyword in title_lower for keyword in ["stock split", "share split"]) and "reverse" not in title_lower:
                        # Try to extract forward split ratio
                        import re
                        # Pattern like "3-for-2", "4-for-1"
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
                                # If left > right, it's a forward split
                                if left > right:
                                    ratio = f"{left}:{right}"
                                # If right > left, it might be expressed backwards
                                else:
                                    ratio = f"{right}:{left}"
                                    is_reverse = True
                                break
                    
                    
                    # Extract the article link (always store as array)
                    article_links = []
                    try:
                        title_element = row.find_element(By.CSS_SELECTOR, "div[name='title'] a.feed-link")
                        article_link = title_element.get_attribute('href')
                        article_links.append(article_link)
                        logging.info(f"Found article link for {symbol}: {article_link}")
                    except Exception as e:
                        logging.warning(f"Could not extract article link for {symbol}: {e}")
                    
                    split_info = {
                        'symbol': symbol,
                        'ratio': ratio,
                        'effective_date': effective_date,
                        'fractional': 'Not specified',
                        'is_reverse': is_reverse,
                        'source': 'StockTitan',
                        'exchange': exchange,
                        'title': title,
                        'article_link': article_links
                    }
                    
                    # Add to appropriate lists
                    if split_date >= prev_week:
                        recent_splits.append(split_info)
                        logging.info(f"Found recent StockTitan split: {symbol} ({exchange}) - {ratio} on {effective_date}")
                    
                    # Add to all splits list if it has article links
                    if article_links:
                        all_splits_with_links.append(split_info)
                        # logging.info(f"Added {symbol} to all splits with links")
                        
                except Exception as e:
                    logging.error(f"Error processing StockTitan ticker in row: {e}")
                    continue
                    
            except Exception as e:
                logging.error(f"Error processing StockTitan news row: {e}")
                continue
        
        logging.info(f"Successfully scraped {len(recent_splits)} recent splits and {len(all_splits_with_links)} total splits with links from StockTitan")
        
    except Exception as e:
        logging.error(f"Error processing StockTitan data: {e}")
        raise
    finally:
        # Always close the WebDriver to free resources
        if driver:
            try:
                driver.quit()
                logging.info("StockTitan WebDriver closed successfully")
            except Exception as e:
                logging.error(f"Error closing StockTitan WebDriver: {e}")
    return recent_splits, all_splits_with_links


def scrape_nasdaq():
    """
    Scrape upcoming stock splits from Nasdaq.com using Selenium.
    Returns a list of dictionaries containing split information.
    """
    splits = []
    driver = None
    
    try:
        # Set up Chrome options for headless browsing
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
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
        logging.info("Initializing Chrome WebDriver for Nasdaq scraping")
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to Nasdaq stock splits page
        url = "https://www.nasdaq.com/market-activity/stock-splits"
        logging.info(f"Navigating to {url}")
        driver.get(url)
        
        # Give the page a moment to load JavaScript content
        time.sleep(3)
        
        # Log the page title for debugging
        logging.info(f"Page title: {driver.title}")
        
        # Wait for the table to be present
        wait = WebDriverWait(driver, 15)
        
        # Let's log the page source to debug what classes are actually present
        logging.info("Capturing Nasdaq page structure for debugging")
        page_source = driver.page_source[:5000]  # First 5000 chars to avoid overly large logs
        logging.info(f"Nasdaq page structure preview: {page_source}")
        
        # Take a screenshot for debugging if needed
        try:
            driver.save_screenshot("/tmp/nasdaq_debug.png")
            logging.info("Screenshot saved to /tmp/nasdaq_debug.png")
        except Exception as e:
            logging.warning(f"Could not save screenshot: {e}")
        
        # Log all elements with 'table' or 'split' in their class names
        logging.info("Searching for table-related elements in the DOM")
        try:
            potential_tables = driver.find_elements(By.XPATH, "//*[contains(@class, 'table') or contains(@class, 'split')]")
            logging.info(f"Found {len(potential_tables)} potential table-related elements")
            for i, elem in enumerate(potential_tables[:10]):  # Log first 10 only
                logging.info(f"Potential table element {i}: Tag={elem.tag_name}, Class={elem.get_attribute('class')}")
        except Exception as e:
            logging.warning(f"Error searching for potential tables: {e}")
        
        try:
            # Try multiple different selectors to find the table
            selectors = [
                # Original selector
                (By.CLASS_NAME, "jupiter22-stock-splits__data"),
                # Try the div with role="table"
                (By.CSS_SELECTOR, "div[role='table']"),
                # Try the simple-table-template class
                (By.CLASS_NAME, "simple-table-template"),
                # Try any element with table-body
                (By.CSS_SELECTOR, "div.table-body[role='rowgroup']"),
                # Try any element containing table rows
                (By.CSS_SELECTOR, "div[role='row']")
            ]
            
            table_container = None
            table_body = None
            
            # Try each selector until we find something
            for selector_type, selector in selectors:
                try:
                    logging.info(f"Trying to find element with {selector_type}: {selector}")
                    elements = driver.find_elements(selector_type, selector)
                    if elements:
                        logging.info(f"Found {len(elements)} elements matching {selector}")
                        table_container = elements[0]
                        break
                except Exception as e:
                    logging.warning(f"Error with selector {selector}: {e}")
            
            if table_container:
                logging.info(f"Table container found: {table_container.tag_name}, Class: {table_container.get_attribute('class')}")
                
                # Try to find the table body
                try:
                    # First, try within the container
                    table_body = table_container.find_element(By.CSS_SELECTOR, "div.table-body[role='rowgroup']")
                    logging.info("Nasdaq splits table body found within container")
                except Exception:
                    # If not found in the container, try direct search
                    try:
                        table_body = driver.find_element(By.CSS_SELECTOR, "div.table-body[role='rowgroup']")
                        logging.info("Nasdaq splits table body found through direct search")
                    except Exception:
                        logging.warning("Could not find table body with role='rowgroup'")
                        # Try to find any element that might contain rows
                        table_body = table_container
            else:
                logging.warning("Could not find any suitable table container")
                # Try a last-resort approach - just look for rows directly
                rows = driver.find_elements(By.CSS_SELECTOR, "div[role='row']")
                if rows:
                    logging.info(f"Found {len(rows)} rows directly in the page")
                    # Process rows directly here instead of using undefined function
                    for row in rows:
                        try:
                            cells = row.find_elements(By.CSS_SELECTOR, "div[role='cell']")
                            if len(cells) >= 4:
                                # Extract basic information and add to splits
                                # This is simplified processing
                                splits.append({
                                    'symbol': cells[0].text.strip(),
                                    'company': cells[1].text.strip() if len(cells) > 1 else '',
                                    'ratio': cells[2].text.strip() if len(cells) > 2 else '',
                                    'effective_date': datetime.now().strftime('%Y-%m-%d'),
                                    'fractional': 'Not specified',
                                    'is_reverse': 'reverse' in row.text.lower()
                                })
                        except Exception as e:
                            logging.error(f"Error processing direct row: {e}")
                return splits
            
            # Get all rows from the table (except header row)
            if table_body:
                rows = table_body.find_elements(By.CSS_SELECTOR, "div[role='row']")
                if not rows:
                    # Try alternative selectors
                    rows = table_body.find_elements(By.CSS_SELECTOR, ".table-row")
                logging.info(f"Found {len(rows)} rows in Nasdaq splits table")
            
                # Skip the header row if it's included
                try:
                    header_rows = [row for row in rows if "header" in row.get_attribute("class").lower()]
                    if header_rows:
                        logging.info(f"Found {len(header_rows)} header rows, will exclude them")
                        rows = [row for row in rows if row not in header_rows]
                    
                    # Alternative approach - if we have a header row with column titles
                    for i, row in enumerate(rows):
                        if i == 0:  # Check if the first row is a header
                            cell_texts = [cell.text.strip().upper() for cell in row.find_elements(By.CSS_SELECTOR, "div[role='cell']")]
                            if "SYMBOL" in cell_texts or "COMPANY" in cell_texts or "RATIO" in cell_texts:
                                logging.info(f"First row appears to be header: {cell_texts}")
                                rows = rows[1:]  # Skip the first row
                                break
                except Exception as e:
                    logging.warning(f"Error handling header row: {e}")
            
            if not rows:
                logging.warning("No data rows found in the Nasdaq table")
                return splits
                
            logging.info(f"Found {len(rows)} data rows in Nasdaq splits table")
            
        except Exception as e:
            logging.warning(f"Error finding Nasdaq splits table: {e}")
            # Try to search for split data directly in the page as a last resort
            try:
                # Look for any elements that might contain stock split information
                logging.info("Attempting fallback to find any split information directly")
                split_elements = driver.find_elements(By.XPATH, 
                    "//*[contains(text(), 'Split') or contains(text(), 'split') or contains(text(), 'SPLIT')]")
                logging.info(f"Found {len(split_elements)} elements containing 'split' text")
                if split_elements:
                    for elem in split_elements[:5]:  # Log first 5
                        logging.info(f"Split element text: {elem.text[:100]}")
            except Exception:
                pass
                
            return splits
            
        # Get today's date for filtering
        next_day = next_market_day(datetime.now().date())
        
        # Process each row
        for row in rows:
            try:
                # Extract cells from each row
                cells = row.find_elements(By.CSS_SELECTOR, "div.table-cell[role='cell']")
                if len(cells) < 4:  # Need Symbol, Company, Ratio, Date
                    logging.warning(f"Row has insufficient cells: {len(cells)}")
                    continue
                
                # Extract data from cells
                symbol = cells[0].text.strip()
                # Check if there's a link inside the cell
                symbol_link = cells[0].find_elements(By.TAG_NAME, "a")
                if symbol_link and symbol_link[0].text.strip():
                    symbol = symbol_link[0].text.strip()
                
                company = cells[1].text.strip()
                ratio = cells[2].text.strip()
                date_text = cells[3].text.strip()
                
                # Skip if essential data is missing
                if not symbol or not date_text or not ratio:
                    logging.warning("Missing essential data in row")
                    continue
                
                # Parse date (format is typically MM/DD/YYYY)
                try:
                    # Handle multiple date formats that might appear
                    date_formats = ['%m/%d/%Y', '%Y-%m-%d', '%B %d, %Y']
                    date_obj = None
                    
                    for fmt in date_formats:
                        try:
                            date_obj = datetime.strptime(date_text, fmt)
                            break
                        except ValueError:
                            continue
                    
                    if not date_obj:
                        logging.warning(f"Could not parse Nasdaq date: {date_text}")
                        continue
                        
                    effective_date = date_obj.strftime('%Y-%m-%d')
                    split_date = date_obj.date()
                    
                    # Skip past splits
                    if split_date < next_day:
                        # logging.info(f"Skipping past Nasdaq split: {symbol} on {effective_date}")
                        continue
                        
                except Exception as e:
                    logging.warning(f"Date parsing error for '{date_text}': {e}")
                    continue
                
                # Determine if this is a reverse split
                is_reverse = False
                if ":" in ratio:
                    parts = ratio.replace(" ", "").split(":")
                    if len(parts) == 2:
                        try:
                            left = float(parts[0])
                            right = float(parts[1])
                            is_reverse = left < right  # e.g., 1:10 is a reverse split
                        except ValueError:
                            pass
                
                # Format title for display
                split_type = "Reverse Split" if is_reverse else "Forward Split"
                title = f"{company} ({symbol}) {split_type} {ratio} on {date_text}"
                
                split_info = {
                    'symbol': symbol,
                    'company': company,
                    'ratio': ratio,
                    'effective_date': effective_date,
                    'fractional': 'Not specified',
                    'title': title,
                    'is_reverse': is_reverse,
                    'source': 'Nasdaq',
                    'article_link': []
                }
                
                splits.append(split_info)
                logging.info(f"Found Nasdaq split: {symbol} - {ratio} on {effective_date}")
                
            except Exception as e:
                logging.error(f"Error processing Nasdaq row: {e}")
                continue
        
        logging.info(f"Successfully scraped {len(splits)} splits from Nasdaq")
        
    except Exception as e:
        logging.error(f"Error scraping Nasdaq: {e}")
        raise
    finally:
        # Always close the WebDriver to free resources
        if driver:
            try:
                driver.quit()
                logging.info("Nasdaq WebDriver closed successfully")
            except Exception as e:
                logging.error(f"Error closing Nasdaq WebDriver: {e}")
    return splits
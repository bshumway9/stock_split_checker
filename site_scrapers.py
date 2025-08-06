import re
from datetime import datetime
import logging
import requests
from bs4 import BeautifulSoup


def extract_split_ratio_from_title(title):
    """Extract split ratio from news title."""
    if not title:
        return 'Unknown'
    
    title = title.lower()
    
    # Look for patterns like "1-for-10", "1-for-25", "five-for-one", etc.
    patterns = [
        r'(\d+)-for-(\d+)',  # e.g., "1-for-10"
        r'(\d+)\s*for\s*(\d+)',  # e.g., "1 for 10"
        r'one-for-(\d+)',  # e.g., "one-for-10"
        r'(\w+)-for-one',  # e.g., "five-for-one"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            if 'one-for-' in pattern:
                return f"1-for-{match.group(1)}"
            elif '-for-one' in pattern:
                # Convert word numbers to digits
                word_to_num = {
                    'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
                    'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10'
                }
                word = match.group(1)
                num = word_to_num.get(word, word)
                return f"{num}-for-1"
            else:
                return f"{match.group(1)}-for-{match.group(2)}"
    
    # If reverse split is mentioned but no ratio found
    if 'reverse' in title:
        return 'Reverse split (ratio unknown)'
    elif 'split' in title:
        return 'Split (ratio unknown)'
    
    return 'Unknown'



def parse_stocktitan_date(date_str):
    """Parse date from StockTitan format (MM/DD/YYYY) to YYYY-MM-DD."""
    try:
        if not date_str:
            return None
        
        # Remove any extra whitespace
        date_str = date_str.strip()
        
        # Parse MM/DD/YYYY format
        date_obj = datetime.strptime(date_str, '%m/%d/%Y')
        return date_obj.strftime('%Y-%m-%d')
    except Exception as e:
        logging.error(f"Error parsing date '{date_str}': {e}")
        return None

def scrape_sec_edgar():
    """Scrape reverse stock split data from SEC.gov EDGAR filings."""
    try:
        url = "https://www.sec.gov/edgar/search/#/q=split&dateRange=custom&startdt=2025-07-23&enddt=2025-07-23"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        logging.info(soup)
        # Placeholder for parsing SEC data (simplified due to JavaScript-heavy page)
        # In practice, you may need Selenium or an API for dynamic content
        splits = []
        # Example data from provided SEC results
        sec_data = [
            {'symbol': 'AGRI', 'ratio': 'Unknown', 'effective_date': '2025-07-24', 'fractional': 'Not specified'},
            {'symbol': 'AIHS', 'ratio': '1-for-10', 'effective_date': '2025-07-24', 'fractional': 'Not specified'},
            {'symbol': 'MRSN', 'ratio': '1-for-25', 'effective_date': '2025-07-24', 'fractional': 'Not specified'},
            {'symbol': 'IMNN', 'ratio': '1-for-15', 'effective_date': '2025-07-25', 'fractional': 'Rounded up to nearest whole share'}
        ]
        for item in sec_data:
            if datetime.strptime(item['effective_date'], '%Y-%m-%d') >= datetime.now():
                splits.append(item)
        return splits
    except Exception as e:
        logging.error(f"Error scraping SEC.gov: {e}")
        return []

def scrape_stocktitan():
    """Scrape reverse stock split data from StockTitan.net."""
    try:
        url = "https://www.stocktitan.net/search?query=split"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        splits = []
        today = datetime.now().date()
        
        # Find the news results table
        news_table = None
        tables = soup.find_all('table', class_='custom-table')
        
        for table in tables:
            # Look for the table that has Date, Symbol, Title columns
            headers = table.find('thead')
            if headers:
                header_cells = headers.find_all('th')
                if len(header_cells) >= 3:
                    header_texts = [cell.get_text().strip() for cell in header_cells]
                    if 'Date' in header_texts and 'Symbol' in header_texts and 'Title' in header_texts:
                        news_table = table
                        break
        
        if not news_table:
            logging.warning("Could not find news table in StockTitan response")
            return splits
        
        # Parse the table rows
        tbody = news_table.find('tbody')
        if not tbody:
            logging.warning("Could not find tbody in news table")
            return splits
        
        rows = tbody.find_all('tr')
        logging.info(f"Found {len(rows)} news rows to process")
        
        for row in rows:
            # logging.info(f"Processing row: {row}")
            # splits.append(row)
            try:
                cells = row.find_all('td')
                if len(cells) < 3:
                    logging.warning("Row does not have enough cells, skipping")
                    continue

                # Extract symbol (second column)
                symbol_cell = cells[1]
                symbol_link = symbol_cell.find('a', class_='symbol-link')
                if symbol_link:
                    symbol = symbol_link.get_text().strip()
                else:
                    symbol = symbol_cell.get_text().strip()
                
                # Remove any trailing commas or extra characters
                symbol = symbol.rstrip(',').strip()
                
                # Extract date (first column)
                date_cell = cells[0]
                date_span = date_cell.find('span', attrs={'name': 'date'})
                if date_span:
                    date_text = date_span.get_text().strip()
                else:
                    date_text = date_cell.get_text().strip()
                
                # Parse and validate date
                parsed_date = parse_stocktitan_date(date_text)
                if not parsed_date:
                    logging.warning(f"Invalid date format: {date_text}")
                    continue
                
                split_date = datetime.strptime(parsed_date, '%Y-%m-%d').date()
                
                # Only include splits from today onward
                if split_date < today:
                    logging.info(f"Skipping split from past date: {split_date}, symbol: {symbol}")
                    continue
                
                
                # Extract title (third column)
                title_cell = cells[2]
                title_link = title_cell.find('a')
                if title_link:
                    title = title_link.get_text().strip()
                else:
                    title = title_cell.get_text().strip()
                
                # Skip if no symbol found
                if not symbol:
                    logging.warning("No symbol found in row, skipping")
                    continue
                
                # # Extract split ratio from title
                # ratio = extract_split_ratio_from_title(title)
                
                # # Determine fractional share handling
                # fractional = 'Not specified'
                # if 'rounded up' in title.lower():
                #     fractional = 'Rounded up to nearest whole share'
                # elif 'cash in lieu' in title.lower() or 'cash payment' in title.lower():
                #     fractional = 'Cash payment for fractional shares'
                
                split_info = {
                    'symbol': symbol,
                    # 'ratio': ratio,
                    'effective_date': parsed_date,
                    # 'fractional': fractional,
                    'title': title
                }
                
                splits.append(split_info)
                logging.info(f"Found split: {symbol} on {parsed_date}")
                
            except Exception as e:
                logging.error(f"Error processing row: {e}")
                continue
        
        logging.info(f"Successfully scraped {len(splits)} splits from StockTitan")
        return splits
        
    except Exception as e:
        logging.error(f"Error scraping StockTitan: {e}")
        return []
import random
import datetime
import yfinance as yf
import logging
import pandas_market_calendars as mcal
import re

def get_random_emoji():
                # Unicode ranges for emojis
                emoji_ranges = [
                    (0x1F600, 0x1F64F),  # Emoticons
                    (0x1F300, 0x1F5FF),  # Misc Symbols and Pictographs
                    (0x1F680, 0x1F6FF),  # Transport and Map Symbols
                    (0x1F700, 0x1F77F),  # Alchemical Symbols
                    (0x1F780, 0x1F7FF),  # Geometric Shapes Extended
                    (0x1F800, 0x1F8FF),  # Supplemental Arrows-C
                    (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
                    (0x1FA00, 0x1FA6F),  # Chess Symbols
                    (0x1FA70, 0x1FAFF),  # Symbols and Pictographs Extended-A
                    (0x2600, 0x26FF),    # Miscellaneous Symbols
                    (0x2700, 0x27BF),    # Dingbats
                    (0xFE00, 0xFE0F),    # Variation Selectors
                    (0x1F1E6, 0x1F1FF),  # Regional Indicator Symbols
                ]
                # Flatten all codepoints in the ranges
                all_emojis = []
                for start, end in emoji_ranges:
                    all_emojis.extend(range(start, end + 1))
                # Pick a random codepoint and convert to character
                codepoint = random.choice(all_emojis)
                try:
                    emoji = chr(codepoint)
                except ValueError:
                    emoji = ""
                return emoji



def sort_key(split):
        val = split.get('fractional', '').lower()
        if "rounded up to nearest whole share" in val:
            return 0
        if "rounded up if fractional shares exceed a certain threshold" in val:
            return 1
        if "cash payment for fractional shares" in val or "rounded down to nearest whole share" in val:
            return 2
        if "not specified" in val:
            return 4
        return 3  # Other

def next_market_day(date=None, previous=False, days=1):
    """
    Returns the next (or previous) market day from the given date.
    Market days are Monday to Friday (excluding weekends).
    :param date: datetime.date object. If None, uses today.
    :param past: If True, goes to previous market days.
    :param days: Number of market days to move forward/backward.
    :return: datetime.date object of the target market day.
    """
    if date is None:
        date = datetime.date.today()
    delta = -1 if previous else 1
    count = 0
    current = date
    while count < days:
        current += datetime.timedelta(days=delta)
        if current.weekday() < 5:  # Monday=0, Friday=4
            count += 1
    return current



def add_current_prices(splits):
    """Add current stock prices to splits data using yfinance.
        Also checks if it is an OTC stock and removes it if so.
    """
    if not splits:
        return splits
    
    logging.info("Fetching current stock prices...")
    
    # Extract all symbols
    symbols = [split['symbol'] for split in splits]

    try:
        # Fetch all prices using the correct format
        multiple_tickers = yf.Tickers(symbols)

        # Create a dictionary to store prices
        prices = {}
        # Keep track of OTC symbols to remove
        otc_symbols = set()

        for symbol in symbols:
            try:
                ticker_info = multiple_tickers.tickers[symbol].info

                # Check if stock is OTC
                if 'fullExchangeName' in ticker_info and 'OTC' in ticker_info['fullExchangeName']:
                    logging.info(f"{symbol} is OTC ({ticker_info['fullExchangeName']}), removing from splits.")
                    otc_symbols.add(symbol)
                    continue

                # Try to get current price from different fields
                current_price = None
                if 'currentPrice' in ticker_info:
                    current_price = ticker_info['currentPrice']
                elif 'regularMarketPrice' in ticker_info:
                    current_price = ticker_info['regularMarketPrice']
                elif 'previousClose' in ticker_info:
                    current_price = ticker_info['previousClose']

                if current_price:
                    prices[symbol] = round(float(current_price), 2)
                    logging.info(f"Fetched price for {symbol}: ${current_price}")
                else:
                    logging.warning(f"Could not fetch price for {symbol}")
                    prices[symbol] = None

            except Exception as e:
                logging.error(f"Error fetching price for {symbol}: {e}")
                prices[symbol] = None

        # Remove OTC stocks from splits
        splits = [split for split in splits if split['symbol'] not in otc_symbols]

        # Add prices to splits data
        for split in splits:
            symbol = split['symbol']
            split['current_price'] = prices.get(symbol, None)

        logging.info(f"Successfully added prices for {len([p for p in prices.values() if p is not None])}/{len(symbols)} stocks (removed {len(otc_symbols)} OTC)")

    except Exception as e:
        logging.error(f"Error fetching stock prices: {e}")
        # Add None prices if fetching fails
        for split in splits:
            split['current_price'] = None

    return splits

def market_is_open(date):
    result = mcal.get_calendar("NYSE").schedule(start_date=date, end_date=date)
    return result.empty == False

def get_side_from_ratio(split, side='max'):
    """
    Extracts the larger or smaller side from the split ratio string.
    Args:
        split (dict): The split dictionary containing a 'ratio' key.
        side (str): 'max' for larger side, 'min' for smaller side.
    Returns:
        int or None: The requested side value, or None if not found.
    """
    ratio = split.get('ratio')
    if ratio:
        match = re.search(r'(\d+)\s*[:\-–>]\s*(\d+)', ratio)
        if match:
            num1 = int(match.group(1))
            num2 = int(match.group(2))
            return max(num1, num2) if side == 'max' else min(num1, num2)
        else:
            nums = [int(n) for n in re.findall(r'\d+', ratio)]
            if nums:
                return max(nums) if side == 'max' else min(nums)
    return ratio
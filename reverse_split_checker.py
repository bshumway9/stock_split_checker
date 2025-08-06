import schedule
import time
from datetime import datetime
import logging
import asyncio
from send_txt_msg import send_txt, send_txts, send_email
from dotenv import dotenv_values
from check_roundup import check_roundup
from table_scrapers import scrape_yahoo_finance_selenium, scrape_hedge_follow, scrape_nasdaq
from site_scrapers import scrape_stocktitan, scrape_sec_edgar
from helper_functions import get_random_emoji, next_market_day
from collections import defaultdict

# Load environment variables
# Required .env variables:
# - SENDER_EMAIL: Email address to send notifications from
# - SENDER_PASSWORD: Password for sender email
# - RECIPIENT_EMAIL: Email address to send notifications to
# - GEMINI_API_KEY: Google Gemini API key for fractional shares checking
#   Note: For grounding functionality, your API key must have permission to use the Google Search tool
env = dotenv_values('.env')

# Set up logging
logging.basicConfig(filename='stock_split_checker.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')



def get_reverse_splits():
    """Aggregate reverse split data from multiple sources."""
    splits = []
    # splits.extend(scrape_sec_edgar())
    # splits.extend(scrape_stocktitan())
    # splits.extend(scrape_yahoo_finance())  # Legacy HTTP method
    splits.extend(scrape_yahoo_finance_selenium())  # New Selenium method
    splits.extend(scrape_hedge_follow())
    # splits.extend(scrape_nasdaq())
    
    # Remove duplicates based on symbol and effective date
    unique_splits = []
    seen = set()
    for split in splits:
        key = (split['symbol'], split['effective_date'])
        if key not in seen:
            seen.add(key)
            if split.get('is_reverse', False):  # Only keep reverse splits
                unique_splits.append(split)
    
    # Filter for splits from today onward
    today = next_market_day()
    upcoming_splits = [
        split for split in unique_splits
        if datetime.strptime(split['effective_date'], '%Y-%m-%d').date() >= today
    ]
    return upcoming_splits

def send_message(splits):
    """Send text message with reverse split data."""
    try:
        # Format text message content
        if not splits:
            body = "No upcoming reverse stock splits found for today."
        else:
            # Categorize splits by fractional share handling
            buy_1_share = []
            buy_threshold = []
            check_rounding = []
            
            for split in splits:
                fractional = split.get('fractional', '').lower()
                if fractional == "rounded up to nearest whole share":
                    buy_1_share.append(split)
                elif fractional == "rounded up if fractional shares exceed a certain threshold":
                    buy_threshold.append(split)
                else:
                    check_rounding.append(split)
            
            body = ""


            emoji = get_random_emoji()
            # Buy 1 share section
            if buy_1_share:
                # Get the date from the first split (assuming all are same date)
                date = buy_1_share[0]['effective_date']
                body += f"Buy 1 share\n\n"
                # Group splits by effective_date
                splits_by_date = defaultdict(list)
                for split in buy_1_share:
                    splits_by_date[split['effective_date']].append(split)
                # Sort dates
                for date in sorted(splits_by_date.keys()):
                    for split in splits_by_date[date]:
                        ratio = split.get('ratio', 'N/A')
                        body += f"{emoji} {split['symbol']}   {ratio}\n"
                    prev_market_day = next_market_day(datetime.strptime(date, '%Y-%m-%d').date(), previous=True)
                    body += f"(Last day to buy: {prev_market_day})\n\n"
                body += "\n"
            # Buy ? shares section  
            if buy_threshold:
                body += f"Buy ? shares\n\n"
                # Group splits by effective_date
                splits_by_date = defaultdict(list)
                for split in buy_threshold:
                    splits_by_date[split['effective_date']].append(split)
                # Sort dates
                for date in sorted(splits_by_date.keys()):
                    for split in splits_by_date[date]:
                        ratio = split.get('ratio', 'N/A')
                        body += f"{emoji} {split['symbol']}   {ratio}\n"
                    prev_market_day = next_market_day(datetime.strptime(date, '%Y-%m-%d').date(), previous=True)
                    body += f"(Last day to buy: {prev_market_day})\n\n"
                body += "\n"
            
            # Check Rounding section
            if check_rounding:
                body += f"Check Rounding\n\n"
                # Group splits by effective_date
                splits_by_date = defaultdict(list)
                for split in check_rounding:
                    splits_by_date[split['effective_date']].append(split)
                # Sort dates
                for date in sorted(splits_by_date.keys()):
                    for split in splits_by_date[date]:
                        ratio = split.get('ratio', 'N/A')
                        body += f"{emoji} {split['symbol']}   {ratio}\n"
                    prev_market_day = next_market_day(datetime.strptime(date, '%Y-%m-%d').date(), previous=True)
                    body += f"(Last day to buy: {prev_market_day})\n\n"
                body += "\n"

        _num = env.get("PHONE_NUMBER", "")
        _carrier = "verizon"
        _email = env.get("SENDER_EMAIL", "")
        _pword = env.get("GMAIL_KEY", "")
        _msg = body
        _subj = "Upcoming Reverse Stock Splits"
        # coro = send_txt(_num, _carrier, _email, _pword, _msg, _subj)
        coro = send_email(_email, _subj, _msg, _email, _pword)

        # _nums = {"999999999", "000000000"}
        # coro = send_txts(_nums, _carrier, _email, _pword, _msg, _subj)
        asyncio.run(coro)
        logging.info("Text message sent successfully")
    except Exception as e:
        logging.info("Error sending text message: {}".format(e))
        logging.info("body: {}".format(body))
        logging.error(f"Error sending text message: {e}")

def main():
    """Main function to run the reverse split checker."""
    logging.info("Starting reverse split check")
    splits = get_reverse_splits()
    logging.info(f"Found {len(splits)} upcoming reverse splits")
    
    # Check if stocks will round up fractional shares
    if splits:
        logging.info("Checking fractional shares handling with Gemini API")
        splits = check_roundup(splits)
        logging.info(splits)
    send_message(splits)
    logging.info("Reverse split check completed")

def schedule_task():
    """Schedule the task to run daily at 8:00 AM."""
    schedule.every().day.at("08:00").do(main)

if __name__ == "__main__":
    # Run once immediately for testing
    main()
    
    # # Schedule daily execution
    # schedule_task()
    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)  # Check every minute
import schedule
import time
from datetime import datetime
import logging
import asyncio
from send_txt_msg import send_txt, send_txts, send_email
from send_discord_msg import send_discord_message, send_discord_webhook, format_discord_message
from dotenv import dotenv_values
from check_roundup import check_roundup
from table_scrapers import scrape_yahoo_finance_selenium, scrape_hedge_follow, scrape_nasdaq, scrape_stock_titan
from site_scrapers import scrape_stocktitan, scrape_sec_edgar
from helper_functions import get_random_emoji, next_market_day, add_current_prices
from collections import defaultdict

# Load environment variables
# Required .env variables:
# - SENDER_EMAIL: Email address to send notifications from
# - SENDER_PASSWORD: Password for sender email
# - RECIPIENT_EMAIL: Email address to send notifications to
# - GEMINI_API_KEY: Google Gemini API key for fractional shares checking
#   Note: For grounding functionality, your API key must have permission to use the Google Search tool
# - DISCORD_WEBHOOK_URL: Discord webhook URL for sending notifications (optional)
#   To get a webhook URL: Server Settings > Integrations > Webhooks > New Webhook
env = dotenv_values('.env')

# Set up logging
logging.basicConfig(filename='stock_split_checker.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')



def get_reverse_splits():
    """Aggregate reverse split data from multiple sources."""
    splits = []
    past_splits = []  # To store past splits if needed
    check_splits = []
    # splits.extend(scrape_sec_edgar())
    # splits.extend(scrape_stocktitan())
    # splits.extend(scrape_yahoo_finance())  # Legacy HTTP method
    splits.extend(scrape_yahoo_finance_selenium())  # New Selenium method

    new_splits, new_past_splits = scrape_hedge_follow()  # New HedgeFollow scraper
    splits.extend(new_splits)
    past_splits.extend(new_past_splits)

    recent_splits, all_splits_with_links = scrape_stock_titan()  # New StockTitan scraper
    
    # Add recent splits to main list
    for split in recent_splits:
        if split['symbol'] not in [s['symbol'] for s in splits] and split['symbol'] not in [s['symbol'] for s in past_splits]:
            check_splits.append(split)
    
    # Merge article links for existing splits
    for new_split in all_splits_with_links:
        symbol = new_split['symbol']
        new_links = new_split.get('article_link', [])
        
        # Check against current splits
        for existing_split in splits:
            if existing_split['symbol'] == symbol:
                existing_links = existing_split.get('article_link', [])
                if isinstance(existing_links, str):
                    existing_links = [existing_links]
                # Merge unique links
                merged_links = list(set(existing_links + new_links))
                existing_split['article_link'] = merged_links
                logging.info(f"Merged article links for {symbol}: {len(merged_links)} total links")
                break
        
        # Check against past splits
        for existing_split in past_splits:
            if existing_split['symbol'] == symbol:
                existing_links = existing_split.get('article_link', [])
                if isinstance(existing_links, str):
                    existing_links = [existing_links]
                # Merge unique links
                merged_links = list(set(existing_links + new_links))
                existing_split['article_link'] = merged_links
                logging.info(f"Merged article links for past split {symbol}: {len(merged_links)} total links")
                break

    # splits.extend(scrape_nasdaq())
    
    # Remove duplicates based on symbol and effective date
    unique_splits = []
    splits_by_symbol = {}

    # Group splits by symbol
    for split in splits:
        symbol = split['symbol']
        # Skip if not a reverse split
        if not split.get('is_reverse', False):
            continue
            
        if symbol not in splits_by_symbol:
            splits_by_symbol[symbol] = []
        
        splits_by_symbol[symbol].append(split)

    # Process each symbol group
    for symbol, symbol_splits in splits_by_symbol.items():
        # Sort splits by effective date (latest first)
        sorted_splits = sorted(
            symbol_splits, 
            key=lambda x: datetime.strptime(x['effective_date'], '%Y-%m-%d'), 
            reverse=True
        )
        
        # Take the split with the latest effective date as our base
        latest_split = sorted_splits[0]
        
        # Combine article_links from all splits with this symbol
        all_article_links = []
        for split in sorted_splits:
            links = split.get('article_link', [])
            # Convert single string to list if necessary
            if isinstance(links, str):
                all_article_links.append(links)
            else:
                # For lists, add each item
                all_article_links.extend(links)
        
        # Remove duplicates
        if all_article_links:  # Only set if we have links
            latest_split['article_link'] = list(set(all_article_links))
        
        unique_splits.append(latest_split)

    # Filter for splits from today onward
    today = next_market_day()
    upcoming_splits = [
        split for split in unique_splits
        if datetime.strptime(split['effective_date'], '%Y-%m-%d').date() >= today
    ]
    logging.info(f"Found {len([split for split in upcoming_splits if split['article_link']])} upcoming splits with article links with {len(upcoming_splits)} total upcoming splits")
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
                        current_price = split.get('current_price', None)
                        
                        # Format price display if we have both price and ratio
                        if current_price and ratio != 'N/A':
                            try:
                                # Extract the ratio number (e.g., "1:10" -> 10)
                                if '->' in ratio:
                                    ratio_parts = ratio.split('->')
                                    if len(ratio_parts) == 2:
                                        multiplier = float(ratio_parts[1]) / float(ratio_parts[0])
                                        projected_price = current_price * float(ratio_parts[0])
                                        price_display = f"${current_price}--->${projected_price:.2f}"
                                    else:
                                        price_display = f"${current_price} ({ratio})"
                                else:
                                    price_display = f"${current_price} ({ratio})"
                            except (ValueError, ZeroDivisionError):
                                price_display = f"${current_price} ({ratio})"
                        else:
                            price_display = ratio
                        
                        body += f"{emoji} {split['symbol']}   {price_display}\n"
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
                        current_price = split.get('current_price', None)
                        
                        # Format price display if we have both price and ratio
                        if current_price and ratio != 'N/A':
                            try:
                                # Extract the ratio number (e.g., "1:10" -> 10)
                                if '->' in ratio:
                                    ratio_parts = ratio.split('->')
                                    if len(ratio_parts) == 2:
                                        multiplier = float(ratio_parts[1]) / float(ratio_parts[0])
                                        projected_price = current_price * float(ratio_parts[0])
                                        price_display = f"${current_price}--->${projected_price:.2f}"
                                    else:
                                        price_display = f"${current_price} ({ratio})"
                                else:
                                    price_display = f"${current_price} ({ratio})"
                            except (ValueError, ZeroDivisionError):
                                price_display = f"${current_price} ({ratio})"
                        else:
                            price_display = ratio
                        
                        body += f"{emoji} {split['symbol']}   {price_display}\n"
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
                        current_price = split.get('current_price', None)
                        
                        # Format price display if we have both price and ratio
                        if current_price and ratio != 'N/A':
                            try:
                                # Extract the ratio number (e.g., "1:10" -> 10)
                                if '->' in ratio:
                                    ratio_parts = ratio.split('->')
                                    if len(ratio_parts) == 2:
                                        multiplier = float(ratio_parts[1]) / float(ratio_parts[0])
                                        projected_price = current_price * float(ratio_parts[0])
                                        price_display = f"${current_price}--->${projected_price:.2f}"
                                    else:
                                        price_display = f"${current_price} ({ratio})"
                                else:
                                    price_display = f"${current_price} ({ratio})"
                            except (ValueError, ZeroDivisionError):
                                price_display = f"${current_price} ({ratio})"
                        else:
                            price_display = ratio
                        
                        body += f"{emoji} {split['symbol']}   {price_display}\n"
                    prev_market_day = next_market_day(datetime.strptime(date, '%Y-%m-%d').date(), previous=True)
                    body += f"(Last day to buy: {prev_market_day})\n\n"
                body += "\n"

        # Try Discord first, fallback to email if Discord fails or is not configured
        discord_webhook = env.get("DISCORD_WEBHOOK_URL", "")
        discord_sent = False
        email_sent = False
        
        if discord_webhook:
            try:
                logging.info("Sending Discord message")
                discord_success = asyncio.run(send_discord_message(discord_webhook, splits, "Stock Split Bot"))
                if discord_success:
                    logging.info("Discord message sent successfully")
                    discord_sent = True
                else:
                    logging.error("Failed to send Discord message - will fallback to email")
            except Exception as e:
                logging.error(f"Error sending Discord message: {e} - will fallback to email")

        # Send email only if Discord wasn't sent or if no Discord webhook is configured
        if not discord_sent:
            _email = env.get("SENDER_EMAIL", "")
            _pword = env.get("GMAIL_KEY", "")
            _msg = body
            _subj = "Upcoming Reverse Stock Splits"
            
            # Only send email if email credentials are provided
            if _email and _pword:
                try:
                    coro = send_email(_email, _subj, _msg, _email, _pword)
                    asyncio.run(coro)
                    logging.info("Email sent successfully")
                    email_sent = True
                except Exception as e:
                    logging.error(f"Error sending email: {e} - will fallback to SMS")
            else:
                logging.warning("No email credentials provided - will try SMS fallback")

        # Final fallback: SMS if both Discord and email failed
        if not discord_sent and not email_sent:
            _num = env.get("PHONE_NUMBER", "")
            _carrier = "verizon"
            
            if _num:
                try:
                    fallback_msg = f"Stock Split Bot: Both Discord and email notifications failed. Found {len(splits)} splits. Check logs for details."
                    coro = send_txt(_num, _carrier, fallback_msg)
                    asyncio.run(coro)
                    logging.info("SMS fallback notification sent successfully")
                except Exception as e:
                    logging.error(f"All notification methods failed - Discord, Email, and SMS: {e}")
                    logging.critical("CRITICAL: No notifications could be sent - manual check required")
            else:
                logging.error("All notification methods failed - no phone number configured for SMS fallback")
                logging.critical("CRITICAL: No notifications could be sent - manual check required")

    except Exception as e:
        logging.info("Error sending messages: {}".format(e))
        logging.info("body: {}".format(body))
        logging.error(f"Error sending messages: {e}")

def main():
    """Main function to run the reverse split checker."""
    logging.info("Starting reverse split check")
    splits = get_reverse_splits()
    logging.info(f"Found {len(splits)} upcoming reverse splits")
    
    # Add current stock prices
    if splits:
        splits = add_current_prices(splits)
    
    # Check if stocks will round up fractional shares
    if splits:
        logging.info("Checking fractional shares handling with Gemini API")
        splits = check_roundup(splits)
        logging.info(splits)
    send_message(splits)
    logging.info("Reverse split check completed")

def schedule_task():
    """Schedule the task to run daily at 8:00 AM on weekdays."""
    # Note: When running in Docker, scheduling is handled by cron
    # This function is kept for backwards compatibility
    schedule.every().monday.at("14:00").do(main)  # 2 PM UTC
    schedule.every().tuesday.at("14:00").do(main) # 8 AM MST
    schedule.every().wednesday.at("14:00").do(main)
    schedule.every().thursday.at("14:00").do(main)
    schedule.every().friday.at("14:00").do(main)

if __name__ == "__main__":
    # Run once immediately for testing
    main()
    
    # # Schedule daily execution
    # schedule_task()
    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)  # Check every minute
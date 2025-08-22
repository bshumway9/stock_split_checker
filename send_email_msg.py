from collections import defaultdict
from datetime import datetime
from dotenv import dotenv_values
from typing import Optional, List
import asyncio
import logging
from helper_functions import get_random_emoji, next_market_day
from send_txt_msg import send_email


env = dotenv_values('.env')
    

def format_email_message(splits: list, prev_splits: Optional[List[dict]] = None) -> str:
    prev_splits = prev_splits or []
    if not splits and not prev_splits:
        body = "No upcoming reverse stock splits found for today."
    else:
        # Categorize splits by fractional share handling
        buy_1_share = []
        buy_threshold = []
        check_rounding = []
        prev_buy_1_share = []
        prev_buy_threshold = []
        prev_check_rounding = []

        for split in splits:
            fractional = split.get('fractional', '').lower()
            # Skip decided non-actionable outcomes from display
            if fractional in ("cash payment for fractional shares", "rounded down to nearest whole share"):
                continue
            if fractional == "rounded up to nearest whole share":
                buy_1_share.append(split)
            elif fractional == "rounded up if fractional shares exceed a certain threshold":
                buy_threshold.append(split)
            else:
                check_rounding.append(split)
        for split in prev_splits:
            fractional = split.get('fractional', '').lower()
            # Skip decided non-actionable outcomes from display
            if fractional in ("cash payment for fractional shares", "rounded down to nearest whole share"):
                continue
            if fractional == "rounded up to nearest whole share":
                prev_buy_1_share.append(split)
            elif fractional == "rounded up if fractional shares exceed a certain threshold":
                prev_buy_threshold.append(split)
            else:
                prev_check_rounding.append(split)
        
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
                                    multiplier = float(ratio_parts[0]) / float(ratio_parts[1])
                                    projected_price = current_price * multiplier
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
                    if date.lower() != "unknown":
                        prev_market_day = next_market_day(datetime.strptime(date, '%Y-%m-%d').date(), previous=True)
                    else:
                        prev_market_day = "Unknown"
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
                    min_shares = split.get('min_shares_for_roundup')
                    threshold_explanation = split.get('threshold_explanation')
                    
                    # Format price display if we have both price and ratio
                    if current_price and ratio != 'N/A':
                        try:
                            # Extract the ratio number (e.g., "1:10" -> 10)
                            if '->' in ratio:
                                ratio_parts = ratio.split('->')
                                if len(ratio_parts) == 2:
                                    multiplier = float(ratio_parts[0]) / float(ratio_parts[1])
                                    projected_price = current_price * multiplier
                                    price_display = f"${current_price}x{min_shares}({current_price*min_shares})--->${projected_price:.2f}" if min_shares else f"${current_price}--->${projected_price:.2f}"
                                else:
                                    price_display = f"${current_price} ({ratio})"
                            else:
                                price_display = f"${current_price} ({ratio})"
                        except (ValueError, ZeroDivisionError):
                            price_display = f"${current_price} ({ratio})"
                    else:
                        price_display = ratio
                    
                    body += f"{emoji} {split['symbol']} - {price_display}"
                    if min_shares:
                        body += f" | Buy {min_shares} shares"
                    body += "\n"
                    if threshold_explanation:
                        body += f"Roundup Notes: {threshold_explanation}\n"
                    if date.lower() != "unknown":
                        prev_market_day = next_market_day(datetime.strptime(date, '%Y-%m-%d').date(), previous=True)
                    else:
                        prev_market_day = "Unknown"
                    body += f"(Last day to buy: {prev_market_day})\n\n"
            body += "\n"
        
        # Check Rounding section (combine new + previously sent insufficient info)
        combined_check_rounding = check_rounding + prev_check_rounding
        if combined_check_rounding:
            body += f"Check Rounding\n\n"
            # Group splits by effective_date
            splits_by_date = defaultdict(list)
            for split in combined_check_rounding:
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
                    if date.lower() != "unknown":
                        prev_market_day = next_market_day(datetime.strptime(date, '%Y-%m-%d').date(), previous=True)
                    else:
                        prev_market_day = "Unknown"
                    body += f"(Last day to buy: {prev_market_day})\n\n"
            body += "\n"

        # Previously sent section (exclude insufficient info, which is already shown above)
        prev_non_insufficient = prev_buy_1_share + prev_buy_threshold
        if prev_non_insufficient:
            body += f"Previously Sent (Still Buyable)\n\n"
            # Group splits by effective_date
            splits_by_date = defaultdict(list)
            for split in prev_non_insufficient:
                splits_by_date[split['effective_date']].append(split)
            # Sort dates
            for date in sorted(splits_by_date.keys()):
                for split in splits_by_date[date]:
                    ratio = split.get('ratio', 'N/A')
                    current_price = split.get('current_price', None)
                    
                    # Format price display if we have both price and ratio
                    if current_price and ratio != 'N/A':
                        try:
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
                    if date.lower() != "unknown":
                        prev_market_day = next_market_day(datetime.strptime(date, '%Y-%m-%d').date(), previous=True)
                    else:
                        prev_market_day = "Unknown"
                    body += f"(Last day to buy: {prev_market_day})\n\n"
            body += "\n"

def send_email_message(splits: list, prev_splits: Optional[List[dict]] = None) -> bool:
    _email = env.get("SENDER_EMAIL", "")
    _pword = env.get("GMAIL_KEY", "")
    _msg = format_email_message(splits, prev_splits)
    _subj = "Upcoming Reverse Stock Splits"

    if _email and _pword:
        try:
            coro = send_email(_email, _subj, _msg, _email, _pword)
            asyncio.run(coro)
            logging.info("Email sent successfully")
            return True
        except Exception as e:
            logging.error(f"Error sending email: {e} - will fallback to SMS")
            logging.info("Email body: {}".format(_msg))
            return False
    else:
        logging.warning("No email credentials provided - will try SMS fallback")
        logging.info("Email body: {}".format(_msg))
        return False
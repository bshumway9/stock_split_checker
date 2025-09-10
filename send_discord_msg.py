import logging
import requests
from typing import Optional, List
from datetime import datetime
from helper_functions import next_market_day, get_random_emoji
from collections import defaultdict


def send_discord_webhook(webhook_url: str, message: str, username: Optional[str] = None) -> bool:
    """
    Send a message to Discord using a webhook URL.
    
    Args:
        webhook_url (str): Discord webhook URL
        message (str): Message content to send
        username (str, optional): Username to display for the bot
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    try:
        # Prepare the payload
        payload = {
            "content": message
        }
        
        if username:
            payload["username"] = username
        
        # Send the message
        response = requests.post(webhook_url, json=payload)
        
        if response.status_code == 204:  # Discord returns 204 for successful webhook
            logging.info("Discord message sent successfully")
            return True
        else:
            logging.error(f"Failed to send Discord message. Status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logging.error(f"Error sending Discord message: {e}")
        return False


async def send_discord_bot_message(bot_token: str, channel_id: str, message: str) -> bool:
    """
    Send a message to Discord using a bot token (alternative to webhook).
    
    Args:
        bot_token (str): Discord bot token
        channel_id (str): Discord channel ID to send message to
        message (str): Message content to send
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    try:
        headers = {
            'Authorization': f'Bot {bot_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'content': message
        }
        
        url = f'https://discord.com/api/v10/channels/{channel_id}/messages'
        
        # Use requests for synchronous call (can be made async if needed)
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            logging.info("Discord bot message sent successfully")
            return True
        else:
            logging.error(f"Failed to send Discord bot message. Status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logging.error(f"Error sending Discord bot message: {e}")
        return False


def format_discord_message(splits: list, prev_splits: Optional[List[dict]] = None) -> str:
    """
    Format the splits data for Discord with proper formatting.
    
    Args:
        splits (list): List of split dictionaries
        
    Returns:
        str: Formatted message for Discord
    """
    prev_splits = prev_splits or []

    if not splits and not prev_splits:
        return f"📊 **No splits found today {datetime.now().strftime('%m-%d-%Y')}**"

    message = f"🚨 **Upcoming Splits {datetime.now().strftime('%m-%d-%Y')}** 🚨\n\n"
    logging.info(f"formatting discord message with splits: {splits}, prev_splits: {prev_splits}")
    # Categorize splits by fractional share handling
    buy_1_share = []
    buy_threshold = []
    check_rounding = []
    prev_buy_1_share = []
    prev_buy_threshold = []
    prev_check_rounding = []
    
    def is_insufficient(frac: str) -> bool:
        f = (frac or '').strip().lower()
        return f in ("check rounding policy", "unknown", "not specified", "unspecified", "")

    for split in splits:
        fractional = split.get('fractional', '').lower()
        # Skip decided non-actionable outcomes from display (still persisted in DB)
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
        # Skip decided non-actionable outcomes from display (still persisted in DB)
        if fractional in ("cash payment for fractional shares", "rounded down to nearest whole share"):
            continue
        if fractional == "rounded up to nearest whole share":
            prev_buy_1_share.append(split)
        elif fractional == "rounded up if fractional shares exceed a certain threshold":
            prev_buy_threshold.append(split)
        else:
            prev_check_rounding.append(split)

    if not (buy_1_share or buy_threshold or check_rounding or prev_buy_1_share or prev_buy_threshold or prev_check_rounding):
        return f"📊 **No splits found today {datetime.now().strftime('%m-%d-%Y')}**"
    
    emoji = get_random_emoji()  # Assuming this function returns a random emoji for the message

    # Buy 1 share section
    if buy_1_share:
        message += "💰 **Buy 1 Share** 💰\n```\n"
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
                
                message += f"{emoji} {split['symbol']} - {price_display}\n"
            if date.lower() != "unknown":
                prev_market_day = next_market_day(datetime.strptime(date, '%Y-%m-%d').date(), previous=True)
            else:
                prev_market_day = "Unknown"
            message += f"(Last day to buy: {prev_market_day})\n\n"
        message += "```\n\n"
    
    # Buy ? shares section
    if buy_threshold:
        message += "🤔 **Buy ? Shares** 🤔\n```\n"
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
                                multiplier = float(ratio_parts[1]) / float(ratio_parts[0])
                                projected_price = current_price * float(ratio_parts[0])
                                price_display = f"${current_price}x{min_shares}({current_price*min_shares})--->${projected_price:.2f}" if min_shares else f"${current_price}--->${projected_price:.2f}"
                            else:
                                price_display = f"${current_price} ({ratio})"
                        else:
                            price_display = f"${current_price} ({ratio})"
                    except (ValueError, ZeroDivisionError):
                        price_display = f"${current_price} ({ratio})"
                else:
                    price_display = ratio
                
                message += f"{emoji} {split['symbol']} - {price_display}"
                if min_shares:
                    message += f" | Buy {min_shares} shares"
                message += "\n"
                if threshold_explanation:
                    message += f"Roundup Notes: {threshold_explanation}\n"
            if date.lower() != "unknown":
                prev_market_day = next_market_day(datetime.strptime(date, '%Y-%m-%d').date(), previous=True)
            else:
                prev_market_day = "Unknown"
            message += f"(Last day to buy: {prev_market_day})\n\n"
        message += "```\n\n"
    
    # Check rounding section (combine new + previously sent insufficient info)
    combined_check_rounding = check_rounding + prev_check_rounding
    if combined_check_rounding:
        message += "🔍 **Check Rounding Policy** 🔍\n```\n"
        # Group splits by effective_date
        splits_by_date = defaultdict(list)
        for split in combined_check_rounding:
            splits_by_date[split['effective_date']].append(split)
        # Sort dates
        for date in sorted(splits_by_date.keys()):
            for split in splits_by_date[date]:
                ratio = split.get('ratio', 'N/A')
                current_price = split.get('current_price', None)
                source = split.get('source', 'Unknown')
                
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
                
                message += f"{emoji} {split['symbol']} - {price_display} [Source: {source}]\n"
            if date.lower() != "unknown":
                prev_market_day = next_market_day(datetime.strptime(date, '%Y-%m-%d').date(), previous=True)
            else:
                prev_market_day = "Unknown"
            message += f"(Last day to buy: {prev_market_day})\n\n"
        message += "```\n\n"
    
    # Previously Sent section (exclude insufficient info; combined above)
    prev_non_insufficient = prev_buy_1_share + prev_buy_threshold
    if prev_non_insufficient:
        message += "🕓 **Previously Sent (Still Buyable)** 🕓\n```\n"

        # Categorize and group by date similar to above
        splits_by_date = defaultdict(list)
        for split in prev_non_insufficient:
            splits_by_date[split.get('effective_date','Unknown')].append(split)
        for date_str in sorted(splits_by_date.keys()):
            for split in splits_by_date[date_str]:
                ratio = split.get('ratio', 'N/A')
                current_price = split.get('current_price', None)
                min_shares = split.get('min_shares_for_roundup')
                threshold_explanation = split.get('threshold_explanation')
                try:
                    if current_price and ratio != 'N/A':
                        if '->' in ratio:
                            parts = ratio.split('->')
                            if len(parts) == 2:
                                multiplier = float(parts[1]) / float(parts[0])
                                projected_price = current_price * float(parts[0])
                                if split in prev_buy_threshold and min_shares:
                                    price_display = f"${current_price}x{min_shares}({current_price*min_shares})--->${projected_price:.2f}"
                                else:
                                    price_display = f"${current_price}--->${projected_price:.2f}"
                            else:
                                price_display = f"${current_price} ({ratio})"
                        else:
                            price_display = f"${current_price} ({ratio})"
                    else:
                        price_display = ratio
                except (ValueError, ZeroDivisionError):
                    price_display = f"${current_price} ({ratio})" if current_price else ratio
                message += f"{get_random_emoji()} {split.get('symbol','?')} - {price_display}"
                if split in prev_buy_threshold and min_shares:
                    message += f" | Buy {min_shares} shares"
                message += "\n"
                if split in prev_buy_threshold and threshold_explanation:
                    message += f"Roundup Notes: {threshold_explanation}\n"
            if date_str.lower() != "unknown":
                prev_day = next_market_day(datetime.strptime(date_str, '%Y-%m-%d').date(), previous=True)
            else:
                prev_day = "Unknown"
            message += f"(Last day to buy: {prev_day})\n\n"
        message += "```\n\n"

    # message += f"📅 **Last updated:** {datetime.now().strftime('%H:%M:%S')}\n"
    # message += "⚠️ **Always verify split details before trading!**"
    return message


# For backwards compatibility and easy testing
async def send_discord_message(webhook_url: str, splits: list, username: str = "Stock Split Bot", prev_splits: Optional[List[dict]] = None) -> bool:
    """
    Convenience function to format and send Discord message.
    
    Args:
        webhook_url (str): Discord webhook URL
        splits (list): List of split dictionaries  
        username (str): Username for the bot
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        formatted_message = format_discord_message(splits, prev_splits=prev_splits)
        return send_discord_webhook(webhook_url, formatted_message, username)
    except Exception as e:
        logging.error(f"Error in send_discord_message: {e}")
        return False


def format_discord_buy_message(splits, dry_run=True):
    buy_1_share = []
    for split in splits:
        fractional = split.get('fractional', '').lower()
        current_price = split.get('current_price', None)
        # Skip decided non-actionable outcomes from display (still persisted in DB)
        if fractional == "rounded up to nearest whole share" and current_price and current_price < 1.25:
            buy_1_share.append(split)
        else:
            continue
    if not buy_1_share:
        return None
    symbols = [split['symbol'].upper() for split in buy_1_share]
    message = "!rsa buy 1 " + ",".join(symbols) + f" all {"false" if not dry_run else "true"}"
    return message

async def send_discord_buy_message(webhook_url: str, splits: list, username: str = "Stock Split Bot", dry_run=True) -> bool:
    """
    Send a Discord message for buying 1 share of each stock in the splits list.

    Args:
        webhook_url (str): The Discord webhook URL.
        splits (list): The list of stock splits.
        username (str): The username to display for the bot.

    Returns:
        bool: True if the message was sent successfully, False otherwise.
    """
    try:
        message = format_discord_buy_message(splits, dry_run=dry_run)
        if message:
            return send_discord_webhook(webhook_url, message, username)
    except Exception as e:
        logging.error(f"Error in send_discord_buy_message: {e}")
        return False
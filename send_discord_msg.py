import asyncio
import logging
import requests
from typing import Optional
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


def format_discord_message(splits: list) -> str:
    """
    Format the splits data for Discord with proper formatting.
    
    Args:
        splits (list): List of split dictionaries
        
    Returns:
        str: Formatted message for Discord
    """
    if not splits:
        return f"📊 **No splits found today {datetime.now().strftime('%m-%d-%Y')}**"

    message = f"🚨 **Upcoming Splits {datetime.now().strftime('%m-%d-%Y')}** 🚨\n\n"

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
            prev_market_day = next_market_day(datetime.strptime(date, '%Y-%m-%d').date(), previous=True)
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
            prev_market_day = next_market_day(datetime.strptime(date, '%Y-%m-%d').date(), previous=True)
            message += f"(Last day to buy: {prev_market_day})\n\n"
        message += "```\n\n"
    
    # Check rounding section
    if check_rounding:
        message += "🔍 **Check Rounding Policy** 🔍\n```\n"
        # Group splits by effective_date
        splits_by_date = defaultdict(list)
        for split in check_rounding:
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
            prev_market_day = next_market_day(datetime.strptime(date, '%Y-%m-%d').date(), previous=True)
            message += f"(Last day to buy: {prev_market_day})\n\n"
        message += "```\n\n"
    
    # message += f"📅 **Last updated:** {asyncio.get_event_loop().time()}\n"
    # message += "⚠️ **Always verify split details before trading!**"
    
    return message


# For backwards compatibility and easy testing
async def send_discord_message(webhook_url: str, splits: list, username: str = "Stock Split Bot") -> bool:
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
        formatted_message = format_discord_message(splits)
        return send_discord_webhook(webhook_url, formatted_message, username)
    except Exception as e:
        logging.error(f"Error in send_discord_message: {e}")
        return False

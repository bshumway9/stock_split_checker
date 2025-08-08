#!/usr/bin/env python3

import asyncio
import logging
from send_discord_msg import send_discord_message, format_discord_message
from dotenv import dotenv_values

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def test_discord_messaging():
    """Test Discord messaging functionality."""
    print("Testing Discord messaging...")
    
    # Load environment variables
    env = dotenv_values('.env')
    webhook_url = env.get("DISCORD_WEBHOOK_URL", "")
    
    if not webhook_url:
        print("❌ DISCORD_WEBHOOK_URL not found in .env file")
        print("\nTo set up Discord messaging:")
        print("1. Go to your Discord server")
        print("2. Right-click on a channel and select 'Edit Channel'")
        print("3. Go to 'Integrations' tab")
        print("4. Click 'Webhooks' and then 'New Webhook'")
        print("5. Copy the webhook URL and add it to your .env file as:")
        print("   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL")
        return
    
    # Create sample split data for testing
    sample_splits = [
        {
            'symbol': 'TEST1',
            'company': 'Test Company 1',
            'ratio': '1:10',
            'effective_date': '2025-08-08',
            'fractional': 'rounded up to nearest whole share',
            'is_reverse': True,
            'source': 'Test',
            'current_price': 0.29
        },
        {
            'symbol': 'TEST2', 
            'company': 'Test Company 2',
            'ratio': '1:20',
            'effective_date': '2025-08-09',
            'fractional': 'rounded up if fractional shares exceed a certain threshold',
            'is_reverse': True,
            'source': 'Test',
            'current_price': 0.15
        },
        {
            'symbol': 'TEST3',
            'company': 'Test Company 3', 
            'ratio': '1:5',
            'effective_date': '2025-08-10',
            'fractional': 'check rounding policy',
            'is_reverse': True,
            'source': 'Test',
            'current_price': 1.50
        },
        {
            'symbol': 'TEST4',
            'company': 'Test Company 4',
            'ratio': '1:15',
            'effective_date': '2025-08-08',
            'fractional': 'rounded up to nearest whole share',
            'is_reverse': True,
            'source': 'Test',
            'current_price': 0.33
        },
        {
            'symbol': 'TEST5',
            'company': 'Test Company 5',
            'ratio': '1:3',
            'effective_date': '2025-08-11',
            'fractional': 'rounded up to nearest whole share',
            'is_reverse': True,
            'source': 'Test',
            'current_price': 2.25
        }
    ]
    
    try:
        print("📤 Sending test Discord message...")
        
        # Test the formatting function
        formatted_message = format_discord_message(sample_splits)
        print("📝 Formatted message:")
        print(formatted_message)
        print("\n" + "="*50 + "\n")
        
        # Send the message
        success = asyncio.run(send_discord_message(webhook_url, sample_splits, "Stock Split Test Bot"))
        
        if success:
            print("✅ Discord test message sent successfully!")
            print("Check your Discord channel to see the message.")
        else:
            print("❌ Failed to send Discord message")
            
    except Exception as e:
        print(f"❌ Error testing Discord messaging: {e}")
        logging.error(f"Error testing Discord messaging: {e}")

def test_empty_splits():
    """Test Discord messaging with no splits."""
    print("\nTesting Discord messaging with no splits...")
    
    env = dotenv_values('.env')
    webhook_url = env.get("DISCORD_WEBHOOK_URL", "")
    
    if not webhook_url:
        print("❌ DISCORD_WEBHOOK_URL not found in .env file")
        return
    
    try:
        success = asyncio.run(send_discord_message(webhook_url, [], "Stock Split Test Bot"))
        
        if success:
            print("✅ Discord 'no splits' message sent successfully!")
        else:
            print("❌ Failed to send Discord 'no splits' message")
            
    except Exception as e:
        print(f"❌ Error testing Discord messaging: {e}")

if __name__ == "__main__":
    test_discord_messaging()
    test_empty_splits()

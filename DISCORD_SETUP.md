# Discord Setup Guide for Stock Split Checker

## Setting up Discord Webhook

### Step 1: Create or Access Your Discord Server
1. Open Discord and navigate to your server
2. If you don't have a server, create one by clicking the "+" icon on the left sidebar

### Step 2: Create a Webhook
1. Right-click on the channel where you want to receive notifications
2. Select "Edit Channel" from the context menu
3. Go to the "Integrations" tab in the left sidebar
4. Click on "Webhooks"
5. Click "New Webhook" or "Create Webhook"
6. Give your webhook a name (e.g., "Stock Split Bot")
7. Optionally, upload an avatar for your bot
8. Copy the "Webhook URL" - this is what you'll need for the .env file

### Step 3: Add Webhook URL to Environment Variables
1. Open your `.env` file in the project directory
2. Add the following line:
   ```
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
   ```
   Replace the URL with the one you copied from Discord

### Step 4: Test the Setup
Run the test script to verify Discord messaging works:
```bash
python test_discord.py
```

## Example .env File
```
# Email settings
SENDER_EMAIL=your-email@gmail.com
GMAIL_KEY=your-app-password
PHONE_NUMBER=1234567890

# API keys
GEMINI_API_KEY=your-gemini-api-key

# Discord settings
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz
```

## Discord Message Features

The Discord bot will send formatted messages with:
- 🚨 Eye-catching headers with emojis
- 📊 Categorized splits by fractional share handling:
  - 💰 **Buy 1 Share** - Stocks that round up any fractional shares
  - 🤔 **Buy ? Shares** - Stocks with threshold-based rounding
  - 🔍 **Check Rounding Policy** - Stocks requiring manual verification
- 📅 Effective dates for each split
- ⚠️ Source attribution and disclaimers
- Code blocks for clean formatting

## Troubleshooting

### Common Issues:
1. **"Invalid Webhook URL"** - Double-check the webhook URL format
2. **"Forbidden"** - Make sure the webhook hasn't been deleted or disabled
3. **"Not Found"** - Verify the webhook URL is correct and the channel still exists

### Testing:
- Use `test_discord.py` to test messaging without running the full stock checker
- Check Discord's server settings if messages aren't appearing
- Verify the bot has permission to send messages in the channel

### Message Limits:
- Discord has a 2000 character limit per message
- If your splits list is very long, the message may be truncated
- Consider splitting into multiple messages if needed (this can be added if required)

## Security Notes:
- Keep your webhook URL secret - anyone with it can send messages to your channel
- Consider using a private Discord server or restricted channel
- Don't commit your .env file to version control
- Regenerate webhook URL if it's compromised

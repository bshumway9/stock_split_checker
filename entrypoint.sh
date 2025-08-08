#!/bin/bash

# Start cron daemon
service cron start

# Print some useful information
echo "Stock Split Checker Docker Container Started"
echo "Cron jobs scheduled:"
crontab -l

echo "Current time: $(date)"
echo "Timezone: $(cat /etc/timezone)"

# Create .env file if it doesn't exist
if [ ! -f /app/.env ]; then
    echo "Creating .env template file..."
    cat > /app/.env << 'EOF'
# Email Configuration (optional - will fallback to SMS if not configured)
SENDER_EMAIL=your_email@gmail.com
GMAIL_KEY=your_gmail_app_password

# Discord Configuration (optional - primary notification method)
DISCORD_WEBHOOK_URL=your_discord_webhook_url

# SMS Configuration (required for fallback notifications)
PHONE_NUMBER=1234567890

# Gemini API for fractional shares checking
GEMINI_API_KEY=your_gemini_api_key
EOF
    echo "Please edit /app/.env with your actual credentials"
fi

# Run the script once immediately for testing
echo "Running initial test..."
cd /app && python reverse_split_checker.py

# Keep container running and show logs
echo "Container ready. Monitoring cron logs..."
tail -f /var/log/cron.log

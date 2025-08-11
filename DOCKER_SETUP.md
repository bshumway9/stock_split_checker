# Stock Split Checker Docker Setup

This Docker setup runs the stock split checker automatically every weekday at 8:00 AM MST.

## Quick Start

1. **Create your .env file with credentials:**
```bash
cp .env.example .env
# Edit .env with your actual credentials
nano .env
```

2. **Build and run with Docker Compose:**
```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

## Manual Docker Commands

If you prefer not to use docker-compose:

```bash
# Build the image
docker build -t stock-split-checker .

# Run the container
docker run -d \
  --name stock-split-checker \
  --restart unless-stopped \
  -v $(pwd)/.env:/app/.env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/stock_split_checker.log:/app/stock_split_checker.log \
  -e TZ=America/New_York \
  stock-split-checker
```

## Configuration

### Required .env Variables
Create a `.env` file with your credentials:

```env
# Discord Configuration (Primary notification - optional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your/webhook/url

# Email Configuration (Secondary notification - optional)
SENDER_EMAIL=your_email@gmail.com
GMAIL_KEY=your_gmail_app_password

# SMS Configuration (Emergency fallback - at least one notification method required)
PHONE_NUMBER=1234567890

# Gemini API for fractional shares checking
GEMINI_API_KEY=your_gemini_api_key
```

### Schedule
- **Runs:** Monday through Friday at 8:00 AM MST
- **Timezone:** America/New_York (EST/EDT)
- **Cron expression:** `0 8 * * 1-5`

## Monitoring

### View Container Logs
```bash
# View all logs
docker-compose logs -f

# View only cron logs
docker exec stock-split-checker tail -f /var/log/cron.log

# View application logs
docker exec stock-split-checker tail -f /app/stock_split_checker.log
```

### Check Container Status
```bash
# Check if container is running
docker-compose ps

# Check cron jobs
docker exec stock-split-checker crontab -l
```

## Troubleshooting

### Test Run
```bash
# Run the script manually inside container
docker exec stock-split-checker python /app/reverse_split_checker.py
```

### Debug Container
```bash
# Get shell access to container
docker exec -it stock-split-checker /bin/bash

# Check cron service
docker exec stock-split-checker service cron status
```

### Timezone Issues
```bash
# Check container timezone
docker exec stock-split-checker date
docker exec stock-split-checker cat /etc/timezone
```

## File Persistence

The following are mounted as volumes to persist data:
- `.env` - Your credentials
- `logs/` - Browser debug logs
- `stock_split_checker.log` - Application logs

## Updates

### When you make code changes:
Docker builds an image with a snapshot of your code, so changes to `.py` files require rebuilding:

```bash
# Method 1: Rebuild and restart in one command
docker-compose up -d --build

# Method 2: Manual steps for more control
docker-compose down          # Stop container
docker-compose build --no-cache  # Rebuild with latest code
docker-compose up -d         # Start updated container
```

### What requires rebuilding:
- ✅ **Requires rebuild**: Changes to `.py` files, `requirements.txt`, `Dockerfile`, etc.
- ❌ **No rebuild needed**: Changes to `.env` file (mounted as volume)
- ❌ **No rebuild needed**: Log files (mounted as volumes)

### Quick rebuild command:
```bash
# This is the fastest way to update your code changes
docker-compose up -d --build
```

## Security Notes

- Never commit your `.env` file to version control
- Use app passwords for Gmail, not your main password
- Discord webhooks are safer than storing Discord bot tokens
- Consider using Docker secrets for production deployments

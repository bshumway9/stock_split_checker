# Stock Split Checker

A Python application that monitors upcoming reverse stock splits from multiple financial data sources and automatically sends notifications via Discord, email, or SMS. The application helps identify stocks that round up fractional shares during reverse splits, which can be profitable for investors holding small positions.

---

## Table of Contents

1. [Features](#features)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Notifications & Automation](#notifications--automation)
   - [Discord Webhook Setup](#discord-webhook-setup)
   - [Discord Buy Bot Integration](#discord-buy-bot-integration)
5. [Usage](#usage)
6. [File Structure](#file-structure)
7. [How It Works](#how-it-works)
8. [Troubleshooting](#troubleshooting)
9. [Customization](#customization)
10. [Contributing](#contributing)
11. [License](#license)
12. [Disclaimer](#disclaimer)

---

## Features

- **Multi-Source Data Aggregation**: Scrapes stock split data from:
   - Yahoo Finance (primary source)
   - HedgeFollow.com (primary source)
   - Nasdaq.com (optional) (currently unavailable)
   - SEC Edgar filings (optional) (currently unavailable)
   - StockTitan.net (optional) (currently unavailable)
- **AI-Powered Analysis**: Uses Google Gemini API to automatically research and categorize how companies handle fractional shares during reverse splits, and extract split details and thresholds.
- **Smart Categorization**: Organizes reverse splits into actionable categories (Buy 1 Share, Buy ? Shares, Check Rounding)
- **Flexible Notifications**: Sends notifications via Discord, Email (Gmail SMTP), and (limited) SMS (email-to-SMS gateways; not fully supported)
- **Automated Scheduling**: Can be configured to run daily checks
- **Docker Support**: Run the app easily in a container ([see Docker Support](#docker-support))
## Quick Start

1. **Clone or download the project:**
   ```bash
   git clone <repository-url>
   cd stock_split_checker
   ```
2. **Copy and edit the example environment file:**
   ```bash
   cp example.env .env
   nano .env
   ```
3. **(Recommended) Create a virtual environment and install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Run once for testing:**
   ```bash
   python reverse_split_checker.py
   ```
5. **For Docker users:**
   See [Docker Support](#docker-support) or [DOCKER_SETUP.md](DOCKER_SETUP.md) for full container instructions.

---

## Docker Support

You can run this project in a container for easy scheduling and isolation. See [DOCKER_SETUP.md](DOCKER_SETUP.md) for full instructions, including how to mount your `.env` and `logs/` directories for persistence.

---


## Configuration

Create a `.env` file in the project root directory with the following variables (see `example.env` for a template):

### Required Variables
```env
# Discord webhook (Required for notifications) (Primary Notification)
DISCORD_WEBHOOK_URL=your-discord-webhook-url
DISCORD_BUY_WEBHOOK_URL=your-discord-buy-webhook-url
# Gmail Configuration (Required for notifications) (Secondary Notification)
SENDER_EMAIL=your-gmail@gmail.com
GMAIL_KEY=your-app-password
# Google Gemini API (Required for AI analysis of fractional share handling)
GEMINI_API_KEY=your-gemini-api-key
# Phone Number (Optional, for SMS notifications; limited support)
PHONE_NUMBER=1234567890
```

### Optional Variables
```env
# Additional Email Recipients (not yet implemented)
RECIPIENT_EMAIL=recipient@example.com
```

**Security Tip:** Never commit your `.env` file with real credentials to a public repo.

---

## Optional: Setting Up Google Gemini API

The Gemini API is used to automatically research how companies handle fractional shares during reverse splits. This feature is optional but highly recommended for accurate categorization.

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create a new API key
3. Ensure your API key has access to the Google Search grounding tool (usually automatic)
4. Add the API key to your `.env` file as `GEMINI_API_KEY`

**Note:** Without the Gemini API, all splits will be categorized as "Check Rounding" and you'll need to research fractional share handling manually.

---

## Notifications & Automation


### [Discord Webhook Setup](DISCORD_SETUP.md)

To enable Discord notifications, set up a Discord webhook and add its URL to your `.env` file. For a full step-by-step guide and to see the message formatting, see [DISCORD_SETUP.md](DISCORD_SETUP.md).


### Discord Buy Bot Integration

This project supports seamless stock purchases via Discord using a buy command webhook. When actionable splits are found, the app sends a buy message to a Discord bot (such as [auto-rsa](https://github.com/NelsonDane/auto-rsa)) that is already set up and connected to your brokerages. Only stocks that round up fractional shares to a whole share are included. To actually execute buys, set `dry_run=False` in `reverse_split_checker.py`.

**Setup:**
1. Set up the [auto-rsa](https://github.com/NelsonDane/auto-rsa) Discord bot and connect it to your brokerages (see that repo for Docker container setup and instructions).
2. Add your Discord buy webhook URL to your `.env` as `DISCORD_BUY_WEBHOOK_URL`.
3. When a qualifying split is found, the bot will send the buy command to your Discord, and the auto-rsa bot will handle the purchase.

**Message Format Example:**
```
!rsa buy 1 SYMBOL1,SYMBOL2,SYMBOL3 all true
```
Where `SYMBOL1,SYMBOL2,...` are the stock symbols that round up fractional shares to a whole share ("Buy 1 Share" category). The final `true` or `false` indicates whether the message is a dry run (test) or a live command.

> **Note:** Follow the [auto-rsa GitHub repo](https://github.com/NelsonDane/auto-rsa) for the latest on Docker container setup and brokerage integration.

---


## Gemini-Powered Extraction Details

- **Split Ratio Format**: Always returned as `X->Y` (e.g. `100->1` for reverse, `1->5` for forward)
- **Effective Date Format**: Always returned as `YYYY-MM-DD`
- **Fractional Handling**: Always one of:
   - `ROUND_UP` (round up to nearest whole share)
   - `CASH_IN_LIEU` (pay cash for fractional shares)
   - `ROUND_DOWN` (round down)
   - `THRESHOLD_ROUND_UP` (round up only if fractional shares exceed a threshold)
   - `OTHER/NOT_ENOUGH_INFO` (other or unknown)
- **Threshold Extraction**: For splits with a threshold, `get_threshold_minimum_shares` will extract the minimum shares required and explanation, retrying up to 3 times if needed.

## Input Requirements for AI Functions

- `get_split_details` only requires `symbol` and `article_link` for each stock; all other details are extracted automatically.
- `get_threshold_minimum_shares` requires `symbol`, `ratio`, and optionally a grounding link.

## Requirements

- Python 3.7+
- Chrome/Chromium browser (for Selenium web scraping)
- Gmail account with App Password enabled
- Google Gemini API key (for AI analysis)
- Email for sending and receiving results

## Installation

1. **Clone or download the project**:
   ```bash
   git clone <repository-url>
   cd stock_split_checker
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install required packages**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Chrome WebDriver** (automatic via webdriver-manager):
   The application will automatically download and manage the Chrome WebDriver when first run.

## Configuration

Create a `.env` file in the project root directory with the following variables:

### Required Variables

```env
# Discord webhook (Required for notifications) (Primary Notification)

# Gmail Configuration (Required for notifications) (Secondary Notification)
SENDER_EMAIL=your-gmail@gmail.com
GMAIL_KEY=your-app-password

# Google Gemini API (Required for AI analysis of fractional share handling)
GEMINI_API_KEY=your-gemini-api-key

# Phone Number (Optional, for SMS notifications) (Last resort notifications)
PHONE_NUMBER=1234567890
```

### Optional Variables

```env

# Additional Email Recipients (if different from sender)(not yet implemented will only use sender)
RECIPIENT_EMAIL=recipient@example.com
```

## Setting Up Gmail App Password

1. **Enable 2-Factor Authentication** on your Gmail account
2. Go to your [Google Account settings](https://myaccount.google.com/)
3. Navigate to **Security** → **2-Step Verification** → **App passwords**
4. Generate a new app password for "Mail"
5. Use this 16-character password as your `GMAIL_KEY` in the `.env` file

**Important**: Do not use your regular Gmail password. You must use an App Password.

## Setting Up Google Gemini API

The Gemini API is used to automatically research how companies handle fractional shares during reverse splits. This feature is optional but highly recommended for accurate categorization.

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create a new API key
3. Ensure your API key has access to the Google Search grounding tool (usually automatic)
4. Add the API key to your `.env` file as `GEMINI_API_KEY`

**Note**: Without the Gemini API, all splits will be categorized as "Check Rounding" and you'll need to research fractional share handling manually.

## Usage

### Run Once (Testing)

```bash
python reverse_split_checker.py
```

### Previously Sent Tracking and Querying

This project tracks splits that have already been sent and keeps them available until their execution date passes (or the date is unknown). Two files are created in the host-mounted `logs/` directory:

- `logs/previously_sent_db.json` — a JSON database with full split records, including when they were first sent and last seen
- `logs/previously_sent.txt` — a human‑readable list of previously sent, still‑buyable items

Emails and Discord messages include a separate "Previously Sent (Still Buyable)" section. The main sections only show new items from the current run to avoid noise.

#### Query the DB from your host

Use the included CLI to query the persisted DB without opening the container:

```bash
# Show all still-buyable previously sent
python3 query_sent_db.py --still-buyable

# Filter by symbol
python3 query_sent_db.py --symbol ABCD

# Filter by effective date or date range
python3 query_sent_db.py --on 2025-08-20
python3 query_sent_db.py --from 2025-08-01 --to 2025-08-31

# Get raw JSON output (for piping/automation)
python3 query_sent_db.py --json --symbol ABCD
```

Notes:
- The default DB path is `logs/previously_sent_db.json`. Override with `--db /path/to/db.json` if needed.
- "Still buyable" means execution date is unknown or on/after today’s next market day.
- The DB keys are `SYMBOL|EFFECTIVE_DATE`; the stored value includes the full split record under `data`, plus `first_sent` and `last_seen` timestamps.

### Enable Scheduled Daily Runs

Uncomment the scheduling code at the bottom of `reverse_split_checker.py`:

```python
if __name__ == "__main__":
    # Run once immediately for testing
    # main()
    
    # Schedule daily execution
    schedule_task()
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute
```

### Test Individual Components

Test specific scrapers:
```bash
python test_yahoo_finance.py
python test_hedge_follow.py
python test_nasdaq_scraper.py #(nasdaq doesn't work currently)
```

## File Structure

```
stock_split_checker/
├── reverse_split_checker.py     # Main application entry point
├── query_sent_db.py             # CLI tool to query previously sent DB
├── requirements.txt             # Python dependencies
├── .env                        # Environment variables (create this)
├── README.md                   # This file
├── send_txt_msg.py            # Email/SMS notification handler
├── check_roundup.py           # Gemini AI analysis for fractional shares
├── table_scrapers.py          # Selenium-based web scrapers
├── site_scrapers.py           # Additional web scrapers
├── helper_functions.py        # Utility functions
├── test_*.py                  # Individual scraper test scripts
└── logs/                      # Debug logs, screenshots, and persisted data
   ├── stock_split_checker.log    # Application log file
   ├── last_run.txt            # Last application run time
   ├── previously_sent_db.json # Full records of previously sent splits (host-visible)
   └── previously_sent.txt     # Human-readable “Previously Sent (Still Buyable)” list
```

## How It Works

1. **Data Collection**: The application scrapes upcoming stock split data from multiple financial websites using Selenium WebDriver

2. **Filtering**: Only reverse stock splits are kept (where the ratio results in fewer shares)

3. **Deduplication**: Removes duplicate entries based on stock symbol and effective date

4. **AI Analysis**: If Gemini API is configured, the application researches each company's fractional share handling policy

5. **Categorization**: Splits are organized into actionable categories:
   - **Buy 1 Share**: Guaranteed to round up any fractional shares
   - **Buy ? Shares**: May round up depending on threshold
   - **Check Rounding**: Requires manual research

6. **Notification**: Sends formatted email/SMS with the categorized results

## Troubleshooting

### Common Issues

1. **"No module named" errors**: Ensure all requirements are installed with `pip install -r requirements.txt`

2. **Chrome/ChromeDriver issues**: The application automatically manages ChromeDriver. If you encounter issues, ensure Chrome browser is installed and up to date.

3. **Email authentication errors**: 
   - Verify you're using an App Password, not your regular Gmail password
   - Ensure 2-Factor Authentication is enabled on your Gmail account
   - Check that `SENDER_EMAIL` and `GMAIL_KEY` are correct in your `.env` file

4. **No splits found**: This is normal when there are no upcoming reverse splits. The application will send a notification stating "No upcoming reverse stock splits found."

5. **Gemini API errors**: 
   - Verify your API key is correct
   - Ensure your API key has access to the Google Search grounding tool
   - Check your API usage limits

### Debug Information

- Last run time is written to `logs/last_run.txt`
- Application logs are written to `logs/stock_split_checker.log`
- Selenium debug screenshots and HTML are saved to the `logs/` directory (maybe?)
- Run individual test scripts to debug specific scrapers

### Rate Limiting

The application includes built-in rate limiting and delays to avoid overwhelming target websites. If you encounter blocking:

- Increase delays in the scraper code
- Consider running less frequently
- Check if target websites have changed their structure

## Customization

### Adding New Data Sources

To add new stock split data sources:

1. Create a new scraper function in `site_scrapers.py` or `table_scrapers.py`
2. Add the scraper to the `get_reverse_splits()` function in `reverse_split_checker.py`
3. Ensure the scraper returns data in the expected format:

```python
{
    'symbol': 'STOCK',
    'company': 'Company Name',
    'ratio': '1-for-10',
    'effective_date': '2025-08-15',
    'fractional': 'Not specified',
    'is_reverse': True,
    'source': 'Source Name'
}
```

### Modifying Notification Format

Edit the `send_message()` function in `reverse_split_checker.py` to customize the notification format.

### Changing Carriers for SMS (SMS not fully supported)

Modify the `CARRIER_MAP` in `send_txt_msg.py` to add support for additional mobile carriers.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is for educational and personal use. Please respect the terms of service of the websites being scraped and use appropriate rate limiting.

## Disclaimer

**Not Financial or Investment Advice:**

This application is for informational and educational purposes only. It does not constitute financial, investment, or trading advice. No guarantee is made regarding the accuracy, completeness, or reliability of the data or actions taken by the bot. Always do your own research and consult a qualified financial advisor before making investment decisions. Use at your own risk.

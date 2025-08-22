
import schedule
from datetime import datetime
import logging
import asyncio
from send_txt_msg import send_txt
from send_discord_msg import send_discord_buy_message, send_discord_message
from dotenv import dotenv_values
from check_roundup import check_roundup, get_split_details, get_threshold_minimum_shares
from send_email_msg import send_email_message
from table_scrapers import scrape_yahoo_finance_selenium, scrape_hedge_follow, scrape_stock_titan
from helper_functions import next_market_day, add_current_prices, market_is_open, get_side_from_ratio
import time as pytime
import json
import os

# Generic retry helper
def run_with_retries(func, max_retries=2, delay=5, *args, **kwargs):
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            logging.warning(f"Error in {func.__name__} (attempt {attempt+1}/{max_retries+1}): {e}")
            if attempt < max_retries:
                logging.info(f"Retrying {func.__name__} in {delay} seconds...")
                pytime.sleep(delay)
    logging.error(f"All {max_retries+1} attempts failed for {func.__name__}")
    if last_exception:
        raise last_exception
    return None

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
    try:
        splits.extend(run_with_retries(scrape_yahoo_finance_selenium, max_retries=2, delay=10))
    except Exception as e:
        logging.error(f"Yahoo Finance scraping failed after retries: {e}")

    try:
        new_splits, new_past_splits = run_with_retries(scrape_hedge_follow, max_retries=2, delay=10)
        splits.extend(new_splits)
        past_splits.extend(new_past_splits)
    except Exception as e:
        logging.error(f"HedgeFollow scraping failed after retries: {e}")

    try:
        recent_splits, all_splits_with_links = run_with_retries(scrape_stock_titan, max_retries=2, delay=10)
    except Exception as e:
        logging.error(f"StockTitan scraping failed after retries: {e}")
        recent_splits, all_splits_with_links = [], []

    # If you want to add Nasdaq with retries, uncomment below:
    # try:
    #     splits.extend(run_with_retries(scrape_nasdaq, max_retries=2, delay=10))
    # except Exception as e:
    #     logging.error(f"Nasdaq scraping failed after retries: {e}")
    
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
                # logging.info(f"Merged article links for past split {symbol}: {len(merged_links)} total links")
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

    # Filter out symbols already known in DB unless info is unknown/insufficient
    try:
        db = _load_sent_db()
        # Build map: symbol -> list of stored records (data dicts)
        db_by_symbol = {}
        for _k, _v in db.items():
            _data = _get_rec_data(_v)
            _sym = _norm_symbol(_data.get('symbol', '')) if isinstance(_data, dict) else ''
            if _sym:
                db_by_symbol.setdefault(_sym, []).append(_data)

        def _is_unknown(val: str) -> bool:
            v = (val or '').strip().lower()
            return v in ('', 'unknown')

        def _is_insufficient_fractional(frac: str) -> bool:
            f = (frac or '').strip().lower()
            return f in (
                'check rounding policy',
                'unknown',
                'not specified',
                'unspecified',
                '',
                'not enough information'
            )

        filtered_check_splits = []
        for s in check_splits:
            sym = _norm_symbol(s.get('symbol', ''))
            if not sym:
                filtered_check_splits.append(s)
                continue
            recs = db_by_symbol.get(sym, [])
            if not recs:
                # No record in DB — classify
                filtered_check_splits.append(s)
                continue
            # If any record for this symbol has all known fields, skip classification
            skip = False
            for rec in recs:
                ratio_known = not _is_unknown(rec.get('ratio'))
                date_known = not _is_unknown(rec.get('effective_date'))
                frac_sufficient = not _is_insufficient_fractional(rec.get('fractional'))
                if ratio_known and date_known and frac_sufficient:
                    skip = True
                    break
            if not skip:
                filtered_check_splits.append(s)

        check_splits = filtered_check_splits
    except Exception as _filter_e:
        logging.warning(f"Failed filtering pre-check splits against DB: {_filter_e}")

    check_splits = get_split_details(check_splits)

    # Filter for splits from today onward
    today = next_market_day()
    prev_week = next_market_day(datetime.now().date(), previous=True, days=5)
    upcoming_splits = [
        split for split in unique_splits
        if (
            split['effective_date'].lower() == "unknown"
            or datetime.strptime(split['effective_date'], '%Y-%m-%d').date() >= today
        )
    ]
    checked_splits = [
        split for split in check_splits
        if (
            split['effective_date'].lower() == "unknown"
            or datetime.strptime(split['effective_date'], '%Y-%m-%d').date() >= today
        )
    ]

    logging.info(f"Found {len([split for split in upcoming_splits if split['article_link']])} upcoming splits with article links with {len(upcoming_splits)} total upcoming splits")
    return upcoming_splits, checked_splits


SENT_DB_PATH = 'logs/previously_sent_db.json'
SENT_REPORT_PATH = 'logs/previously_sent.txt'

def _split_key(s):
    return f"{_norm_symbol(s.get('symbol',''))}|{_norm_effective_date(s.get('effective_date','unknown'))}"

def _norm_symbol(sym: str) -> str:
    try:
        return (sym or '').strip().upper()
    except Exception:
        return (sym or '').upper()

def _norm_effective_date(ed: str) -> str:
    if not ed:
        return 'unknown'
    s = str(ed).strip()
    if not s:
        return 'unknown'
    low = s.lower()
    if low in ('unknown', 'n/a', 'na', 'tbd', 'pending', '-', '—', 'none'):
        return 'unknown'
    # Try to parse common formats and normalize to YYYY-MM-DD
    from datetime import datetime as _dt
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d', '%m-%d-%Y'):
        try:
            return _dt.strptime(s, fmt).strftime('%Y-%m-%d')
        except Exception:
            pass
    # As a fallback, return lowercase token or original if resembles YYYY-MM-DD
    return s if len(s) == 10 and s[4] == '-' else 'unknown'

def _load_sent_db():
    try:
        if os.path.exists(SENT_DB_PATH):
            with open(SENT_DB_PATH, 'r') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load sent DB: {e}")
    return {}

def _save_sent_db(db: dict):
    try:
        os.makedirs(os.path.dirname(SENT_DB_PATH), exist_ok=True)
        with open(SENT_DB_PATH, 'w') as f:
            json.dump(db, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save sent DB: {e}")

def _get_rec_data(rec: dict) -> dict:
    """Return the split dict from a DB record, supporting legacy schema."""
    if isinstance(rec, dict) and 'data' in rec:
        return rec['data']
    return rec

def _write_sent_report(db: dict):
    try:
        os.makedirs(os.path.dirname(SENT_REPORT_PATH), exist_ok=True)
        lines = ["Previously Sent (Still Buyable)\n", "===============================\n\n"]
        today = next_market_day()
        count = 0
        def sort_key(item):
            rec = _get_rec_data(item[1])
            return rec.get('effective_date', '')
        for k, v in sorted(db.items(), key=sort_key):
            rec = _get_rec_data(v)
            eff = rec.get('effective_date','unknown')
            # Show only those still buyable
            try:
                still_buyable = eff.lower() == 'unknown' or datetime.strptime(eff, '%Y-%m-%d').date() >= today
            except Exception:
                still_buyable = True
            if not still_buyable:
                continue
            count += 1
            first_sent = v.get('first_sent', '') if isinstance(v, dict) else ''
            if isinstance(v, dict) and 'data' in v:
                first_sent = v.get('first_sent', '')
            lines.append(f"{rec.get('symbol','?')}  {rec.get('ratio','N/A')}  effective: {eff}  first_sent: {first_sent}\n")
        if count == 0:
            lines.append("(none)\n")
        with open(SENT_REPORT_PATH, 'w') as f:
            f.writelines(lines)
    except Exception as e:
        logging.error(f"Failed to write sent report: {e}")


def send_message(splits, prev_splits=None):
    """Send text message with reverse split data."""
    try:
        prev_splits = prev_splits or []

        # Try Discord first, fallback to email if Discord fails or is not configured
        discord_webhook = env.get("DISCORD_WEBHOOK_URL", "")
        discord_sent = False
        email_sent = False

        if discord_webhook:
            try:
                logging.info("Sending Discord message")
                discord_success = asyncio.run(
                    send_discord_message(discord_webhook, splits, "Stock Split Bot", prev_splits=prev_splits)
                )
                if discord_success:
                    logging.info("Discord message sent successfully")
                    discord_sent = True
                else:
                    logging.error("Failed to send Discord message - will fallback to email")
            except Exception as e:
                logging.error(f"Error sending Discord message: {e} - will fallback to email")

        # Send email only if Discord wasn't sent or if no Discord webhook is configured
        if not discord_sent:
            logging.info("Sending email message")
            email_sent = send_email_message(splits, prev_splits=prev_splits)
            if email_sent:
                logging.info("Email sent successfully")
            else:
                logging.error("Failed to send email - will fallback to SMS")

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
        logging.error(f"Error sending messages: {e}")

def main():
    """Main function to run the reverse split checker."""
    # check if market is open today
    is_open = market_is_open(datetime.now().strftime("%Y-%m-%d"))
    if not is_open:
        logging.warning("Market is closed today, purchasing will be skipped.")
    else:
        logging.info("Market is open today, purchases may be executed.")
    logging.info("Starting reverse split check")
    splits, pre_checked_splits = get_reverse_splits()
    logging.info(f"Found {len(splits)} upcoming reverse splits")

    # Combine candidates
    candidates = list(splits)
    if pre_checked_splits:
        candidates += pre_checked_splits

    # Load sent DB and split into new vs previously sent (still buyable)
    db = _load_sent_db()
    today = next_market_day()
    prev_week = next_market_day(datetime.now().date(), previous=True, days=5)

    def is_still_buyable(s):
        try:
            ed = s.get('effective_date', 'unknown')
            return ed.lower() == 'unknown' or datetime.strptime(ed, '%Y-%m-%d').date() >= today
        except Exception:
            return True

    prev_splits = []  # will contain stored full records' data
    new_splits = []
    seen_keys = set()
    for s in candidates:
        key = _split_key(s)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        # Lookups with migration: if not found, try to find same symbol with unknown/known date
        rec = db.get(key)
        if not rec:
            sym_norm = _norm_symbol(s.get('symbol',''))
            ed_norm = _norm_effective_date(s.get('effective_date','unknown'))
            # Try find unknown record for this symbol
            unknown_key = f"{sym_norm}|unknown"
            known_match_key = None
            if ed_norm != 'unknown' and unknown_key in db:
                known_match_key = unknown_key
            # Or if scraped is unknown, try any known-date record for this symbol
            if not known_match_key and ed_norm == 'unknown':
                for k in list(db.keys()):
                    if k.startswith(f"{sym_norm}|") and not k.endswith('|unknown'):
                        known_match_key = k
                        break
            if known_match_key:
                # Migrate record under new normalized key
                rec = db.pop(known_match_key)
                rec_data = _get_rec_data(rec)
                rec_data['effective_date'] = ed_norm
                if isinstance(rec, dict):
                    rec['data'] = rec_data
                    rec['last_seen'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                db[key] = rec
        if rec:
            # Use stored record data to avoid reprocessing
            rec_data = _get_rec_data(rec)
            # Merge some fresh scraped fields into stored data (keep processed fields like 'fractional')
            try:
                # Update ratio/company/source if changed
                for fld in ['company', 'ratio', 'source']:
                    val = s.get(fld)
                    if val:
                        rec_data[fld] = val
                # Merge article links
                new_links = s.get('article_link', [])
                if new_links:
                    if isinstance(new_links, str):
                        new_links = [new_links]
                    existing_links = rec_data.get('article_link', [])
                    if isinstance(existing_links, str):
                        existing_links = [existing_links]
                    rec_data['article_link'] = list({*existing_links, *new_links})
                now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # Upgrade fractional decision if DB is missing/insufficient and scraped has decided
                def _is_insufficient(frac: str) -> bool:
                    f = (frac or '').strip().lower()
                    return f in ("check rounding policy", "unknown", "not specified", "unspecified", "")
                scraped_frac = s.get('fractional')
                if scraped_frac:
                    db_frac = rec_data.get('fractional')
                    if _is_insufficient(db_frac) and not _is_insufficient(scraped_frac):
                        rec_data['fractional'] = scraped_frac
                # Write back merged data
                if isinstance(rec, dict):
                    rec['data'] = rec_data
            except Exception as merge_e:
                logging.warning(f"Failed merging fresh fields for {key}: {merge_e}")
            if is_still_buyable(rec_data):
                prev_splits.append(rec_data)
            # Update last_seen metadata
            if isinstance(rec, dict):
                rec.setdefault('last_seen', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                db[key] = rec
        else:
            new_splits.append(s)

    # Process new splits only
    if new_splits:
        # Always refresh current prices for new items
        new_splits = add_current_prices(new_splits)
        # Split into those already carrying a fractional decision vs those needing processing
        already_processed = []
        to_process = []
        for s in new_splits:
            frac = (s.get('fractional') or '').strip().lower()
            key = _split_key(s)
            if frac and frac not in ("check rounding policy", "unknown", "not specified", "unspecified"):
                already_processed.append(s)
            elif key in db:
                # A DB record exists (possibly from migration); treat as processed
                rec = db.get(key)
                rec_data = _get_rec_data(rec)
                already_processed.append(rec_data or s)
            else:
                to_process.append(s)
        if to_process:
            logging.info("Checking fractional shares handling with Gemini API for new items (subset)")
            to_process = check_roundup(to_process)

        for split in to_process:
            if (split.get('fractional') or '').strip().lower() == "rounded up if fractional shares exceed a certain threshold":
                larger_side = get_side_from_ratio(split, side='max')
                min_shares, explanation = get_threshold_minimum_shares(
                    split.get('symbol'), larger_side, split.get('article_link')
                )
                split['min_shares_for_roundup'] = min_shares
                split['threshold_explanation'] = explanation

        new_splits = already_processed + to_process

    # Clean DB: keep unknown dates and anything from the last week of market days (supports legacy and new schema)
    clean_db = {}
    for k, v in db.items():
        rec_data = _get_rec_data(v)
        eff = rec_data.get('effective_date', 'unknown')
        try:
            eff_date = datetime.strptime(eff, '%Y-%m-%d').date()
            keep = eff.lower() == 'unknown' or eff_date >= prev_week
        except Exception:
            keep = True
        if keep:
            clean_db[k] = v
    db = clean_db

    # Add current run new items into DB
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for s in new_splits:
        key = _split_key(s)
        db[key] = {
            'data': s,
            'first_sent': now_str,
            'last_seen': now_str
        }

    # Also, if any prev_splits got a newly determined 'fractional' during this run, update DB record
    for s in prev_splits:
        key = _split_key(s)
        rec = db.get(key)
        if isinstance(rec, dict):
            data = rec.get('data', {})
            old_frac = (data.get('fractional') or '').strip().lower()
            new_frac = (s.get('fractional') or '').strip().lower()
            if new_frac and new_frac != old_frac:
                data['fractional'] = s.get('fractional')
                rec['data'] = data
                rec['last_seen'] = now_str
        elif rec is None:
            # Safety: if somehow not in DB but we have a decided result, add it now
            frac = (s.get('fractional') or '').strip().lower()
            if frac and frac not in ("check rounding policy", "unknown", "not specified", "unspecified", "not enough information", ""):
                db[key] = {
                    'data': s,
                    'first_sent': now_str,
                    'last_seen': now_str
                }

    # Persist DB and human-readable report
    logging.info(f"Persisting sent DB with {len(db)} records to {SENT_DB_PATH}")
    _save_sent_db(db)
    _write_sent_report(db)

    # Send messages including previously sent section; main sections show only new items
    send_message(new_splits, prev_splits=prev_splits)
    logging.info("Reverse split check completed")
    if is_open:
        discord_buy_webhook = env.get("DISCORD_BUY_WEBHOOK_URL", "")
        if not discord_buy_webhook:
            logging.warning("Discord buy webhook URL is not set.")
            return
        logging.info("Market is open today, attempting purchases now.")
        try:
            buy_success = asyncio.run(send_discord_buy_message(discord_buy_webhook, new_splits, dry_run=True))
            if buy_success:
                logging.info("Discord buy message sent successfully")
        except Exception as e:
            logging.error(f"Error sending Discord buy message FAILED PURCHASES: {e}")

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
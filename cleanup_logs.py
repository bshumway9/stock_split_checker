#!/usr/bin/env python3
"""
Log cleanup script for stock split checker.
Removes log entries older than 30 days to keep the log file manageable.
"""

import os
import re
from datetime import datetime, timedelta

# Configuration
LOG_FILE_PATH = "/app/logs/stock_split_checker.log"
DAYS_TO_KEEP = 30

def parse_log_timestamp(line):
    """Extract timestamp from log line."""
    # Match timestamp format: 2025-11-19 11:35:41,188
    match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d{3}', line)
    if match:
        try:
            return datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None
    return None

def cleanup_log_file():
    """Remove log entries older than DAYS_TO_KEEP days."""
    
    if not os.path.exists(LOG_FILE_PATH):
        print(f"Log file {LOG_FILE_PATH} not found")
        return
    
    # Calculate cutoff date
    cutoff_date = datetime.now() - timedelta(days=DAYS_TO_KEEP)
    print(f"Cleaning log entries older than {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Read original file
        with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        original_count = len(lines)
        print(f"Original log file has {original_count} lines")
        
        # Filter lines to keep only recent entries
        filtered_lines = []
        for line in lines:
            timestamp = parse_log_timestamp(line)
            if timestamp is None:
                # Keep lines without timestamps (continuation lines, etc.)
                filtered_lines.append(line)
            elif timestamp >= cutoff_date:
                # Keep recent entries
                filtered_lines.append(line)
        
        # Write filtered content back to original file
        with open(LOG_FILE_PATH, 'w', encoding='utf-8') as f:
            f.writelines(filtered_lines)
        
        filtered_count = len(filtered_lines)
        removed_count = original_count - filtered_count
        
        print(f"Cleanup completed:")
        print(f"  - Original lines: {original_count}")
        print(f"  - Remaining lines: {filtered_count}")
        print(f"  - Removed lines: {removed_count}")
        
    except Exception as e:
        print(f"Error during log cleanup: {e}")

if __name__ == "__main__":
    print(f"Starting log cleanup at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    cleanup_log_file()
    print("Log cleanup completed")
import os
from datetime import datetime, timedelta, time
import pytz
import subprocess
import sys

# Set your scheduled run time (Mountain Time)
SCHEDULED_HOUR = 8
SCHEDULED_MINUTE = 0
MT_TZ = pytz.timezone('America/Denver')
LAST_RUN_FILE = './last_run.txt'
SCRIPT_PATH = './reverse_split_checker.py'
PYTHON_PATH = sys.executable

now_mt = datetime.now(MT_TZ)
scheduled_today = now_mt.replace(hour=SCHEDULED_HOUR, minute=SCHEDULED_MINUTE, second=0, microsecond=0)

# Only check on weekdays
if now_mt.weekday() < 5:
    missed = False
    if os.path.exists(LAST_RUN_FILE):
        with open(LAST_RUN_FILE, 'r') as f:
            last_run_str = f.read().strip()
        try:
            last_run = datetime.strptime(last_run_str, '%Y-%m-%d %H:%M:%S')
            last_run = MT_TZ.localize(last_run)
            # If last run was before today's scheduled time and now is after scheduled time
            if last_run < scheduled_today and now_mt > scheduled_today:
                missed = True
        except Exception:
            missed = True
    else:
        # No record, assume missed
        missed = True
    if missed:
        # Run the main script
        subprocess.run([PYTHON_PATH, SCRIPT_PATH])
        # Update last run file
        with open(LAST_RUN_FILE, 'w') as f:
            f.write(now_mt.strftime('%Y-%m-%d %H:%M:%S'))

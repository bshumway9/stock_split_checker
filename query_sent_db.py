#!/usr/bin/env python3

import argparse
import json
import os
from datetime import datetime
from typing import Dict, Any, List

from helper_functions import next_market_day

DB_DEFAULT = os.path.join('logs', 'previously_sent_db.json')


def load_db(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        print(f"No DB found at {path}")
        return {}
    with open(path, 'r') as f:
        return json.load(f)


def get_rec_data(rec: Dict[str, Any]) -> Dict[str, Any]:
    # Support legacy schema where the record itself is the data
    if isinstance(rec, dict) and 'data' in rec:
        return rec['data']
    return rec


def is_still_buyable(effective_date: str) -> bool:
    try:
        if not effective_date or effective_date.lower() == 'unknown':
            return True
        return datetime.strptime(effective_date, '%Y-%m-%d').date() >= next_market_day()
    except Exception:
        return True


def filter_records(db: Dict[str, Any], symbol: str = None, on: str = None, frm: str = None, to: str = None,
                   still_buyable_only: bool = False, expired_only: bool = False) -> List[Dict[str, Any]]:
    results = []
    on_date = datetime.strptime(on, '%Y-%m-%d').date() if on else None
    from_date = datetime.strptime(frm, '%Y-%m-%d').date() if frm else None
    to_date = datetime.strptime(to, '%Y-%m-%d').date() if to else None

    for key, rec in db.items():
        data = get_rec_data(rec)
        eff_str = data.get('effective_date', 'unknown')
        sym = data.get('symbol', '')
        status_still = is_still_buyable(eff_str)

        # Symbol filter
        if symbol and sym.upper() != symbol.upper():
            continue

        # Date filters
        if eff_str.lower() != 'unknown':
            try:
                eff_date = datetime.strptime(eff_str, '%Y-%m-%d').date()
            except Exception:
                eff_date = None
        else:
            eff_date = None

        if on_date and eff_date and eff_date != on_date:
            continue
        if from_date and eff_date and eff_date < from_date:
            continue
        if to_date and eff_date and eff_date > to_date:
            continue

        if still_buyable_only and not status_still:
            continue
        if expired_only and status_still:
            continue

        results.append({
            'key': key,
            'data': data,
            'first_sent': rec.get('first_sent') if isinstance(rec, dict) else None,
            'last_seen': rec.get('last_seen') if isinstance(rec, dict) else None,
            'still_buyable': status_still
        })

    return results


def print_table(items: List[Dict[str, Any]]):
    if not items:
        print('(no results)')
        return
    # Columns: SYMBOL | EFFECTIVE_DATE | RATIO | FIRST_SENT | LAST_SEEN | STATUS
    rows = []
    for it in items:
        d = it['data']
        rows.append([
            d.get('symbol', ''),
            d.get('effective_date', ''),
            d.get('ratio', ''),
            it.get('first_sent', ''),
            it.get('last_seen', ''),
            'STILL' if it.get('still_buyable') else 'EXPIRED'
        ])
    # Compute widths
    headers = ['SYMBOL', 'EFFECTIVE_DATE', 'RATIO', 'FIRST_SENT', 'LAST_SEEN', 'STATUS']
    cols = list(zip(*([headers] + rows)))
    widths = [max(len(str(cell)) for cell in col) for col in cols]
    def fmt_row(r):
        return '  '.join(str(cell).ljust(w) for cell, w in zip(r, widths))
    print(fmt_row(headers))
    print('  '.join('-' * w for w in widths))
    for r in rows:
        print(fmt_row(r))


def main():
    p = argparse.ArgumentParser(description='Query previously sent reverse split records')
    p.add_argument('--db', default=DB_DEFAULT, help='Path to previously_sent_db.json')
    p.add_argument('--symbol', help='Filter by symbol (exact match)')
    p.add_argument('--on', help='Filter by effective date (YYYY-MM-DD)')
    p.add_argument('--from', dest='frm', help='Filter from effective date (YYYY-MM-DD)')
    p.add_argument('--to', help='Filter to effective date (YYYY-MM-DD)')
    p.add_argument('--still-buyable', action='store_true', help='Show only still buyable')
    p.add_argument('--expired', action='store_true', help='Show only expired')
    p.add_argument('--json', action='store_true', help='Output raw JSON for results')

    args = p.parse_args()
    db = load_db(args.db)
    items = filter_records(db, symbol=args.symbol, on=args.on, frm=args.frm, to=args.to,
                           still_buyable_only=args.still_buyable, expired_only=args.expired)

    if args.json:
        print(json.dumps(items, indent=2))
    else:
        print_table(items)


if __name__ == '__main__':
    main()

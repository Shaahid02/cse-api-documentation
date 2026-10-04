"""
CSE Historical Trades Fetcher
Loops through every company in company_data/data.json, fetches its daily OHLC
history from the authenticated historicalTrades endpoint, and saves one CSV per
company to historical_trades/<SYMBOL>.csv. Failures are logged to
historical_trades/logs/.

Requires the cse.lk `accessToken` cookie (see README), e.g. in PowerShell:
    $env:CSE_ACCESS_TOKEN = "eyJ..."
    python tools/fetch_historical_trades.py
    python tools/fetch_historical_trades.py --from-date 2020-01-01 --skip-existing
"""

import argparse
import csv
import json
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import CSE_API

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PARENT_DIR, "historical_trades")
LOG_DIR = os.path.join(OUTPUT_DIR, "logs")

# tradeDate is midnight Sri Lanka time; convert in that zone so dates don't shift on other machines
SRI_LANKA_TZ = timezone(timedelta(hours=5, minutes=30))

CSV_COLUMNS = ['date', 'open', 'high', 'low', 'close', 'turnover', 'share_volume', 'trade_volume']


DEFAULT_COMPANIES_FILE = os.path.join(PARENT_DIR, 'company_data', 'data.json')


def load_companies(path=DEFAULT_COMPANIES_FILE):
    """Load the company list (a JSON list of {symbol, name, ...}), by default company_data/data.json"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def setup_logger(timestamp):
    """Log everything to the console and to historical_trades/logs/fetch_<timestamp>.log"""
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger("historical_trades")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter('%(asctime)s %(levelname)-7s %(message)s', '%Y-%m-%d %H:%M:%S')
    log_path = os.path.join(LOG_DIR, f"fetch_{timestamp}.log")
    # Some company names don't fit the Windows console encoding; print them with replacements
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')
    for handler in (logging.FileHandler(log_path, encoding='utf-8'), logging.StreamHandler(sys.stdout)):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger, log_path


def rows_to_csv(rows, csv_path):
    """Write API rows (newest first) to a CSV sorted oldest first"""
    rows = sorted(rows, key=lambda r: r['tradeDate'])
    tmp_path = csv_path + '.tmp'
    with open(tmp_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_COLUMNS)
        for r in rows:
            trade_date = datetime.fromtimestamp(r['tradeDate'] / 1000, SRI_LANKA_TZ).date().isoformat()
            writer.writerow([trade_date, r.get('open'), r.get('high'), r.get('low'), r.get('close'),
                             r.get('turnover'), r.get('shareVolume'), r.get('tradeVolume')])
    os.replace(tmp_path, csv_path)  # never leave a half-written CSV behind
    return rows


def fetch_with_retry(cse, symbol, from_date, to_date, retries, logger):
    """Fetch one symbol, retrying network errors and 5xx responses"""
    for attempt in range(retries + 1):
        result = cse.get_historical_trades(symbol, from_date, to_date, period='D')
        status = result.get('status_code')
        transient = not result['success'] and (status is None or status >= 500)
        if not transient or attempt == retries:
            return result
        wait = 5 * (attempt + 1)
        logger.warning(f"{symbol}: {result['error']} - retrying in {wait}s ({attempt + 1}/{retries})")
        time.sleep(wait)


def fetch_all_historical_trades(from_date="2012-01-01", to_date=None, delay=1.0, limit=None,
                            skip_existing=False, retries=2, access_token=None,
                            companies_file=DEFAULT_COMPANIES_FILE):
    """
    Fetch daily history for every company in data.json and save one CSV per company

    Args:
        from_date: Start date (date, 'YYYY-MM-DD' or 'DD-MM-YYYY'), default 1 Jan 2012
        to_date: End date, defaults to today
        delay: Seconds to wait between companies
        limit: Only process the first N companies (for testing)
        skip_existing: Skip companies whose CSV already exists (to resume a run)
        retries: Retries per company for network errors / 5xx responses
        access_token: cse.lk accessToken cookie; defaults to CSE_ACCESS_TOKEN
        companies_file: JSON list of companies to fetch, default company_data/data.json

    Returns:
        Dict summary with lists of saved, empty, skipped and failed symbols
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger, log_path = setup_logger(timestamp)
    to_date = to_date or date.today()

    cse = CSE_API(access_token=access_token)
    if not cse.access_token:
        logger.error("No access token. Set CSE_ACCESS_TOKEN to the cse.lk accessToken cookie (see README).")
        return None

    companies = load_companies(companies_file)
    if limit:
        companies = companies[:limit]
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    logger.info(f"Fetching daily history {from_date} -> {to_date} for {len(companies)} companies")
    logger.info(f"Output: {OUTPUT_DIR}")

    saved, empty, skipped, failed = [], [], [], []

    for i, company in enumerate(companies, 1):
        symbol = company['symbol']
        name = company.get('name', '')
        csv_path = os.path.join(OUTPUT_DIR, f"{symbol}.csv")
        prefix = f"[{i}/{len(companies)}] {symbol}"

        if skip_existing and os.path.exists(csv_path):
            skipped.append(symbol)
            logger.info(f"{prefix}: CSV exists, skipped")
            continue

        try:
            result = fetch_with_retry(cse, symbol, from_date, to_date, retries, logger)

            if not result['success']:
                status = result.get('status_code')
                if status == 404:
                    # CSE answers "no trades in this range" with an empty 404
                    empty.append(symbol)
                    logger.warning(f"{prefix}: no data in range (HTTP 404) - {name}")
                else:
                    failed.append({'symbol': symbol, 'name': name, 'status_code': status, 'error': result['error']})
                    logger.error(f"{prefix}: FAILED - {result['error']}")
                    if status == 417:
                        # Token expired - every remaining request would fail the same way
                        not_attempted = companies[i:]
                        failed.extend({'symbol': c['symbol'], 'name': c.get('name', ''), 'status_code': None,
                                       'error': 'not attempted: access token expired'} for c in not_attempted)
                        logger.error(f"Access token expired - stopping. {len(not_attempted)} companies not attempted. "
                                     "Log in again, update CSE_ACCESS_TOKEN and rerun with --skip-existing.")
                        break
            else:
                rows = (result['data'] or {}).get('reqDaysOhlc') or []
                if not rows:
                    empty.append(symbol)
                    logger.warning(f"{prefix}: no data in range - {name}")
                else:
                    rows = rows_to_csv(rows, csv_path)
                    first = datetime.fromtimestamp(rows[0]['tradeDate'] / 1000, SRI_LANKA_TZ).date()
                    last = datetime.fromtimestamp(rows[-1]['tradeDate'] / 1000, SRI_LANKA_TZ).date()
                    saved.append(symbol)
                    logger.info(f"{prefix}: saved {len(rows)} days ({first} -> {last})")
        except Exception as e:
            # Unexpected response shape, disk errors, etc. - log and keep going
            failed.append({'symbol': symbol, 'name': name, 'status_code': None, 'error': f"{type(e).__name__}: {e}"})
            logger.exception(f"{prefix}: FAILED - unexpected error")

        if i < len(companies):
            time.sleep(delay)

    # Failures as a CSV too, so they're easy to filter or retry
    failed_path = None
    if failed:
        failed_path = os.path.join(LOG_DIR, f"failed_{timestamp}.csv")
        with open(failed_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['symbol', 'name', 'status_code', 'error'])
            writer.writeheader()
            writer.writerows(failed)

    logger.info("=" * 60)
    logger.info(f"Saved: {len(saved)} | No data: {len(empty)} | Skipped: {len(skipped)} | Failed: {len(failed)}")
    if empty:
        logger.info(f"No data: {', '.join(empty)}")
    if failed_path:
        logger.info(f"Failures written to: {failed_path}")
    logger.info(f"Full log: {log_path}")

    return {'saved': saved, 'empty': empty, 'skipped': skipped, 'failed': failed,
            'log_file': log_path, 'failed_file': failed_path}


def main():
    parser = argparse.ArgumentParser(description="Fetch daily trade history for every company in data.json")
    parser.add_argument('--from-date', default='2012-01-01', help="Start date, YYYY-MM-DD (default 2012-01-01)")
    parser.add_argument('--to-date', default=None, help="End date, YYYY-MM-DD (default today)")
    parser.add_argument('--delay', type=float, default=1.0, help="Seconds between companies (default 1.0)")
    parser.add_argument('--limit', type=int, default=None, help="Only process the first N companies")
    parser.add_argument('--skip-existing', action='store_true', help="Skip companies that already have a CSV")
    parser.add_argument('--retries', type=int, default=2, help="Retries for network errors / 5xx (default 2)")
    parser.add_argument('--companies-file', default=DEFAULT_COMPANIES_FILE,
                        help="JSON list of companies to fetch (default company_data/data.json)")
    args = parser.parse_args()

    summary = fetch_all_historical_trades(from_date=args.from_date, to_date=args.to_date, delay=args.delay,
                                      limit=args.limit, skip_existing=args.skip_existing, retries=args.retries,
                                      companies_file=args.companies_file)
    sys.exit(0 if summary is not None and not summary['failed'] else 1)


if __name__ == "__main__":
    main()

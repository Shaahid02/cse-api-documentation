"""
CSE Financial Reports Downloader
Downloads the files companies publish under "Financial Reports" on cse.lk (interim/quarterly
statements, annual reports and audited accounts, prospectuses, trust deeds, ...) into

    <output dir>/<SYMBOL>/<report type folder>/<upload date>_<title>_<id>.pdf

where <SYMBOL> is the company's full symbol (e.g. LHCL.N0000, see resolve_symbols) and the
report type folders are the values of REPORT_FOLDERS. Files already on disk are
skipped, so a run can be repeated or resumed. Each run writes a log and a CSV manifest to
<output dir>/logs/.

    python tools/download_financial_reports.py --all --output-dir "D:/CSE/Reports"     # everything
    python tools/download_financial_reports.py                             # last 12 months, all companies
    python tools/download_financial_reports.py --company LOLC --company "ABANS ELECTRICALS" --from-date 2015-01-01
    python tools/download_financial_reports.py --type annual --all         # every annual report
    python tools/download_financial_reports.py --company JKH --type interim --list    # list only, no download

Reports go back to 2007 (about 23,000 files in total). No access token is needed.
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta
from urllib.parse import quote, urljoin

import requests

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import CSE_API

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PARENT_DIR, "reports", "financial_reports")
CDN_URL = "https://cdn.cse.lk/"
EARLIEST_DATE = "2007-01-01"  # oldest financial report on cse.lk

# Report type -> sub folder inside each company folder ('/' isn't allowed in folder names)
REPORT_FOLDERS = {
    'interim': 'Interim & quarterly financial statements',
    'annual': 'Annual reports',
    'prospectus': 'Prospectuses',
    'trust-deed': 'Trust deeds (debentures & bonds)',
    'accountants-report': "Accountants' reports & five-year summaries",
    'other': 'Other',
}
REPORT_TYPES = list(REPORT_FOLDERS)

# Report types, matched against the free-text title in order (first match wins).
# Accountants' reports come first since some mention the prospectus they're for. "Annual report"
# is checked before interim so "Annual Report ... 31st March" isn't caught by the interim
# patterns; the broader annual patterns (audited, year ended) come after, so
# "Audited ... nine months ended" stays interim. Anything unmatched (press releases,
# articles of association, valuation reports, ...) is 'other'.
_TYPE_PATTERNS = [
    ('accountants-report', re.compile(r'ACCOUNTANT|AUDITOR.{0,3}GENERAL|\b(FIVE|\d)[ -]YEARS?\s+SUMM')),
    ('annual', re.compile(r'\bANN\w*L\s+REPORT')),
    ('interim', re.compile(r'INTERIM|\bQU[A-Z]*LY\b|QUARTER|\bQ[1-4]\b|[1-4]Q ?FY|'
                           r'\b(0?3|0?6|0?9|THREE|SIX|NINE)[ -]MONTHS?\b|PERIOD ENDED|HALF[ -]YEAR')),
    ('annual', re.compile(r'ANNUAL|AUDITED|YEAR ENDED|YEAR END\b')),
    ('prospectus', re.compile(r'PROSPECTUS|INTRODUCTORY DOCUMENT')),
    ('trust-deed', re.compile(r'TRUST DEED')),
]

# Share classes tried, in order, when turning a report's bare symbol ('LHCL') into the company's
# full symbol ('LHCL.N0000'): ordinary voting shares, then non-voting shares, then fund units
SYMBOL_SUFFIXES = ['N0000', 'X0000', 'U0000']

MANIFEST_COLUMNS = ['status', 'symbol', 'company_name', 'report_type', 'file_text', 'uploaded_date',
                    'announcement_id', 'local_path', 'file_size', 'url', 'error']


def classify_report(title):
    """Map a report title to one of REPORT_TYPES"""
    title = (title or '').upper()
    for report_type, pattern in _TYPE_PATTERNS:
        if pattern.search(title):
            return report_type
    return 'other'


def file_url(path):
    """
    CDN URL for a report's path. Older reports (before about mid-2019) have paths like
    'upload_report_file/x.pdf', but every file lives under cmt/ - without it the CDN answers 403.
    """
    path = path.lstrip('/')
    if not path.startswith('cmt/'):
        path = 'cmt/' + path
    return urljoin(CDN_URL, quote(path, safe='/'))


def base_symbol(symbol):
    """'ABAN.N0000' -> 'ABAN' (announcements use the bare symbol)"""
    return (symbol or '').split('.')[0].strip().upper()


def sanitize_filename(text, max_length=80):
    """Make text safe for a Windows/Unix filename"""
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', text or '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_length].rstrip(' .') or 'report'


def parse_uploaded_date(value):
    """'30 Sep 2026 02:41:48 PM' -> datetime, or None"""
    try:
        return datetime.strptime(value, '%d %b %Y %I:%M:%S %p')
    except (TypeError, ValueError):
        return None


def fs_path(path):
    """On Windows, add the long-path prefix so paths over 260 characters still work"""
    if os.name != 'nt':
        return path
    path = os.path.abspath(path)
    if path.startswith('\\\\?\\'):
        return path
    if path.startswith('\\\\'):  # network share
        return '\\\\?\\UNC\\' + path[2:]
    return '\\\\?\\' + path


def to_iso_date(value):
    """Accept a date or 'YYYY-MM-DD' and return 'YYYY-MM-DD' (what the API expects)"""
    if isinstance(value, date):
        return value.isoformat()
    return date.fromisoformat(str(value).strip()).isoformat()


class CSE_ReportDownloader:
    def __init__(self, output_dir=OUTPUT_DIR, delay=1.0, retries=2):
        """
        Args:
            output_dir: Root folder for downloads; files go to <output_dir>/<SYMBOL>/
            delay: Seconds to wait between downloads (not applied to skipped files)
            retries: Retries per request for network errors / 5xx responses
        """
        self.cse_api = CSE_API()
        self.output_dir = os.path.normpath(output_dir)
        self.delay = delay
        self.retries = retries
        self.session = requests.Session()
        self.session.headers['User-Agent'] = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                              '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        self.company_data = self.load_company_data()
        self.logger = logging.getLogger("financial_reports")
        self.fetch_failed = False
        self.symbol_map = {}  # bare symbol -> full symbol (None if the issuer has no listed shares)

    # ---------------------------------------------------------------- company lookup

    def load_company_data(self):
        """Load company data from company_data/data.json to get security IDs"""
        try:
            with open(os.path.join(PARENT_DIR, 'company_data', 'data.json'), 'r', encoding='utf-8') as f:
                return json.load(f)
        except (OSError, ValueError) as e:
            print(f"Warning: could not load company_data/data.json ({e}). Security ID lookup unavailable.")
            return []

    def find_security_id(self, symbol_or_name):
        """
        Find a security ID by symbol or name. Exact symbol ('ABAN' or 'ABAN.N0000') wins, then
        exact name, then the first partial name match.

        Returns:
            int or None
        """
        term = symbol_or_name.strip().upper()
        for match in (lambda c: base_symbol(c['symbol']) == base_symbol(term),
                      lambda c: c['name'].upper() == term,
                      lambda c: term in c['name'].upper()):
            for company in self.company_data:
                if match(company):
                    return company['securityId']
        return None

    def get_company_info(self, security_id):
        """Get company information (from data.json) by security ID"""
        for company in self.company_data:
            if company['securityId'] == security_id:
                return company
        return None

    # ---------------------------------------------------------------- fetching and filtering

    def fetch_announcements(self, from_date, to_date, security_id=None):
        """
        Fetch the financial report list for a date range (optionally one company)

        The endpoint needs a date range: without one it only returns the 5 newest reports.

        Returns:
            List of announcement dicts (newest first), or None if the request failed
        """
        from_date, to_date = to_iso_date(from_date), to_iso_date(to_date)
        company_ids = str(security_id) if security_id is not None else None
        for attempt in range(self.retries + 1):
            result = self.cse_api.get_financial_announcements_filtered(from_date, to_date, company_ids)
            if result['success']:
                return (result['data'] or {}).get('reqFinancialAnnouncemnets') or []
            status = result.get('status_code')
            if (status is not None and status < 500) or attempt == self.retries:
                self._log().error(f"Failed to fetch report list: {result['error']}")
                return None
            self._log().warning(f"Report list request failed ({result['error']}) - retrying")
            time.sleep(5 * (attempt + 1))

    @staticmethod
    def filter_announcements(announcements, companies=None, report_types=None, title_contains=None):
        """
        Filter announcements client-side

        Args:
            companies: Symbols ('LOLC', 'LOLC.N0000') or names. A term that exactly matches a
                       symbol in the list selects that symbol only; otherwise it matches any
                       company whose name contains it (case-insensitive)
            report_types: Iterable of REPORT_TYPES to keep
            title_contains: Keep reports whose title contains this text (case-insensitive)
        """
        if companies:
            symbols_present = {base_symbol(a['symbol']) for a in announcements}
            wanted_symbols, name_terms = set(), []
            for term in companies:
                if base_symbol(term) in symbols_present:
                    wanted_symbols.add(base_symbol(term))
                else:
                    name_terms.append(term.strip().upper())
            announcements = [a for a in announcements
                             if base_symbol(a['symbol']) in wanted_symbols
                             or any(t in (a['name'] or '').upper() for t in name_terms)]
        if report_types:
            report_types = set(report_types)
            announcements = [a for a in announcements if classify_report(a['fileText']) in report_types]
        if title_contains:
            needle = title_contains.upper()
            announcements = [a for a in announcements if needle in (a['fileText'] or '').upper()]
        return announcements

    # ---------------------------------------------------------------- full symbols

    def full_symbol(self, symbol):
        """'LHCL' -> 'LHCL.N0000' (after resolve_symbols); falls back to the bare symbol"""
        base = base_symbol(symbol) or 'UNKNOWN'
        return self.symbol_map.get(base) or base

    def resolve_symbols(self, bases):
        """
        Map bare report symbols ('LHCL') to full symbols ('LHCL.N0000') for the folder names

        Reports are filed per company, so a company with several securities gets one folder,
        named after the first class in SYMBOL_SUFFIXES it has. company_data/data.json and
        alll_companies.json are checked first; other symbols (mostly delisted companies) are
        looked up on cse.lk. Results are cached in <output_dir>/symbol_map.json so folder names
        stay the same between runs. Issuers with no listed shares (e.g. bond-only issuers like
        BOC) keep the bare symbol.

        Returns:
            False if a lookup failed with a network/server error
        """
        logger = self._log()
        cache_path = os.path.join(self.output_dir, 'symbol_map.json')
        try:
            with open(fs_path(cache_path), encoding='utf-8') as f:
                self.symbol_map.update(json.load(f))
        except FileNotFoundError:
            pass
        todo = sorted({b for b in bases if b and b not in self.symbol_map})
        if not todo:
            return True

        listed = {}
        for name in ('data.json', 'alll_companies.json'):
            try:
                with open(os.path.join(PARENT_DIR, 'company_data', name), encoding='utf-8') as f:
                    for company in json.load(f):
                        symbol = company['symbol'].strip().upper()
                        listed.setdefault(base_symbol(symbol), set()).add(symbol)
            except (OSError, ValueError, KeyError) as e:
                logger.warning(f"Could not read company_data/{name}: {e}")

        looked_up, no_shares, ok = 0, [], True
        for base in todo:
            candidates = [f"{base}.{suffix}" for suffix in SYMBOL_SUFFIXES]
            in_lists = [c for c in candidates if c in listed.get(base, ())]
            if in_lists:
                self.symbol_map[base] = in_lists[0]
                continue
            looked_up += 1
            found, failed = None, False
            for candidate in candidates:
                result = self._lookup_symbol(candidate)
                # Unknown symbols get 404; a 417 that persists through the retries means the
                # security exists but CSE can't show it (e.g. SMLL.N0000, delisted in 2013)
                if (result['success'] and ((result['data'] or {}).get('reqSymbolInfo') or {}).get('symbol')
                        or result.get('status_code') == 417):
                    found = candidate
                    break
                if not result['success'] and result.get('status_code') != 404:
                    logger.error(f"Symbol lookup for {candidate} failed: {result['error']}")
                    failed, ok = True, False
                    break
            if failed:
                continue  # not cached, so it's retried next run
            self.symbol_map[base] = found
            if not found:
                no_shares.append(base)

        os.makedirs(fs_path(self.output_dir), exist_ok=True)
        with open(fs_path(cache_path), 'w', encoding='utf-8') as f:
            json.dump(dict(sorted(self.symbol_map.items())), f, indent=1)
        logger.info(f"Resolved {len(todo)} company symbols ({looked_up} looked up on cse.lk)")
        if no_shares:
            logger.info(f"No listed shares, keeping the bare symbol: {', '.join(no_shares)}")
        return ok

    def _lookup_symbol(self, symbol):
        """companyInfoSummery for one symbol, pacing requests and retrying throttling (417) and 5xx"""
        for attempt in range(self.retries + 2):
            time.sleep(0.5)
            result = self.cse_api.get_company_info(symbol)
            status = result.get('status_code')
            if result['success'] or status == 404 or (status is not None and status < 500 and status != 417):
                return result
            if attempt <= self.retries:
                time.sleep(10 * (attempt + 1))
        return result

    # ---------------------------------------------------------------- downloading

    def local_path_for(self, announcement):
        """
        <output_dir>/<full symbol>/<report type folder>/<uploaded date>_<title>_<id>.<ext>
        The path is stable, so reruns can skip files already downloaded.
        """
        uploaded = parse_uploaded_date(announcement['uploadedDate'])
        day = uploaded.date().isoformat() if uploaded else 'unknown-date'
        ext = os.path.splitext(announcement['path'] or '')[1].lower()
        if not re.fullmatch(r'\.[a-z0-9]{2,5}', ext):
            ext = '.pdf'  # a few paths have no real extension
        type_folder = REPORT_FOLDERS[classify_report(announcement['fileText'])]
        filename = f"{day}_{sanitize_filename(announcement['fileText'])}_{announcement['id']}{ext}"
        return os.path.join(self.output_dir, self.full_symbol(announcement['symbol']), type_folder, filename)

    def download_file(self, url, local_path):
        """Download url to local_path (via a .tmp file), retrying network errors and 5xx"""
        local_path = fs_path(local_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        tmp_path = local_path + '.tmp'
        for attempt in range(self.retries + 1):
            try:
                response = self.session.get(url, timeout=60)
                response.raise_for_status()
                if not response.content:
                    raise ValueError("empty response")
                with open(tmp_path, 'wb') as f:
                    f.write(response.content)
                os.replace(tmp_path, local_path)  # never leave a half-written file behind
                return len(response.content)
            except requests.exceptions.RequestException as e:
                status = getattr(e.response, 'status_code', None)
                if (status is not None and status < 500) or attempt == self.retries:
                    raise
                wait = 5 * (attempt + 1)
                self._log().warning(f"    {e} - retrying in {wait}s ({attempt + 1}/{self.retries})")
                time.sleep(wait)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

    def download_announcements(self, announcements, overwrite=False, limit=None):
        """
        Download the file of each announcement, skipping ones already on disk

        Returns:
            List of result dicts (one per announcement) with 'success', 'status'
            ('downloaded', 'exists', 'no_file' or 'failed'), 'local_path', 'error', ...
        """
        logger = self._log()
        if limit:
            announcements = announcements[:limit]
        if not self.resolve_symbols({base_symbol(a['symbol']) for a in announcements}):
            logger.error("Some company symbols couldn't be looked up (network error) - nothing downloaded, "
                         "try again later so every file lands in the right folder")
            self.fetch_failed = True
            return []
        results = []
        counts = Counter()
        try:
            for i, a in enumerate(announcements, 1):
                symbol = self.full_symbol(a['symbol'])
                result = {
                    'symbol': symbol,
                    'company_name': a['name'],
                    'report_type': classify_report(a['fileText']),
                    'file_text': (a['fileText'] or '').strip(),
                    'uploaded_date': a['uploadedDate'],
                    'manual_date': a.get('manualDate'),
                    'announcement_id': a['id'],
                    'local_path': None, 'file_size': None, 'url': None, 'error': None,
                }
                prefix = f"[{i}/{len(announcements)}] {symbol}"

                if not a.get('path'):
                    # e.g. webinar entries that only have a title
                    result.update(success=False, status='no_file', error='announcement has no file')
                    logger.warning(f"{prefix}: no file attached - {result['file_text']}")
                else:
                    url = file_url(a['path'])
                    local_path = self.local_path_for(a)
                    result.update(url=url, local_path=local_path)
                    if os.path.exists(fs_path(local_path)) and not overwrite:
                        result.update(success=True, status='exists', file_size=os.path.getsize(fs_path(local_path)))
                        logger.info(f"{prefix}: already downloaded - {os.path.basename(local_path)}")
                    else:
                        try:
                            size = self.download_file(url, local_path)
                            result.update(success=True, status='downloaded', file_size=size)
                            logger.info(f"{prefix}: saved {os.path.basename(local_path)} ({size:,} bytes)")
                        except Exception as e:
                            result.update(success=False, status='failed', error=f"{type(e).__name__}: {e}")
                            logger.error(f"{prefix}: FAILED {result['file_text']} - {result['error']}")
                        if i < len(announcements):
                            time.sleep(self.delay)

                counts[result['status']] += 1
                results.append(result)
        except KeyboardInterrupt:
            logger.warning("Interrupted - rerun the same command to resume (downloaded files are skipped)")
            raise
        finally:
            logger.info("=" * 60)
            logger.info(f"Downloaded: {counts['downloaded']} | Already had: {counts['exists']} | "
                        f"No file: {counts['no_file']} | Failed: {counts['failed']}")
            logger.info(f"Files: {self.output_dir}")
            self._write_manifest(results)
        return results

    def download(self, from_date=None, to_date=None, companies=None, report_types=None, title_contains=None,
                 limit=None, overwrite=False, list_only=False, security_id=None):
        """
        Fetch the report list for a date range, filter it, then download (or just list) the files

        Args:
            from_date: Start date ('YYYY-MM-DD' or date), default 12 months ago
            to_date: End date, default today
            companies: List of symbols or names (see filter_announcements)
            report_types: List of REPORT_TYPES, e.g. ['annual']
            title_contains: Only reports whose title contains this text
            limit: Only the first N matching reports (newest first)
            overwrite: Download again even if the file exists
            list_only: Print the matching reports without downloading
            security_id: Ask the API for one company only (by data.json security ID)

        Returns:
            List of result dicts (see download_announcements); for list_only, the matching announcements
        """
        to_date = to_iso_date(to_date or date.today())
        from_date = to_iso_date(from_date or date.today() - timedelta(days=365))
        logger = self._setup_logger()

        logger.info(f"Fetching financial report list {from_date} -> {to_date}"
                    + (f" (security ID {security_id})" if security_id is not None else ""))
        announcements = self.fetch_announcements(from_date, to_date, security_id)
        self.fetch_failed = announcements is None
        if self.fetch_failed:
            return []
        total = len(announcements)
        announcements = self.filter_announcements(announcements, companies, report_types, title_contains)
        filters = [f"companies={', '.join(companies)}" if companies else '',
                   f"types={', '.join(report_types)}" if report_types else '',
                   f"title contains '{title_contains}'" if title_contains else '']
        filters = '; '.join(f for f in filters if f)
        logger.info(f"{total} reports in range" + (f", {len(announcements)} match {filters}" if filters else ""))

        if companies:
            matched = sorted({(base_symbol(a['symbol']), a['name'] or '') for a in announcements})
            logger.info(f"Companies matched ({len(matched)}): " + ', '.join(f"{s} ({n})" for s, n in matched))
            for term in companies:
                if not self.filter_announcements(announcements, [term]):
                    logger.warning(f"No matching reports for '{term}' - check the symbol/name or widen the dates")
        if announcements:
            by_type = Counter(classify_report(a['fileText']) for a in announcements)
            logger.info("By type: " + ', '.join(f"{t} {by_type[t]}" for t in REPORT_TYPES if by_type[t]))

        if list_only:
            announcements = announcements[:limit] if limit else announcements
            if not self.resolve_symbols({base_symbol(a['symbol']) for a in announcements}):
                self.fetch_failed = True
            for a in announcements:
                uploaded = parse_uploaded_date(a['uploadedDate'])
                day = uploaded.date().isoformat() if uploaded else '?'
                print(f"{day:<10}  {self.full_symbol(a['symbol']):<11}  "
                      f"{classify_report(a['fileText']):<13}  {(a['fileText'] or '').strip()}")
            return announcements
        return self.download_announcements(announcements, overwrite=overwrite, limit=limit)

    # ---------------------------------------------------------------- older entry points (kept for existing callers)

    def download_financial_reports(self, limit=None, company_filter=None):
        """Download every financial report since 2007, optionally for companies whose name contains company_filter"""
        return self.download(EARLIEST_DATE, companies=[company_filter] if company_filter else None, limit=limit)

    def download_specific_reports(self, symbols_list, from_date=EARLIEST_DATE, to_date=None):
        """Download reports for specific symbols, e.g. ['LOLC', 'CSLK'] (all history by default)"""
        return self.download(from_date, to_date, companies=symbols_list)

    def download_reports_by_date_range(self, from_date, to_date, security_id=None):
        """Download reports in a date range, optionally for one company by security ID (e.g. 642)"""
        return self.download(from_date, to_date, security_id=security_id)

    def download_reports_by_company_name(self, company_name_or_symbol, from_date, to_date):
        """Download reports for a company by symbol or name in a date range"""
        return self.download(from_date, to_date, companies=[company_name_or_symbol])

    def download_reports_by_security_id(self, security_id, from_date, to_date):
        """DEPRECATED: use download_reports_by_date_range()"""
        return self.download_reports_by_date_range(from_date, to_date, security_id)

    def download_reports_by_time_range(self, from_date, to_date):
        """DEPRECATED: use download_reports_by_date_range()"""
        return self.download_reports_by_date_range(from_date, to_date)

    # ---------------------------------------------------------------- logging

    def _setup_logger(self):
        """Log to the console and to <output_dir>/logs/download_<timestamp>.log"""
        self.run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.path.join(self.output_dir, "logs")
        os.makedirs(fs_path(log_dir), exist_ok=True)
        logger = self.logger
        logger.setLevel(logging.INFO)
        logger.propagate = False
        for handler in logger.handlers:
            handler.close()
        logger.handlers.clear()
        formatter = logging.Formatter('%(asctime)s %(levelname)-7s %(message)s', '%Y-%m-%d %H:%M:%S')
        # Some company names don't fit the Windows console encoding; print them with replacements
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(errors='replace')
        self.log_path = os.path.join(log_dir, f"download_{self.run_timestamp}.log")
        for handler in (logging.FileHandler(fs_path(self.log_path), encoding='utf-8'),
                        logging.StreamHandler(sys.stdout)):
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def _log(self):
        if not self.logger.handlers:
            self._setup_logger()
        return self.logger

    def _write_manifest(self, results):
        """One CSV row per report handled in this run, to filter or retry failures"""
        if not results:
            return
        path = os.path.join(self.output_dir, "logs", f"manifest_{self.run_timestamp}.csv")
        with open(fs_path(path), 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(results)
        self.logger.info(f"Manifest: {path}")
        self.logger.info(f"Full log: {self.log_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Download CSE financial reports (interim/annual statements, prospectuses, ...)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Report types: " + ', '.join(REPORT_TYPES) + "\n\n"
               "examples:\n"
               "  %(prog)s --all --output-dir D:\\CSE\\Reports\n"
               "  %(prog)s --company LOLC --from-date 2015-01-01\n"
               "  %(prog)s --type annual --all\n"
               "  %(prog)s --company JKH,SAMP --type interim --list")
    parser.add_argument('--from-date', default=None,
                        help=f"Start date YYYY-MM-DD (default 12 months ago; {EARLIEST_DATE} for everything)")
    parser.add_argument('--all', action='store_true', help=f"All history (same as --from-date {EARLIEST_DATE})")
    parser.add_argument('--to-date', default=None, help="End date YYYY-MM-DD (default today)")
    parser.add_argument('--company', action='append', default=[],
                        help="Symbol (LOLC) or part of a company name; repeat or comma-separate for several")
    parser.add_argument('--type', action='append', default=[], choices=REPORT_TYPES, dest='types',
                        help="Only this report type; repeat for several")
    parser.add_argument('--title', default=None, help="Only reports whose title contains this text")
    parser.add_argument('--limit', type=int, default=None, help="Only the first N matching reports (newest first)")
    parser.add_argument('--list', action='store_true', help="List matching reports without downloading")
    parser.add_argument('--overwrite', action='store_true', help="Download again even if the file exists")
    parser.add_argument('--delay', type=float, default=1.0, help="Seconds between downloads (default 1.0)")
    parser.add_argument('--retries', type=int, default=2, help="Retries for network errors / 5xx (default 2)")
    parser.add_argument('--output-dir', default=OUTPUT_DIR,
                        help="Folder to create the company folders in (default reports/financial_reports)")
    args = parser.parse_args()

    companies = [c.strip() for value in args.company for c in value.split(',') if c.strip()]
    try:
        from_date = to_iso_date(args.from_date) if args.from_date else (EARLIEST_DATE if args.all else None)
        to_date = to_iso_date(args.to_date) if args.to_date else None
    except ValueError as e:
        parser.error(f"invalid date ({e}); use YYYY-MM-DD")

    downloader = CSE_ReportDownloader(output_dir=args.output_dir, delay=args.delay, retries=args.retries)
    results = downloader.download(from_date, to_date, companies=companies or None, report_types=args.types or None,
                                  title_contains=args.title, limit=args.limit, overwrite=args.overwrite,
                                  list_only=args.list)
    failed = [] if args.list else [r for r in results if r['status'] == 'failed']
    sys.exit(1 if failed or downloader.fetch_failed else 0)


if __name__ == "__main__":
    main()

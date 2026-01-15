# CSE API Documentation & Python Client

This repository contains a comprehensive Python client for the Colombo Stock Exchange (CSE) API, along with documentation, examples, and powerful analysis tools.

<b>Visit <a href='https://shaahid02.github.io/cse-api-documentation/' target="_blank" rel="noopener noreferrer">this link</a> to see web view<b>

## 📚 Table of Contents

- [Files Overview](#-files-overview)
- [Quick Start](#-quick-start)
- [Available API Endpoints](#-available-api-endpoints)
- [Tools Package](#️-tools-package)
- [Usage Examples](#-usage-examples)
- [Advanced API Usage](#advanced-api-usage)
- [API Response Examples](#-api-response-examples)
- [Technical Details](#-technical-details)
- [Dependencies](#️-dependencies)
- [Testing](#-testing)
- [Contributing](#-contributing)

## 📁 Files Overview

### Core API Client

- **`app.py`** - Main CSE API client class with all endpoint methods
- **`cse_api_examples.py`** - Comprehensive examples and demonstrations
- **`quick_test.py`** - Quick test script to verify API functionality

### Documentation

- **`index.html`** - Web-based API documentation
- **`api_endpoint_urls.txt`** - List of all available API endpoints
- **`TOOLS_MIGRATION.md`** - Documentation for tools package migration

### Tools Package

- **`tools/`** - Advanced analysis and utility tools (see [Tools Section](#-tools-package))

### Data & Reports

- **`company_data/`** - Company information and announcement categories
- **`reports/`** - Downloaded financial reports and analysis results
- **`analysis/`** - Investment analysis outputs
- **`training_data/`** - Historical data for analysis

## 🚀 Quick Start

```python
from app import CSE_API

# Initialize the API client
cse = CSE_API()

# Get market status
status = cse.get_market_status()
print(status['data'])

# Get company information
company = cse.get_company_info("LOLC.N0000")
print(company['data'])
```

## 📊 Available API Endpoints

### Stock Information APIs

| Method                              | Endpoint           | Parameters          | Description                              |
| ----------------------------------- | ------------------ | ------------------- | ---------------------------------------- |
| `get_company_info(symbol)`          | companyInfoSummery | symbol (required)   | Detailed info of a single stock/security |
| `get_trade_summary()`               | tradeSummary       | None                | Summary of trades for all securities     |
| `get_today_share_price()`           | todaySharePrice    | None                | Today's share price data                 |
| `get_top_gainers()`                 | topGainers         | None                | List of top gaining stocks               |
| `get_top_losers()`                  | topLooses          | None                | List of top losing stocks                |
| `get_most_active_trades()`          | mostActiveTrades   | None                | Most active trades by volume             |
| `get_detailed_trades(symbol)`       | detailedTrades     | symbol (optional)   | Detailed trades information              |
| `get_companies_by_alphabet(letter)` | alphabetical       | alphabet (required) | Companies starting with specific letter  |
| `get_all_companies()`               | alphabetical (A-Z) | None                | All registered companies (iterates A-Z)  |

### Market Data APIs

| Method                       | Endpoint           | Parameters | Description                               |
| ---------------------------- | ------------------ | ---------- | ----------------------------------------- |
| `get_market_status()`        | marketStatus       | None       | Market open/close status                  |
| `get_market_summary()`       | marketSummery      | None       | Market summary data                       |
| `get_daily_market_summary()` | dailyMarketSummery | None       | Daily market summary with historical data |

### Index Data APIs

| Method                   | Endpoint   | Parameters        | Description                 |
| ------------------------ | ---------- | ----------------- | --------------------------- |
| `get_aspi_data()`        | aspiData   | None              | All Share Price Index data  |
| `get_snp_data()`         | snpData    | None              | S&P Sri Lanka 20 Index data |
| `get_chart_data(symbol)` | chartData  | symbol (required) | Chart data for stocks       |
| `get_all_sectors()`      | allSectors | None              | All sector data             |

### Announcement APIs

| Method                                    | Endpoint                                  | Parameters                                         | Description                            |
| ----------------------------------------- | ----------------------------------------- | -------------------------------------------------- | -------------------------------------- |
| `get_new_listings_announcements()`        | getNewListingsRelatedNoticesAnnouncements | None                                               | New listings and related announcements |
| `get_buy_in_board_announcements()`        | getBuyInBoardAnnouncements                | None                                               | Buy-in board announcements             |
| `get_approved_announcements()`            | approvedAnnouncement                      | None                                               | Approved announcements                 |
| `get_covid_announcements()`               | getCOVIDAnnouncements                     | None                                               | COVID-related announcements            |
| `get_financial_announcements()`           | getFinancialAnnouncement                  | None                                               | Financial announcements                |
| `get_financial_announcements_filtered()`  | getFinancialAnnouncement                  | from_date, to_date, company_ids (optional)         | Filtered financial announcements       |
| `get_circular_announcements()`            | circularAnnouncement                      | None                                               | Circular announcements                 |
| `get_directive_announcements()`           | directiveAnnouncement                     | None                                               | Directive announcements                |
| `get_non_compliance_announcements()`      | getNonComplianceAnnouncements             | None                                               | Non-compliance announcements           |
| `get_corporate_announcement_categories()` | getCorporateAnnouncementCategories        | None                                               | Available announcement categories      |
| `get_approved_announcements()` (filtered) | getApprovedAnnouncements                  | announcement_type, from_date, to_date, company_ids | Advanced filtered announcements        |
| `get_announcement_by_id()`                | getAnnouncementById                       | announcement_id (required)                         | Get specific announcement by ID        |

## 🛠️ Tools Package

The `tools/` package contains powerful analysis and utility tools built on top of the CSE API client. These tools provide advanced functionality for investment analysis, financial report downloading, and data processing.

### Available Tools

#### 📊 Investment Analysis Tools

**`CSE_InvestmentAnalyzer`** (`tools/company_analyzer.py`)

- Comprehensive investment analysis and recommendations
- Multi-style investment strategies (conservative, aggressive, value, balanced)
- Risk assessment and financial metrics calculation
- Automated report generation with detailed insights

```python
from tools.company_analyzer import CSE_InvestmentAnalyzer

analyzer = CSE_InvestmentAnalyzer()
analyzer.analyze_companies(limit=10)  # Analyze top 10 companies
analyzer.save_analysis()  # Save results to analysis/ folder
```

**`EnhancedInvestmentAnalyzer`** (`tools/enhanced_analyzer.py`)

- Advanced analysis combining dividends and corporate announcements
- Enhanced risk metrics and trend analysis
- Comprehensive reporting with multiple data sources

```python
from tools.enhanced_analyzer import EnhancedInvestmentAnalyzer

enhanced = EnhancedInvestmentAnalyzer()
enhanced.analyze_company_comprehensive("LOLC.N0000")
```

#### 💰 Dividend Analysis Tools

**`DividendTracker`** (`tools/dividend_tracker.py`)

- Track dividend announcements and payments
- Dividend yield calculations and trend analysis
- Generate comprehensive dividend reports
- Export to Excel and JSON formats

```python
from tools.dividend_tracker import DividendTracker

tracker = DividendTracker()
tracker.track_dividends_for_symbols(["LOLC.N0000", "JKH.N0000"])
tracker.generate_dividend_report()
```

#### 📄 Report Download Tools

**`CSE_ReportDownloader`** (`tools/download_financial_reports.py`)

- Download financial reports from CSE announcements
- Filter by company, date range, and report type
- Organize downloads with proper file naming
- Generate download logs and summaries

```python
from tools.download_financial_reports import CSE_ReportDownloader

downloader = CSE_ReportDownloader()
# Download reports for specific company and date range
downloader.download_reports_by_company_name(
    "ABANS ELECTRICALS",
    "2024-01-01",
    "2025-08-26"
)
```

#### 🔍 Data Collection Tools

**`fetch_and_store_categories()`** (`tools/fetch_categories.py`)

- Fetch and store announcement categories
- Categorize announcements by type (dividend, financial, meetings)
- Save structured data for further analysis

```python
from tools.fetch_categories import fetch_and_store_categories

fetch_and_store_categories()  # Downloads and saves categories
```

**Company Data Tools** (`tools/get_all_companies.py`)

- Fetch all registered companies from CSE
- Save data in multiple formats (JSON, CSV)
- Comprehensive company information extraction

```python
from tools.get_all_companies import main as get_all_companies

get_all_companies()  # Fetches all companies A-Z
```

**Filter and Processing** (`tools/filter_scraper.py`)

- Process and filter company training data
- Generate CSV files for individual companies
- Data preparation for analysis

### Tools Installation and Usage

```python
# Import individual tools
from tools.company_analyzer import CSE_InvestmentAnalyzer
from tools.download_financial_reports import CSE_ReportDownloader

# Or import multiple tools at once
from tools import (
    CSE_InvestmentAnalyzer,
    DividendTracker,
    CSE_ReportDownloader,
    EnhancedInvestmentAnalyzer
)

# Example workflow
analyzer = CSE_InvestmentAnalyzer()
downloader = CSE_ReportDownloader()

# Analyze companies
analyzer.analyze_companies(limit=5)
analyzer.save_analysis()

# Download reports
downloader.download_reports_by_time_range("2024-01-01", "2025-08-26")
```

### Tools Output Structure

```
├── analysis/                    # Investment analysis results
│   ├── *_investment_analysis.json
│   ├── *_raw_data.json
│   └── *_failed_requests.json
├── reports/                     # Downloaded financial reports
│   ├── company_folders/
│   │   └── *.pdf
│   └── download_logs/
└── company_data/               # Company and category data
    ├── data.json
    └── announcement_categories.json
```

### Advanced Features

- **Automated Analysis**: Tools can run comprehensive analysis across multiple companies
- **Smart Filtering**: Filter companies by various criteria (sector, market cap, etc.)
- **Export Options**: Multiple output formats (JSON, Excel, CSV, PDF)
- **Error Handling**: Robust error handling and retry mechanisms
- **Progress Tracking**: Real-time progress indicators for long-running operations
- **Customizable**: Configurable parameters for different analysis needs

## 💡 Usage Examples

### Basic Usage

```python
from app import CSE_API

cse = CSE_API()

# Get market dashboard
def market_dashboard():
    # Market status
    status = cse.get_market_status()
    print(f"Market Status: {status['data']['status']}")

    # ASPI Index
    aspi = cse.get_aspi_data()
    print(f"ASPI: {aspi['data']['value']} ({aspi['data']['change']:+.2f})")

    # Top gainers
    gainers = cse.get_top_gainers()
    print("Top Gainers:")
    for stock in gainers['data'][:5]:
        print(f"  {stock['symbol']}: +{stock['changePercentage']:.2f}%")
```

### Stock Analysis

```python
def analyze_stock(symbol):
    cse = CSE_API()

    # Company information
    info = cse.get_company_info(symbol)
    if info['success']:
        company_name = info['data']['reqSymbolInfo']['name']
        print(f"Company: {company_name}")

    # Detailed trades
    trades = cse.get_detailed_trades(symbol)
    if trades['success']:
        for trade in trades['data']['reqDetailTrades']:
            if trade['symbol'] == symbol:
                print(f"Price: {trade['price']}")
                print(f"Change: {trade['change']} ({trade['changePercentage']:.2f}%)")
                print(f"Volume: {trade['qty']}")

# Usage
analyze_stock("LOLC.N0000")
```

### Advanced API Usage

#### Filtered Financial Announcements

```python
def get_filtered_announcements():
    cse = CSE_API()

    # Get financial announcements for a specific date range
    result = cse.get_financial_announcements_filtered(
        from_date="2024-01-01",
        to_date="2025-08-26",
        company_ids="642"  # Abans Electricals
    )

    if result['success']:
        announcements = result['data']
        print(f"Found {len(announcements)} financial announcements")
        for announcement in announcements[:5]:
            print(f"- {announcement['subject']} ({announcement['announcementDate']})")

# Get announcement categories
def get_announcement_categories():
    cse = CSE_API()

    categories = cse.get_corporate_announcement_categories()
    if categories['success']:
        for category in categories['data']['categories']:
            print(f"Category: {category['categoryName']} (ID: {category['id']})")

# Get specific announcement details
def get_announcement_details(announcement_id):
    cse = CSE_API()

    announcement = cse.get_announcement_by_id(announcement_id)
    if announcement['success']:
        details = announcement['data']
        print(f"Subject: {details['subject']}")
        print(f"Company: {details['companyName']}")
        print(f"Date: {details['announcementDate']}")
```

### Tools Integration Example

```python
# Combined workflow using API and tools
def comprehensive_analysis_workflow():
    from app import CSE_API
    from tools import CSE_InvestmentAnalyzer, CSE_ReportDownloader, DividendTracker

    # Step 1: Get market overview
    cse = CSE_API()
    market_status = cse.get_market_status()
    top_gainers = cse.get_top_gainers()

    # Step 2: Perform investment analysis
    analyzer = CSE_InvestmentAnalyzer()
    analyzer.analyze_companies(limit=20)
    analyzer.save_analysis()

    # Step 3: Track dividends for top performers
    tracker = DividendTracker()
    top_symbols = [stock['symbol'] for stock in top_gainers['data'][:10]]
    tracker.track_dividends_for_symbols(top_symbols)

    # Step 4: Download financial reports for analysis
    downloader = CSE_ReportDownloader()
    downloader.download_reports_by_time_range("2024-01-01", "2025-08-26")

    print("✅ Comprehensive analysis completed!")
```

### Getting All Companies

````python
def get_companies_by_letter():
    cse = CSE_API()

    # Get companies starting with 'A'
    result = cse.get_companies_by_alphabet('A')
    if result['success']:
        companies = result['data']['reqAlphabetical']
        for company in companies[:5]:  # Show first 5
            print(f"{company['name']} ({company['symbol']}) - ${company['price']}")

def get_all_registered_companies():
    cse = CSE_API()

    # This will fetch ALL companies (A-Z) - takes 2-3 minutes
    result = cse.get_all_companies()
    if result['success']:
        print(f"Total companies: {result['total_companies']}")

        # Save to file
        with open('all_companies.json', 'w') as f:
            json.dump(result['data'], f, indent=2)

        return result['data']

# Usage
get_companies_by_letter()
all_companies = get_all_registered_companies()
```### Error Handling

All API methods return a dictionary with the following structure:

```python
{
    'success': True/False,
    'status_code': 200,  # HTTP status code
    'data': {...},       # API response data (if success=True)
    'error': "..."       # Error message (if success=False)
}
````

Example with error handling:

```python
response = cse.get_company_info("INVALID.SYMBOL")
if response['success']:
    print("Data:", response['data'])
else:
    print(f"Error: {response['error']}")
    print(f"Status Code: {response['status_code']}")
```

## 🧪 Running Tests

### Quick Test

```bash
python quick_test.py
```

### Comprehensive Test

```bash
python cse_api_examples.py
```

### Interactive Examples

```bash
python cse_api_examples.py
# Choose from:
# 1. Market Dashboard
# 2. Specific Stock Analysis
# 3. Comprehensive API Test
```

## 📋 API Response Examples

### Company Information

```json
{
  "reqSymbolInfo": {
    "symbol": "LOLC.N0000",
    "name": "L O L C HOLDINGS PLC",
    "sector": "Diversified Financials",
    "currentPrice": 285.0
  },
  "reqLogo": {
    "path": "upload_logo/378_1601611239.jpeg"
  }
}
```

### Market Status

```json
{
  "status": "Market Closed"
}
```

### Top Gainers

```json
[
  {
    "symbol": "HEXP.N0000",
    "changePercentage": 15.86,
    "price": 12.5,
    "change": 1.7
  }
]
```

### Market Summary

```json
{
  "tradeVolume": 3263762020.0,
  "shareVolume": 115084307,
  "marketCap": 6940225783432.0
}
```

### Companies by Alphabet

```json
{
  "reqAlphabetical": [
    {
      "id": 188,
      "name": "BAIRAHA FARMS PLC",
      "symbol": "BFL.N0000",
      "lastTradedTime": 1756109291425,
      "price": 211.0,
      "turnover": 596200.25,
      "sharevolume": 2849,
      "tradevolume": 29,
      "percentageChange": 0.7159904534606205,
      "change": 1.5
    }
  ]
}
```

}

```

## 🔧 Technical Details

### Base URL

```

https://www.cse.lk/api/

````

### Request Method

All endpoints use **POST** requests with `application/x-www-form-urlencoded` content type.

### Headers

```python
{
    'Content-Type': 'application/x-www-form-urlencoded',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
````

### Rate Limiting

The API doesn't specify rate limits, but it's recommended to:

- Add delays between requests
- Implement retry logic for failed requests
- Cache responses when appropriate

## 🛠️ Dependencies

### Core API Client

```bash
pip install requests
```

### Tools Package (Optional)

For using the analysis and utility tools:

```bash
pip install pandas numpy openpyxl
```

### Complete Installation

```bash
# Install all dependencies at once
pip install requests pandas numpy openpyxl

# Or install from requirements file (if available)
pip install -r requirements.txt
```

### Package Versions

- **requests**: For API communication
- **pandas**: For data manipulation and analysis
- **numpy**: For numerical computations
- **openpyxl**: For Excel file operations (dividend tracker)

## 📝 Notes

1. **Symbol Format**: Stock symbols typically end with `.N0000` or `.X0000`
2. **Chart Data**: May return HTTP 400 for some symbols
3. **Market Hours**: Some data may be limited during market closed hours
4. **Response Format**: All responses are in JSON format
5. **New Features**:
   - Filtered announcement endpoints support date ranges and company filtering
   - Tools package provides advanced analysis capabilities
   - Announcement categories can be fetched and used for filtering
   - Individual announcements can be retrieved by ID
6. **Tools Migration**: Analysis tools have been moved to the `tools/` package for better organization

## 🤝 Contributing

Feel free to contribute by:

- Adding new endpoint methods
- Improving error handling
- Adding more examples
- Updating documentation
- Enhancing the tools package with new analysis features

## 🧪 Testing

The repository includes comprehensive tests for both the API client and tools:

```bash
# Test core API functionality
python quick_test.py

# Test comprehensive API examples
python cse_api_examples.py

# Test tools functionality
python tools_usage_example.py

# Test specific tool (example with Abans Electrical)
python test_abans_download.py
```

### Test Results Summary

- ✅ All API endpoints functional
- ✅ Tools package migration successful
- ✅ Financial report downloads working (tested with Abans Electrical)
- ✅ Analysis tools operational with 285+ companies loaded

## ⚠️ Disclaimer

This is an unofficial API client. The CSE API is provided by the Colombo Stock Exchange and may change without notice. Always verify data accuracy for trading decisions.

## 📞 Support

For API-related questions, contact the Colombo Stock Exchange directly. For client library issues, please create an issue in this repository.

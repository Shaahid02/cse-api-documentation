# CSE API Documentation

This documentation provides comprehensive information about the Colombo Stock Exchange (CSE) API endpoints.

## Files in this project:

- `api-docs-complete.html` - Complete, professional API documentation
- `index.html` - Original documentation file
- `api_req_res_structure.txt` - Raw API structure data
- `company_data_for_payload.json` - Original company symbols and data
- `companies.json` - Enhanced company data with sectors (structured for easy access)
- `companies.csv` - Company data in CSV format for spreadsheet use

## Company Data Access Solutions:

### 🔍 **Interactive Company Directory**
The documentation now includes a comprehensive company directory with:
- **Live Search**: Type to find companies instantly
- **Sector Filtering**: Filter by Banking, Hotels, Manufacturing, etc.
- **Copy Buttons**: Click to copy symbols to clipboard
- **Download Options**: Get data as JSON or CSV
- **API Examples**: Ready-to-use code snippets

### 📋 **Multiple Data Formats**

1. **JSON Format** (`companies.json`):
   ```json
   {
     "companies": [...],
     "sectors": {...},
     "popular": [...]
   }
   ```

2. **CSV Format** (`companies.csv`):
   - Easy to import into Excel/Google Sheets
   - Perfect for bulk operations
   - Include all company details

3. **JavaScript Array** (embedded in HTML):
   - Ready for web applications
   - Includes sector categorization
   - Optimized for search functionality

## Features of the New Documentation:

### 🎨 Professional Design
- Modern dark theme with gradient backgrounds
- Responsive design that works on all devices
- Smooth animations and hover effects
- Professional color scheme optimized for readability

### 🔍 Interactive Features
- **Company Symbol Search**: Type to find company symbols quickly
- **Quick Navigation**: Jump to any endpoint section
- **Collapsible Sections**: Keep the page organized and easy to navigate
- **Smooth Scrolling**: Better user experience when navigating

### 📋 Comprehensive Information
Each endpoint includes:
- Complete URL with base path
- HTTP method (GET/POST)
- Required and optional parameters
- Detailed parameter descriptions
- Request examples (for POST endpoints)
- Complete response examples with real data
- Clear descriptions of what each endpoint does

### 📊 Covered Endpoints:
1. **Trade Summary** - Complete trading data for all securities
2. **Company Information Summary** - Detailed company data (requires symbol parameter)
3. **Market Capitalization** - Companies sorted by market cap
4. **Top Gainers** - Best performing stocks
5. **Top Losers** - Worst performing stocks  
6. **Most Active Trades** - Highest volume trading activity
7. **Market Status** - Current market open/closed status
8. **Detailed Trades** - Detailed trading information
9. **Today Share Price** - Current day's price data

## How to Use:

1. **Open the documentation**: Open `api-docs-complete.html` in any web browser
2. **Navigate**: Use the quick navigation menu to jump to specific endpoints
3. **Search companies**: Use the search box to quickly find company symbols
4. **Test endpoints**: Copy the URLs and parameters to test in your application

## For Developers:

### Company Symbol Format
All company symbols follow the format: `SYMBOL.N0000` (e.g., `ABAN.N0000`, `JKH.N0000`)

### Common Parameters
- `symbol`: Company trading symbol (required for company-specific endpoints)
- Most endpoints use GET requests, but `companyInfoSummery` uses POST

### Response Format
- All responses are in JSON format
- Arrays contain multiple companies/records
- Objects contain single company/record data
- Timestamps are in Unix milliseconds format

### Testing the API
You can test these endpoints using:
- Postman or similar API testing tools
- cURL commands
- Your preferred programming language's HTTP client

### Example cURL for Company Info:
```bash
curl -X POST https://www.cse.lk/api/companyInfoSummery \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "symbol=JKH.N0000"
```

## Maintenance:

To update the documentation:
1. Edit the HTML file to add new endpoints
2. Update the company data array in the JavaScript section
3. Modify the navigation menu to include new sections
4. Test the search functionality after changes

## Support:

- Base URL: `https://www.cse.lk/api/`
- All data is from the official Colombo Stock Exchange
- Response times may vary based on market activity
- Some endpoints may have rate limiting (check with CSE)

---

Last updated: January 15, 2026
# Nasdaq Stock Screener

A Python-based Nasdaq stock screener with a Tkinter GUI. It connects to Interactive Brokers via `ib_insync`, retrieves historical OHLC data, applies a set of 47 technical conditions (e.g., price comparisons across hourly intervals), and displays the filtered results in a table. Users can upload a list of ticker symbols, select screening date, and export results to CSV.

## Features
- GUI built with Tkinter for easy interaction
- Connects to Interactive Brokers to fetch market data
- Applies multiple technical criteria (price comparisons, EMA, RSI, volume, market cap)
- Upload and manage custom ticker lists
- Export screened results to CSV
- Real‑time data handling via `ib_insync`

## Requirements
```
tk
tkcalendar
requests
pandas
pytz
ib_insync
```

## Installation
```bash
pip install -r requirements.txt
```

## Configuration
The application does not require additional environment variables; all configuration is performed through the GUI (screening date, ticker list, and condition selection).

## Usage
Run the main application script:
```bash
python main.py
```

## Project Structure
```
├── .github/workflows/main.yml   # CI workflow configuration
├── LICENSE                     # MIT license
├── README.md                   # Project documentation
├── main.py                     # Entry point and GUI implementation
├── script.py                   # Alternative implementation (not used as entry point)
├── requirements.txt            # Python dependencies
├── screener_results.txt        # Sample output file
├── test.py                     # Simple test script
├── tickers.txt                 # Example ticker list
```

## License
MIT License (see LICENSE file).

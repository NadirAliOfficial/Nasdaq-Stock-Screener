import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import datetime
import pandas as pd
from pandas.tseries.offsets import BDay
from ib_insync import IB, Stock, util

# Connect globally (ensure IB Gateway/TWS is running)
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

class StockScreenerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Nasdaq Stock Screener")
        self.tickers = []           # List of ticker symbols (e.g. "AWH", "GMHS", "MNTS")
        self.ticker_vars = {}       # Dict of {ticker: BooleanVar} for selection
        self.ohlc_data = {}
        self.conditions = {}        # Indicator (conditions) checkboxes
        self.results = []
        self.create_widgets()
        self.setup_conditions()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.grid(row=0, column=0, sticky=tk.NSEW)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Controls Frame
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding=10)
        control_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=5, pady=5)
        ttk.Label(control_frame, text="Screening Date:").grid(row=0, column=0, sticky=tk.W)
        self.date_entry = ttk.Entry(control_frame)
        self.date_entry.grid(row=0, column=1, sticky=tk.EW)
        self.date_entry.insert(0, self.get_default_date().strftime("%Y-%m-%d"))
        ttk.Button(control_frame, text="Upload Ticker List", command=self.upload_file)\
            .grid(row=1, column=0, columnspan=2, pady=5)
        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Run Screener", command=self.run_screener)\
            .pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Reset", command=self.reset)\
            .pack(side=tk.LEFT, padx=5)
        
        # Conditions (Indicators) Frame
        cond_frame = ttk.LabelFrame(main_frame, text="Indicators", padding=10)
        cond_frame.grid(row=0, column=1, sticky=tk.NSEW, padx=5, pady=5)
        cond_canvas = tk.Canvas(cond_frame, borderwidth=0)
        cond_scrollbar = ttk.Scrollbar(cond_frame, orient="vertical", command=cond_canvas.yview)
        self.cond_scrollable = ttk.Frame(cond_canvas)
        self.cond_scrollable.bind("<Configure>", lambda e: cond_canvas.configure(scrollregion=cond_canvas.bbox("all")))
        cond_canvas.create_window((0, 0), window=self.cond_scrollable, anchor="nw")
        cond_canvas.configure(yscrollcommand=cond_scrollbar.set)
        cond_canvas.pack(side="left", fill="both", expand=True)
        cond_scrollbar.pack(side="right", fill="y")
        
        # Ticker Selection Frame
        self.ticker_frame = ttk.LabelFrame(main_frame, text="Ticker Selection", padding=10)
        self.ticker_frame.grid(row=0, column=2, sticky=tk.NSEW, padx=5, pady=5)
        self.ticker_inner_frame = ttk.Frame(self.ticker_frame)
        self.ticker_inner_frame.pack(fill=tk.BOTH, expand=True)
        ticker_btn_frame = ttk.Frame(self.ticker_frame)
        ticker_btn_frame.pack(pady=5)
        ttk.Button(ticker_btn_frame, text="Select All", command=self.select_all_tickers)\
            .pack(side=tk.LEFT, padx=2)
        ttk.Button(ticker_btn_frame, text="Unselect All", command=self.unselect_all_tickers)\
            .pack(side=tk.LEFT, padx=2)
        
        # Results Frame
        results_frame = ttk.LabelFrame(main_frame, text="Results", padding=10)
        results_frame.grid(row=1, column=0, columnspan=3, sticky=tk.NSEW, padx=5, pady=5)
        self.tree = ttk.Treeview(results_frame, columns=("Num", "Ticker", "Open"), show="headings")
        self.tree.heading("Num", text="Number")
        self.tree.heading("Ticker", text="Ticker")
        self.tree.heading("Open", text="Open 16h DAY-1")
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Grid weight configuration
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)
        main_frame.rowconfigure(1, weight=1)
    
    def setup_conditions(self):
        # Define 47 indicator conditions (unchecked by default)
        cond_defs = [
            (1, "Close 5h ≥ Open 5h"), (2, "Close 6h ≥ Open 6h"),
            (3, "Close 7h ≥ Open 7h"), (4, "Close 8h ≥ Open 8h"),
            (5, "Close 9h ≥ Open 9h"), (6, "Close 10h ≥ Open 10h"),
            (7, "Close 11h ≥ Open 11h"), (8, "Close 12h ≥ Open 12h"),
            (9, "Close 13h ≥ Open 13h"), (10, "Close 15h ≥ Open 15h"),
            (11, "Close 16h ≥ Open 16h"), (12, "Close 17h ≥ Open 17h"),
            (13, "Close 18h ≥ Open 18h"), (14, "Close 19h ≥ Open 19h"),
            (15, "High 15h ≠ Low 15h"), (16, "High 16h ≠ Low 16h"),
            (17, "High 17h ≠ Low 17h"), (18, "High 18h ≠ Low 18h"),
            (19, "High 19h ≠ Low 19h"), (20, "Open 18h = Low 18h"),
            (21, "Close 18h ≠ High 18h"), (22, "High [4h;20h] = High [10h;15h]"),
            (23, "Close 18h < Open 18h"), (24, "Open 18h ≠ High 18h"),
            (25, "Close 18h = Low 18h"), (26, "High 18h = Low 18h"),
            (27, "High [4h;20h] = High [10h;20h]"), (28, "Close 10h < Open 10h"),
            (29, "High 10h ≥ High 9h"), (30, "Low 10h ≥ Low 9h"),
            (31, "Low 17h ≤ Low 16h"), (32, "Open 17h = Low 17h"),
            (33, "Open 18h = High 18h"), (34, "Close 18h ≠ Low 18h"),
            (35, "Close 19h > Low 16h"), (36, "Low 19h > Low 16h"),
            (37, "Low 19h > Low 17h"), (38, "Low 19h > Low 18h"),
            (39, "Open 16h = Low 16h"), (40, "Open 16h = High 16h"),
            (41, "Close < Open and High in [4h;20h]"),
            (42, "Close ≥ Open and High in [4h;20h]"),
            (43, "High [4h;20h] > 1.5*Open16h DAY-1"),
            (44, "High [4h;20h] > 1.7*Open16h DAY-1"),
            (45, "High [4h;20h] > 2*Open16h DAY-1"),
            (46, "High [4h;20h] > 2.3*Open16h DAY-1"),
            (47, "Low [4h;20h] < 0.5*Open16h DAY-1")
        ]
        for i, (cid, desc) in enumerate(cond_defs):
            var = tk.BooleanVar(value=False)
            ttk.Checkbutton(self.cond_scrollable, text=f"{cid}. {desc}", variable=var)\
                .grid(row=i, column=0, sticky=tk.W)
            self.conditions[cid] = var

    def get_default_date(self):
        now = datetime.datetime.today()
        return (now + BDay(1)).date() if now.time() > datetime.time(20) else now.date()
    
    def upload_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if path:
            try:
                content = open(path, 'r').read().strip()
                # Split by commas and remove any "NASDAQ:" prefix
                tickers = [x.strip() for x in content.split(",") if x.strip()]
                tickers = [ticker.split(":")[-1] for ticker in tickers]
                if len(tickers) > 50:
                    messagebox.showerror("Error", "Maximum 50 tickers allowed")
                    return
                self.tickers = tickers
                messagebox.showinfo("Success", f"Loaded {len(tickers)} tickers:\n{', '.join(tickers)}")
                self.populate_ticker_selection()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {e}")
    
    def populate_ticker_selection(self):
        # Clear existing tickers from the ticker selection panel
        for widget in self.ticker_inner_frame.winfo_children():
            widget.destroy()
        self.ticker_vars = {}
        # Display tickers with numbering in order (e.g., "1. AWH")
        for i, ticker in enumerate(self.tickers, start=1):
            var = tk.BooleanVar(value=True)
            ttk.Checkbutton(self.ticker_inner_frame, text=f"{i}. {ticker}", variable=var)\
                .grid(row=i, column=0, sticky=tk.W)
            self.ticker_vars[ticker] = var

    def select_all_tickers(self):
        for var in self.ticker_vars.values():
            var.set(True)

    def unselect_all_tickers(self):
        for var in self.ticker_vars.values():
            var.set(False)
    
    def fetch_data(self, ticker, day_minus1, day):
        try:
            # Since tickers are now plain symbols (e.g., "AWH"), this still works:
            symbol = ticker.split(":")[-1]
            contract = Stock(symbol, 'SMART', 'USD')
            ib.qualifyContracts(contract)
            end_time = pd.Timestamp(f"{day} 20:00:00").strftime("%Y%m%d %H:%M:%S")
            bars = ib.reqHistoricalData(
                contract, endDateTime=end_time, durationStr="2 D",
                barSizeSetting="1 hour", whatToShow="TRADES",
                useRTH=False, formatDate=1
            )
            if not bars:
                print(f"No data for {ticker}")
                return pd.DataFrame()
            df = util.df(bars)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"}, inplace=True)
            return df
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            return pd.DataFrame()
    
    def evaluate_conditions(self, data, open_16h_day_minus1):
        try:
            results = {}
            # Conditions 1-14: Check Close >= Open at specific hours
            for hour in [5,6,7,8,9,10,11,12,13,15,16,17,18,19]:
                row = data.between_time(f"{hour:02d}:00", f"{hour:02d}:00").iloc[0]
                results[hour] = row['Close'] >= row['Open']
            # Conditions 15-19: Check High != Low (IDs: hour+1)
            for hour in range(15,20):
                row = data.between_time(f"{hour:02d}:00", f"{hour:02d}:00").iloc[0]
                results[hour+1] = row['High'] != row['Low']
            row18 = data.between_time('18:00', '18:00').iloc[0]
            results[20] = row18['Open'] == row18['Low']
            results[21] = row18['Close'] != row18['High']
            high1 = data.between_time('04:00', '20:00')['High'].max()
            high2 = data.between_time('10:00', '15:00')['High'].max()
            results[22] = (high1 == high2)
            results[23] = row18['Close'] < row18['Open']
            results[24] = row18['Open'] != row18['High']
            results[25] = row18['Close'] == row18['Low']
            results[26] = row18['High'] == row18['Low']
            high3 = data.between_time('10:00', '20:00')['High'].max()
            results[27] = (high1 == high3)
            row10 = data.between_time('10:00', '10:00').iloc[0]
            row9 = data.between_time('09:00', '09:00').iloc[0]
            results[28] = row10['Close'] < row10['Open']
            results[29] = row10['High'] >= row9['High']
            results[30] = row10['Low'] >= row9['Low']
            row16 = data.between_time('16:00', '16:00').iloc[0]
            row17 = data.between_time('17:00', '17:00').iloc[0]
            results[31] = row17['Low'] <= row16['Low']
            results[32] = row17['Open'] == row17['Low']
            results[33] = row18['Open'] == row18['High']
            results[34] = row18['Close'] != row18['Low']
            row19 = data.between_time('19:00', '19:00').iloc[0]
            results[35] = row19['Close'] > row16['Low']
            results[36] = row19['Low'] > row16['Low']
            results[37] = row19['Low'] > row17['Low']
            results[38] = row19['Low'] > row18['Low']
            results[39] = row16['Open'] == row16['Low']
            results[40] = row16['Open'] == row16['High']
            results[41] = (row18['Close'] < row18['Open']) and (high1 is not None)
            results[42] = (row18['Close'] >= row18['Open']) and (high1 is not None)
            results[43] = high1 > 1.5 * open_16h_day_minus1
            results[44] = high1 > 1.7 * open_16h_day_minus1
            results[45] = high1 > 2 * open_16h_day_minus1
            results[46] = high1 > 2.3 * open_16h_day_minus1
            low_range = data.between_time('04:00', '20:00')['Low'].min()
            results[47] = low_range < 0.5 * open_16h_day_minus1
            # Only return True if all enabled conditions are True
            return all(results.get(cid, False) for cid, var in self.conditions.items() if var.get())
        except Exception as e:
            print("Error evaluating conditions:", e)
            return False
    
    def save_results(self):
        with open('screener_results.txt', 'w') as f:
            f.write("Num\tTicker\tOpen16hDay-1\n")
            for num, ticker, open_val in sorted(self.results, key=lambda x: x[0]):
                f.write(f"{num}\t{ticker}\t{open_val:.2f}\n")
    
    def run_screener(self):
        self.tree.delete(*self.tree.get_children())
        try:
            screening_date = datetime.datetime.strptime(self.date_entry.get(), "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Error", "Invalid date format (YYYY-MM-DD)")
            return
        day_minus1 = screening_date - datetime.timedelta(days=1)
        self.ohlc_data, self.results = {}, []
        # Only process tickers that are checked in the ticker panel
        selected_tickers = [ticker for ticker, var in self.ticker_vars.items() if var.get()]
        for ticker in selected_tickers:
            print("Fetching:", ticker)
            df = self.fetch_data(ticker, day_minus1, screening_date)
            if df.empty or not isinstance(df.index, pd.DatetimeIndex):
                print("Skipped:", ticker)
                continue
            self.ohlc_data[ticker] = df
            # Using the first row as 16h DAY-1 (adjust if needed)
            open_16h = df.iloc[0]['Open']
            if self.evaluate_conditions(df, open_16h):
                self.results.append((len(self.results) + 1, ticker, open_16h))
        for res in self.results:
            self.tree.insert("", "end", values=res)
        self.save_results()
        messagebox.showinfo("Success", f"Found {len(self.results)} matches.\nResults saved to screener_results.txt")
    
    def reset(self):
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, self.get_default_date().strftime("%Y-%m-%d"))
        self.tickers = []
        self.ticker_vars = {}
        self.ohlc_data = {}
        self.results = []
        self.tree.delete(*self.tree.get_children())
        for var in self.conditions.values():
            var.set(False)
        for widget in self.ticker_inner_frame.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = StockScreenerApp(root)
    root.mainloop()

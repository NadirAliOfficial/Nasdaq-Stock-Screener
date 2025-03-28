import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import datetime
import pytz
import logging
import pandas as pd
from pandas.tseries.offsets import BDay
from ib_insync import IB, Stock, util

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

eastern = pytz.timezone("US/Eastern")

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)
logger.info("Connected to IB Gateway/TWS")

class StockScreenerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Nasdaq Stock Screener")
        self.tickers = []
        self.ticker_vars = {}
        self.ohlc_data = {}
        self.conditions = {}
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
        ttk.Label(control_frame, text="Screening Date (YYYY-MM-DD):").grid(row=0, column=0, sticky=tk.W)
        self.date_entry = ttk.Entry(control_frame)
        self.date_entry.grid(row=0, column=1, sticky=tk.EW)
        self.date_entry.insert(0, self.get_default_date().strftime("%Y-%m-%d"))
        ttk.Button(control_frame, text="Upload Ticker List", command=self.upload_file).grid(row=1, column=0, columnspan=2, pady=5)
        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Run Screener", command=self.run_screener).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Reset", command=self.reset).pack(side=tk.LEFT, padx=5)
        
        # Conditions Frame
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
        ttk.Button(ticker_btn_frame, text="Select All", command=self.select_all_tickers).pack(side=tk.LEFT, padx=2)
        ttk.Button(ticker_btn_frame, text="Unselect All", command=self.unselect_all_tickers).pack(side=tk.LEFT, padx=2)
        
        # Results Frame
        results_frame = ttk.LabelFrame(main_frame, text="Results", padding=10)
        results_frame.grid(row=1, column=0, columnspan=3, sticky=tk.NSEW, padx=5, pady=5)
        self.tree = ttk.Treeview(results_frame, columns=("Num", "Ticker", "Open"), show="headings")
        self.tree.heading("Num", text="Number")
        self.tree.heading("Ticker", text="Ticker")
        self.tree.heading("Open", text="Open 16h Day-1")
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)
        main_frame.rowconfigure(1, weight=1)
    
    def setup_conditions(self):
        # List all 47 conditions.
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
            (41, "Bar with highest High (04h-20h): Close < Open"),   # Modified logic for 41
            (42, "Bar with highest High (04h-20h): Close ≥ Open"),   # Modified logic for 42
            (43, "High [4h;20h] > 1.5*Open16h DAY-1"),
            (44, "High [4h;20h] > 1.7*Open16h DAY-1"),
            (45, "High [4h;20h] > 2*Open16h DAY-1"),
            (46, "High [4h;20h] > 2.3*Open16h DAY-1"),
            (47, "Low [4h;20h] < 0.5*Open16h DAY-1")
        ]
        for cid, desc in cond_defs:
            var = tk.BooleanVar(value=False)
            ttk.Checkbutton(self.cond_scrollable, text=f"{cid}. {desc}", variable=var)\
                .grid(padx=2, pady=2, row=cid-1, column=0, sticky=tk.W)
            self.conditions[cid] = var

    def get_default_date(self):
        now = datetime.datetime.now(eastern)
        default_date = (now + BDay(1)).date() if now.time() > datetime.time(20, 0) else now.date()
        logger.info(f"Default screening date set to: {default_date}")
        return default_date
    
    def upload_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if path:
            try:
                with open(path, "r") as f:
                    content = f.read().strip()
                tickers = [x.strip() for x in content.split(",") if x.strip()]
                tickers = [ticker.split(":")[-1] for ticker in tickers]
                if len(tickers) > 50:
                    messagebox.showerror("Error", "Maximum 50 tickers allowed")
                    return
                self.tickers = tickers
                messagebox.showinfo("Success", f"Loaded {len(tickers)} tickers:\n{', '.join(tickers)}")
                logger.info(f"Tickers loaded: {', '.join(tickers)}")
                self.populate_ticker_selection()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {e}")
                logger.error(f"Error loading file: {e}")
    
    def populate_ticker_selection(self):
        for widget in self.ticker_inner_frame.winfo_children():
            widget.destroy()
        self.ticker_vars = {}
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
        """
        Fetch extended hours data over 7 days to cover weekends/holidays.
        """
        try:
            contract = Stock(ticker, "SMART", "USD")
            ib.qualifyContracts(contract)
            target_datetime = datetime.datetime.combine(day + datetime.timedelta(days=1), datetime.time(11, 0))
            localized_dt = eastern.localize(target_datetime).astimezone(pytz.utc)
            end_time_str = localized_dt.strftime("%Y%m%d %H:%M:%S")
            logger.info(f"Fetching data for {ticker} with end time {end_time_str} (US/Eastern, extended hours)")
            
            bars = ib.reqHistoricalData(
                contract,
                endDateTime=end_time_str,
                durationStr="7 D",
                barSizeSetting="1 hour",
                whatToShow="TRADES",
                useRTH=False,
                formatDate=1
            )
            
            if not bars:
                logger.warning(f"No data returned for {ticker}")
                return pd.DataFrame()
            df = util.df(bars)
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            if df.index.tz is None:
                df.index = df.index.tz_localize("UTC").tz_convert("US/Eastern")
            else:
                df.index = df.index.tz_convert("US/Eastern")
            df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"}, inplace=True)
            logger.info(f"Data for {ticker} covers timestamps: {df.index.tolist()}")
            df.to_csv(f"{ticker}_raw_data.csv")
            logger.info(f"Raw data for {ticker} saved to {ticker}_raw_data.csv")
            return df
        except Exception as e:
            logger.error(f"Error fetching {ticker}: {e}")
            return pd.DataFrame()

    def find_previous_16h_open(self, df, screening_date):
        """
        Starting from screening_date - 1, go backwards until finding a day with an exact 16:00 bar.
        Return the 'Open' of that bar, or None if not found.
        """
        day_cursor = screening_date - datetime.timedelta(days=1)
        for _ in range(7):
            prev_data = df[df.index.date == day_cursor]
            if not prev_data.empty:
                target_bar = prev_data.between_time("16:00", "16:00")
                if not target_bar.empty:
                    open_16h = target_bar.iloc[0]["Open"]
                    logger.info(f"Found 16:00 bar for {day_cursor}, open={open_16h}")
                    return open_16h
            day_cursor -= datetime.timedelta(days=1)
        return None

    def evaluate_conditions(self, data, open_16h_day_minus1):
        try:
            results = {}
            # Conditions 1-14: Check if for each mapped hour, Close >= Open.
            hour_map = {
                1:5, 2:6, 3:7, 4:8, 5:9,
                6:10, 7:11, 8:12, 9:13, 10:15,
                11:16, 12:17, 13:18, 14:19
            }
            for cid in range(1, 15):
                if not self.conditions.get(cid, tk.BooleanVar()).get():
                    continue
                hour = hour_map[cid]
                rows = data.between_time(f"{hour:02d}:00", f"{hour:02d}:59")
                if rows.empty:
                    logger.info(f"No bar found for hour {hour} => condition {cid} = False")
                    results[cid] = False
                else:
                    row = rows.iloc[-1]
                    results[cid] = (row["Close"] >= row["Open"])
                    logger.info(f"[Condition {cid}] Hour {hour}: Open={row['Open']}, Close={row['Close']} => {results[cid]}")
            # Conditions 15-19: For hours 15 to 19, check High != Low.
            for cid, hour in zip(range(15, 20), range(15, 20)):
                if not self.conditions.get(cid, tk.BooleanVar()).get():
                    continue
                rows = data.between_time(f"{hour:02d}:00", f"{hour:02d}:59")
                if rows.empty:
                    logger.info(f"No bar found for hour {hour} => condition {cid} = False")
                    results[cid] = False
                else:
                    row = rows.iloc[-1]
                    results[cid] = (row["High"] != row["Low"])
                    logger.info(f"[Condition {cid}] Hour {hour}: High={row['High']}, Low={row['Low']} => {results[cid]}")
            # Conditions 20-26: Using 18:00 bar.
            row18 = data.between_time("18:00", "18:59")
            if row18.empty:
                logger.info("No bar found for 18:00 => Conditions 20-26 = False")
                for cid in [20, 21, 23, 24, 25, 26]:
                    results[cid] = False
            else:
                r18 = row18.iloc[-1]
                results[20] = (r18["Open"] == r18["Low"])
                results[21] = (r18["Close"] != r18["High"])
                results[23] = (r18["Close"] < r18["Open"])
                results[24] = (r18["Open"] != r18["High"])
                results[25] = (r18["Close"] == r18["Low"])
                results[26] = (r18["High"] == r18["Low"])
                logger.info(f"[18:00] r18: {r18.to_dict()}, Conditions 20-26: {{20: {results[20]}, 21: {results[21]}, 23: {results[23]}, 24: {results[24]}, 25: {results[25]}, 26: {results[26]}}}")
            # Condition 22: High from 04:00-20:00 equals High from 10:00-15:00.
            high1 = data.between_time("04:00", "20:00")["High"].max()
            high2 = data.between_time("10:00", "15:00")["High"].max()
            results[22] = (high1 == high2)
            logger.info(f"High1 (04:00-20:00) = {high1}, High2 (10:00-15:00) = {high2}, Condition 22 = {results[22]}")
            # Condition 27: High from 04:00-20:00 equals High from 10:00-20:00.
            high3 = data.between_time("10:00", "20:00")["High"].max()
            results[27] = (high1 == high3)
            logger.info(f"High3 (10:00-20:00) = {high3}, Condition 27 = {results[27]}")
            # Conditions 28-30: Compare 10:00 and 09:00 bars.
            row10 = data.between_time("10:00", "10:59")
            row9  = data.between_time("09:00", "09:59")
            if row10.empty or row9.empty:
                results[28] = results[29] = results[30] = False
            else:
                r10 = row10.iloc[-1]
                r9 = row9.iloc[-1]
                results[28] = (r10["Close"] < r10["Open"])
                results[29] = (r10["High"] >= r9["High"])
                results[30] = (r10["Low"] >= r9["Low"])
                logger.info(f"[10:00] r10: {r10.to_dict()}, [09:00] r9: {r9.to_dict()}, Conditions 28-30: {{28: {results[28]}, 29: {results[29]}, 30: {results[30]}}}")
            # Conditions 31-32: Compare 16:00 and 17:00 bars.
            row16 = data.between_time("16:00", "16:59")
            row17 = data.between_time("17:00", "17:59")
            if row16.empty or row17.empty:
                results[31] = results[32] = False
            else:
                r16 = row16.iloc[-1]
                r17 = row17.iloc[-1]
                results[31] = (r17["Low"] <= r16["Low"])
                results[32] = (r17["Open"] == r17["Low"])
                logger.info(f"[16:00] r16: {r16.to_dict()}, [17:00] r17: {r17.to_dict()}, Conditions 31-32: {{31: {results[31]}, 32: {results[32]}}}")
            # Conditions 33-34: For 18:00 bar.
            if not row18.empty:
                r18 = row18.iloc[-1]
                results[33] = (r18["Open"] == r18["High"])
                results[34] = (r18["Close"] != r18["Low"])
                logger.info(f"[18:00] Conditions 33-34: {{33: {results[33]}, 34: {results[34]}}}")
            else:
                results[33] = results[34] = False
            # Conditions 35-38: Compare 19:00 bar with 16:00, 17:00, 18:00.
            row19 = data.between_time("19:00", "19:59")
            if row16.empty or row19.empty:
                results[35] = results[36] = results[37] = results[38] = False
            else:
                r19 = row19.iloc[-1]
                results[35] = (r19["Close"] > row16.iloc[-1]["Low"])
                results[36] = (r19["Low"] > row16.iloc[-1]["Low"])
                results[37] = (r19["Low"] > (row17.iloc[-1]["Low"] if not row17.empty else r19["Low"]))
                results[38] = (r19["Low"] > (r18["Low"] if not row18.empty else r19["Low"]))
                logger.info(f"[19:00] r19: {r19.to_dict()}, Conditions 35-38: {{35: {results[35]}, 36: {results[36]}, 37: {results[37]}, 38: {results[38]}}}")
            # Conditions 39-40: For 16:00 bar.
            if not row16.empty:
                r16 = row16.iloc[-1]
                results[39] = (r16["Open"] == r16["Low"])
                results[40] = (r16["Open"] == r16["High"])
                logger.info(f"[16:00] Conditions 39-40: {{39: {results[39]}, 40: {results[40]}}}")
            else:
                results[39] = results[40] = False
            # Conditions 41-42: Use the bar with the highest High between 04:00 and 20:00.
            row_range = data.between_time("04:00", "20:00")
            if row_range.empty:
                results[41] = results[42] = False
            else:
                max_high = row_range["High"].max()
                highest_bar = row_range[row_range["High"] == max_high].iloc[0]
                results[41] = (highest_bar["Close"] < highest_bar["Open"])
                results[42] = (highest_bar["Close"] >= highest_bar["Open"])
                logger.info(f"[Highest Bar] {highest_bar.to_dict()}, Condition 41: {results[41]}, Condition 42: {results[42]}")
            # Conditions 43-46: Compare max high from 04:00-20:00 (high1) with multiples of Open16hDay-1.
            results[43] = (high1 > 1.5 * open_16h_day_minus1) if high1 is not None else False
            results[44] = (high1 > 1.7 * open_16h_day_minus1) if high1 is not None else False
            results[45] = (high1 > 2.0 * open_16h_day_minus1) if high1 is not None else False
            results[46] = (high1 > 2.3 * open_16h_day_minus1) if high1 is not None else False
            # Condition 47: Check if minimum low from 04:00-20:00 is less than 0.5 * Open16hDay-1.
            low_range = data.between_time("04:00", "20:00")["Low"].min()
            results[47] = (low_range < 0.5 * open_16h_day_minus1) if low_range is not None else False

            logger.info(f"Evaluated conditions: {results}")
            return all(results.get(cid, False) for cid, var in self.conditions.items() if var.get())
        except Exception as e:
            logger.error("Error evaluating conditions: " + str(e))
            return False

    def save_results(self):
        with open("screener_results.txt", "w") as f:
            f.write("Num\tTicker\tOpen16hDay-1\n")
            for num, ticker, open_val in sorted(self.results, key=lambda x: x[0]):
                f.write(f"{num}\t{ticker}\t{open_val:.2f}\n")
        logger.info("Results saved to screener_results.txt")
    
    def run_screener(self):
        self.tree.delete(*self.tree.get_children())
        try:
            screening_date = datetime.datetime.strptime(self.date_entry.get(), "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Error", "Invalid date format (YYYY-MM-DD)")
            return

        self.ohlc_data, self.results = {}, []
        selected_tickers = [t for t, var in self.ticker_vars.items() if var.get()]
        logger.info(f"Running screener for date {screening_date} on tickers: {selected_tickers}")

        for ticker in selected_tickers:
            logger.info(f"Fetching data for {ticker}")
            df = self.fetch_data(ticker, screening_date - datetime.timedelta(days=1), screening_date)
            if df.empty or not isinstance(df.index, pd.DatetimeIndex):
                logger.warning(f"Data empty or index invalid for {ticker}, skipping.")
                continue
            self.ohlc_data[ticker] = df

            # Find Open16hDay-1 by scanning backwards for a day with an exact 16:00 bar.
            open_16h = self.find_previous_16h_open(df, screening_date)
            if open_16h is None:
                logger.info(f"No valid 16:00 bar found for {ticker} within ~7 days before {screening_date}. Skipping ticker.")
                continue
            logger.info(f"For {ticker}, Open16hDay-1 is taken as {open_16h}")

            # Evaluate conditions only on the screening date's data.
            screening_data = df[df.index.date == screening_date]
            if screening_data.empty:
                logger.info(f"No data for {ticker} on screening date {screening_date}. Skipping ticker.")
                continue

            if self.evaluate_conditions(screening_data, open_16h):
                self.results.append((len(self.results) + 1, ticker, open_16h))

        for res in self.results:
            self.tree.insert("", "end", values=res)

        self.save_results()
        messagebox.showinfo("Success", f"Found {len(self.results)} matches.\nResults saved to screener_results.txt")
        logger.info(f"Screener finished with {len(self.results)} matches.")
    
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
        logger.info("Application reset.")

if __name__ == "__main__":
    root = tk.Tk()
    # For Windows, use iconbitmap (requires a .ico file)
    try:
        root.iconbitmap("money_analyze_icon_143358.ico")
    except Exception as e:
        print("Error setting icon with iconbitmap:", e)
    app = StockScreenerApp(root)
    root.mainloop()

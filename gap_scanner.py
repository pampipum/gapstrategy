import yfinance as yf
import pandas as pd
from datetime import datetime
import concurrent.futures
import time
import sys
import io

class GapScanner:
    def __init__(self, min_gap_percent=0.5, lookback_days=30):
        self.sp500_symbols = self._get_sp500_symbols()
        self.min_gap_percent = min_gap_percent
        self.lookback_days = lookback_days
        self.company_info = self._get_company_info()
        
    def _get_sp500_symbols(self):
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        tables = pd.read_html(url)
        sp500 = tables[0]
        self.company_data = sp500
        symbols = sp500['Symbol'].tolist()
        
        fixed_symbols = []
        for symbol in symbols:
            if symbol == 'BRK.B':
                fixed_symbols.append('BRK-B')
            elif symbol == 'BF.B':
                fixed_symbols.append('BF-B')
            else:
                fixed_symbols.append(symbol)
        return fixed_symbols

    def _get_company_info(self):
        info_dict = {}
        for idx, row in self.company_data.iterrows():
            symbol = row['Symbol']
            if symbol == 'BRK.B':
                symbol = 'BRK-B'
            elif symbol == 'BF.B':
                symbol = 'BF-B'
            info_dict[symbol] = {
                'name': row['Security'],
                'sector': row['GICS Sector']
            }
        return info_dict

    def _download_batch_data(self, symbols):
        try:
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
            
            data = yf.download(
                symbols,
                period=f"{self.lookback_days}d",
                interval="1d",
                group_by='ticker',
                auto_adjust=True,
                prepost=True,
                threads=True,
                progress=False,
                timeout=5
            )
            
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            return data
        except Exception:
            return None

    def identify_gaps(self, symbol, data):
        try:
            if isinstance(data, pd.DataFrame) and 'Close' in data.columns:
                df = data
            else:
                df = pd.DataFrame(data[symbol]).dropna()
                
            if len(df) < 2:
                return None
            
            gaps = []
            for i in range(1, len(df)):
                prev_day_high = df['High'].iloc[i-1]
                prev_day_low = df['Low'].iloc[i-1]
                current_open = df['Open'].iloc[i]
                current_date = df.index[i].strftime('%Y-%m-%d')
                current_price = df['Close'].iloc[i]
                volume = df['Volume'].iloc[i]
                
                gap_up = current_open > prev_day_high
                gap_down = current_open < prev_day_low
                
                if gap_up:
                    gap_size = ((current_open - prev_day_high) / prev_day_high) * 100
                    gap_type = 'up'
                elif gap_down:
                    gap_size = ((prev_day_low - current_open) / prev_day_low) * 100
                    gap_type = 'down'
                else:
                    continue
                    
                if abs(gap_size) >= self.min_gap_percent:
                    company_info = self.company_info.get(symbol, {'name': symbol, 'sector': 'Unknown'})
                    gaps.append({
                        'symbol': symbol,
                        'companyName': company_info['name'],
                        'sector': company_info['sector'],
                        'date': current_date,
                        'gap_type': gap_type,
                        'gap_size': round(gap_size, 2),
                        'prev_high': round(prev_day_high, 2),
                        'prev_low': round(prev_day_low, 2),
                        'current_open': round(current_open, 2),
                        'price': round(current_price, 2),
                        'volume': int(volume)
                    })
            
            return gaps
        except Exception:
            return None

    def process_batch(self, symbols):
        data = self._download_batch_data(symbols)
        if data is None:
            return []
        
        results = []
        for symbol in symbols:
            gaps = self.identify_gaps(symbol, data)
            if gaps:
                results.extend(gaps)
        return results

    def scan_market(self, batch_size=20):
        gap_data = []
        total_symbols = len(self.sp500_symbols)
        processed = 0

        symbol_batches = [
            self.sp500_symbols[i:i + batch_size] 
            for i in range(0, len(self.sp500_symbols), batch_size)
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for batch in symbol_batches:
                futures.append(executor.submit(self.process_batch, batch))

            for future in concurrent.futures.as_completed(futures):
                batch_results = future.result()
                gap_data.extend(batch_results)
                processed += batch_size
                print(f"Scanning: {min(processed, total_symbols)}/{total_symbols}", end='\r')

        print(" " * 50, end='\r')
        return pd.DataFrame(gap_data)
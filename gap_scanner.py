import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures
import time
import sys
import io
import pytz

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

    def _get_market_cap(self, symbol):
        try:
            ticker = yf.Ticker(symbol)
            time.sleep(0.1)  # Add small delay to avoid rate limiting
            return ticker.info.get('marketCap', 0)
        except:
            return 0

    def _download_batch_data(self, symbols):
        try:
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
            
            # Get current time in EST
            est = pytz.timezone('US/Eastern')
            now = datetime.now(est)
            
            # Calculate start date to get last 3 trading days
            start_date = now - timedelta(days=5)  # Get 5 calendar days to ensure 3 trading days
            
            data = yf.download(
                symbols,
                start=start_date,
                end=now,
                interval="1m",  # Using 1-minute data to build 12-minute candles
                group_by='ticker',
                auto_adjust=True,
                prepost=True,
                threads=False,  # Disable threading to avoid rate limits
                progress=False,
                timeout=10
            )
            
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            return data
        except Exception as e:
            print(f"Error downloading data: {e}")
            return None

    def identify_gaps(self, symbol, data):
        try:
            if isinstance(data, pd.DataFrame) and 'Close' in data.columns:
                df = data
            else:
                df = pd.DataFrame(data[symbol]).dropna()
                
            if len(df) < 2:  # Need at least 2 days of data
                return None
                
            # Get current time in EST
            est = pytz.timezone('US/Eastern')
            now = datetime.now(est)
            
            # Only scan between 9:42 and 9:45 AM EST
            market_open = now.replace(hour=9, minute=42)
            market_cutoff = now.replace(hour=9, minute=45)
            if not (market_open <= now <= market_cutoff):
                return None
            
            # Resample to 12-minute candles
            df_12min = df.resample('12T').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
            # Get today's first 12-min candle
            today_candle = df_12min[-1:]
            if len(today_candle) == 0:
                return None
                
            # Get previous day's high/low
            prev_day = df.resample('D').agg({
                'High': 'max',
                'Low': 'min',
                'Volume': 'sum'
            }).dropna()
            
            if len(prev_day) < 2:
                return None
                
            prev_day_high = prev_day['High'].iloc[-2]
            prev_day_low = prev_day['Low'].iloc[-2]
            
            current_open = today_candle['Open'].iloc[0]
            first_candle_close = today_candle['Close'].iloc[0]
            
            # Check for gap conditions
            gap_up = current_open < prev_day_low and first_candle_close > current_open  # Trap de compra
            gap_down = current_open > prev_day_high and first_candle_close < current_open  # Trap de venda
            
            if gap_up:
                gap_size = ((prev_day_low - current_open) / prev_day_low) * 100
                gap_type = 'up'
            elif gap_down:
                gap_size = ((current_open - prev_day_high) / prev_day_high) * 100
                gap_type = 'down'
            else:
                return None
                    
            if abs(gap_size) >= self.min_gap_percent:
                company_info = self.company_info.get(symbol, {'name': symbol, 'sector': 'Unknown'})
                market_cap = self._get_market_cap(symbol)
                volume = today_candle['Volume'].iloc[0]
                avg_volume = df['Volume'].mean()
                
                return {
                    'symbol': symbol,
                    'companyName': company_info['name'],
                    'sector': company_info['sector'],
                    'date': now.strftime('%Y-%m-%d'),
                    'gap_type': gap_type,
                    'gap_size': round(gap_size, 2),
                    'prev_high': round(prev_day_high, 2),
                    'prev_low': round(prev_day_low, 2),
                    'current_open': round(current_open, 2),
                    'price': round(first_candle_close, 2),
                    'volume': int(volume),
                    'avg_volume': int(avg_volume),
                    'market_cap': market_cap,
                    'relative_volume': round(volume/avg_volume, 2) if avg_volume > 0 else 0
                }
            
            return None
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            return None

    def process_batch(self, symbols):
        data = self._download_batch_data(symbols)
        if data is None:
            return []
        
        # Add delay between batches
        time.sleep(2)
        
        results = []
        for symbol in symbols:
            gap = self.identify_gaps(symbol, data)
            if gap:
                results.append(gap)
        return results

    def scan_market(self, batch_size=10):  # Reduced batch size
        gap_data = []
        total_symbols = len(self.sp500_symbols)
        processed = 0

        symbol_batches = [
            self.sp500_symbols[i:i + batch_size] 
            for i in range(0, len(self.sp500_symbols), batch_size)
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:  # Reduced workers
            futures = []
            for batch in symbol_batches:
                futures.append(executor.submit(self.process_batch, batch))

            for future in concurrent.futures.as_completed(futures):
                batch_results = future.result()
                gap_data.extend(batch_results)
                processed += batch_size
                print(f"Scanning: {min(processed, total_symbols)}/{total_symbols}", end='\r')

        # Convert to DataFrame and include all data from last 3 days
        df = pd.DataFrame(gap_data)
        if not df.empty:
            # Sort by date (descending) and gap size (absolute value)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values(['date', 'gap_size'], ascending=[False, True])
            # Keep only last 3 days
            df = df[df['date'] >= (datetime.now() - timedelta(days=3))]
            
        return df
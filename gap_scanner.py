import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures
import time
import sys
import io
import pytz
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GapScanner:
    def __init__(self, min_gap_percent=0.5, lookback_days=30):
        self.sp500_symbols = self._get_sp500_symbols()
        self.min_gap_percent = min_gap_percent
        self.lookback_days = lookback_days
        self.company_info = self._get_company_info()
        logger.info(f"Initialized GapScanner with {len(self.sp500_symbols)} symbols")

    def _get_sp500_symbols(self):
        logger.info("Fetching S&P 500 symbols...")
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
        logger.info(f"Found {len(fixed_symbols)} S&P 500 symbols")
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
            est = pytz.timezone('US/Eastern')
            now = datetime.now(est)
            start_date = now - timedelta(days=5)
            
            data = yf.download(
                symbols,
                start=start_date,
                end=now,
                interval="1m",
                group_by='ticker',
                auto_adjust=True,
                prepost=True,
                threads=True,
                progress=False,
                timeout=20
            )
            return data
        except Exception as e:
            logger.error(f"Error downloading data: {str(e)}")
            return None

    def identify_gaps(self, symbol, data):
        try:
            # Handle multi-symbol data differently than single symbol data
            if isinstance(data.columns, pd.MultiIndex):
                # Get data for specific symbol
                symbol_data = data[symbol].copy()
            else:
                symbol_data = data.copy()

            if len(symbol_data) < 2:
                return None

            # Resample to 12-minute candles
            df_12min = symbol_data.resample('12min').agg({
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
            prev_day = symbol_data.resample('D').agg({
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
            first_candle_high = today_candle['High'].iloc[0]
            first_candle_low = today_candle['Low'].iloc[0]
            first_candle_open = today_candle['Open'].iloc[0]

            # Check for gap conditions
            gap_up = (current_open < prev_day_low and
                     first_candle_close > first_candle_open)

            gap_down = (current_open > prev_day_high and
                       first_candle_close < first_candle_open)

            if gap_up:
                gap_size = ((prev_day_low - current_open) / prev_day_low) * 100
                gap_type = 'up'
                entry_price = first_candle_high + 0.01
                stop_loss = first_candle_low - 0.01
                risk = entry_price - stop_loss
                target = entry_price + (risk * 2)
            elif gap_down:
                gap_size = ((current_open - prev_day_high) / prev_day_high) * 100
                gap_type = 'down'
                entry_price = first_candle_low - 0.01
                stop_loss = first_candle_high + 0.01
                risk = stop_loss - entry_price
                target = entry_price - (risk * 2)
            else:
                return None

            if abs(gap_size) >= self.min_gap_percent:
                company_info = self.company_info.get(symbol, {'name': symbol, 'sector': 'Unknown'})
                volume = today_candle['Volume'].iloc[0]
                avg_volume = symbol_data['Volume'].mean()

                # Convert timestamps to strings
                current_time = datetime.now(pytz.timezone('US/Eastern'))
                date_str = current_time.strftime('%Y-%m-%d')

                return {
                    'symbol': symbol,
                    'companyName': company_info['name'],
                    'sector': company_info['sector'],
                    'date': date_str,
                    'gap_type': gap_type,
                    'gap_size': round(gap_size, 2),
                    'prev_high': round(prev_day_high, 2),
                    'prev_low': round(prev_day_low, 2),
                    'current_open': round(current_open, 2),
                    'price': round(first_candle_close, 2),
                    'first_candle_high': round(first_candle_high, 2),
                    'first_candle_low': round(first_candle_low, 2),
                    'entry_price': round(entry_price, 2),
                    'stop_loss': round(stop_loss, 2),
                    'target': round(target, 2),
                    'risk_amount': round(risk, 2),
                    'reward_amount': round(risk * 2, 2),
                    'volume': int(volume),
                    'avg_volume': int(avg_volume),
                    'relative_volume': round(volume/avg_volume, 2) if avg_volume > 0 else 0
                }
            return None

        except Exception as e:
            logger.error(f"Error processing {symbol}: {str(e)}")
            return None

    def scan_market_with_log(self, batch_size=25):
        logger.info("Starting market scan with logging...")
        gap_data = []
        scan_log = []
        total_symbols = len(self.sp500_symbols)
        processed = 0
        est = pytz.timezone('US/Eastern')
        scan_time = datetime.now(est).strftime('%H:%M:%S')

        # Process symbols in larger batches
        symbol_batches = [
            self.sp500_symbols[i:i + batch_size] 
            for i in range(0, len(self.sp500_symbols), batch_size)
        ]

        for batch in symbol_batches:
            try:
                data = self._download_batch_data(batch)
                if data is None:
                    for symbol in batch:
                        scan_log.append({
                            'symbol': symbol,
                            'companyName': self.company_info.get(symbol, {}).get('name', 'Unknown'),
                            'sector': self.company_info.get(symbol, {}).get('sector', 'Unknown'),
                            'status': 'download_failed',
                            'time': scan_time,
                            'has_gap': False
                        })
                    continue

                for symbol in batch:
                    try:
                        gap = self.identify_gaps(symbol, data)
                        company_info = self.company_info.get(symbol, {'name': symbol, 'sector': 'Unknown'})

                        if gap:
                            gap_data.append(gap)
                            status = 'gap_found'
                            has_gap = True
                        else:
                            status = 'no_gap'
                            has_gap = False

                        scan_log.append({
                            'symbol': symbol,
                            'companyName': company_info['name'],
                            'sector': company_info['sector'],
                            'status': status,
                            'time': scan_time,
                            'has_gap': has_gap
                        })

                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {str(e)}")
                        scan_log.append({
                            'symbol': symbol,
                            'companyName': self.company_info.get(symbol, {}).get('name', 'Unknown'),
                            'sector': self.company_info.get(symbol, {}).get('sector', 'Unknown'),
                            'status': f'error: {str(e)}',
                            'time': scan_time,
                            'has_gap': False
                        })

                processed += len(batch)
                logger.info(f"Processed {processed}/{total_symbols} symbols")

            except Exception as e:
                logger.error(f"Batch processing error: {str(e)}")

        logger.info(f"Scan complete. Found {len(gap_data)} gaps. Log entries: {len(scan_log)}")
        return pd.DataFrame(gap_data) if gap_data else pd.DataFrame(), scan_log

    def scan_market(self, batch_size=25):
        df, _ = self.scan_market_with_log(batch_size)
        return df
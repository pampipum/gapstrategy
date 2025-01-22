import pandas as pd
import yfinance as yf
import time

def test_sp500_symbols():
    # Get symbols from Wikipedia
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    tables = pd.read_html(url)
    sp500 = tables[0]
    symbols = sp500['Symbol'].tolist()
    
    # Test each symbol
    working_symbols = []
    failed_symbols = []
    
    for symbol in symbols:
        try:
            # Fix known symbol issues
            if symbol == 'BRK.B':
                symbol = 'BRK-B'
            elif symbol == 'BF.B':
                symbol = 'BF-B'
                
            print(f"Testing {symbol}...")
            ticker = yf.Ticker(symbol)
            info = ticker.info
            working_symbols.append({
                'symbol': symbol,
                'name': info.get('longName', 'N/A'),
                'sector': info.get('sector', 'N/A')
            })
            time.sleep(0.1)  # Be nice to the API
        except Exception as e:
            failed_symbols.append({
                'symbol': symbol,
                'error': str(e)
            })
            print(f"Failed: {symbol} - {str(e)}")
    
    print("\nResults:")
    print(f"Working symbols: {len(working_symbols)}")
    print(f"Failed symbols: {len(failed_symbols)}")
    
    if failed_symbols:
        print("\nFailed Symbols:")
        for fail in failed_symbols:
            print(f"{fail['symbol']}: {fail['error']}")
            
    return working_symbols, failed_symbols

if __name__ == "__main__":
    working, failed = test_sp500_symbols()
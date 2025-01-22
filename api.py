from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from gap_scanner import GapScanner
import asyncio
from datetime import datetime, timedelta
import pytz
import logging
import json
import os
from typing import List, Dict, Any

# Set up logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Gap Strategy API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://gapstrategy.vercel.app", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# File to store historical data
HISTORY_FILE = "gap_history.json"

# Cache for storing scan results
cache = {
    'last_scan': None,
    'historical_data': [],
    'scanning': False,
    'scan_log': []
}

def load_historical_data():
    """Load historical data from file"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
                logger.info(f"Loaded {len(data)} historical records")
                return data
    except Exception as e:
        logger.error(f"Error loading historical data: {e}")
    return []

def save_historical_data(data: List[Dict[str, Any]]):
    """Save historical data to file"""
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(data, f)
        logger.info(f"Saved {len(data)} records to history file")
    except Exception as e:
        logger.error(f"Error saving historical data: {e}")

# Load historical data on startup
cache['historical_data'] = load_historical_data()

async def scan_market():
    if cache['scanning']:
        logger.info("Scan already in progress, skipping")
        return
        
    try:
        cache['scanning'] = True
        scanner = GapScanner(min_gap_percent=0.5, lookback_days=30)
        loop = asyncio.get_event_loop()
        
        # Get current time in EST
        est = pytz.timezone('US/Eastern')
        now = datetime.now(est)
        
        logger.info("Starting market scan...")
        results, scan_log = await loop.run_in_executor(None, scanner.scan_market_with_log)
        
        # Store scan log
        cache['scan_log'] = scan_log
        
        if not results.empty:
            # Convert DataFrame to list of dictionaries
            new_results = results.to_dict('records')
            
            # Add to historical data
            current_date = now.strftime('%Y-%m-%d')
            
            # Remove old data for the current date if it exists
            cache['historical_data'] = [
                entry for entry in cache['historical_data'] 
                if entry['date'] != current_date
            ]
            
            # Add new data
            cache['historical_data'].extend(new_results)
            
            # Keep only last 3 days
            dates = sorted(set(entry['date'] for entry in cache['historical_data']))
            if len(dates) > 3:
                keep_dates = dates[-3:]
                cache['historical_data'] = [
                    entry for entry in cache['historical_data']
                    if entry['date'] in keep_dates
                ]
            
            # Save to file
            save_historical_data(cache['historical_data'])
            
            logger.info(f"Market scan completed, found {len(new_results)} gaps")
        else:
            logger.info("No gaps found in current scan")
            
        cache['last_scan'] = now
        
    except Exception as e:
        logger.error(f"Error during market scan: {str(e)}")
        raise
    finally:
        cache['scanning'] = False

@app.get("/api/gaps")
async def get_gaps():
    logger.info(f"Gaps request received. Have {len(cache['historical_data'])} records")
    
    # Force a new scan on every request for testing
    try:
        await scan_market()
    except Exception as e:
        logger.error(f"Scan failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    # Return historical data sorted by date (newest first) and gap size
    sorted_data = sorted(
        cache['historical_data'],
        key=lambda x: (x['date'], abs(x['gap_size'])),
        reverse=True
    )
    
    logger.info(f"Returning {len(sorted_data)} gaps")
    return {
        "gaps": sorted_data,
        "scan_log": cache['scan_log'],
        "last_scan": cache['last_scan'].isoformat() if cache['last_scan'] else None
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    est = pytz.timezone('US/Eastern')
    now = datetime.now(est)
    
    time_since_last_scan = None
    if cache['last_scan']:
        time_since_last_scan = int((now - cache['last_scan']).total_seconds())

    return {
        "status": "healthy",
        "last_scan": cache['last_scan'].isoformat() if cache['last_scan'] else None,
        "scanning": cache['scanning'],
        "market_time": now.strftime("%H:%M:%S EST"),
        "cached_results_count": len(cache['historical_data']),
        "seconds_since_last_scan": time_since_last_scan,
        "data_dates": list(set(entry['date'] for entry in cache['historical_data']))
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
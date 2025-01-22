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
    'scanning': False
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
        
        # Only scan during market hours between 9:42-9:45 AM EST
        market_open = now.replace(hour=9, minute=42)
        market_cutoff = now.replace(hour=9, minute=45)
        
        logger.info(f"Current time: {now}, Market window: {market_open} - {market_cutoff}")
        
        if market_open <= now <= market_cutoff:
            logger.info("Starting market scan")
            results = await loop.run_in_executor(None, scanner.scan_market)
            
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
        else:
            logger.info("Outside of scanning window")
            
        cache['last_scan'] = now
        
    except Exception as e:
        logger.error(f"Error during market scan: {str(e)}")
        raise
    finally:
        cache['scanning'] = False

@app.get("/")
async def root():
    """Root endpoint with API information."""
    last_scan_time = cache['last_scan'].isoformat() if cache['last_scan'] else None
    return {
        "name": "Gap Strategy API",
        "version": "1.0",
        "endpoints": {
            "gaps": "/api/gaps",
            "health": "/api/health"
        },
        "status": "running",
        "last_scan": last_scan_time,
        "scanning": cache['scanning']
    }

@app.get("/api/gaps")
async def get_gaps():
    logger.info(f"Gaps request received. Have {len(cache['historical_data'])} records")
    
    # If we haven't scanned yet today during market hours, try to scan
    est = pytz.timezone('US/Eastern')
    now = datetime.now(est)
    market_open = now.replace(hour=9, minute=42)
    market_cutoff = now.replace(hour=9, minute=45)
    
    if market_open <= now <= market_cutoff:
        if not cache['last_scan'] or (now - cache['last_scan']).total_seconds() > 60:
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
    return sorted_data

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    est = pytz.timezone('US/Eastern')
    now = datetime.now(est)
    
    time_since_last_scan = None
    if cache['last_scan']:
        time_since_last_scan = int((now - cache['last_scan']).total_seconds())

    market_open = now.replace(hour=9, minute=42)
    market_cutoff = now.replace(hour=9, minute=45)
    is_scan_window = market_open <= now <= market_cutoff

    return {
        "status": "healthy",
        "last_scan": cache['last_scan'].isoformat() if cache['last_scan'] else None,
        "scanning": cache['scanning'],
        "is_scan_window": is_scan_window,
        "market_time": now.strftime("%H:%M:%S EST"),
        "cached_results_count": len(cache['historical_data']),
        "seconds_since_last_scan": time_since_last_scan,
        "data_dates": list(set(entry['date'] for entry in cache['historical_data']))
    }

async def background_scanner():
    """Background task to periodically check and scan if in window."""
    while True:
        try:
            est = pytz.timezone('US/Eastern')
            now = datetime.now(est)
            market_open = now.replace(hour=9, minute=42)
            market_cutoff = now.replace(hour=9, minute=45)
            
            if market_open <= now <= market_cutoff:
                logger.info("Background scanner triggering scan")
                await scan_market()
            
        except Exception as e:
            logger.error(f"Background scan failed: {str(e)}")
        
        await asyncio.sleep(60)  # Check every minute

@app.on_event("startup")
async def start_background_tasks():
    asyncio.create_task(background_scanner())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from gap_scanner import GapScanner
import asyncio
from datetime import datetime, timedelta
import pytz
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache for storing scan results
cache = {
    'last_scan': None,
    'results': None,
    'scanning': False
}

def is_market_hours():
    et_tz = pytz.timezone('US/Eastern')
    now = datetime.now(et_tz)
    
    # Check if it's a weekday
    if now.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return False
    
    # Convert current time to minutes since midnight
    current_time = now.hour * 60 + now.minute
    market_open = 9 * 60 + 30  # 9:30 AM
    market_close = 16 * 60  # 4:00 PM
    
    return market_open <= current_time <= market_close

async def scan_market():
    """Run market scan and update cache."""
    if cache['scanning']:
        return
    
    try:
        cache['scanning'] = True
        scanner = GapScanner(min_gap_percent=0.5, lookback_days=30)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, scanner.scan_market)
        
        cache['results'] = results.to_dict('records')
        cache['last_scan'] = datetime.now()
        logger.info(f"Market scan completed at {cache['last_scan']}")
        
    except Exception as e:
        logger.error(f"Error during market scan: {str(e)}")
        raise
    finally:
        cache['scanning'] = False

@app.on_event("startup")
async def startup_event():
    """Initial scan when server starts."""
    try:
        await scan_market()
    except Exception as e:
        logger.error(f"Initial scan failed: {str(e)}")

@app.get("/api/gaps")
async def get_gaps():
    # If we don't have any data yet, run initial scan
    if cache['results'] is None:
        try:
            await scan_market()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # If we have data but it's old (> 5 min during market hours)
    elif is_market_hours():
        time_since_last_scan = (datetime.now() - cache['last_scan']).total_seconds() if cache['last_scan'] else float('inf')
        if time_since_last_scan > 300:  # 5 minutes
            try:
                asyncio.create_task(scan_market())  # Non-blocking scan
            except Exception:
                logger.error("Background scan failed")
    
    return cache['results'] or []

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "last_scan": cache['last_scan'].isoformat() if cache['last_scan'] else None,
        "scanning": cache['scanning'],
        "cached_results_available": cache['results'] is not None,
        "market_hours": is_market_hours()
    }

async def background_scanner():
    """Background task to periodically scan market during trading hours."""
    while True:
        if is_market_hours():
            try:
                await scan_market()
            except Exception as e:
                logger.error(f"Background scan failed: {str(e)}")
        
        await asyncio.sleep(300)  # Wait 5 minutes before next scan

@app.on_event("startup")
async def start_background_tasks():
    asyncio.create_task(background_scanner())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from gap_scanner import GapScanner
import asyncio
from datetime import datetime
import pytz
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
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

# Cache for storing scan results
cache = {
    'last_scan': None,
    'results': None,
    'scanning': False
}

async def scan_market():
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
    # If we don't have any data yet, run initial scan
    if cache['results'] is None:
        try:
            await scan_market()
        except Exception as e:
            logger.error(f"Initial scan failed: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # If we have data but it's old (> 5 min)
    else:
        time_since_last_scan = (datetime.now() - cache['last_scan']).total_seconds() if cache['last_scan'] else float('inf')
        if time_since_last_scan > 300:  # 5 minutes
            try:
                asyncio.create_task(scan_market())  # Non-blocking scan
            except Exception as e:
                logger.error(f"Background scan failed: {str(e)}")
    
    return cache['results'] or []

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    time_since_last_scan = None
    if cache['last_scan']:
        time_since_last_scan = int((datetime.now() - cache['last_scan']).total_seconds())

    return {
        "status": "healthy",
        "last_scan": cache['last_scan'].isoformat() if cache['last_scan'] else None,
        "scanning": cache['scanning'],
        "cached_results_available": cache['results'] is not None,
        "results_count": len(cache['results']) if cache['results'] else 0,
        "seconds_since_last_scan": time_since_last_scan
    }

async def background_scanner():
    """Background task to periodically scan market."""
    while True:
        try:
            await scan_market()
        except Exception as e:
            logger.error(f"Background scan failed: {str(e)}")
        
        await asyncio.sleep(300)  # Wait 5 minutes

@app.on_event("startup")
async def start_background_tasks():
    asyncio.create_task(background_scanner())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
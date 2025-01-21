from http.server import BaseHTTPRequestHandler
from gap_scanner import GapScanner
import json
from datetime import datetime
import pytz

# Global cache (Note: This will reset on cold starts)
cache = {
    'last_scan': None,
    'results': None
}

def scan_market():
    try:
        scanner = GapScanner(min_gap_percent=0.5, lookback_days=30)
        results = scanner.scan_market()
        return results.to_dict('records')
    except Exception as e:
        return {'error': str(e)}

def get_cached_data():
    global cache
    now = datetime.now()
    
    # If we have recent cached results (less than 5 minutes old)
    if (cache['results'] is not None and 
        cache['last_scan'] is not None and 
        (now - cache['last_scan']).total_seconds() < 300):
        return cache['results']
    
    # Get new data
    results = scan_market()
    cache['results'] = results
    cache['last_scan'] = now
    return results

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type')
        self.end_headers()

        if self.path == '/api/gaps':
            results = get_cached_data()
            self.wfile.write(json.dumps(results).encode())
            return
        
        elif self.path == '/api/health':
            health_status = {
                "status": "healthy",
                "last_scan": cache['last_scan'].isoformat() if cache['last_scan'] else None,
                "cached_results_available": cache['results'] is not None
            }
            self.wfile.write(json.dumps(health_status).encode())
            return
        
        self.wfile.write(json.dumps({"error": "Not found"}).encode())
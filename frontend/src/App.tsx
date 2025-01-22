import { useState, useEffect } from 'react';
import DailyGaps from './components/DailyGaps';
import ScanLog from './components/ScanLog';
import './App.css';
import { Gap, ScanLogEntry } from './types/gap';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function App() {
  const [gaps, setGaps] = useState<Gap[]>([]);
  const [scanLog, setScanLog] = useState<ScanLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const fetchGaps = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`${API_URL}/api/gaps`);
      
      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage;
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || 'Failed to fetch gaps';
        } catch {
          errorMessage = `Server error: ${response.status}`;
        }
        throw new Error(errorMessage);
      }
      
      const data = await response.json();
      
      if (!data || typeof data !== 'object') {
        throw new Error('Invalid data format received');
      }

      const { gaps: gapsData, scan_log: scanLogData, last_scan: lastScan } = data;
      
      if (!Array.isArray(gapsData)) {
        throw new Error('Invalid gaps data format');
      }
      
      // Process gaps data
      const processedGaps = gapsData.map(gap => ({
        ...gap,
        date: new Date(gap.date).toISOString().split('T')[0]
      }));
      
      setGaps(processedGaps);
      
      // Process scan log
      if (Array.isArray(scanLogData)) {
        setScanLog(scanLogData);
      }
      
      // Update last scan time
      if (lastScan) {
        setLastUpdate(new Date(lastScan));
      }
    } catch (err) {
      console.error('Fetch error:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGaps();
    const intervalId = setInterval(fetchGaps, 5 * 60 * 1000); // Fetch every 5 minutes
    return () => clearInterval(intervalId);
  }, []);

  // Get current time in EST
  const now = new Date().toLocaleString('en-US', {
    timeZone: 'America/New_York',
    hour12: false,
    hour: '2-digit',
    minute: '2-digit'
  });

  const isMarketOpen = () => {
    const [hours, minutes] = now.split(':').map(Number);
    return (hours === 9 && minutes >= 42 && minutes <= 45);
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Main Container - using screen breakpoints instead of container */}
      <div className="w-full lg:max-w-[90%] xl:max-w-[1600px] mx-auto px-4 py-6">
        {/* Header Section */}
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center mb-6 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Stock Gap Scanner</h1>
            <p className="text-sm text-gray-500 mt-1">Scanning S&P 500 stocks for trading opportunities</p>
          </div>
          <div className="flex flex-col items-end">
            <div className="text-sm text-gray-500">
              Last updated: {lastUpdate ? lastUpdate.toLocaleTimeString() : 'Never'}
            </div>
            <div className={`text-sm ${isMarketOpen() ? 'text-green-600' : 'text-gray-500'}`}>
              Market Time: {now} EST
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading && !gaps.length && (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        )}

        {/* Content Sections */}
        <div className="space-y-8">
          {/* Gaps Section */}
          <section className="bg-white rounded-lg shadow-sm overflow-hidden">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold">Recent Gaps</h2>
                <div className="text-sm">
                  {isMarketOpen() ? (
                    <span className="text-green-600">● Scanning for gaps</span>
                  ) : (
                    <span className="text-gray-500">○ Waiting for market open</span>
                  )}
                </div>
              </div>
              
              {gaps.length > 0 ? (
                <DailyGaps gaps={gaps} />
              ) : (
                <div className="text-gray-500 text-center py-8">
                  {loading ? 'Loading gap data...' : 'No gap data available'}
                </div>
              )}
            </div>
          </section>

          {/* Scan Log Section */}
          <section>
            <ScanLog 
              entries={scanLog} 
              lastScanTime={lastUpdate?.toLocaleTimeString() || null}
            />
          </section>
        </div>
      </div>
    </div>
  );
}

export default App;
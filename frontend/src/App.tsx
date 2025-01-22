import { useState, useEffect } from 'react';
import DailyGaps from './components/DailyGaps';
import GapChart from './components/GapChart';
import './App.css';
import { Gap } from './types/gap';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function App() {
  const [gaps, setGaps] = useState<Gap[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const fetchGaps = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('Fetching from:', `${API_URL}/api/gaps`);
      
      const response = await fetch(`${API_URL}/api/gaps`);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('API Error:', errorText);
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
      console.log('Received raw data:', data);
      
      if (!Array.isArray(data)) {
        console.error('Received non-array data:', data);
        throw new Error('Invalid data format received');
      }
      
      // Validate and transform dates to ensure correct format
      const processedData = data.map(gap => ({
        ...gap,
        date: new Date(gap.date).toISOString().split('T')[0]
      }));
      
      console.log('Processed data:', processedData);
      setGaps(processedData);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Fetch error:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    console.log('Using API URL:', API_URL);
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

  console.log('Current gaps state:', gaps);
  console.log('Is loading:', loading);
  console.log('Error state:', error);

  return (
    <div className="min-h-screen bg-gray-100 py-6 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Stock Gap Scanner</h1>
          <div className="flex flex-col items-end">
            <div className="text-sm text-gray-500">
              {lastUpdate ? (
                `Last updated: ${lastUpdate.toLocaleTimeString()}`
              ) : (
                loading ? 'Updating...' : 'Never updated'
              )}
            </div>
            <div className={`text-sm ${isMarketOpen() ? 'text-green-600' : 'text-gray-500'}`}>
              Market Time: {now} EST
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
            <br />
            <span className="text-sm">API URL: {API_URL}</span>
          </div>
        )}

        {loading && !gaps.length && (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        )}

        <div className="space-y-6">
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex justify-between items-center mb-4">
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
          
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Gap Statistics</h2>
            <GapChart gaps={gaps} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
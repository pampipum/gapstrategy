import { useState, FormEvent } from 'react';

interface ScannerProps {
  onScan: (lookbackDays: number, minGapPercent: number) => Promise<void>;
  loading: boolean;
}

function Scanner({ onScan, loading }: ScannerProps) {
  const [lookbackDays, setLookbackDays] = useState(30);
  const [minGapPercent, setMinGapPercent] = useState(0.5);

  const handleScan = (e: FormEvent) => {
    e.preventDefault();
    onScan(lookbackDays, minGapPercent);
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-lg mb-6">
      <form onSubmit={handleScan} className="flex flex-wrap gap-4 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Lookback Days
          </label>
          <input
            type="number"
            min="1"
            max="90"
            value={lookbackDays}
            onChange={(e) => setLookbackDays(Number(e.target.value))}
            className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        
        <div className="flex-1 min-w-[200px]">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Min Gap %
          </label>
          <input
            type="number"
            min="0.1"
            max="10"
            step="0.1"
            value={minGapPercent}
            onChange={(e) => setMinGapPercent(Number(e.target.value))}
            className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        
        <button
          type="submit"
          disabled={loading}
          className={`px-6 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed min-w-[120px]`}
        >
          {loading ? 'Scanning...' : 'Scan Now'}
        </button>
      </form>
    </div>
  );
}

export default Scanner;
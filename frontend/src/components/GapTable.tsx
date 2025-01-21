import { useEffect, useState } from 'react';
import { Gap } from '../types/gap';

interface GapTableProps {
  gaps: Gap[];
  loading: boolean;
}

interface SortConfig {
  key: keyof Gap;
  direction: 'asc' | 'desc';
}

function GapTable({ gaps, loading }: GapTableProps) {
  const [sortedGaps, setSortedGaps] = useState<Gap[]>([]);
  const [sortConfig, setSortConfig] = useState<SortConfig>({ key: 'market_cap', direction: 'desc' });
  const [filter, setFilter] = useState('');

  // Format market cap as B or M
  const formatMarketCap = (marketCap: number | undefined) => {
    if (!marketCap) return 'N/A';
    if (marketCap >= 1e9) {
      return `$${(marketCap / 1e9).toFixed(1)}B`;
    }
    return `$${(marketCap / 1e6).toFixed(1)}M`;
  };

  // Format volume with K, M, B
  const formatVolume = (volume: number | undefined) => {
    if (!volume) return 'N/A';
    if (volume >= 1e9) {
      return `${(volume / 1e9).toFixed(1)}B`;
    }
    if (volume >= 1e6) {
      return `${(volume / 1e6).toFixed(1)}M`;
    }
    if (volume >= 1e3) {
      return `${(volume / 1e3).toFixed(1)}K`;
    }
    return volume.toString();
  };

  useEffect(() => {
    let filtered = [...gaps];
    if (filter) {
      filtered = gaps.filter(gap => 
        gap.symbol.toLowerCase().includes(filter.toLowerCase()) ||
        gap.companyName.toLowerCase().includes(filter.toLowerCase()) ||
        gap.sector?.toLowerCase().includes(filter.toLowerCase())
      );
    }

    const sorted = filtered.sort((a, b) => {
      if (sortConfig.key === 'date') {
        return sortConfig.direction === 'asc' 
          ? a.date.localeCompare(b.date)
          : b.date.localeCompare(a.date);
      }
      
      const aValue = a[sortConfig.key];
      const bValue = b[sortConfig.key];
      
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortConfig.direction === 'asc' ? aValue - bValue : bValue - aValue;
      }
      
      return 0;
    });
    
    setSortedGaps(sorted);
  }, [gaps, sortConfig, filter]);

  const handleSort = (key: keyof Gap) => {
    setSortConfig({
      key,
      direction:
        sortConfig.key === key && sortConfig.direction === 'asc'
          ? 'desc'
          : 'asc',
    });
  };

  if (loading && !sortedGaps.length) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <input
          type="text"
          placeholder="Filter by symbol, company, or sector..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <div className="text-sm text-gray-600">
          Found {sortedGaps.length} gaps
        </div>
      </div>
      
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th
                onClick={() => handleSort('date')}
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                Date ↕
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Symbol & Company
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Sector
              </th>
              <th
                onClick={() => handleSort('market_cap')}
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                Market Cap ↕
              </th>
              <th
                onClick={() => handleSort('gap_size')}
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                Gap % ↕
              </th>
              <th
                onClick={() => handleSort('volume')}
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                Volume ↕
              </th>
              <th
                onClick={() => handleSort('relative_volume')}
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                Rel Vol ↕
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Price
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedGaps.map((gap, index) => (
              <tr 
                key={`${gap.symbol}-${gap.date}-${index}`}
                className="hover:bg-gray-50"
              >
                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                  {new Date(gap.date).toLocaleDateString()}
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className="flex flex-col">
                    <div className="text-sm font-medium text-gray-900">
                      {gap.symbol}
                    </div>
                    <div className="text-sm text-gray-500">
                      {gap.companyName}
                    </div>
                  </div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                  {gap.sector}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                  {formatMarketCap(gap.market_cap)}
                </td>
                <td className={`px-4 py-4 whitespace-nowrap text-sm font-medium ${
                  gap.gap_type === 'up' ? 'text-green-600' : 'text-red-600'
                }`}>
                  {gap.gap_type === 'up' ? '+' : '-'}{Math.abs(gap.gap_size)}%
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                  {formatVolume(gap.volume)}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                  {gap.relative_volume?.toFixed(1)}x
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                  ${gap.price?.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default GapTable;
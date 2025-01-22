import { useEffect, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { Gap, ChartDataPoint } from '../types/gap';

interface GapChartProps {
  gaps: Gap[];
}

function GapChart({ gaps }: GapChartProps) {
  const [chartData, setChartData] = useState<ChartDataPoint[]>([]);

  useEffect(() => {
    // Process gaps data for visualization
    const processedData = gaps.reduce<{ [key: string]: ChartDataPoint }>((acc, gap) => {
      const dateKey = gap.date;
      
      if (!acc[dateKey]) {
        acc[dateKey] = {
          date: dateKey,
          count: 0,
          up: 0,
          down: 0
        };
      }
      
      acc[dateKey].count += 1;
      acc[dateKey][gap.gap_type] += 1;
      
      return acc;
    }, {});

    // Convert to array and sort by date
    const sortedData = Object.values(processedData).sort((a, b) => 
      a.date.localeCompare(b.date)
    );

    setChartData(sortedData);
  }, [gaps]);

  if (gaps.length === 0) {
    return (
      <div className="h-[400px] flex items-center justify-center text-gray-500">
        No data available for visualization
      </div>
    );
  }

  return (
    <div className="h-[400px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.5} />
          <XAxis 
            dataKey="date" 
            tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric'
            })}
          />
          <YAxis allowDecimals={false} />
          <Tooltip 
            formatter={(value: number, name: string) => [value, name === 'up' ? 'Gap Up' : 'Gap Down']}
            labelFormatter={(label) => new Date(label).toLocaleDateString('en-US', {
              weekday: 'short',
              month: 'short',
              day: 'numeric'
            })}
          />
          <Legend 
            formatter={(value) => value === 'up' ? 'Gap Up' : 'Gap Down'} 
          />
          <Bar dataKey="up" name="up" fill="#4CAF50" stackId="stack" />
          <Bar dataKey="down" name="down" fill="#EF5350" stackId="stack" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default GapChart;
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
    const processedData = gaps.reduce<ChartDataPoint[]>((acc, gap) => {
      const dateKey = gap.date;
      const existing = acc.find(item => item.date === dateKey);
      
      if (existing) {
        existing.count += 1;
        existing[gap.gap_type] += 1;
      } else {
        acc.push({
          date: dateKey,
          count: 1,
          up: gap.gap_type === 'up' ? 1 : 0,
          down: gap.gap_type === 'down' ? 1 : 0
        });
      }
      
      return acc;
    }, []);

    setChartData(processedData.sort((a, b) => a.date.localeCompare(b.date)));
  }, [gaps]);

  return (
    <div className="h-[400px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="up" fill="#4CAF50" name="Gap Up" />
          <Bar dataKey="down" fill="#EF5350" name="Gap Down" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default GapChart;
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { ChartCard } from './ChartCard';
import { useChartTheme } from '../../hooks/useChartTheme';

type DataPoint = { name: string; value?: number; count?: number };

type Props = {
  title: string;
  data: DataPoint[];
  isLoading?: boolean;
  dataKey?: string;
  color?: string;
};

const DEFAULT_COLOR = '#3b82f6';

export function BarChartCard({
  title,
  data,
  isLoading = false,
  dataKey = 'count',
  color = DEFAULT_COLOR,
}: Props) {
  const theme = useChartTheme();
  const isEmpty = !data || data.length === 0;

  const chartData = data.map((d) => ({
    name: d.name.length > 20 ? d.name.slice(0, 20) + '…' : d.name,
    [dataKey]: d.value ?? d.count ?? 0,
  }));

  return (
    <ChartCard title={title} isLoading={isLoading} isEmpty={isEmpty}>
      {!isLoading && !isEmpty && (
        <div className="h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.gridStroke} />
              <XAxis type="number" tick={{ fontSize: 11, fill: theme.textColor }} />
              <YAxis
                type="category"
                dataKey="name"
                width={100}
                tick={{ fontSize: 10, fill: theme.textColor }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: theme.tooltipBg,
                  border: `1px solid ${theme.tooltipBorder}`,
                  borderRadius: '0.5rem',
                }}
              />
              <Bar dataKey={dataKey} fill={color} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </ChartCard>
  );
}

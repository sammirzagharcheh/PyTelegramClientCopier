import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { ChartCard } from './ChartCard';
import { useChartTheme } from '../../hooks/useChartTheme';

type DataPoint = { name: string; value: number };

type Props = {
  title: string;
  data: DataPoint[];
  isLoading?: boolean;
  nameKey?: string;
  valueKey?: string;
};

const LIGHT_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444'];
const DARK_COLORS = ['#60a5fa', '#34d399', '#fbbf24', '#a78bfa', '#f87171'];

export function PieChartCard({
  title,
  data,
  isLoading = false,
  nameKey = 'name',
  valueKey = 'value',
}: Props) {
  const theme = useChartTheme();
  const isEmpty = !data || data.length === 0;
  const colors = theme.isDark ? DARK_COLORS : LIGHT_COLORS;

  const chartData = data.map((d) => ({
    name: d[nameKey as keyof DataPoint] ?? d.name,
    value: d[valueKey as keyof DataPoint] ?? d.value,
  }));

  return (
    <ChartCard title={title} isLoading={isLoading} isEmpty={isEmpty}>
      {!isLoading && !isEmpty && (
        <div className="h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={40}
                outerRadius={70}
                paddingAngle={2}
                dataKey="value"
                nameKey="name"
              >
                {chartData.map((_, index) => (
                  <Cell key={index} fill={colors[index % colors.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: theme.tooltipBg,
                  border: `1px solid ${theme.tooltipBorder}`,
                  borderRadius: '0.5rem',
                }}
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </ChartCard>
  );
}

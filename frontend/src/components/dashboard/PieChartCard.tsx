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
  onSliceClick?: (point: DataPoint) => void;
};

export function PieChartCard({
  title,
  data,
  isLoading = false,
  nameKey = 'name',
  valueKey = 'value',
  onSliceClick,
}: Props) {
  const theme = useChartTheme();
  const isEmpty = !data || data.length === 0;

  const chartData = data.map((d) => ({
    name: String(d[nameKey as keyof DataPoint] ?? d.name),
    value: Number(d[valueKey as keyof DataPoint] ?? d.value),
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
                stroke={theme.tooltipBg}
                strokeWidth={2}
                onClick={(_, idx) => {
                  if (onSliceClick && typeof idx === 'number' && idx >= 0 && idx < chartData.length) {
                    onSliceClick(chartData[idx]);
                  }
                }}
                style={{ cursor: onSliceClick ? 'pointer' : 'default' }}
              >
                {chartData.map((entry, index) => (
                  <Cell key={String(entry.name)} fill={theme.series[index % theme.series.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: theme.tooltipBg,
                  border: `1px solid ${theme.tooltipBorder}`,
                  borderRadius: 'var(--radius-control)',
                  color: theme.tooltipInk,
                  fontSize: '0.8125rem',
                  boxShadow: 'var(--shadow-raised)',
                }}
                itemStyle={{ color: theme.tooltipInk }}
              />
              <Legend
                iconType="circle"
                iconSize={8}
                wrapperStyle={{ fontSize: '0.75rem', color: theme.textColor }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </ChartCard>
  );
}

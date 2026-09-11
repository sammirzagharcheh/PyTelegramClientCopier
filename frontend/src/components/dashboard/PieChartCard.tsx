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

export function PieChartCard({
  title,
  data,
  isLoading = false,
  nameKey = 'name',
  valueKey = 'value',
}: Props) {
  const theme = useChartTheme();
  const isEmpty = !data || data.length === 0;

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
                stroke={theme.tooltipBg}
                strokeWidth={2}
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

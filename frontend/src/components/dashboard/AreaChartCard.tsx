import { useId } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { ChartCard } from './ChartCard';
import { useChartTheme } from '../../hooks/useChartTheme';

type DataPoint = { date: string; count: number };

type Props = {
  title: string;
  data: DataPoint[];
  isLoading?: boolean;
  color?: string;
};

export function AreaChartCard({
  title,
  data,
  isLoading = false,
  color,
}: Props) {
  const theme = useChartTheme();
  // Two of these can share a page, and a duplicated gradient id makes the
  // second chart adopt the first one's colour.
  const gradientId = useId().replace(/:/g, '');
  const isEmpty = !data || data.length === 0;
  const strokeColor = color || theme.stroke;

  return (
    <ChartCard title={title} isLoading={isLoading} isEmpty={isEmpty}>
      {!isLoading && !isEmpty && (
        <div className="h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={strokeColor} stopOpacity={0.28} />
                  <stop offset="100%" stopColor={strokeColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.gridStroke} vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: theme.textColor }}
                tickLine={false}
                axisLine={{ stroke: theme.gridStroke }}
              />
              <YAxis
                tick={{ fontSize: 11, fill: theme.textColor }}
                tickLine={false}
                axisLine={false}
                width={36}
              />
              <Tooltip
                cursor={{ stroke: theme.gridStroke }}
                contentStyle={{
                  backgroundColor: theme.tooltipBg,
                  border: `1px solid ${theme.tooltipBorder}`,
                  borderRadius: 'var(--radius-control)',
                  color: theme.tooltipInk,
                  fontSize: '0.8125rem',
                  boxShadow: 'var(--shadow-raised)',
                }}
                labelStyle={{ color: theme.tooltipInk, fontWeight: 500 }}
                itemStyle={{ color: theme.tooltipInk }}
                formatter={(value: number | undefined) => [value ?? 0, 'Messages']}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke={strokeColor}
                fill={`url(#${gradientId})`}
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </ChartCard>
  );
}

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

type DataPoint = Record<string, unknown> & { name: string; value?: number; count?: number };

type Props = {
  title: string;
  data: DataPoint[];
  isLoading?: boolean;
  dataKey?: string;
  color?: string;
  tooltipLabelKey?: string;
};

type TooltipContentProps = {
  active?: boolean;
  payload?: Array<{ payload: Record<string, unknown>; value?: unknown }>;
  tooltipLabelKey?: string;
  dataKey: string;
};

function CustomTooltip(props: TooltipContentProps) {
  const { active, payload, tooltipLabelKey, dataKey } = props;
  const theme = useChartTheme();
  if (!active || !payload?.length) return null;
  const p = payload[0].payload as Record<string, unknown>;
  const label =
    tooltipLabelKey && p[tooltipLabelKey] != null
      ? String(p[tooltipLabelKey])
      : String(p.name);
  const value = p[dataKey] != null ? p[dataKey] : payload[0].value;
  return (
    <div
      style={{
        backgroundColor: theme.tooltipBg,
        border: `1px solid ${theme.tooltipBorder}`,
        borderRadius: 'var(--radius-control)',
        padding: '0.5rem 0.75rem',
        fontSize: '0.8125rem',
        boxShadow: 'var(--shadow-raised)',
      }}
    >
      <div style={{ color: theme.tooltipInk, fontWeight: 500 }}>{label}</div>
      <div style={{ color: theme.textColor }}>
        {dataKey}: {String(value)}
      </div>
    </div>
  );
}

export function BarChartCard({
  title,
  data,
  isLoading = false,
  dataKey = 'count',
  color,
  tooltipLabelKey,
}: Props) {
  const theme = useChartTheme();
  const isEmpty = !data || data.length === 0;

  const chartData = data.map((d) => {
    const base: Record<string, unknown> = {
      name: String(d.name).length > 20 ? String(d.name).slice(0, 20) + '...' : d.name,
      [dataKey]: d.value ?? d.count ?? 0,
    };
    if (tooltipLabelKey && d[tooltipLabelKey] != null) {
      base[tooltipLabelKey] = d[tooltipLabelKey];
    }
    return base;
  });

  return (
    <ChartCard title={title} isLoading={isLoading} isEmpty={isEmpty}>
      {!isLoading && !isEmpty && (
        <div className="h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.gridStroke} horizontal={false} />
              <XAxis
                type="number"
                tick={{ fontSize: 11, fill: theme.textColor }}
                tickLine={false}
                axisLine={{ stroke: theme.gridStroke }}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={100}
                tick={{ fontSize: 10, fill: theme.textColor }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                cursor={{ fill: theme.gridStroke, fillOpacity: 0.4 }}
                content={(contentProps: unknown) => (
                  <CustomTooltip
                    {...(contentProps as Omit<TooltipContentProps, 'tooltipLabelKey' | 'dataKey'>)}
                    tooltipLabelKey={tooltipLabelKey}
                    dataKey={dataKey}
                  />
                )}
              />
              <Bar dataKey={dataKey} fill={color ?? theme.stroke} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </ChartCard>
  );
}

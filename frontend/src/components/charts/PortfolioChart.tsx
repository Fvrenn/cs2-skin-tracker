'use client';

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { PortfolioHistoryPoint } from '@/types';

interface PortfolioChartProps {
  data: PortfolioHistoryPoint[];
}

export function PortfolioChart({ data }: PortfolioChartProps) {
  const chartData = data.map((p) => ({
    label: new Date(p.day).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
    }),
    value: p.value_eur,
  }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
        <defs>
          <linearGradient id="portfolioGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#818cf8" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#818cf8" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: '#71717a' }}
          axisLine={false}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fontSize: 11, fill: '#71717a' }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => `${v.toFixed(0)}€`}
          width={52}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#18181b',
            border: '1px solid #27272a',
            borderRadius: '6px',
            fontSize: 12,
          }}
          labelStyle={{ color: '#71717a' }}
          itemStyle={{ color: '#818cf8' }}
          formatter={(value: number) => [`${value.toFixed(2)} €`, 'Valeur portefeuille']}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke="#818cf8"
          strokeWidth={2}
          fill="url(#portfolioGrad)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

"use client";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";

interface MetricChartProps {
  data: { name: string; value: number | null }[];
  height?: number;
}

function getColor(value: number): string {
  if (value >= 0.7) return "#10b981";
  if (value >= 0.3) return "#f59e0b";
  return "#ef4444";
}

export function MetricChart({ data, height = 250 }: MetricChartProps) {
  const chartData = data
    .filter((d) => d.value !== null)
    .map((d) => ({ name: d.name, value: d.value as number }));

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-[250px] text-slate-500">
        No metrics available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
        <XAxis
          dataKey="name"
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          axisLine={{ stroke: "#334155" }}
          tickLine={false}
        />
        <YAxis
          domain={[0, 1]}
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          axisLine={{ stroke: "#334155" }}
          tickLine={false}
          width={35}
        />
        <Tooltip
          contentStyle={{
            background: "#1e293b",
            border: "1px solid #334155",
            borderRadius: 8,
            color: "#f1f5f9",
            fontSize: 12,
          }}
          formatter={(value: number) => [value.toFixed(3), "Score"]}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={40}>
          {chartData.map((entry, index) => (
            <Cell key={index} fill={getColor(entry.value)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

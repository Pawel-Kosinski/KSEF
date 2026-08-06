"use client";

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Loader2 } from "lucide-react";

import { DashboardCard } from "@/components/DashboardCard";
import { EmptyDataHint } from "@/components/EmptyDataHint";
import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { formatPln, toNumber } from "@/lib/api";
import {
  CHART_AXIS_TICK,
  CHART_GRID_STROKE,
  formatCompactPln,
  formatPeriodLabel,
  GRANULARITY_LABELS,
} from "@/lib/chartUtils";
import type { CashflowResponse } from "@/lib/types";

interface CashflowChartProps {
  cashflow: CashflowResponse | null;
  loading?: boolean;
}

interface CashflowPoint {
  label: string;
  period: string;
  revenue: number;
  cost: number;
  net: number;
}

function CashflowTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ dataKey: string; value: number; color: string; payload: CashflowPoint }>;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;

  return (
    <div className="rounded-xl border border-slate-200/80 bg-white/95 px-4 py-3 shadow-lg backdrop-blur-sm dark:border-slate-600 dark:bg-slate-900/95">
      <p className="mb-2 text-xs font-medium text-slate-500 dark:text-slate-400">
        {point.period}
      </p>
      <p className="text-sm font-semibold text-emerald-500">
        Przychód: {formatPln(point.revenue)}
      </p>
      <p className="mt-1 text-sm font-semibold text-red-500">
        Koszt: {formatPln(point.cost)}
      </p>
      <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">
        Saldo: {formatPln(point.net)}
      </p>
    </div>
  );
}

export function CashflowChart({ cashflow, loading = false }: CashflowChartProps) {
  const granularity = cashflow?.granularity ?? "month";

  const chartData: CashflowPoint[] = useMemo(() => {
    return (
      cashflow?.items.map((item) => {
        const revenue = toNumber(item.sales);
        const cost = toNumber(item.costs);
        return {
          label: formatPeriodLabel(item.date, granularity),
          period: item.date,
          revenue,
          cost,
          net: toNumber(item.balance),
        };
      }) ?? []
    );
  }, [cashflow, granularity]);

  const totals = useMemo(
    () => ({
      revenue: cashflow ? toNumber(cashflow.total_sales) : 0,
      cost: cashflow ? toNumber(cashflow.total_costs) : 0,
      net: cashflow ? toNumber(cashflow.total_balance) : 0,
    }),
    [cashflow],
  );

  const hasData = chartData.some((point) => point.revenue > 0 || point.cost > 0);

  return (
    <DashboardCard
      title="Cashflow"
      subtitle={`Przychody vs koszty netto (${GRANULARITY_LABELS[granularity] ?? granularity})`}
      className="col-span-full"
    >
      {loading ? (
        <div className="flex h-72 items-center justify-center text-slate-500">
          <HydrationSafeIcon icon={Loader2} className="mr-2 h-5 w-5 animate-spin" />
          Ładowanie…
        </div>
      ) : !hasData ? (
        <EmptyDataHint />
      ) : (
        <>
          <div className="mb-4 flex flex-wrap gap-x-6 gap-y-2 text-sm">
            <span className="text-emerald-600 dark:text-emerald-400">
              Przychód: <strong>{formatPln(totals.revenue)}</strong>
            </span>
            <span className="text-red-600 dark:text-red-400">
              Koszty: <strong>{formatPln(totals.cost)}</strong>
            </span>
            <span className="text-slate-700 dark:text-slate-200">
              Saldo:{" "}
              <strong className={totals.net >= 0 ? "text-emerald-600" : "text-red-600"}>
                {formatPln(totals.net)}
              </strong>
            </span>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke={CHART_GRID_STROKE} strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11, fill: CHART_AXIS_TICK }}
                tickLine={false}
                axisLine={false}
                interval={chartData.length > 14 ? "preserveStartEnd" : 0}
                angle={granularity === "day" && chartData.length > 10 ? -45 : 0}
                textAnchor={granularity === "day" && chartData.length > 10 ? "end" : "middle"}
                height={granularity === "day" && chartData.length > 10 ? 50 : 30}
              />
              <YAxis
                tick={{ fontSize: 12, fill: CHART_AXIS_TICK }}
                tickLine={false}
                axisLine={false}
                tickFormatter={formatCompactPln}
                width={56}
              />
              <Tooltip content={<CashflowTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }}
                formatter={(value) =>
                  value === "revenue" ? "Przychód" : value === "cost" ? "Koszt" : value
                }
              />
              <Bar
                dataKey="revenue"
                name="revenue"
                fill="#10b981"
                radius={[4, 4, 0, 0]}
                maxBarSize={40}
              />
              <Bar
                dataKey="cost"
                name="cost"
                fill="#ef4444"
                radius={[4, 4, 0, 0]}
                maxBarSize={40}
              />
            </BarChart>
          </ResponsiveContainer>
        </>
      )}
    </DashboardCard>
  );
}

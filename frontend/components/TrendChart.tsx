"use client";

import { useId, useMemo } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
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
  CHART_PREVIOUS_STROKE,
  formatCompactPln,
  formatPeriodLabel,
  GRANULARITY_LABELS,
} from "@/lib/chartUtils";
import type { InvoiceRole, TrendResponse } from "@/lib/types";
import { ROLE_LABELS } from "@/lib/types";

interface TrendChartProps {
  role: InvoiceRole;
  trend: TrendResponse | null;
  previousTrend?: TrendResponse | null;
  loading?: boolean;
}

interface TrendTooltipPayload {
  period: string;
  previousPeriod: string | null;
  total: number;
  previous: number | null;
}

function TrendTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: TrendTooltipPayload }>;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;

  return (
    <div className="rounded-xl border border-slate-200/80 bg-white/95 px-4 py-3 shadow-lg backdrop-blur-sm dark:border-slate-600 dark:bg-slate-900/95">
      <p className="mb-2 text-xs font-medium text-slate-500 dark:text-slate-400">
        {point.period}
      </p>
      <p className="text-sm font-semibold text-slate-900 dark:text-white">
        Bieżący okres: {formatPln(point.total)}
      </p>
      {point.previous != null ? (
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Poprzedni
          {point.previousPeriod ? ` (${point.previousPeriod})` : ""}:{" "}
          {formatPln(point.previous)}
        </p>
      ) : null}
    </div>
  );
}

export function TrendChart({
  role,
  trend,
  previousTrend = null,
  loading = false,
}: TrendChartProps) {
  const gradientId = useId().replace(/:/g, "");
  const labels = ROLE_LABELS[role];
  const granularity = trend?.granularity ?? "month";

  const chartData = useMemo(() => {
    const currentItems = trend?.items ?? [];
    const previousItems = previousTrend?.items ?? [];

    return currentItems.map((item, index) => {
      const prev = previousItems[index];
      return {
        label: formatPeriodLabel(item.period, granularity),
        period: item.period,
        total: toNumber(item.total_net),
        previous: prev ? toNumber(prev.total_net) : null,
        previousPeriod: prev?.period ?? null,
      };
    });
  }, [trend, previousTrend, granularity]);

  const hasComparison = chartData.some((point) => point.previous != null);

  return (
    <DashboardCard
      title={labels.trendTitle}
      subtitle={`${labels.trendSubtitle} (${GRANULARITY_LABELS[granularity] ?? granularity})`}
      className="col-span-full"
    >
      {loading ? (
        <div className="flex h-72 items-center justify-center text-slate-500">
          <HydrationSafeIcon icon={Loader2} className="mr-2 h-5 w-5 animate-spin" />
          Ładowanie…
        </div>
      ) : chartData.length === 0 ? (
        <EmptyDataHint />
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-slate-500">
            <span>
              Łącznie w okresie:{" "}
              <span className="font-semibold text-slate-900 dark:text-white">
                {formatPln(trend!.total_net)}
              </span>
            </span>
            {hasComparison ? (
              <span className="flex items-center gap-3">
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="inline-block h-0.5 w-4 rounded"
                    style={{ backgroundColor: labels.barColor }}
                  />
                  Bieżący
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="inline-block h-0 w-4 border-t-2 border-dashed"
                    style={{ borderColor: CHART_PREVIOUS_STROKE }}
                  />
                  Poprzedni okres
                </span>
              </span>
            ) : null}
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`trend-fill-${gradientId}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={labels.barColor} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={labels.barColor} stopOpacity={0} />
                </linearGradient>
              </defs>
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
              <Tooltip content={<TrendTooltip />} />
              <Area
                type="monotone"
                dataKey="total"
                stroke={labels.barColor}
                strokeWidth={2}
                fill={`url(#trend-fill-${gradientId})`}
                dot={{ r: 3, fill: labels.barColor, strokeWidth: 0 }}
                activeDot={{ r: 5, strokeWidth: 0 }}
              />
              {hasComparison ? (
                <Line
                  type="monotone"
                  dataKey="previous"
                  stroke={CHART_PREVIOUS_STROKE}
                  strokeWidth={2}
                  strokeDasharray="6 4"
                  dot={false}
                  activeDot={{ r: 4, fill: CHART_PREVIOUS_STROKE, strokeWidth: 0 }}
                />
              ) : null}
            </ComposedChart>
          </ResponsiveContainer>
        </>
      )}
    </DashboardCard>
  );
}

"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Loader2 } from "lucide-react";

import { DashboardCard } from "@/components/DashboardCard";
import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { EmptyDataHint } from "@/components/EmptyDataHint";
import { apiFetch, formatPln, toNumber } from "@/lib/api";
import type { InvoiceRole, TrendResponse } from "@/lib/types";
import { ROLE_LABELS } from "@/lib/types";

const GRANULARITY_LABELS: Record<string, string> = {
  day: "dziennie",
  week: "tygodniowo",
  month: "miesięcznie",
};

function formatPeriodLabel(period: string, granularity: string): string {
  if (granularity === "day") {
    return period.slice(5);
  }
  if (granularity === "week") {
    return period.replace("-W", " W");
  }
  return period;
}

interface TrendChartProps {
  role: InvoiceRole;
  refreshKey?: number;
  dateFrom?: string;
  dateTo?: string;
}

export function TrendChart({
  role,
  refreshKey = 0,
  dateFrom,
  dateTo,
}: TrendChartProps) {
  const [data, setData] = useState<TrendResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const labels = ROLE_LABELS[role];

  useEffect(() => {
    setLoading(true);
    setError(null);
    apiFetch<TrendResponse>("/stats/trend", { role, date_from: dateFrom, date_to: dateTo })
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Błąd"))
      .finally(() => setLoading(false));
  }, [role, refreshKey, dateFrom, dateTo]);

  const granularity = data?.granularity ?? "month";
  const chartData =
    data?.items.map((item) => ({
      label: formatPeriodLabel(item.period, granularity),
      period: item.period,
      total: toNumber(item.total_net),
    })) ?? [];

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
      ) : error ? (
        <p className="text-sm text-red-600">{error}</p>
      ) : chartData.length === 0 ? (
        <EmptyDataHint />
      ) : (
        <>
          <p className="mb-4 text-sm text-slate-500">
            Łącznie w okresie:{" "}
            <span className="font-semibold text-slate-900 dark:text-white">
              {formatPln(data!.total_net)}
            </span>
          </p>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                interval={chartData.length > 14 ? "preserveStartEnd" : 0}
                angle={granularity === "day" && chartData.length > 10 ? -45 : 0}
                textAnchor={granularity === "day" && chartData.length > 10 ? "end" : "middle"}
                height={granularity === "day" && chartData.length > 10 ? 50 : 30}
              />
              <YAxis
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) =>
                  new Intl.NumberFormat("pl-PL", {
                    notation: "compact",
                    compactDisplay: "short",
                  }).format(v)
                }
              />
              <Tooltip
                labelFormatter={(_, payload) =>
                  payload?.[0]?.payload?.period
                    ? String(payload[0].payload.period)
                    : ""
                }
                formatter={(value) => [formatPln(value as number), "Suma netto"]}
                contentStyle={{ borderRadius: "8px", fontSize: "13px" }}
              />
              <Bar dataKey="total" fill={labels.barColor} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </>
      )}
    </DashboardCard>
  );
}

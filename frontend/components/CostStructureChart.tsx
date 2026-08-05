"use client";

import { useEffect, useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Loader2 } from "lucide-react";

import { DashboardCard } from "@/components/DashboardCard";
import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { EmptyDataHint } from "@/components/EmptyDataHint";
import { apiFetch, formatPln, toNumber } from "@/lib/api";
import type { CostStructureResponse, InvoiceRole } from "@/lib/types";
import { ROLE_LABELS } from "@/lib/types";

const COLORS = [
  "#2563eb",
  "#7c3aed",
  "#0891b2",
  "#059669",
  "#d97706",
  "#dc2626",
  "#64748b",
];

interface CostStructureChartProps {
  role: InvoiceRole;
  refreshKey?: number;
  dateFrom?: string;
  dateTo?: string;
}

export function CostStructureChart({
  role,
  refreshKey = 0,
  dateFrom,
  dateTo,
}: CostStructureChartProps) {
  const [data, setData] = useState<CostStructureResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const labels = ROLE_LABELS[role];

  useEffect(() => {
    setLoading(true);
    setError(null);
    apiFetch<CostStructureResponse>("/stats/cost-structure", {
      role,
      date_from: dateFrom,
      date_to: dateTo,
    })
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Błąd"))
      .finally(() => setLoading(false));
  }, [role, refreshKey, dateFrom, dateTo]);

  const chartData =
    data?.items.map((item) => ({
      name: item.category,
      value: toNumber(item.total_net),
    })) ?? [];

  return (
    <DashboardCard title={labels.structureTitle} subtitle={labels.structureSubtitle}>
      {loading ? (
        <div className="flex h-64 items-center justify-center text-slate-500">
          <HydrationSafeIcon icon={Loader2} className="mr-2 h-5 w-5 animate-spin" />
          Ładowanie…
        </div>
      ) : error ? (
        <p className="text-sm text-red-600">{error}</p>
      ) : chartData.length === 0 ? (
        <EmptyDataHint />
      ) : (
        <>
          <p className="mb-4 text-2xl font-bold text-slate-900 dark:text-white">
            {formatPln(data!.total_net)}
            <span className="ml-2 text-sm font-normal text-slate-500">łącznie netto</span>
          </p>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={chartData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={2}
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value) => formatPln(value as number)}
                contentStyle={{ borderRadius: "8px", fontSize: "13px" }}
              />
            </PieChart>
          </ResponsiveContainer>
          <ul className="mt-4 space-y-2">
            {chartData.map((item, index) => (
              <li key={item.name} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">
                  <span
                    className="inline-block h-3 w-3 rounded-full"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  />
                  <span className="max-w-[200px] truncate">{item.name}</span>
                </span>
                <span className="font-medium">{formatPln(item.value)}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </DashboardCard>
  );
}

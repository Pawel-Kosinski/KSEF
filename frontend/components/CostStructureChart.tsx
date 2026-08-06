"use client";

import { useMemo } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { LineChart, Loader2 } from "lucide-react";

import { DashboardCard } from "@/components/DashboardCard";
import { EmptyDataHint } from "@/components/EmptyDataHint";
import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { formatPln, toNumber } from "@/lib/api";
import { CHART_DONUT_COLORS, formatPercent } from "@/lib/chartUtils";
import type { CostStructureResponse, InvoiceRole } from "@/lib/types";
import { ROLE_LABELS } from "@/lib/types";

interface CostStructureChartProps {
  role: InvoiceRole;
  structure: CostStructureResponse | null;
  loading?: boolean;
  onAnalyzeCategory?: (category?: string) => void;
}

interface SliceData {
  name: string;
  value: number;
  percent: number;
}

function StructureTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: SliceData; color?: string }>;
}) {
  if (!active || !payload?.length) return null;
  const slice = payload[0].payload;
  const color = payload[0].color;

  return (
    <div className="rounded-xl border border-slate-200/80 bg-white/95 px-4 py-3 shadow-lg backdrop-blur-sm dark:border-slate-600 dark:bg-slate-900/95">
      <div className="mb-1 flex items-center gap-2">
        <span
          className="inline-block h-2.5 w-2.5 rounded-full"
          style={{ backgroundColor: color }}
        />
        <span className="text-sm font-semibold text-slate-900 dark:text-white">
          {slice.name}
        </span>
      </div>
      <p className="text-sm text-slate-700 dark:text-slate-200">{formatPln(slice.value)}</p>
      <p className="text-xs text-slate-500 dark:text-slate-400">{slice.percent.toFixed(1)}%</p>
    </div>
  );
}

export function CostStructureChart({
  role,
  structure,
  loading = false,
  onAnalyzeCategory,
}: CostStructureChartProps) {
  const labels = ROLE_LABELS[role];
  const total = structure ? toNumber(structure.total_net) : 0;

  const chartData: SliceData[] = useMemo(() => {
    return (
      structure?.items.map((item) => {
        const value = toNumber(item.total_net);
        return {
          name: item.category,
          value,
          percent: total > 0 ? (value / total) * 100 : 0,
        };
      }) ?? []
    );
  }, [structure, total]);

  function handleSliceClick(_: unknown, index: number) {
    const category = chartData[index]?.name;
    if (!category || !onAnalyzeCategory) return;
    onAnalyzeCategory(category);
  }

  return (
    <DashboardCard title={labels.structureTitle} subtitle={labels.structureSubtitle}>
      {loading ? (
        <div className="flex h-64 items-center justify-center text-slate-500">
          <HydrationSafeIcon icon={Loader2} className="mr-2 h-5 w-5 animate-spin" />
          Ładowanie…
        </div>
      ) : chartData.length === 0 ? (
        <EmptyDataHint />
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <p className="text-2xl font-bold text-slate-900 dark:text-white">
              {formatPln(total)}
              <span className="ml-2 text-sm font-normal text-slate-500">łącznie netto</span>
            </p>
            {onAnalyzeCategory ? (
              <button
                type="button"
                onClick={() => onAnalyzeCategory()}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                <HydrationSafeIcon icon={LineChart} className="h-4 w-4" />
                Analizuj kategorię
              </button>
            ) : null}
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={chartData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius="42%"
                outerRadius="72%"
                paddingAngle={2}
                onClick={handleSliceClick}
                style={{ cursor: onAnalyzeCategory ? "pointer" : "default" }}
              >
                {chartData.map((item, index) => (
                  <Cell
                    key={item.name}
                    fill={CHART_DONUT_COLORS[index % CHART_DONUT_COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip content={<StructureTooltip />} />
            </PieChart>
          </ResponsiveContainer>
          <p className="mt-2 text-xs text-slate-400">
            Kliknij wycinek wykresu, aby otworzyć analizę wybranej kategorii.
          </p>
          <ul className="mt-4 max-h-48 space-y-2 overflow-y-auto">
            {chartData.map((item, index) => (
              <li key={item.name}>
                <button
                  type="button"
                  onClick={() => onAnalyzeCategory?.(item.name)}
                  className="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left text-sm transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50"
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <span
                      className="inline-block h-3 w-3 shrink-0 rounded-full"
                      style={{
                        backgroundColor: CHART_DONUT_COLORS[index % CHART_DONUT_COLORS.length],
                      }}
                    />
                    <span className="truncate">{item.name}</span>
                  </span>
                  <span className="ml-2 shrink-0 text-right">
                    <span className="font-medium text-slate-900 dark:text-white">
                      {formatPln(item.value)}
                    </span>
                    <span className="ml-2 text-xs text-slate-500">
                      {formatPercent(item.value, total)}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </DashboardCard>
  );
}

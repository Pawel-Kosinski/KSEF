"use client";

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Loader2, Pin, PinOff, X } from "lucide-react";

import { EmptyDataHint } from "@/components/EmptyDataHint";
import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { InvoiceList } from "@/components/InvoiceList";
import { useApiQuery } from "@/hooks/useApiQuery";
import { formatPln, toNumber } from "@/lib/api";
import {
  CHART_AXIS_TICK,
  CHART_GRID_STROKE,
  formatCompactPln,
  formatPeriodLabel,
  GRANULARITY_LABELS,
} from "@/lib/chartUtils";
import type { DateRange } from "@/lib/dateRange";
import type { InvoiceRole, TrendResponse } from "@/lib/types";
import { ROLE_LABELS } from "@/lib/types";

export const CATEGORY_PANEL_MIN_WIDTH = 320;
export const CATEGORY_PANEL_MAX_WIDTH = 720;
export const CATEGORY_PANEL_DEFAULT_WIDTH = 400;

interface CategoryAnalysisDialogProps {
  open: boolean;
  pinned: boolean;
  width: number;
  role: InvoiceRole;
  dateRange: DateRange;
  categories: string[];
  initialCategory?: string | null;
  onClose: () => void;
  onPinnedChange: (pinned: boolean) => void;
  onWidthChange: (width: number) => void;
}

function clampPanelWidth(value: number): number {
  return Math.min(CATEGORY_PANEL_MAX_WIDTH, Math.max(CATEGORY_PANEL_MIN_WIDTH, value));
}

function CategoryTrendTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: { label: string; total: number } }>;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="rounded-xl border border-slate-200/80 bg-white/95 px-4 py-3 shadow-lg backdrop-blur-sm dark:border-slate-600 dark:bg-slate-900/95">
      <p className="mb-1 text-xs text-slate-500">{point.label}</p>
      <p className="text-sm font-semibold text-slate-900 dark:text-white">
        {formatPln(point.total)}
      </p>
    </div>
  );
}

function CategoryTrendChart({
  trend,
  role,
  loading,
}: {
  trend: TrendResponse | null;
  role: InvoiceRole;
  loading: boolean;
}) {
  const gradientId = useId().replace(/:/g, "");
  const labels = ROLE_LABELS[role];
  const granularity = trend?.granularity ?? "month";

  const chartData = useMemo(() => {
    return (trend?.items ?? []).map((item) => ({
      label: formatPeriodLabel(item.period, granularity),
      total: toNumber(item.total_net),
    }));
  }, [trend, granularity]);

  if (loading) {
    return (
      <div className="flex h-56 items-center justify-center text-slate-500">
        <HydrationSafeIcon icon={Loader2} className="mr-2 h-5 w-5 animate-spin" />
        Ładowanie trendu…
      </div>
    );
  }

  if (chartData.length === 0) {
    return <EmptyDataHint />;
  }

  return (
    <>
      <p className="mb-3 text-sm text-slate-500">
        Suma w okresie:{" "}
        <span className="font-semibold text-slate-900 dark:text-white">
          {formatPln(trend!.total_net)}
        </span>
        <span className="ml-2 text-xs">
          ({GRANULARITY_LABELS[granularity] ?? granularity})
        </span>
      </p>
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={`cat-trend-${gradientId}`} x1="0" y1="0" x2="0" y2="1">
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
          />
          <YAxis
            tick={{ fontSize: 12, fill: CHART_AXIS_TICK }}
            tickLine={false}
            axisLine={false}
            tickFormatter={formatCompactPln}
            width={56}
          />
          <Tooltip content={<CategoryTrendTooltip />} />
          <Area
            type="monotone"
            dataKey="total"
            stroke={labels.barColor}
            strokeWidth={2}
            fill={`url(#cat-trend-${gradientId})`}
            dot={{ r: 3, fill: labels.barColor, strokeWidth: 0 }}
            activeDot={{ r: 5, strokeWidth: 0 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </>
  );
}

export function CategoryAnalysisDialog({
  open,
  pinned,
  width,
  role,
  dateRange,
  categories,
  initialCategory = null,
  onClose,
  onPinnedChange,
  onWidthChange,
}: CategoryAnalysisDialogProps) {
  const labels = ROLE_LABELS[role];
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const resizingRef = useRef(false);

  useEffect(() => {
    if (!open) return;
    if (initialCategory && categories.includes(initialCategory)) {
      setSelectedCategory(initialCategory);
      return;
    }
    setSelectedCategory(categories[0] ?? "");
  }, [open, initialCategory, categories]);

  useEffect(() => {
    if (!open) return;

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    document.addEventListener("keydown", onKeyDown);
    if (!pinned) {
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [open, pinned, onClose]);

  const handleResizeStart = useCallback(
    (event: React.MouseEvent) => {
      event.preventDefault();
      resizingRef.current = true;
      const startX = event.clientX;
      const startWidth = width;

      function onMouseMove(moveEvent: MouseEvent) {
        if (!resizingRef.current) return;
        const delta = moveEvent.clientX - startX;
        onWidthChange(clampPanelWidth(startWidth + delta));
      }

      function onMouseUp() {
        resizingRef.current = false;
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      }

      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    },
    [onWidthChange, width],
  );

  const { data: trend, loading: trendLoading } = useApiQuery<TrendResponse>(
    "/stats/trend",
    {
      role,
      date_from: dateRange.dateFrom,
      date_to: dateRange.dateTo,
      category: selectedCategory,
    },
    [role, dateRange.dateFrom, dateRange.dateTo, selectedCategory],
    { enabled: open && Boolean(selectedCategory) },
  );

  if (!open) return null;

  const panel = (
    <aside
      role="dialog"
      aria-modal={!pinned}
      aria-labelledby="category-analysis-title"
      style={{ width }}
      className="relative flex h-full max-w-[92vw] flex-col border-r border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-900"
    >
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label="Zmień szerokość panelu"
        onMouseDown={handleResizeStart}
        className="absolute -right-1 top-0 z-10 h-full w-2 cursor-col-resize hover:bg-blue-500/20"
      />

      <header className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-4 dark:border-slate-800">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {labels.tab} · Analiza kategorii
          </p>
          <h2
            id="category-analysis-title"
            className="truncate text-lg font-bold text-slate-900 dark:text-white"
          >
            Drill-down kategorii
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Okres: {dateRange.dateFrom} – {dateRange.dateTo}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            onClick={() => onPinnedChange(!pinned)}
            className={`rounded-lg p-2 transition-colors ${
              pinned
                ? "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                : "text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
            title={pinned ? "Odepnij panel (tryb modalny)" : "Przypnij panel (przeglądaj dashboard)"}
            aria-label={pinned ? "Odepnij panel" : "Przypnij panel"}
            aria-pressed={pinned}
          >
            <HydrationSafeIcon icon={pinned ? PinOff : Pin} className="h-5 w-5" />
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Zamknij"
          >
            <HydrationSafeIcon icon={X} className="h-5 w-5" />
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {categories.length === 0 ? (
          <p className="text-sm text-slate-500">
            Brak kategorii w wybranej zakładce ({labels.tab.toLowerCase()}) w tym okresie.
          </p>
        ) : (
          <div className="space-y-6">
            <div>
              <label
                htmlFor="category-analysis-select"
                className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-200"
              >
                Wybierz kategorię ({labels.tab})
              </label>
              <select
                id="category-analysis-select"
                value={selectedCategory}
                onChange={(event) => setSelectedCategory(event.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              >
                {categories.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </div>

            <section className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
              <h3 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">
                Trend: {selectedCategory}
              </h3>
              <CategoryTrendChart trend={trend} role={role} loading={trendLoading} />
            </section>

            <section>
              <h3 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">
                Faktury w kategorii
              </h3>
              <InvoiceList
                role={role}
                dateFrom={dateRange.dateFrom}
                dateTo={dateRange.dateTo}
                categoryFilter={selectedCategory}
              />
            </section>
          </div>
        )}
      </div>
    </aside>
  );

  if (pinned) {
    return (
      <div className="fixed left-0 top-0 z-40 h-full">{panel}</div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-start">
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/50 backdrop-blur-[1px]"
        aria-label="Zamknij analizę kategorii"
        onClick={onClose}
      />
      <div className="relative h-full">{panel}</div>
    </div>
  );
}

export const UNCATEGORIZED_LABEL = "Niesklasyfikowane";

/** Paleta wysokokontrastowa na ciemnym tle dashboardu. */
export const CHART_DONUT_COLORS = [
  "#22d3ee",
  "#a78bfa",
  "#f472b6",
  "#facc15",
  "#34d399",
  "#fb923c",
  "#60a5fa",
  "#e879f9",
];

export const CHART_GRID_STROKE = "#334155";
export const CHART_AXIS_TICK = "#94a3b8";
export const CHART_PREVIOUS_STROKE = "#94a3b8";

export const GRANULARITY_LABELS: Record<string, string> = {
  day: "dziennie",
  week: "tygodniowo",
  month: "miesięcznie",
};

export function formatPeriodLabel(period: string, granularity: string): string {
  if (granularity === "day") {
    return period.slice(5);
  }
  if (granularity === "week") {
    return period.replace("-W", " W");
  }
  return period;
}

export function formatCompactPln(value: number): string {
  return new Intl.NumberFormat("pl-PL", {
    notation: "compact",
    compactDisplay: "short",
  }).format(value);
}

export function formatPercent(value: number, total: number): string {
  if (total <= 0) return "0%";
  return `${((value / total) * 100).toFixed(1)}%`;
}

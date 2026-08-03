"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { apiFetch, formatPln } from "@/lib/api";
import type { InvoiceRole, SummaryResponse } from "@/lib/types";
import { ROLE_LABELS } from "@/lib/types";

interface KpiSummaryCardsProps {
  role: InvoiceRole;
  refreshKey?: number;
  dateFrom?: string;
  dateTo?: string;
}

export function KpiSummaryCards({
  role,
  refreshKey = 0,
  dateFrom,
  dateTo,
}: KpiSummaryCardsProps) {
  const [data, setData] = useState<SummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const labels = ROLE_LABELS[role];

  useEffect(() => {
    setLoading(true);
    setError(null);
    apiFetch<SummaryResponse>("/stats/summary", {
      role,
      date_from: dateFrom,
      date_to: dateTo,
    })
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Błąd"))
      .finally(() => setLoading(false));
  }, [role, refreshKey, dateFrom, dateTo]);

  if (loading) {
    return (
      <div className="col-span-full flex h-24 items-center justify-center text-slate-500">
        <HydrationSafeIcon icon={Loader2} className="mr-2 h-5 w-5 animate-spin" />
        Ładowanie podsumowania…
      </div>
    );
  }

  if (error) {
    return (
      <div className="col-span-full rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        {error}
      </div>
    );
  }

  const netLabel = role === "sales" ? "Przychody netto" : "Koszty netto";

  return (
    <div className="col-span-full grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{netLabel}</p>
        <p className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">
          {formatPln(data?.total_net ?? 0)}
        </p>
      </div>
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Podatek VAT</p>
        <p className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">
          {formatPln(data?.total_vat ?? 0)}
        </p>
      </div>
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Razem brutto</p>
        <p
          className={`mt-2 text-2xl font-bold ${
            role === "sales" ? "text-emerald-700 dark:text-emerald-400" : "text-blue-700 dark:text-blue-400"
          }`}
        >
          {formatPln(data?.total_gross ?? 0)}
        </p>
      </div>
    </div>
  );
}

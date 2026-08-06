"use client";

import { Loader2 } from "lucide-react";

import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { formatPln } from "@/lib/api";
import type { InvoiceRole, SummaryResponse } from "@/lib/types";
import { ROLE_LABELS } from "@/lib/types";

interface KpiSummaryCardsProps {
  role?: InvoiceRole;
  summary: SummaryResponse | null;
  loading?: boolean;
}

export function KpiSummaryCards({
  role = "cost",
  summary,
  loading = false,
}: KpiSummaryCardsProps) {
  if (loading) {
    return (
      <div className="col-span-full flex h-24 items-center justify-center text-slate-500">
        <HydrationSafeIcon icon={Loader2} className="mr-2 h-5 w-5 animate-spin" />
        Ładowanie podsumowania…
      </div>
    );
  }

  const netLabel = role === "sales" ? "Przychody netto" : "Koszty netto";

  return (
    <div className="col-span-full grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{netLabel}</p>
        <p className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">
          {formatPln(summary?.total_net ?? 0)}
        </p>
      </div>
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Podatek VAT</p>
        <p className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">
          {formatPln(summary?.total_vat ?? 0)}
        </p>
      </div>
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Razem brutto</p>
        <p
          className={`mt-2 text-2xl font-bold ${
            role === "sales" ? "text-emerald-700 dark:text-emerald-400" : "text-blue-700 dark:text-blue-400"
          }`}
        >
          {formatPln(summary?.total_gross ?? 0)}
        </p>
      </div>
    </div>
  );
}

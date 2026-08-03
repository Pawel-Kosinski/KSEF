"use client";

import { BarChart3 } from "lucide-react";

import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";

export function DashboardHeader() {
  return (
    <header className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="mx-auto flex max-w-7xl items-center gap-3 px-6 py-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white">
          <HydrationSafeIcon icon={BarChart3} className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-white">
            Wirtualny CFO – Panel Główny
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Analityka kosztów z faktur KSeF
          </p>
        </div>
      </div>
    </header>
  );
}

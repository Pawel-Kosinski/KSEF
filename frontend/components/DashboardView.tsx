"use client";

import { useState } from "react";

import { CostStructureChart } from "@/components/CostStructureChart";
import { DashboardHeader } from "@/components/DashboardHeader";
import { DashboardPeriodBar } from "@/components/DashboardPeriodBar";
import { DashboardRoleTabs } from "@/components/DashboardRoleTabs";
import { DevSetupBanner } from "@/components/DevSetupBanner";
import { InvoiceList } from "@/components/InvoiceList";
import { KpiSummaryCards } from "@/components/KpiSummaryCards";
import { TopCounterpartiesList } from "@/components/TopCounterpartiesList";
import { TrendChart } from "@/components/TrendChart";
import { currentMonthRange } from "@/lib/dateRange";
import type { InvoiceRole } from "@/lib/types";

export function DashboardView() {
  const [role, setRole] = useState<InvoiceRole>("cost");
  const [refreshKey, setRefreshKey] = useState(0);
  const [dateRange, setDateRange] = useState(currentMonthRange);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <DashboardHeader />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <DevSetupBanner />
        <DashboardPeriodBar
          range={dateRange}
          onRangeChange={setDateRange}
          onSyncComplete={() => setRefreshKey((key) => key + 1)}
        />
        <div className="mb-6">
          <DashboardRoleTabs role={role} onChange={setRole} />
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <KpiSummaryCards
            role={role}
            refreshKey={refreshKey}
            dateFrom={dateRange.dateFrom}
            dateTo={dateRange.dateTo}
          />
          <TrendChart
            role={role}
            refreshKey={refreshKey}
            dateFrom={dateRange.dateFrom}
            dateTo={dateRange.dateTo}
          />
          <CostStructureChart
            role={role}
            refreshKey={refreshKey}
            dateFrom={dateRange.dateFrom}
            dateTo={dateRange.dateTo}
          />
          <TopCounterpartiesList
            role={role}
            refreshKey={refreshKey}
            dateFrom={dateRange.dateFrom}
            dateTo={dateRange.dateTo}
          />
          <InvoiceList
            role={role}
            refreshKey={refreshKey}
            dateFrom={dateRange.dateFrom}
            dateTo={dateRange.dateTo}
          />
        </div>
      </main>
    </div>
  );
}

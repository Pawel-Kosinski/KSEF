"use client";

import { useEffect, useState } from "react";

import { CostStructureChart } from "@/components/CostStructureChart";
import { DashboardHeader } from "@/components/DashboardHeader";
import { DashboardPeriodBar } from "@/components/DashboardPeriodBar";
import { DashboardRoleTabs } from "@/components/DashboardRoleTabs";
import { InvoiceList } from "@/components/InvoiceList";
import { KpiSummaryCards } from "@/components/KpiSummaryCards";
import { KsefSetupBanner } from "@/components/KsefSetupBanner";
import { TopCounterpartiesList } from "@/components/TopCounterpartiesList";
import { TrendChart } from "@/components/TrendChart";
import { apiFetch } from "@/lib/api";
import { currentMonthRange } from "@/lib/dateRange";
import type { InvoiceRole, KsefSettingsStatus } from "@/lib/types";

export function DashboardView() {
  const [role, setRole] = useState<InvoiceRole>("cost");
  const [refreshKey, setRefreshKey] = useState(0);
  const [dateRange, setDateRange] = useState(currentMonthRange);
  const [ksefConfigured, setKsefConfigured] = useState<boolean | null>(null);

  useEffect(() => {
    apiFetch<KsefSettingsStatus>("/settings/ksef")
      .then((status) => setKsefConfigured(status.is_configured))
      .catch(() => setKsefConfigured(false));
  }, [refreshKey]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <DashboardHeader />
      <main className="mx-auto max-w-7xl px-6 py-8">
        {ksefConfigured === false ? <KsefSetupBanner /> : null}
        <DashboardPeriodBar
          range={dateRange}
          onRangeChange={setDateRange}
          onSyncComplete={() => setRefreshKey((key) => key + 1)}
          ksefConfigured={ksefConfigured !== false}
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

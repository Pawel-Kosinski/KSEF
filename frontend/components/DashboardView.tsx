"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { CashflowChart } from "@/components/CashflowChart";
import {
  CATEGORY_PANEL_DEFAULT_WIDTH,
  CategoryAnalysisDialog,
} from "@/components/CategoryAnalysisDialog";
import { CostStructureChart } from "@/components/CostStructureChart";
import { DashboardHeader } from "@/components/DashboardHeader";
import { DashboardPeriodBar } from "@/components/DashboardPeriodBar";
import { DashboardRoleTabs } from "@/components/DashboardRoleTabs";
import { InvoiceList } from "@/components/InvoiceList";
import { KpiSummaryCards } from "@/components/KpiSummaryCards";
import { KsefSetupBanner } from "@/components/KsefSetupBanner";
import { TopCounterpartiesList } from "@/components/TopCounterpartiesList";
import { TrendChart } from "@/components/TrendChart";
import { useApiQuery } from "@/hooks/useApiQuery";
import { currentMonthRange } from "@/lib/dateRange";
import { dashboardUrl, parseInvoiceRole } from "@/lib/dashboard";
import type { DashboardResponse, InvoiceRole, KsefSettingsStatus } from "@/lib/types";

export function DashboardView() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const roleFromUrl = parseInvoiceRole(searchParams.get("role"));
  const [role, setRole] = useState<InvoiceRole>(roleFromUrl);
  const [refreshKey, setRefreshKey] = useState(0);
  const [dateRange, setDateRange] = useState(currentMonthRange);
  const [categoryAnalysisOpen, setCategoryAnalysisOpen] = useState(false);
  const [categoryAnalysisPinned, setCategoryAnalysisPinned] = useState(false);
  const [categoryPanelWidth, setCategoryPanelWidth] = useState(CATEGORY_PANEL_DEFAULT_WIDTH);
  const [selectedCategoryForAnalysis, setSelectedCategoryForAnalysis] = useState<
    string | null
  >(null);

  const { data: ksefStatus } = useApiQuery<KsefSettingsStatus>(
    "/settings/ksef",
    undefined,
    [refreshKey],
  );
  const ksefConfigured = ksefStatus?.is_configured ?? null;

  const {
    data: dashboard,
    error: dashboardError,
    loading: dashboardLoading,
  } = useApiQuery<DashboardResponse>(
    "/stats/dashboard",
    {
      role,
      date_from: dateRange.dateFrom,
      date_to: dateRange.dateTo,
    },
    [role, refreshKey, dateRange.dateFrom, dateRange.dateTo],
  );

  const structureCategories =
    dashboard?.cost_structure.items.map((item) => item.category) ?? [];

  useEffect(() => {
    setRole(roleFromUrl);
  }, [roleFromUrl]);

  useEffect(() => {
    setCategoryAnalysisOpen(false);
    setCategoryAnalysisPinned(false);
    setSelectedCategoryForAnalysis(null);
  }, [role]);

  useEffect(() => {
    if (pathname !== "/") {
      setCategoryAnalysisOpen(false);
      setCategoryAnalysisPinned(false);
      setSelectedCategoryForAnalysis(null);
    }
  }, [pathname]);

  function handleRoleChange(nextRole: InvoiceRole) {
    setRole(nextRole);
    router.replace(dashboardUrl(nextRole), { scroll: false });
  }

  function openCategoryAnalysis(category?: string) {
    setSelectedCategoryForAnalysis(category ?? null);
    setCategoryAnalysisOpen(true);
  }

  function closeCategoryAnalysis() {
    setCategoryAnalysisOpen(false);
    setCategoryAnalysisPinned(false);
    setSelectedCategoryForAnalysis(null);
  }

  const contentOffset =
    categoryAnalysisOpen && categoryAnalysisPinned ? categoryPanelWidth : 0;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <div
        className="transition-[margin] duration-200 ease-out"
        style={{ marginLeft: contentOffset }}
      >
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
            <DashboardRoleTabs role={role} onChange={handleRoleChange} />
          </div>
          {dashboardError ? (
            <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {dashboardError}
            </div>
          ) : null}
          <div
            role="tabpanel"
            id={`dashboard-panel-${role}`}
            aria-labelledby={`dashboard-tab-${role}`}
            className="grid grid-cols-1 gap-6 lg:grid-cols-2"
          >
            <KpiSummaryCards
              role={role}
              summary={dashboard?.summary ?? null}
              loading={dashboardLoading}
            />
            <TrendChart
              trend={dashboard?.trend ?? null}
              previousTrend={dashboard?.previous_trend ?? null}
              role={role}
              loading={dashboardLoading}
            />
            <CashflowChart
              cashflow={dashboard?.cashflow ?? null}
              loading={dashboardLoading}
            />
            <CostStructureChart
              structure={dashboard?.cost_structure ?? null}
              role={role}
              loading={dashboardLoading}
              onAnalyzeCategory={openCategoryAnalysis}
            />
            <TopCounterpartiesList
              topCounterparties={dashboard?.top_counterparties ?? null}
              role={role}
              loading={dashboardLoading}
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

      <CategoryAnalysisDialog
        open={categoryAnalysisOpen}
        pinned={categoryAnalysisPinned}
        width={categoryPanelWidth}
        role={role}
        dateRange={dateRange}
        categories={structureCategories}
        initialCategory={selectedCategoryForAnalysis}
        onClose={closeCategoryAnalysis}
        onPinnedChange={setCategoryAnalysisPinned}
        onWidthChange={setCategoryPanelWidth}
      />
    </div>
  );
}

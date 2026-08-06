"use client";

import { Building2, Loader2, UserRound } from "lucide-react";

import { DashboardCard } from "@/components/DashboardCard";
import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { EmptyDataHint } from "@/components/EmptyDataHint";
import { formatPln, toNumber } from "@/lib/api";
import type { InvoiceRole, TopCounterpartiesResponse } from "@/lib/types";
import { ROLE_LABELS } from "@/lib/types";

interface TopCounterpartiesListProps {
  role: InvoiceRole;
  topCounterparties: TopCounterpartiesResponse | null;
  loading?: boolean;
}

export function TopCounterpartiesList({
  role,
  topCounterparties,
  loading = false,
}: TopCounterpartiesListProps) {
  const labels = ROLE_LABELS[role];
  const Icon = role === "sales" ? UserRound : Building2;
  const items = topCounterparties?.items ?? [];

  return (
    <DashboardCard title={labels.counterpartiesTitle} subtitle={labels.counterpartiesSubtitle}>
      {loading ? (
        <div className="flex h-48 items-center justify-center text-slate-500">
          <HydrationSafeIcon icon={Loader2} className="mr-2 h-5 w-5 animate-spin" />
          Ładowanie…
        </div>
      ) : items.length === 0 ? (
        <EmptyDataHint />
      ) : (
        <ol className="space-y-3">
          {items.map((party) => {
            const share =
              toNumber(items[0].total_net) > 0
                ? (toNumber(party.total_net) /
                    items.reduce((sum, v) => sum + toNumber(v.total_net), 0)) *
                  100
                : 0;

            return (
              <li
                key={party.counterparty_nip}
                className="flex items-center gap-4 rounded-lg border border-slate-100 p-3 dark:border-slate-800"
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-50 text-sm font-bold text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                  {party.rank}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <HydrationSafeIcon icon={Icon} className="h-4 w-4 shrink-0 text-slate-400" />
                    <p className="truncate font-medium text-slate-900 dark:text-white">
                      {party.contractor_name ?? `NIP ${party.counterparty_nip}`}
                    </p>
                  </div>
                  <p className="mt-0.5 text-xs text-slate-400">
                    NIP {party.counterparty_nip}
                    {party.ksef_number ? ` · ${party.ksef_number}` : ""}
                  </p>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.max(share, 4)}%`,
                        backgroundColor: role === "sales" ? "#059669" : "#2563eb",
                      }}
                    />
                  </div>
                </div>
                <p className="shrink-0 text-right font-semibold text-slate-900 dark:text-white">
                  {formatPln(party.total_net)}
                </p>
              </li>
            );
          })}
        </ol>
      )}
    </DashboardCard>
  );
}

"use client";

import Link from "next/link";
import { FileText, Loader2 } from "lucide-react";

import { CategorySourceIcon } from "@/components/CategorySourceIcon";
import { DashboardCard } from "@/components/DashboardCard";
import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { useApiQuery } from "@/hooks/useApiQuery";
import { formatPln } from "@/lib/api";
import { invoiceDetailUrl } from "@/lib/dashboard";
import type { InvoiceListItem, InvoiceRole } from "@/lib/types";
import { ROLE_LABELS } from "@/lib/types";

interface InvoiceListProps {
  role: InvoiceRole;
  refreshKey?: number;
  dateFrom?: string;
  dateTo?: string;
  categoryFilter?: string | null;
}

export function InvoiceList({
  role,
  refreshKey = 0,
  dateFrom,
  dateTo,
  categoryFilter = null,
}: InvoiceListProps) {
  const labels = ROLE_LABELS[role];

  const { data: items, error, loading } = useApiQuery<InvoiceListItem[]>(
    "/invoices",
    {
      role,
      limit: 50,
      date_from: dateFrom,
      date_to: dateTo,
      category: categoryFilter ?? undefined,
    },
    [role, refreshKey, dateFrom, dateTo, categoryFilter],
  );

  const subtitle = categoryFilter
    ? `Filtrowane wg kategorii: ${categoryFilter}`
    : "Kliknij fakturę, aby zobaczyć pozycje i przypisać kategorię do każdej z nich";

  return (
    <DashboardCard
      title={labels.invoicesTitle}
      subtitle={subtitle}
      className="col-span-full"
    >
      {loading ? (
        <div className="flex h-32 items-center justify-center text-slate-500">
          <HydrationSafeIcon icon={Loader2} className="mr-2 h-5 w-5 animate-spin" />
          Ładowanie…
        </div>
      ) : error ? (
        <p className="text-sm text-red-600">{error}</p>
      ) : !items?.length ? (
        <p className="text-sm text-slate-500">
          {categoryFilter
            ? "Brak faktur w wybranej kategorii w tym okresie."
            : "Brak faktur w tej kategorii. Kliknij „Pobierz z KSeF” u góry panelu."}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-700">
                <th className="pb-3 pr-4 font-medium">Nr faktury</th>
                <th className="pb-3 pr-4 font-medium">Nr KSeF</th>
                <th className="pb-3 pr-4 font-medium">Data</th>
                <th className="pb-3 pr-4 font-medium">Kontrahent</th>
                <th className="pb-3 pr-4 font-medium">Kategoria</th>
                <th className="pb-3 pr-4 font-medium">Pozycje</th>
                <th className="pb-3 pr-4 font-medium text-right">Netto</th>
                <th className="pb-3 font-medium" />
              </tr>
            </thead>
            <tbody>
              {items?.map((invoice) => {
                const counterpartyNip =
                  role === "sales" ? invoice.buyer_nip : invoice.seller_nip;
                return (
                  <tr
                    key={invoice.id}
                    className="border-b border-slate-100 dark:border-slate-800"
                  >
                    <td className="py-3 pr-4 font-medium text-slate-900 dark:text-white">
                      {invoice.invoice_number}
                    </td>
                    <td className="py-3 pr-4 text-xs text-slate-500 dark:text-slate-400">
                      {invoice.ksef_number ?? "—"}
                    </td>
                    <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">
                      {invoice.issue_date}
                    </td>
                    <td className="py-3 pr-4">
                      <div className="font-medium text-slate-900 dark:text-white">
                        {invoice.contractor_name ?? `NIP ${counterpartyNip}`}
                      </div>
                      <div className="text-xs text-slate-400">NIP {counterpartyNip}</div>
                    </td>
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-1.5">
                        <CategorySourceIcon source={invoice.primary_category_source} />
                        <span className="text-slate-600 dark:text-slate-300">
                          {invoice.primary_category_main ?? "—"}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">
                      {invoice.line_count}
                    </td>
                    <td className="py-3 pr-4 text-right font-semibold text-slate-900 dark:text-white">
                      {formatPln(invoice.total_net)}
                    </td>
                    <td className="py-3">
                      <Link
                        href={invoiceDetailUrl(invoice.id, role)}
                        className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400"
                      >
                        <HydrationSafeIcon icon={FileText} className="h-4 w-4" />
                        Pozycje
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </DashboardCard>
  );
}

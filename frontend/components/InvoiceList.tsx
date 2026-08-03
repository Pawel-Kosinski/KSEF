"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText, Loader2 } from "lucide-react";

import { DashboardCard } from "@/components/DashboardCard";
import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { apiFetch, formatPln } from "@/lib/api";
import type { InvoiceListItem, InvoiceRole } from "@/lib/types";
import { ROLE_LABELS } from "@/lib/types";

interface InvoiceListProps {
  role: InvoiceRole;
  refreshKey?: number;
  dateFrom?: string;
  dateTo?: string;
}

export function InvoiceList({
  role,
  refreshKey = 0,
  dateFrom,
  dateTo,
}: InvoiceListProps) {
  const [items, setItems] = useState<InvoiceListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const labels = ROLE_LABELS[role];

  useEffect(() => {
    setLoading(true);
    setError(null);
    apiFetch<InvoiceListItem[]>("/invoices", {
      role,
      limit: 50,
      date_from: dateFrom,
      date_to: dateTo,
    })
      .then(setItems)
      .catch((err) => setError(err instanceof Error ? err.message : "Błąd"))
      .finally(() => setLoading(false));
  }, [role, refreshKey, dateFrom, dateTo]);

  return (
    <DashboardCard
      title={labels.invoicesTitle}
      subtitle="Kliknij fakturę, aby zobaczyć pozycje i kategoryzację AI"
      className="col-span-full"
    >
      {loading ? (
        <div className="flex h-32 items-center justify-center text-slate-500">
          <HydrationSafeIcon icon={Loader2} className="mr-2 h-5 w-5 animate-spin" />
          Ładowanie…
        </div>
      ) : error ? (
        <p className="text-sm text-red-600">{error}</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-slate-500">
          Brak faktur w tej kategorii. Kliknij „Pobierz z KSeF” u góry panelu.
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
                <th className="pb-3 pr-4 font-medium">Pozycje</th>
                <th className="pb-3 pr-4 font-medium text-right">Netto</th>
                <th className="pb-3 font-medium" />
              </tr>
            </thead>
            <tbody>
              {items.map((invoice) => {
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
                    <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">
                      {invoice.line_count}
                    </td>
                    <td className="py-3 pr-4 text-right font-semibold text-slate-900 dark:text-white">
                      {formatPln(invoice.total_net)}
                    </td>
                    <td className="py-3">
                      <Link
                        href={`/invoices/${invoice.id}`}
                        className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400"
                      >
                        <HydrationSafeIcon icon={FileText} className="h-4 w-4" />
                        Szczegóły
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

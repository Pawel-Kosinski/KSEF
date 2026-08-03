"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";

import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { apiFetch, formatPln } from "@/lib/api";
import type { InvoiceDetail } from "@/lib/types";
import { ROLE_LABELS } from "@/lib/types";

export default function InvoiceDetailPage() {
  const params = useParams<{ id: string }>();
  const invoiceId = params.id;
  const [invoice, setInvoice] = useState<InvoiceDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!invoiceId) return;
    setLoading(true);
    apiFetch<InvoiceDetail>(`/invoices/${invoiceId}`)
      .then(setInvoice)
      .catch((err) => setError(err instanceof Error ? err.message : "Błąd"))
      .finally(() => setLoading(false));
  }, [invoiceId]);

  const roleLabel = invoice ? ROLE_LABELS[invoice.invoice_role] : null;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <header className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-6 py-5">
          <Link
            href="/"
            className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          >
            <HydrationSafeIcon icon={ArrowLeft} className="h-4 w-4" />
            Panel
          </Link>
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">
              Szczegóły faktury
            </h1>
            {invoice ? (
              <p className="text-sm text-slate-500">{invoice.invoice_number}</p>
            ) : null}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        {loading ? (
          <div className="flex items-center gap-2 text-slate-500">
            <HydrationSafeIcon icon={Loader2} className="h-5 w-5 animate-spin" />
            Ładowanie…
          </div>
        ) : error ? (
          <p className="text-sm text-red-600">{error}</p>
        ) : invoice ? (
          <div className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <span
                    className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      invoice.invoice_role === "sales"
                        ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                        : "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300"
                    }`}
                  >
                    {roleLabel?.badge}
                  </span>
                  <h2 className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">
                    {invoice.invoice_number}
                  </h2>
                  {invoice.ksef_number ? (
                    <p className="text-sm text-slate-500">KSeF: {invoice.ksef_number}</p>
                  ) : null}
                </div>
                <div className="text-right">
                  <p className="text-sm text-slate-500">Suma netto</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white">
                    {formatPln(invoice.total_net)}
                  </p>
                </div>
              </div>

              <dl className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <dt className="text-xs text-slate-500">Data wystawienia</dt>
                  <dd className="font-medium">{invoice.issue_date}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Data sprzedaży</dt>
                  <dd className="font-medium">{invoice.sale_date ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Kontrahent</dt>
                  <dd className="font-medium">
                    {invoice.contractor_name ?? "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">VAT</dt>
                  <dd className="font-medium">
                    {invoice.total_vat != null ? formatPln(invoice.total_vat) : "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Brutto</dt>
                  <dd className="font-medium">
                    {invoice.total_gross != null ? formatPln(invoice.total_gross) : "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Sprzedawca (NIP)</dt>
                  <dd className="font-medium">{invoice.seller_nip}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Nabywca (NIP)</dt>
                  <dd className="font-medium">{invoice.buyer_nip}</dd>
                </div>
              </dl>
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <h3 className="mb-4 text-lg font-semibold text-slate-900 dark:text-white">
                Pozycje faktury
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-700">
                      <th className="pb-3 pr-4 font-medium">#</th>
                      <th className="pb-3 pr-4 font-medium">Produkt (P_7)</th>
                      <th className="pb-3 pr-4 font-medium">Ilość</th>
                      <th className="pb-3 pr-4 font-medium">Cena netto</th>
                      <th className="pb-3 pr-4 font-medium text-right">Wartość netto</th>
                      {invoice.invoice_role === "cost" ? (
                        <>
                          <th className="pb-3 pr-4 font-medium">Kategoria AI</th>
                          <th className="pb-3 font-medium">Pewność</th>
                        </>
                      ) : null}
                    </tr>
                  </thead>
                  <tbody>
                    {invoice.lines.map((line) => (
                      <tr
                        key={line.id}
                        className="border-b border-slate-100 dark:border-slate-800"
                      >
                        <td className="py-3 pr-4">{line.line_number}</td>
                        <td className="py-3 pr-4 font-medium text-slate-900 dark:text-white">
                          {line.product_name}
                        </td>
                        <td className="py-3 pr-4">{line.quantity}</td>
                        <td className="py-3 pr-4">{formatPln(line.unit_price)}</td>
                        <td className="py-3 pr-4 text-right font-semibold">
                          {formatPln(line.line_net_value)}
                        </td>
                        {invoice.invoice_role === "cost" ? (
                          <>
                            <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">
                              {line.ai_category_main ?? "—"}
                              {line.ai_category_sub ? (
                                <span className="text-xs text-slate-400">
                                  {" "}
                                  / {line.ai_category_sub}
                                </span>
                              ) : null}
                            </td>
                            <td className="py-3">
                              {line.ai_confidence != null ? `${line.ai_confidence}%` : "—"}
                            </td>
                          </>
                        ) : null}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        ) : null}
      </main>
    </div>
  );
}

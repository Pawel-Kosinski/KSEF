"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";

import { CategoryPicker } from "@/components/CategoryPicker";
import { CategorySourceIcon } from "@/components/CategorySourceIcon";
import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { apiFetch, apiPatch, formatPln } from "@/lib/api";
import { dashboardUrl, parseInvoiceRole } from "@/lib/dashboard";
import type {
  CategoryListResponse,
  CategorySource,
  InvoiceDetail,
  InvoiceLine,
  InvoiceLineCategoryUpdateResponse,
} from "@/lib/types";
import { ROLE_LABELS } from "@/lib/types";

function getContractorNip(invoice: InvoiceDetail): string {
  return invoice.invoice_role === "sales" ? invoice.buyer_nip : invoice.seller_nip;
}

export default function InvoiceDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const invoiceId = params.id;
  const [invoice, setInvoice] = useState<InvoiceDetail | null>(null);
  const [categories, setCategories] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingLineId, setSavingLineId] = useState<string | null>(null);
  const [ruleFeedback, setRuleFeedback] = useState<string | null>(null);
  const [savingRule, setSavingRule] = useState(false);

  useEffect(() => {
    if (!invoiceId) return;
    setLoading(true);
    setError(null);
    Promise.all([
      apiFetch<InvoiceDetail>(`/invoices/${invoiceId}`),
      apiFetch<CategoryListResponse>("/categories"),
    ])
      .then(([detail, categoryResponse]) => {
        setInvoice(detail);
        setCategories(categoryResponse.categories);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Błąd"))
      .finally(() => setLoading(false));
  }, [invoiceId]);

  const applyLineCategoryUpdate = useCallback(
    (lineId: string, updated: InvoiceLineCategoryUpdateResponse) => {
      setInvoice((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          primary_category_main: updated.invoice_primary_category_main,
          primary_category_sub: updated.invoice_primary_category_sub,
          primary_category_source:
            updated.invoice_primary_category_source as CategorySource | null,
          lines: prev.lines.map((line) =>
            line.id === lineId
              ? {
                  ...line,
                  ai_category_main: updated.ai_category_main,
                  ai_category_sub: updated.ai_category_sub,
                  ai_confidence: updated.ai_confidence,
                  category_source: updated.category_source as CategorySource | null,
                }
              : line,
          ),
        };
      });

      if (updated.rule_saved && updated.contractor_nip) {
        setRuleFeedback(
          `Zapisano regułę dla NIP ${updated.contractor_nip} → ${updated.ai_category_main ?? "—"}`,
        );
      }
    },
    [],
  );

  const handleLineCategoryChange = useCallback(
    async (lineId: string, categoryMain: string) => {
      if (!invoiceId) return;
      setSavingLineId(lineId);
      setError(null);
      setRuleFeedback(null);
      try {
        const updated = await apiPatch<InvoiceLineCategoryUpdateResponse>(
          `/invoices/${invoiceId}/lines/${lineId}/category`,
          { category_main: categoryMain },
        );
        applyLineCategoryUpdate(lineId, updated);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Nie udało się zapisać kategorii");
      } finally {
        setSavingLineId(null);
      }
    },
    [applyLineCategoryUpdate, invoiceId],
  );

  const handleSaveContractorRule = useCallback(async () => {
    if (!invoice) return;

    const lineWithCategory = invoice.lines.find((line) => line.ai_category_main);
    if (!lineWithCategory?.ai_category_main) {
      setRuleFeedback("Najpierw ustaw kategorię na co najmniej jednej pozycji.");
      return;
    }

    setSavingRule(true);
    setError(null);
    setRuleFeedback(null);
    try {
      const updated = await apiPatch<InvoiceLineCategoryUpdateResponse>(
        `/invoices/${invoiceId}/lines/${lineWithCategory.id}/category`,
        {
          category_main: lineWithCategory.ai_category_main,
          learn_rule: true,
        },
      );
      applyLineCategoryUpdate(lineWithCategory.id, updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nie udało się zapisać reguły NIP");
    } finally {
      setSavingRule(false);
    }
  }, [applyLineCategoryUpdate, invoice, invoiceId]);

  const handleCategoryCreated = useCallback((name: string) => {
    setCategories((prev) => (prev.includes(name) ? prev : [...prev, name]));
  }, []);

  const roleLabel = invoice ? ROLE_LABELS[invoice.invoice_role] : null;
  const backRole = invoice
    ? invoice.invoice_role
    : parseInvoiceRole(searchParams.get("from"));
  const backLabel = ROLE_LABELS[backRole].tab;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <header className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-6 py-5">
          <Link
            href={dashboardUrl(backRole)}
            className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          >
            <HydrationSafeIcon icon={ArrowLeft} className="h-4 w-4" />
            Panel – {backLabel}
          </Link>
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">
              Pozycje faktury
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
        ) : error && !invoice ? (
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
                  <dt className="text-xs text-slate-500">Kontrahent</dt>
                  <dd className="font-medium">{invoice.contractor_name ?? "—"}</dd>
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
              <h3 className="mb-1 text-lg font-semibold text-slate-900 dark:text-white">
                Pozycje i kategorie
              </h3>
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm text-slate-500">
                  Każda pozycja ma własną kategorię. Ikona{" "}
                  <span className="text-violet-500">✦</span> = AI,{" "}
                  <span className="text-emerald-600">✓</span> = reguła lub ręczna korekta.
                </p>
                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={() => void handleSaveContractorRule()}
                    disabled={savingRule || savingLineId !== null}
                    className="rounded-lg border border-emerald-600 px-3 py-1.5 text-sm font-medium text-emerald-700 hover:bg-emerald-50 disabled:opacity-50 dark:border-emerald-500 dark:text-emerald-300 dark:hover:bg-emerald-950"
                    title="Przypisuje bieżącą kategorię do tego kontrahenta na przyszłe faktury"
                  >
                    {savingRule
                      ? "Zapisywanie…"
                      : `Zapisz regułę NIP ${getContractorNip(invoice)}`}
                  </button>
                  <Link
                    href="/settings/contractor-rules"
                    className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400"
                  >
                    Lista reguł →
                  </Link>
                </div>
              </div>

              {ruleFeedback ? (
                <p className="mb-4 text-sm text-emerald-700 dark:text-emerald-300">{ruleFeedback}</p>
              ) : null}

              {error ? (
                <p className="mb-4 text-sm text-red-600 dark:text-red-400">{error}</p>
              ) : null}

              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-700">
                      <th className="pb-3 pr-4 font-medium">#</th>
                      <th className="pb-3 pr-4 font-medium">Produkt (P_7)</th>
                      <th className="pb-3 pr-4 font-medium text-right">Wartość netto</th>
                      <th className="pb-3 pr-4 font-medium">Kategoria</th>
                      <th className="pb-3 font-medium">Pewność</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoice.lines.map((line: InvoiceLine) => (
                      <tr
                        key={line.id}
                        className="border-b border-slate-100 dark:border-slate-800"
                      >
                        <td className="py-3 pr-4">{line.line_number}</td>
                        <td className="py-3 pr-4">
                          <div className="font-medium text-slate-900 dark:text-white">
                            {line.product_name}
                          </div>
                          <div className="text-xs text-slate-400">
                            {line.quantity} × {formatPln(line.unit_price)}
                          </div>
                        </td>
                        <td className="py-3 pr-4 text-right font-semibold">
                          {formatPln(line.line_net_value)}
                        </td>
                        <td className="py-3 pr-4">
                          <LineCategoryCell
                            line={line}
                            categories={categories}
                            saving={savingLineId === line.id}
                            onChange={(category) =>
                              void handleLineCategoryChange(line.id, category)
                            }
                            onCategoryCreated={handleCategoryCreated}
                          />
                        </td>
                        <td className="py-3 text-slate-600 dark:text-slate-300">
                          {line.ai_confidence != null ? `${line.ai_confidence}%` : "—"}
                        </td>
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

function LineCategoryCell({
  line,
  categories,
  saving,
  onChange,
  onCategoryCreated,
}: {
  line: InvoiceLine;
  categories: string[];
  saving: boolean;
  onChange: (category: string) => void;
  onCategoryCreated: (name: string) => void;
}) {
  return (
    <div className="min-w-[12rem]">
      <div className="flex items-start gap-1.5">
        <div className="pt-1.5">
          <CategorySourceIcon source={line.category_source} />
        </div>
        <CategoryPicker
          categories={categories}
          value={line.ai_category_main}
          saving={saving}
          onChange={onChange}
          onCategoryCreated={onCategoryCreated}
        />
        {saving ? (
          <HydrationSafeIcon
            icon={Loader2}
            className="mt-1.5 h-3.5 w-3.5 shrink-0 animate-spin text-slate-400"
          />
        ) : null}
      </div>
      {line.ai_category_sub ? (
        <div className="mt-0.5 pl-5 text-xs text-slate-400">{line.ai_category_sub}</div>
      ) : null}
    </div>
  );
}

"use client";

import { useState } from "react";
import { Loader2, Trash2 } from "lucide-react";

import { DashboardHeader } from "@/components/DashboardHeader";
import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { SettingsNav } from "@/components/SettingsNav";
import { useApiQuery } from "@/hooks/useApiQuery";
import { apiDelete, apiPost } from "@/lib/api";
import type { ContractorRuleItem, ContractorRuleListResponse, TenantCategoryListResponse } from "@/lib/types";

export default function ContractorRulesSettingsPage() {
  const [nip, setNip] = useState("");
  const [category, setCategory] = useState("");
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const { data: rulesData, loading, error: loadError } = useApiQuery<ContractorRuleListResponse>(
    "/settings/contractor-rules",
    undefined,
    [refreshKey],
  );
  const { data: categoriesData } = useApiQuery<TenantCategoryListResponse>(
    "/settings/categories",
    undefined,
    [refreshKey],
  );

  const categories = categoriesData?.categories.map((item) => item.name) ?? [];

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await apiPost("/settings/contractor-rules", {
        contractor_nip: nip.trim(),
        category_main: category,
        contractor_name: name.trim() || undefined,
      });
      setNip("");
      setCategory("");
      setName("");
      setRefreshKey((key) => key + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nie udało się dodać reguły");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(rule: ContractorRuleItem) {
    if (!window.confirm(`Usunąć regułę dla NIP ${rule.contractor_nip}?`)) return;
    setError(null);
    try {
      await apiDelete(`/settings/contractor-rules/${rule.id}`);
      setRefreshKey((key) => key + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nie udało się usunąć reguły");
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <DashboardHeader />
      <main className="mx-auto max-w-3xl px-6 py-8">
        <h1 className="mb-2 text-2xl font-bold text-slate-900 dark:text-white">
          Reguły kontrahentów (NIP)
        </h1>
        <p className="mb-6 text-sm text-slate-500">
          Przypisz domyślną kategorię do NIP dostawcy lub klienta. Reguła ma pierwszeństwo przed AI.
        </p>
        <SettingsNav />

        <section className="mb-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-white">
            Dodaj regułę
          </h2>
          <form onSubmit={handleCreate} className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                type="text"
                value={nip}
                onChange={(event) => setNip(event.target.value)}
                placeholder="NIP (10 cyfr)"
                maxLength={10}
                required
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
              />
              <input
                type="text"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Nazwa kontrahenta (opcjonalnie)"
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
              />
            </div>
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              required
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
            >
              <option value="" disabled>
                Wybierz kategorię
              </option>
              {categories.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <button
              type="submit"
              disabled={saving || !nip.trim() || !category}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? "Zapisywanie…" : "Dodaj regułę"}
            </button>
          </form>
          {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-white">
            Aktywne reguły
          </h2>
          {loading ? (
            <div className="flex items-center gap-2 text-slate-500">
              <HydrationSafeIcon icon={Loader2} className="h-4 w-4 animate-spin" />
              Ładowanie…
            </div>
          ) : loadError ? (
            <p className="text-sm text-red-600">{loadError}</p>
          ) : !rulesData?.rules.length ? (
            <p className="text-sm text-slate-500">Brak reguł. Dodaj pierwszą powyżej.</p>
          ) : (
            <ul className="divide-y divide-slate-100 dark:divide-slate-800">
              {rulesData.rules.map((rule) => (
                <li
                  key={rule.id}
                  className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0"
                >
                  <div>
                    <p className="font-medium text-slate-900 dark:text-white">
                      NIP {rule.contractor_nip}
                      {rule.contractor_name ? ` · ${rule.contractor_name}` : ""}
                    </p>
                    <p className="text-sm text-slate-500">
                      {rule.category_main}
                      {rule.category_sub ? ` / ${rule.category_sub}` : ""}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleDelete(rule)}
                    className="rounded p-2 text-slate-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950"
                    aria-label="Usuń regułę"
                  >
                    <HydrationSafeIcon icon={Trash2} className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}

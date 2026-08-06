"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, BarChart3, Loader2, Plus, Trash2 } from "lucide-react";

import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { SettingsNav } from "@/components/SettingsNav";
import { apiDelete, apiFetch, apiPost, apiPut } from "@/lib/api";
import type { TenantCategoryItem, TenantCategoryListResponse } from "@/lib/types";

export default function CategoriesSettingsPage() {
  const [categories, setCategories] = useState<TenantCategoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [adding, setAdding] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [draftNames, setDraftNames] = useState<Record<string, string>>({});

  const loadCategories = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch<TenantCategoryListResponse>(
        "/settings/categories",
      );
      setCategories(response.categories);
      setDraftNames(
        Object.fromEntries(response.categories.map((item) => [item.id, item.name])),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nie udało się pobrać kategorii");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCategories();
  }, [loadCategories]);

  async function handleAdd(event: React.FormEvent) {
    event.preventDefault();
    const name = newCategoryName.trim();
    if (!name) return;

    setAdding(true);
    setError(null);
    try {
      const created = await apiPost<TenantCategoryItem>("/settings/categories", {
        name,
      });
      setCategories((prev) => [...prev, created]);
      setDraftNames((prev) => ({ ...prev, [created.id]: created.name }));
      setNewCategoryName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nie udało się dodać kategorii");
    } finally {
      setAdding(false);
    }
  }

  async function handleSave(categoryId: string) {
    const name = (draftNames[categoryId] ?? "").trim();
    if (!name) return;

    setSavingId(categoryId);
    setError(null);
    try {
      const updated = await apiPut<TenantCategoryItem>(
        `/settings/categories/${categoryId}`,
        { name },
      );
      setCategories((prev) =>
        prev.map((item) => (item.id === categoryId ? updated : item)),
      );
      setDraftNames((prev) => ({ ...prev, [categoryId]: updated.name }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nie udało się zapisać zmian");
    } finally {
      setSavingId(null);
    }
  }

  async function handleDelete(categoryId: string) {
    setDeletingId(categoryId);
    setError(null);
    try {
      await apiDelete(`/settings/categories/${categoryId}`);
      setCategories((prev) => prev.filter((item) => item.id !== categoryId));
      setDraftNames((prev) => {
        const next = { ...prev };
        delete next[categoryId];
        return next;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nie udało się usunąć kategorii");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <header className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white">
              <HydrationSafeIcon icon={BarChart3} className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900 dark:text-white">
                Ustawienia
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Zarządzanie kategoriami kosztów i przychodów
              </p>
            </div>
          </div>
          <Link
            href="/"
            className="flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white"
          >
            <HydrationSafeIcon icon={ArrowLeft} className="h-4 w-4" />
            Dashboard
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-8">
        <SettingsNav />

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            Kategorie finansowe
          </h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Lista używana przez AI do klasyfikacji faktur. Przy rejestracji
            generowana jest automatycznie na podstawie branży Twojej firmy.
          </p>

          {loading ? (
            <div className="mt-6 flex items-center gap-2 text-sm text-slate-500">
              <HydrationSafeIcon icon={Loader2} className="h-4 w-4 animate-spin" />
              Ładowanie kategorii…
            </div>
          ) : (
            <>
              <ul className="mt-6 space-y-3">
                {categories.map((category) => {
                  const isDirty =
                    (draftNames[category.id] ?? "").trim() !== category.name;
                  const isSaving = savingId === category.id;
                  const isDeleting = deletingId === category.id;
                  const canDelete = category.invoice_usage_count === 0;

                  return (
                    <li
                      key={category.id}
                      className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-100 p-3 dark:border-slate-800"
                    >
                      <input
                        type="text"
                        value={draftNames[category.id] ?? category.name}
                        onChange={(event) =>
                          setDraftNames((prev) => ({
                            ...prev,
                            [category.id]: event.target.value,
                          }))
                        }
                        className="min-w-[12rem] flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none ring-blue-500 focus:ring-2 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                      />
                      <span className="text-xs text-slate-400">
                        {category.invoice_usage_count > 0
                          ? `Użyta ${category.invoice_usage_count}×`
                          : "Nieużywana"}
                      </span>
                      <button
                        type="button"
                        disabled={!isDirty || isSaving}
                        onClick={() => void handleSave(category.id)}
                        className="rounded-lg bg-blue-600 px-3 py-2 text-xs font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isSaving ? "Zapisywanie…" : "Zapisz"}
                      </button>
                      <button
                        type="button"
                        disabled={!canDelete || isDeleting}
                        title={
                          canDelete
                            ? "Usuń kategorię"
                            : "Nie można usunąć kategorii przypisanej do faktur"
                        }
                        onClick={() => void handleDelete(category.id)}
                        className="inline-flex items-center gap-1 rounded-lg border border-red-200 px-3 py-2 text-xs font-medium text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-red-900 dark:text-red-400 dark:hover:bg-red-950/30"
                      >
                        {isDeleting ? (
                          <HydrationSafeIcon
                            icon={Loader2}
                            className="h-3.5 w-3.5 animate-spin"
                          />
                        ) : (
                          <HydrationSafeIcon icon={Trash2} className="h-3.5 w-3.5" />
                        )}
                        Usuń
                      </button>
                    </li>
                  );
                })}
              </ul>

              <form onSubmit={handleAdd} className="mt-6 flex flex-wrap gap-2">
                <input
                  type="text"
                  value={newCategoryName}
                  onChange={(event) => setNewCategoryName(event.target.value)}
                  placeholder="Nowa kategoria…"
                  className="min-w-[12rem] flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none ring-blue-500 focus:ring-2 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                />
                <button
                  type="submit"
                  disabled={adding || !newCategoryName.trim()}
                  className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                >
                  {adding ? (
                    <HydrationSafeIcon icon={Loader2} className="h-4 w-4 animate-spin" />
                  ) : (
                    <HydrationSafeIcon icon={Plus} className="h-4 w-4" />
                  )}
                  Dodaj kategorię
                </button>
              </form>
            </>
          )}

          {error ? (
            <p className="mt-4 text-sm text-red-600 dark:text-red-400">{error}</p>
          ) : null}
        </section>
      </main>
    </div>
  );
}

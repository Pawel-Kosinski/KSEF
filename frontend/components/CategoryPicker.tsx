"use client";

import { useState } from "react";
import { Loader2, Plus } from "lucide-react";

import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { apiPost } from "@/lib/api";
import type { TenantCategoryItem } from "@/lib/types";

const NEW_CATEGORY_VALUE = "__new__";

interface CategoryPickerProps {
  categories: string[];
  value: string | null;
  disabled?: boolean;
  saving?: boolean;
  onChange: (category: string) => void;
  onCategoryCreated: (name: string) => void;
}

export function CategoryPicker({
  categories,
  value,
  disabled = false,
  saving = false,
  onChange,
  onCategoryCreated,
}: CategoryPickerProps) {
  const [showNewForm, setShowNewForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    const name = newName.trim();
    if (!name) return;

    setCreating(true);
    setCreateError(null);
    try {
      const created = await apiPost<TenantCategoryItem>("/settings/categories", {
        name,
      });
      onCategoryCreated(created.name);
      onChange(created.name);
      setNewName("");
      setShowNewForm(false);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Nie udało się dodać kategorii");
    } finally {
      setCreating(false);
    }
  }

  function handleSelectChange(next: string) {
    if (next === NEW_CATEGORY_VALUE) {
      setShowNewForm(true);
      setCreateError(null);
      return;
    }
    setShowNewForm(false);
    onChange(next);
  }

  if (categories.length === 0 && !showNewForm) {
    return (
      <button
        type="button"
        disabled={disabled || saving}
        onClick={() => setShowNewForm(true)}
        className="text-xs font-medium text-blue-600 hover:text-blue-700 disabled:opacity-50 dark:text-blue-400"
      >
        + Dodaj pierwszą kategorię
      </button>
    );
  }

  return (
    <div className="space-y-2">
      <select
        className="w-full max-w-[16rem] rounded border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-800 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
        value={value ?? ""}
        disabled={disabled || saving || creating}
        onChange={(event) => handleSelectChange(event.target.value)}
      >
        <option value="" disabled>
          Wybierz kategorię
        </option>
        {categories.map((category) => (
          <option key={category} value={category}>
            {category}
          </option>
        ))}
        <option value={NEW_CATEGORY_VALUE}>+ Dodaj własną…</option>
      </select>

      {showNewForm ? (
        <form onSubmit={handleCreate} className="flex flex-wrap items-center gap-1.5">
          <input
            type="text"
            value={newName}
            onChange={(event) => setNewName(event.target.value)}
            placeholder="Nazwa kategorii"
            maxLength={128}
            disabled={creating}
            className="min-w-[10rem] flex-1 rounded border border-slate-300 px-2 py-1 text-xs text-slate-900 outline-none ring-blue-500 focus:ring-2 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
          />
          <button
            type="submit"
            disabled={creating || !newName.trim()}
            className="inline-flex items-center gap-1 rounded bg-emerald-600 px-2 py-1 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {creating ? (
              <HydrationSafeIcon icon={Loader2} className="h-3 w-3 animate-spin" />
            ) : (
              <HydrationSafeIcon icon={Plus} className="h-3 w-3" />
            )}
            Dodaj
          </button>
          <button
            type="button"
            disabled={creating}
            onClick={() => {
              setShowNewForm(false);
              setNewName("");
              setCreateError(null);
            }}
            className="px-1 text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
          >
            Anuluj
          </button>
        </form>
      ) : null}

      {createError ? (
        <p className="text-xs text-red-600 dark:text-red-400">{createError}</p>
      ) : null}
    </div>
  );
}

"use client";

import { useState } from "react";
import { Download, Loader2 } from "lucide-react";

import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { ApiError, apiPost } from "@/lib/api";
import {
  DATE_RANGE_PRESETS,
  isValidDateRange,
  splitDateRange,
  SYNC_CHUNK_DAYS,
  type DateRange,
} from "@/lib/dateRange";
import type { KsefSyncResponse } from "@/lib/types";

function parseApiErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    try {
      const parsed = JSON.parse(err.message) as { detail?: string };
      if (parsed.detail) return parsed.detail;
    } catch {
      // nie-JSON body
    }
    return err.message;
  }
  if (err instanceof Error) return err.message;
  return "Błąd synchronizacji";
}

interface DashboardPeriodBarProps {
  range: DateRange;
  onRangeChange: (range: DateRange) => void;
  onSyncComplete?: () => void;
  ksefConfigured?: boolean;
}

export function DashboardPeriodBar({
  range,
  onRangeChange,
  onSyncComplete,
  ksefConfigured = true,
}: DashboardPeriodBarProps) {
  const [activePreset, setActivePreset] = useState<string | null>("current-month");
  const [progress, setProgress] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isError, setIsError] = useState(false);
  const [syncing, setSyncing] = useState(false);

  function applyPreset(id: string, presetRange: DateRange) {
    setActivePreset(id);
    onRangeChange(presetRange);
  }

  function handleDateChange(field: "dateFrom" | "dateTo", value: string) {
    setActivePreset(null);
    onRangeChange({ ...range, [field]: value });
  }

  async function handleSync() {
    if (!isValidDateRange(range)) {
      setIsError(true);
      setMessage("Data końcowa musi być nie wcześniejsza niż początkowa.");
      return;
    }

    const chunks = splitDateRange(range.dateFrom, range.dateTo, SYNC_CHUNK_DAYS);

    setSyncing(true);
    setMessage(null);
    setIsError(false);

    let totalProcessed = 0;
    let totalFailed = 0;
    let truncatedPeriods = 0;

    try {
      for (let index = 0; index < chunks.length; index += 1) {
        const chunk = chunks[index];
        setProgress(
          `Paczka ${index + 1}/${chunks.length}: ${chunk.dateFrom}–${chunk.dateTo} (koszty + sprzedaż)`,
        );
        const result = await apiPost<KsefSyncResponse>("/ksef/sync-period", {
          date_from: chunk.dateFrom,
          date_to: chunk.dateTo,
        });
        totalProcessed += result.invoices_processed;
        totalFailed += result.invoices_failed;
        truncatedPeriods += result.truncated_periods;
      }

      let summary = `Zaimportowano ${totalProcessed} faktur z okresu ${range.dateFrom}–${range.dateTo}`;
      if (totalFailed > 0) {
        summary += ` · błędy ETL: ${totalFailed}`;
      }
      if (truncatedPeriods > 0) {
        summary += ` · ${truncatedPeriods} dni z obciętą paczką (za dużo faktur/dzień)`;
      }

      setMessage(summary);
      onSyncComplete?.();
      window.setTimeout(() => setMessage(null), 10000);
    } catch (err) {
      setIsError(true);
      setMessage(parseApiErrorMessage(err));
    } finally {
      setSyncing(false);
      setProgress(null);
    }
  }

  const rangeInvalid = !isValidDateRange(range);

  return (
    <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-3">
          <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
            Okres analizy i pobierania z KSeF
          </p>
          <div className="flex flex-wrap gap-2">
            {DATE_RANGE_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => applyPreset(preset.id, preset.range())}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  activePreset === preset.id
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
              Od
              <input
                type="date"
                value={range.dateFrom}
                onChange={(e) => handleDateChange("dateFrom", e.target.value)}
                className="rounded-md border border-slate-200 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-800"
              />
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
              Do
              <input
                type="date"
                value={range.dateTo}
                onChange={(e) => handleDateChange("dateTo", e.target.value)}
                className="rounded-md border border-slate-200 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-800"
              />
            </label>
          </div>
          {rangeInvalid ? (
            <p className="text-xs text-red-600">Nieprawidłowy zakres dat.</p>
          ) : (
            <p className="text-xs text-slate-400">
              Sync w paczkach {SYNC_CHUNK_DAYS}-dniowych · pierwsze pobranie może trwać kilka
              minut (KSeF + kategoryzacja)
            </p>
          )}
        </div>

        <div className="flex flex-col items-end gap-2">
          <button
            type="button"
            onClick={handleSync}
            disabled={syncing || rangeInvalid || !ksefConfigured}
            title={
              !ksefConfigured
                ? "Skonfiguruj token KSeF w Ustawieniach"
                : undefined
            }
            className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
          >
            {syncing ? (
              <HydrationSafeIcon icon={Loader2} className="h-4 w-4 animate-spin" />
            ) : (
              <HydrationSafeIcon icon={Download} className="h-4 w-4" />
            )}
            {syncing ? "Pobieranie…" : "Pobierz z KSeF"}
          </button>
          {syncing && !progress ? (
            <p className="max-w-xs text-right text-xs text-slate-500">
              Łączenie z KSeF…
            </p>
          ) : null}
          {progress ? (
            <p className="max-w-xs text-right text-xs text-slate-500">{progress}</p>
          ) : null}
          {message ? (
            <p
              className={`max-w-sm text-right text-xs ${isError ? "text-red-600" : "text-emerald-600"}`}
            >
              {message}
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

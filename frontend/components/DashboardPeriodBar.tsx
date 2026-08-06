"use client";

import { useRef, useState } from "react";
import { Download, Loader2, Square } from "lucide-react";

import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { ApiError, apiFetch, apiPost } from "@/lib/api";
import {
  DATE_RANGE_PRESETS,
  isValidDateRange,
  splitDateRange,
  SYNC_CHUNK_DAYS,
  type DateRange,
} from "@/lib/dateRange";
import type { KsefSyncJobCreatedResponse, KsefSyncJobResponse } from "@/lib/types";

const POLL_INTERVAL_MS = 2000;
const TERMINAL_JOB_STATUSES = new Set(["completed", "failed", "cancelled"]);

class SyncCancelledError extends Error {
  constructor() {
    super("Synchronizacja przerwana");
    this.name = "SyncCancelledError";
  }
}

async function pollSyncJob(
  jobId: string,
  shouldCancel: () => boolean,
): Promise<KsefSyncJobResponse> {
  for (;;) {
    if (shouldCancel()) {
      throw new SyncCancelledError();
    }

    const job = await apiFetch<KsefSyncJobResponse>(`/ksef/sync-jobs/${jobId}`);
    if (TERMINAL_JOB_STATUSES.has(job.status)) {
      return job;
    }

    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }
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
  const [isInfo, setIsInfo] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const cancelRequestedRef = useRef(false);
  const currentJobIdRef = useRef<string | null>(null);

  function applyPreset(id: string, presetRange: DateRange) {
    setActivePreset(id);
    onRangeChange(presetRange);
  }

  function handleDateChange(field: "dateFrom" | "dateTo", value: string) {
    setActivePreset(null);
    onRangeChange({ ...range, [field]: value });
  }

  async function handleCancelSync() {
    cancelRequestedRef.current = true;
    const jobId = currentJobIdRef.current;

    if (jobId) {
      try {
        await apiPost<KsefSyncJobResponse>(`/ksef/sync-jobs/${jobId}/cancel`, {});
      } catch {
        // UI i tak przerywa polling; backend mógł już zakończyć zadanie.
      }
    }

    setSyncing(false);
    setProgress(null);
    setIsError(false);
    setIsInfo(true);
    setMessage("Synchronizacja przerwana.");
    currentJobIdRef.current = null;
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
    setIsInfo(false);
    cancelRequestedRef.current = false;
    currentJobIdRef.current = null;

    let totalProcessed = 0;
    let totalFailed = 0;
    let truncatedPeriods = 0;

    try {
      for (let index = 0; index < chunks.length; index += 1) {
        if (cancelRequestedRef.current) {
          throw new SyncCancelledError();
        }

        const chunk = chunks[index];
        setProgress(
          `Paczka ${index + 1}/${chunks.length}: ${chunk.dateFrom}–${chunk.dateTo} (koszty + sprzedaż)`,
        );
        const created = await apiPost<KsefSyncJobCreatedResponse>("/ksef/sync-period", {
          date_from: chunk.dateFrom,
          date_to: chunk.dateTo,
        });
        currentJobIdRef.current = created.job_id;
        const job = await pollSyncJob(created.job_id, () => cancelRequestedRef.current);

        if (job.status === "cancelled") {
          throw new SyncCancelledError();
        }
        if (job.status === "failed") {
          throw new ApiError(job.error_message ?? "Synchronizacja nie powiodła się", 502);
        }

        const result = job.result;
        if (result) {
          totalProcessed += result.invoices_processed;
          totalFailed += result.invoices_failed;
          truncatedPeriods += result.truncated_periods;
        }
        currentJobIdRef.current = null;
      }

      let summary = `Zaimportowano ${totalProcessed} faktur z okresu ${range.dateFrom}–${range.dateTo}`;
      if (totalFailed > 0) {
        summary += ` · błędy ETL: ${totalFailed}`;
      }
      if (truncatedPeriods > 0) {
        summary += ` · ${truncatedPeriods} dni z obciętą paczką (za dużo faktur/dzień)`;
      }

      setMessage(summary);
      setIsInfo(false);
      onSyncComplete?.();
      window.setTimeout(() => setMessage(null), 10000);
    } catch (err) {
      if (err instanceof SyncCancelledError) {
        setIsError(false);
        setIsInfo(true);
        setMessage("Synchronizacja przerwana.");
      } else {
        setIsError(true);
        setIsInfo(false);
        setMessage(
          err instanceof ApiError
            ? err.message
            : err instanceof Error
              ? err.message
              : "Błąd synchronizacji",
        );
      }
    } finally {
      setSyncing(false);
      setProgress(null);
      currentJobIdRef.current = null;
      cancelRequestedRef.current = false;
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
              Sync w tle (paczki {SYNC_CHUNK_DAYS}-dniowe) · pierwsze pobranie może trwać kilka
              minut
            </p>
          )}
        </div>

        <div className="flex flex-col items-end gap-2">
          <div className="flex flex-wrap items-center justify-end gap-2">
            {syncing ? (
              <button
                type="button"
                onClick={() => void handleCancelSync()}
                className="inline-flex items-center gap-2 rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 transition-colors hover:bg-red-50 dark:border-red-800 dark:text-red-300 dark:hover:bg-red-950"
              >
                <HydrationSafeIcon icon={Square} className="h-4 w-4" />
                Przerwij
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => void handleSync()}
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
          </div>
          {progress ? (
            <p className="max-w-xs text-right text-xs text-slate-500">{progress}</p>
          ) : null}
          {message ? (
            <p
              className={`max-w-sm text-right text-xs ${
                isError
                  ? "text-red-600"
                  : isInfo
                    ? "text-slate-500"
                    : "text-emerald-600"
              }`}
            >
              {message}
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

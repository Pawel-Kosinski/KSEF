"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, BarChart3, CheckCircle2, Loader2 } from "lucide-react";

import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { parseApiErrorMessage } from "@/lib/apiErrors";
import { apiFetch } from "@/lib/api";
import type { KsefSettingsStatus } from "@/lib/types";

export default function SettingsPage() {
  const router = useRouter();
  const [ksefToken, setKsefToken] = useState("");
  const [isConfigured, setIsConfigured] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<KsefSettingsStatus>("/settings/ksef")
      .then((status) => setIsConfigured(status.is_configured))
      .catch(() => setIsConfigured(false))
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch("/api/v1/settings/ksef", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({ ksef_token: ksefToken }),
      });

      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        setError(
          parseApiErrorMessage(payload, response.status, "Nie udało się zapisać tokena"),
        );
        return;
      }

      setIsConfigured(true);
      setKsefToken("");
      setSuccess("Token KSeF został zapisany. Możesz teraz pobrać faktury z dashboardu.");
      router.refresh();
    } catch {
      setError("Błąd połączenia z serwerem");
    } finally {
      setSaving(false);
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
                Konfiguracja integracji z KSeF
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
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            Połączenie z KSeF
          </h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Wklej token autoryzacyjny wygenerowany w MCU KSeF. Token jest
            szyfrowany i przechowywany wyłącznie dla Twojej firmy.
          </p>

          {loading ? (
            <div className="mt-6 flex items-center gap-2 text-sm text-slate-500">
              <HydrationSafeIcon icon={Loader2} className="h-4 w-4 animate-spin" />
              Ładowanie statusu…
            </div>
          ) : (
            <div className="mt-4">
              {isConfigured ? (
                <p className="mb-4 flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
                  <HydrationSafeIcon icon={CheckCircle2} className="h-4 w-4" />
                  Token KSeF jest skonfigurowany. Wpisz nowy token, aby go zastąpić.
                </p>
              ) : (
                <p className="mb-4 text-sm text-amber-700 dark:text-amber-300">
                  Brak zapisanego tokena – synchronizacja faktur jest zablokowana.
                </p>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label
                    htmlFor="ksefToken"
                    className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300"
                  >
                    Token autoryzacyjny KSeF
                  </label>
                  <input
                    id="ksefToken"
                    type="password"
                    required
                    autoComplete="off"
                    value={ksefToken}
                    onChange={(e) => setKsefToken(e.target.value)}
                    placeholder="Wklej token z MCU KSeF"
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm text-slate-900 outline-none ring-blue-500 focus:ring-2 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                  />
                </div>

                {error ? (
                  <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                ) : null}
                {success ? (
                  <p className="text-sm text-emerald-600 dark:text-emerald-400">{success}</p>
                ) : null}

                <button
                  type="submit"
                  disabled={saving || !ksefToken.trim()}
                  className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {saving ? (
                    <HydrationSafeIcon icon={Loader2} className="h-4 w-4 animate-spin" />
                  ) : null}
                  Zapisz
                </button>
              </form>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

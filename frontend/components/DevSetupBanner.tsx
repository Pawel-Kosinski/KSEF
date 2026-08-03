"use client";

import { AlertCircle } from "lucide-react";

import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";

function parseTenantId(token: string): string | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    const json = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    return typeof json.tenant_id === "string" ? json.tenant_id : null;
  } catch {
    return null;
  }
}

export function DevSetupBanner() {
  const token = process.env.NEXT_PUBLIC_DEV_TOKEN ?? "";
  const hasToken = token.length > 0 && token !== "your-jwt-token-here";
  const tenantId = hasToken ? parseTenantId(token) : null;

  if (!hasToken) {
    return (
      <div className="mx-auto mb-6 max-w-7xl rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        <p className="flex items-center gap-2 font-medium">
          <HydrationSafeIcon icon={AlertCircle} className="h-4 w-4" />
          Brak tokena JWT
        </p>
        <p className="mt-1 text-amber-800">
          Utwórz plik <code className="rounded bg-amber-100 px-1">.env.local</code>{" "}
          i ustaw <code className="rounded bg-amber-100 px-1">NEXT_PUBLIC_DEV_TOKEN</code>.
          Wygeneruj token:{" "}
          <code className="rounded bg-amber-100 px-1">
            python scripts/create_dev_token.py
          </code>
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto mb-6 max-w-7xl rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
      <p>
        Tryb deweloperski · tenant_id:{" "}
        <code className="rounded bg-slate-100 px-1 text-xs dark:bg-slate-800">
          {tenantId ?? "nieznany"}
        </code>
      </p>
      <p className="mt-1 text-slate-500">
        Pusty dashboard? Załaduj dane testowe dla tego tenanta:{" "}
        <code className="rounded bg-slate-100 px-1 text-xs dark:bg-slate-800">
          python scripts/test_etl_pipeline.py
        </code>{" "}
        lub wygeneruj token z istniejącym UUID / NIP:{" "}
        <code className="rounded bg-slate-100 px-1 text-xs dark:bg-slate-800">
          python scripts/create_dev_token.py --nip 1186638420
        </code>
        {" · faktury z KSeF: wybierz okres i kliknij "}
        <strong>Pobierz z KSeF</strong>
      </p>
    </div>
  );
}

export function EmptyDataHint() {
  return (
    <div className="flex h-48 flex-col items-center justify-center text-center text-sm text-slate-500">
      <p>Brak danych do wyświetlenia.</p>
      <p className="mt-2 max-w-xs text-xs text-slate-400">
        Uruchom potok ETL lub sprawdź, czy token JWT wskazuje na tenanta z
        fakturami w bazie.
      </p>
    </div>
  );
}

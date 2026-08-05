"use client";

import Link from "next/link";
import { AlertTriangle } from "lucide-react";

import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";

export function KsefSetupBanner() {
  return (
    <div className="mb-6 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-100">
      <p className="flex items-center gap-2 font-medium">
        <HydrationSafeIcon icon={AlertTriangle} className="h-4 w-4 shrink-0" />
        Brak połączenia z KSeF
      </p>
      <p className="mt-1 text-amber-800 dark:text-amber-200">
        Aby pobrać dane, musisz najpierw skonfigurować połączenie z KSeF w{" "}
        <Link href="/settings" className="font-semibold underline hover:no-underline">
          Ustawieniach
        </Link>
        .
      </p>
    </div>
  );
}

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { BarChart3, LogOut, Settings } from "lucide-react";

import { ChatToggleButton } from "@/components/ChatPanel";
import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";

interface DashboardHeaderProps {
  chatOpen?: boolean;
  onChatToggle?: () => void;
}

export function DashboardHeader({ chatOpen, onChatToggle }: DashboardHeaderProps = {}) {
  const router = useRouter();

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <header className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-6 py-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white">
            <HydrationSafeIcon icon={BarChart3} className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">
              Wirtualny CFO – Panel Główny
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Analityka kosztów z faktur KSeF
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onChatToggle ? (
            <ChatToggleButton open={chatOpen ?? false} onClick={onChatToggle} />
          ) : null}
          <Link
            href="/settings"
            className="flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <HydrationSafeIcon icon={Settings} className="h-4 w-4" />
            Ustawienia
          </Link>
          <button
          type="button"
          onClick={handleLogout}
          className="flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          <HydrationSafeIcon icon={LogOut} className="h-4 w-4" />
          Wyloguj
        </button>
        </div>
      </div>
    </header>
  );
}

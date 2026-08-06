"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Check, Copy, Loader2 } from "lucide-react";

import { DashboardHeader } from "@/components/DashboardHeader";
import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { SettingsNav } from "@/components/SettingsNav";
import { isAdminUser, useCurrentUser } from "@/hooks/useCurrentUser";
import { useApiQuery } from "@/hooks/useApiQuery";
import type { TeamResponse } from "@/lib/types";

function formatRole(role: string): string {
  return role === "admin" ? "Administrator" : "Użytkownik";
}

export default function TeamSettingsPage() {
  const router = useRouter();
  const { data: user, loading: userLoading } = useCurrentUser();
  const isAdmin = isAdminUser(user);
  const [copied, setCopied] = useState(false);
  const { data, loading, error } = useApiQuery<TeamResponse>(
    "/settings/team",
    undefined,
    [],
    { enabled: isAdmin },
  );

  useEffect(() => {
    if (!userLoading && user && !isAdmin) {
      router.replace("/settings");
    }
  }, [user, userLoading, isAdmin, router]);

  const inviteUrl = useMemo(() => {
    if (!data?.invite_token || typeof window === "undefined") return "";
    return `${window.location.origin}/register?invite=${encodeURIComponent(data.invite_token)}`;
  }, [data?.invite_token]);

  async function handleCopy() {
    if (!inviteUrl) return;
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  if (userLoading || (user && !isAdmin)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-950">
        <HydrationSafeIcon icon={Loader2} className="h-6 w-6 animate-spin text-slate-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <DashboardHeader />
      <main className="mx-auto max-w-3xl px-6 py-8">
        <h1 className="mb-2 text-2xl font-bold text-slate-900 dark:text-white">Zespół</h1>
        <p className="mb-6 text-sm text-slate-500">
          Zaproś współpracowników do firmy. Każdy użytkownik loguje się własnym kontem.
        </p>
        <SettingsNav />

        <section className="mb-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">
            Link z zaproszeniem dla Twojego zespołu
          </h2>
          <p className="mb-4 text-sm text-slate-500">
            Udostępnij link osobom z Twojej firmy. Po rejestracji trafią do tego samego
            konta organizacji z rolą użytkownika.
          </p>

          {loading ? (
            <div className="flex items-center gap-2 text-slate-500">
              <HydrationSafeIcon icon={Loader2} className="h-4 w-4 animate-spin" />
              Ładowanie…
            </div>
          ) : error ? (
            <p className="text-sm text-red-600">{error}</p>
          ) : (
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <input
                readOnly
                value={inviteUrl}
                className="w-full flex-1 rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 font-mono text-xs text-slate-800 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
              />
              <button
                type="button"
                onClick={() => void handleCopy()}
                disabled={!inviteUrl}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                <HydrationSafeIcon icon={copied ? Check : Copy} className="h-4 w-4" />
                {copied ? "Skopiowano" : "Kopiuj"}
              </button>
            </div>
          )}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-white">
            Użytkownicy w firmie
          </h2>

          {loading ? (
            <div className="flex items-center gap-2 text-slate-500">
              <HydrationSafeIcon icon={Loader2} className="h-4 w-4 animate-spin" />
              Ładowanie…
            </div>
          ) : error ? (
            <p className="text-sm text-red-600">{error}</p>
          ) : !data?.members.length ? (
            <p className="text-sm text-slate-500">Brak użytkowników.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-700">
                    <th className="pb-3 pr-4 font-medium">E-mail</th>
                    <th className="pb-3 pr-4 font-medium">Rola</th>
                    <th className="pb-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.members.map((member) => (
                    <tr
                      key={member.id}
                      className="border-b border-slate-100 dark:border-slate-800"
                    >
                      <td className="py-3 pr-4 font-medium text-slate-900 dark:text-white">
                        {member.email}
                      </td>
                      <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">
                        {formatRole(member.role)}
                      </td>
                      <td className="py-3 text-slate-600 dark:text-slate-300">
                        {member.is_active ? "Aktywny" : "Nieaktywny"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

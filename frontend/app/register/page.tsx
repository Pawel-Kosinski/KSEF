"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { BarChart3, Loader2 } from "lucide-react";

import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { parseApiErrorMessage } from "@/lib/apiErrors";

type RegisterMode = "company" | "invite";

function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const inviteFromUrl = searchParams.get("invite")?.trim() ?? "";

  const [mode, setMode] = useState<RegisterMode>(inviteFromUrl ? "invite" : "company");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [industry, setIndustry] = useState("");
  const [nip, setNip] = useState("");
  const [inviteToken, setInviteToken] = useState(inviteFromUrl);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (inviteFromUrl) {
      setMode("invite");
      setInviteToken(inviteFromUrl);
    }
  }, [inviteFromUrl]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    const payload =
      mode === "invite"
        ? {
            email,
            password,
            invite_token: inviteToken.trim(),
          }
        : {
            email,
            password,
            company_name: companyName,
            industry: industry.trim(),
            nip: nip.replace(/\D/g, ""),
          };

    try {
      const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const responsePayload = await response.json().catch(() => null);
        setError(
          parseApiErrorMessage(responsePayload, response.status, "Rejestracja nie powiodła się"),
        );
        return;
      }

      router.push("/");
      router.refresh();
    } catch {
      setError("Błąd połączenia z serwerem");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white">
          <HydrationSafeIcon icon={BarChart3} className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-white">Rejestracja</h1>
          <p className="text-sm text-slate-500">
            {mode === "company"
              ? "Załóż konto firmowe"
              : "Dołącz do zespołu kodem zaproszenia"}
          </p>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-2 rounded-lg bg-slate-100 p-1 dark:bg-slate-800">
        <button
          type="button"
          onClick={() => setMode("company")}
          className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
            mode === "company"
              ? "bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-white"
              : "text-slate-600 dark:text-slate-300"
          }`}
        >
          Rejestruję nową firmę
        </button>
        <button
          type="button"
          onClick={() => setMode("invite")}
          className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
            mode === "invite"
              ? "bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-white"
              : "text-slate-600 dark:text-slate-300"
          }`}
        >
          Mam kod zaproszenia
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {mode === "company" ? (
          <>
            <div>
              <label
                htmlFor="companyName"
                className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300"
              >
                Nazwa firmy
              </label>
              <input
                id="companyName"
                type="text"
                required
                minLength={2}
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none ring-blue-500 focus:ring-2 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
            </div>

            <div>
              <label
                htmlFor="industry"
                className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300"
              >
                Branża / opis działalności
              </label>
              <textarea
                id="industry"
                required
                minLength={3}
                rows={3}
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                placeholder="np. Software house tworzący aplikacje SaaS dla logistyki"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none ring-blue-500 focus:ring-2 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
            </div>

            <div>
              <label
                htmlFor="nip"
                className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300"
              >
                NIP (10 cyfr)
              </label>
              <input
                id="nip"
                type="text"
                required
                pattern="\d{10}"
                maxLength={10}
                inputMode="numeric"
                value={nip}
                onChange={(e) => setNip(e.target.value.replace(/\D/g, ""))}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none ring-blue-500 focus:ring-2 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
            </div>
          </>
        ) : (
          <div>
            <label
              htmlFor="inviteToken"
              className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300"
            >
              Kod zaproszenia
            </label>
            <input
              id="inviteToken"
              type="text"
              required
              minLength={36}
              maxLength={36}
              value={inviteToken}
              onChange={(e) => setInviteToken(e.target.value.trim())}
              placeholder="Wklej kod z linku zaproszenia"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm text-slate-900 outline-none ring-blue-500 focus:ring-2 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            />
          </div>
        )}

        <div>
          <label
            htmlFor="email"
            className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300"
          >
            E-mail
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none ring-blue-500 focus:ring-2 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
          />
        </div>

        <div>
          <label
            htmlFor="password"
            className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300"
          >
            Hasło (min. 8 znaków)
          </label>
          <input
            id="password"
            type="password"
            required
            autoComplete="new-password"
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 outline-none ring-blue-500 focus:ring-2 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
          />
        </div>

        {error ? <p className="text-sm text-red-600 dark:text-red-400">{error}</p> : null}

        <button
          type="submit"
          disabled={loading}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 font-medium text-white transition hover:bg-blue-700 disabled:opacity-60"
        >
          {loading ? (
            <HydrationSafeIcon icon={Loader2} className="h-4 w-4 animate-spin" />
          ) : null}
          {mode === "company" ? "Utwórz firmę i konto" : "Dołącz do zespołu"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        Masz już konto?{" "}
        <Link href="/login" className="font-medium text-blue-600 hover:underline">
          Zaloguj się
        </Link>
      </p>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 dark:bg-slate-950">
      <Suspense
        fallback={
          <div className="flex items-center gap-2 text-slate-500">
            <HydrationSafeIcon icon={Loader2} className="h-5 w-5 animate-spin" />
            Ładowanie…
          </div>
        }
      >
        <RegisterForm />
      </Suspense>
    </div>
  );
}

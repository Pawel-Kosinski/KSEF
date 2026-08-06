"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { isAdminUser, useCurrentUser } from "@/hooks/useCurrentUser";

const LINKS = [
  { href: "/settings", label: "KSeF" },
  { href: "/settings/team", label: "Zespół", adminOnly: true },
  { href: "/settings/categories", label: "Kategorie" },
  { href: "/settings/contractor-rules", label: "Reguły NIP" },
] as const;

export function SettingsNav() {
  const pathname = usePathname();
  const { data: user } = useCurrentUser();
  const isAdmin = isAdminUser(user);

  const visibleLinks = LINKS.filter((link) => !("adminOnly" in link && link.adminOnly) || isAdmin);

  return (
    <nav className="mb-6 flex gap-2 border-b border-slate-200 pb-3 dark:border-slate-700">
      {visibleLinks.map((link) => {
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={
              active
                ? "rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white"
                : "rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            }
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}

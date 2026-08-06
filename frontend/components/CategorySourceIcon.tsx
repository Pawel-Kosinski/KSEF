"use client";

import { Check, Sparkles } from "lucide-react";

import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import type { CategorySource } from "@/lib/types";

export function CategorySourceIcon({ source }: { source: CategorySource | null }) {
  if (source === "ai") {
    return (
      <span title="Kategoria z AI">
        <HydrationSafeIcon
          icon={Sparkles}
          className="h-3.5 w-3.5 shrink-0 text-violet-500"
        />
      </span>
    );
  }
  if (source === "rule" || source === "user") {
    return (
      <span
        title={
          source === "rule"
            ? "Kategoria z reguły NIP"
            : "Kategoria ustawiona ręcznie"
        }
      >
        <HydrationSafeIcon
          icon={Check}
          className="h-3.5 w-3.5 shrink-0 text-emerald-600"
        />
      </span>
    );
  }
  return null;
}

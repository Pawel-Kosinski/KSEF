"use client";

import type { InvoiceRole } from "@/lib/types";
import { ROLE_LABELS } from "@/lib/types";

interface DashboardRoleTabsProps {
  role: InvoiceRole;
  onChange: (role: InvoiceRole) => void;
}

export function DashboardRoleTabs({ role, onChange }: DashboardRoleTabsProps) {
  const roles: InvoiceRole[] = ["cost", "sales"];

  return (
    <div
      role="tablist"
      aria-label="Widok dashboardu"
      className="flex gap-2"
    >
      {roles.map((item) => {
        const active = item === role;
        return (
          <button
            key={item}
            type="button"
            role="tab"
            aria-selected={active}
            id={`dashboard-tab-${item}`}
            aria-controls={`dashboard-panel-${item}`}
            onClick={() => onChange(item)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              active
                ? item === "cost"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "bg-emerald-600 text-white shadow-sm"
                : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50 dark:bg-slate-900 dark:text-slate-300 dark:ring-slate-700 dark:hover:bg-slate-800"
            }`}
          >
            {ROLE_LABELS[item].tab}
          </button>
        );
      })}
    </div>
  );
}

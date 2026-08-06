import type { InvoiceRole } from "@/lib/types";

export function parseInvoiceRole(value: string | null | undefined): InvoiceRole {
  return value === "sales" ? "sales" : "cost";
}

export function dashboardUrl(role: InvoiceRole = "cost"): string {
  return `/?role=${role}`;
}

export function invoiceDetailUrl(invoiceId: string, fromRole: InvoiceRole): string {
  return `/invoices/${invoiceId}?from=${fromRole}`;
}

export type InvoiceRole = "cost" | "sales";

export type KsefSubjectType = "Subject1" | "Subject2";

export interface KsefSyncResponse {
  export_reference_number: string;
  date_from: string;
  date_to: string;
  package_invoice_count: number;
  invoices_processed: number;
  invoices_failed: number;
  lines_processed: number;
  is_truncated: boolean;
  chunks_processed: number;
  truncated_periods: number;
  errors: string[];
}

export interface CostStructureItem {
  category: string;
  total_net: number | string;
}

export interface CostStructureResponse {
  items: CostStructureItem[];
  total_net: number | string;
  date_from: string | null;
  date_to: string | null;
  role?: string | null;
}

export interface TrendItem {
  period: string;
  total_net: number | string;
}

export interface TrendResponse {
  items: TrendItem[];
  total_net: number | string;
  granularity: "day" | "week" | "month";
  date_from: string | null;
  date_to: string | null;
  role?: string | null;
}

export interface SummaryResponse {
  total_net: number | string;
  total_vat: number | string;
  total_gross: number | string;
  date_from: string | null;
  date_to: string | null;
  role?: string | null;
}

export interface TopCounterpartyItem {
  counterparty_nip: string;
  contractor_name: string | null;
  ksef_number: string | null;
  total_net: number | string;
  rank: number;
}

export interface TopCounterpartiesResponse {
  items: TopCounterpartyItem[];
  limit: number;
  date_from: string | null;
  date_to: string | null;
  role?: string | null;
}

export interface InvoiceListItem {
  id: string;
  ksef_number: string | null;
  invoice_number: string;
  issue_date: string;
  sale_date: string | null;
  seller_nip: string;
  buyer_nip: string;
  contractor_name: string | null;
  invoice_role: InvoiceRole;
  currency_code: string;
  total_net: number | string;
  total_vat: number | string | null;
  total_gross: number | string | null;
  line_count: number;
}

export interface InvoiceLine {
  id: string;
  line_number: number;
  product_name: string;
  quantity: number | string;
  unit_price: number | string;
  line_net_value: number | string;
  ai_category_main: string | null;
  ai_category_sub: string | null;
  ai_confidence: number | null;
}

export interface InvoiceDetail {
  id: string;
  ksef_number: string | null;
  invoice_number: string;
  issue_date: string;
  sale_date: string | null;
  seller_nip: string;
  buyer_nip: string;
  contractor_name: string | null;
  invoice_role: InvoiceRole;
  currency_code: string;
  total_net: number | string;
  total_vat: number | string | null;
  total_gross: number | string | null;
  lines: InvoiceLine[];
}

export const ROLE_LABELS: Record<
  InvoiceRole,
  {
    tab: string;
    trendTitle: string;
    trendSubtitle: string;
    structureTitle: string;
    structureSubtitle: string;
    counterpartiesTitle: string;
    counterpartiesSubtitle: string;
    invoicesTitle: string;
    barColor: string;
    badge: string;
  }
> = {
  cost: {
    tab: "Koszty",
    trendTitle: "Trend wydatków",
    trendSubtitle: "Suma kosztów netto – granulacja zależna od wybranego okresu",
    structureTitle: "Struktura kosztów",
    structureSubtitle: "Rozkład wydatków netto wg kategorii AI",
    counterpartiesTitle: "Top dostawcy",
    counterpartiesSubtitle: "Ranking dostawców wg wartości netto (Top 5)",
    invoicesTitle: "Faktury kosztowe",
    barColor: "#2563eb",
    badge: "Koszt",
  },
  sales: {
    tab: "Sprzedaż",
    trendTitle: "Trend przychodów",
    trendSubtitle: "Suma przychodów netto – granulacja zależna od wybranego okresu",
    structureTitle: "Struktura sprzedaży",
    structureSubtitle: "Rozkład przychodów netto wg kategorii AI",
    counterpartiesTitle: "Top klienci",
    counterpartiesSubtitle: "Ranking nabywców wg wartości netto (Top 5)",
    invoicesTitle: "Faktury sprzedaży",
    barColor: "#059669",
    badge: "Sprzedaż",
  },
};

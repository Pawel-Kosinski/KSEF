export type InvoiceRole = "cost" | "sales";

export type CategorySource = "ai" | "rule" | "user" | "fallback";

export interface TenantCategoryItem {
  id: string;
  name: string;
  sort_order: number;
  invoice_usage_count: number;
}

export interface TenantCategoryListResponse {
  categories: TenantCategoryItem[];
}

export interface CategoryListResponse {
  categories: string[];
}

export interface InvoiceLineCategoryUpdateResponse {
  id: string;
  line_number: number;
  ai_category_main: string | null;
  ai_category_sub: string | null;
  ai_confidence: number | null;
  category_source: CategorySource | null;
  invoice_primary_category_main: string | null;
  invoice_primary_category_sub: string | null;
  invoice_primary_category_source: CategorySource | null;
  rule_saved?: boolean;
  contractor_nip?: string | null;
}

export interface InvoiceCategoryUpdateResponse {
  id: string;
  primary_category_main: string | null;
  primary_category_sub: string | null;
  primary_category_source: CategorySource | null;
}

export type KsefSubjectType = "Subject1" | "Subject2";

export interface AuthUser {
  id: string;
  email: string;
  tenant_id: string;
  is_active: boolean;
  role: string;
  company_name?: string | null;
  nip?: string | null;
  industry?: string | null;
}

export interface KsefSettingsStatus {
  is_configured: boolean;
}

export interface TeamMemberItem {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface TeamResponse {
  invite_token: string;
  members: TeamMemberItem[];
}

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
  category?: string | null;
}

export interface CashflowItem {
  date: string;
  sales: number | string;
  costs: number | string;
  balance: number | string;
}

export interface CashflowResponse {
  items: CashflowItem[];
  total_sales: number | string;
  total_costs: number | string;
  total_balance: number | string;
  granularity: "day" | "week" | "month";
  date_from: string | null;
  date_to: string | null;
}

export interface DashboardResponse {
  summary: SummaryResponse;
  trend: TrendResponse;
  previous_trend: TrendResponse | null;
  cost_structure: CostStructureResponse;
  cashflow: CashflowResponse;
  top_counterparties: TopCounterpartiesResponse;
}

export interface KsefSyncJobCreatedResponse {
  job_id: string;
  status: string;
}

export interface KsefSyncJobResponse {
  id: string;
  status: string;
  date_from: string;
  date_to: string;
  progress_message: string | null;
  error_message: string | null;
  result: KsefSyncResponse | null;
  created_at: string;
  completed_at: string | null;
}

export interface ContractorRuleItem {
  id: string;
  contractor_nip: string;
  contractor_name: string | null;
  category_main: string;
  category_sub: string;
  line_usage_count: number;
  updated_at: string | null;
}

export interface ContractorRuleListResponse {
  rules: ContractorRuleItem[];
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
  primary_category_main: string | null;
  primary_category_sub: string | null;
  primary_category_source: CategorySource | null;
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
  category_source: CategorySource | null;
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
  primary_category_main: string | null;
  primary_category_sub: string | null;
  primary_category_source: CategorySource | null;
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

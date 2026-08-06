import type { CashflowResponse } from "@/lib/types";
import { parseApiErrorMessage } from "@/lib/apiErrors";

const API_BASE_URL = "/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function buildHeaders(jsonBody = false): HeadersInit {
  const headers: HeadersInit = {
    Accept: "application/json",
  };

  if (jsonBody) {
    headers["Content-Type"] = "application/json";
  }

  return headers;
}

function buildUrl(
  path: string,
  params?: Record<string, string | number | undefined>,
): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const search = new URLSearchParams();

  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") {
        search.set(key, String(value));
      }
    }
  }

  const query = search.toString();
  return query
    ? `${API_BASE_URL}${normalizedPath}?${query}`
    : `${API_BASE_URL}${normalizedPath}`;
}

async function parseErrorResponse(response: Response): Promise<string> {
  const detail = await response.text();
  if (!detail) {
    return `Błąd API: ${response.status}`;
  }
  try {
    return parseApiErrorMessage(JSON.parse(detail), response.status);
  } catch {
    return detail;
  }
}

export async function apiFetch<T>(
  path: string,
  params?: Record<string, string | number | undefined>,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(buildUrl(path, params), {
    headers: buildHeaders(),
    credentials: "include",
    cache: "no-store",
    ...init,
  });

  if (!response.ok) {
    throw new ApiError(await parseErrorResponse(response), response.status);
  }

  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(buildUrl(path), {
    method: "POST",
    headers: buildHeaders(true),
    body: JSON.stringify(body),
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(await parseErrorResponse(response), response.status);
  }

  return response.json() as Promise<T>;
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(buildUrl(path), {
    method: "PUT",
    headers: buildHeaders(true),
    body: JSON.stringify(body),
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(await parseErrorResponse(response), response.status);
  }

  return response.json() as Promise<T>;
}

export async function apiDelete(path: string): Promise<void> {
  const response = await fetch(buildUrl(path), {
    method: "DELETE",
    headers: buildHeaders(),
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(await parseErrorResponse(response), response.status);
  }
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(buildUrl(path), {
    method: "PATCH",
    headers: buildHeaders(true),
    body: JSON.stringify(body),
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(await parseErrorResponse(response), response.status);
  }

  return response.json() as Promise<T>;
}

export function toNumber(value: number | string): number {
  return typeof value === "number" ? value : parseFloat(value);
}

export function formatPln(value: number | string): string {
  const num = toNumber(value);
  return new Intl.NumberFormat("pl-PL", {
    style: "currency",
    currency: "PLN",
    maximumFractionDigits: 0,
  }).format(num);
}

export interface CashflowQueryParams extends Record<string, string | undefined> {
  date_from?: string;
  date_to?: string;
}

export async function fetchCashflow(
  params?: CashflowQueryParams,
): Promise<CashflowResponse> {
  return apiFetch<CashflowResponse>("/stats/cashflow", params);
}

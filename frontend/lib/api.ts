const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

const DEV_TOKEN = process.env.NEXT_PUBLIC_DEV_TOKEN ?? "";

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

  if (DEV_TOKEN) {
    headers.Authorization = `Bearer ${DEV_TOKEN}`;
  }

  return headers;
}

export async function apiFetch<T>(
  path: string,
  params?: Record<string, string | number | undefined>,
): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path}`);

  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }

  const response = await fetch(url.toString(), {
    headers: buildHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(
      detail || `Błąd API: ${response.status}`,
      response.status,
    );
  }

  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: buildHeaders(true),
    body: JSON.stringify(body),
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(
      detail || `Błąd API: ${response.status}`,
      response.status,
    );
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

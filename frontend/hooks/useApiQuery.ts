"use client";

import { useEffect, useState } from "react";

import { ApiError, apiFetch } from "@/lib/api";

interface UseApiQueryOptions {
  enabled?: boolean;
}

interface UseApiQueryResult<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

export function useApiQuery<T>(
  path: string,
  params: Record<string, string | number | undefined> | undefined,
  deps: unknown[],
  options: UseApiQueryOptions = {},
): UseApiQueryResult<T> {
  const { enabled = true } = options;
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(enabled);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setError(null);

    apiFetch<T>(path, params, { signal: controller.signal })
      .then(setData)
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        if (err instanceof ApiError) {
          setError(err.message);
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Błąd pobierania danych");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- deps przekazywane jawnie
  }, [path, enabled, ...deps]);

  return { data, error, loading };
}

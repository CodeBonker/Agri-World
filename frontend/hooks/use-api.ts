"use client";

import { useCallback, useState } from "react";
import type { ApiError } from "@/lib/types";

export function useApi<T>() {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const run = useCallback(async (request: () => Promise<T>) => {
    setLoading(true);
    setError(null);
    try {
      const result = await request();
      setData(result);
      return result;
    } catch (err) {
      setError(err as ApiError);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, error, setData, run };
}

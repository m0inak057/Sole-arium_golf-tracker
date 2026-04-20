/**
 * Poll session status at intervals until complete or failed.
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getSessionStatus, ApiError } from "@/lib/api";
import type { SessionStatusResponse } from "@/lib/types";

interface UseSessionPollingOptions {
  /** Polling interval in ms. Default 2000. */
  intervalMs?: number;
  /** Whether to start polling immediately. Default true. */
  enabled?: boolean;
}

interface UseSessionPollingResult {
  data: SessionStatusResponse | null;
  error: string | null;
  isPolling: boolean;
}

export function useSessionPolling(
  sessionId: string,
  options: UseSessionPollingOptions = {},
): UseSessionPollingResult {
  const { intervalMs = 2000, enabled = true } = options;

  const [data, setData] = useState<SessionStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const poll = useCallback(async () => {
    try {
      const status = await getSessionStatus(sessionId);
      setData(status);
      setError(null);

      // Stop polling on terminal states
      if (status.status === "complete" || status.status === "failed") {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        setIsPolling(false);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`${err.code}: ${err.message}`);
      } else {
        setError("Failed to poll session status");
      }
    }
  }, [sessionId]);

  useEffect(() => {
    if (!enabled || !sessionId) return;

    setIsPolling(true);
    // Immediate first poll
    poll();
    intervalRef.current = setInterval(poll, intervalMs);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setIsPolling(false);
    };
  }, [sessionId, enabled, intervalMs, poll]);

  return { data, error, isPolling };
}

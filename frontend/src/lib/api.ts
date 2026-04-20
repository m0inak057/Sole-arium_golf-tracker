/**
 * Typed fetch wrappers — all network access goes through this module.
 *
 * No component should call `fetch` directly (rules.md §3).
 */

import type {
  SessionCreateResponse,
  SessionStatusResponse,
  SessionJSON,
  Phase1DetectionResponse,
  CoachingItem,
  Scores,
  OutputStatusResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Helpers ────────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "X-Client-Id": "golf-trainer-web",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body?.error?.code ?? "unknown", body?.error?.message ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ─── Session ────────────────────────────────────────────────────────────────

export async function createSession(
  video: File,
  gender: "male" | "female",
): Promise<SessionCreateResponse> {
  const formData = new FormData();
  formData.append("video", video);
  formData.append("gender", gender);

  return apiFetch<SessionCreateResponse>("/api/session", {
    method: "POST",
    body: formData,
  });
}

export async function getSessionStatus(
  sessionId: string,
): Promise<SessionStatusResponse> {
  return apiFetch<SessionStatusResponse>(`/api/session/${sessionId}/status`);
}

export async function getFullSession(
  sessionId: string,
): Promise<SessionJSON> {
  return apiFetch<SessionJSON>(`/api/session/${sessionId}`);
}

// ─── Phase-specific ─────────────────────────────────────────────────────────

export async function getPhase1Detection(
  sessionId: string,
): Promise<Phase1DetectionResponse> {
  return apiFetch<Phase1DetectionResponse>(`/api/phase1/detection/${sessionId}`);
}

export async function getPhase4Results(
  sessionId: string,
): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(`/api/phase4/results/${sessionId}`);
}

export async function getPhase5Score(
  sessionId: string,
): Promise<Scores> {
  return apiFetch<Scores>(`/api/phase5/score/${sessionId}`);
}

export async function getCoaching(
  sessionId: string,
): Promise<CoachingItem[]> {
  return apiFetch<CoachingItem[]>(`/api/coaching/${sessionId}`);
}

// ─── Output ─────────────────────────────────────────────────────────────────

export async function getOutputStatus(
  sessionId: string,
  kind: "slowmo" | "annotated",
): Promise<OutputStatusResponse> {
  return apiFetch<OutputStatusResponse>(`/api/output/${sessionId}/${kind}/status`);
}

export function getVideoStreamUrl(
  sessionId: string,
  kind: "slowmo" | "annotated",
): string {
  return `${API_BASE}/api/output/${sessionId}/${kind}`;
}

export function getVideoDownloadUrl(
  sessionId: string,
  kind: "slowmo" | "annotated",
): string {
  return `${API_BASE}/api/output/${sessionId}/download/${kind}`;
}

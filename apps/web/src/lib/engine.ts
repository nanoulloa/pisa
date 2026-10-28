import type { AnalysisResult, Job } from "@pisa/contracts";

/** Inlined at build time. Local development talks to `make dev-engine`. */
export const ENGINE_URL = process.env.NEXT_PUBLIC_ENGINE_URL ?? "http://localhost:8000";

export const MAX_UPLOAD_BYTES = 50_000_000;

/** A failure the interface can explain: `code` is a key under `Errors` in the messages. */
export class EngineError extends Error {
  constructor(readonly code: string) {
    super(code);
    this.name = "EngineError";
  }
}

export async function createJob(video: File, locale: string): Promise<Job> {
  const form = new FormData();
  form.append("video", video);
  form.append("locale", locale);
  return request<Job>("/jobs", { method: "POST", body: form });
}

export function getJob(id: string): Promise<Job> {
  return request<Job>(`/jobs/${encodeURIComponent(id)}`);
}

export function getResult(id: string): Promise<AnalysisResult> {
  return request<AnalysisResult>(`/jobs/${encodeURIComponent(id)}/result`);
}

/**
 * On the server: the result when the job is done, else null. It never throws and gives up
 * quickly, so a slow engine only means the browser asks instead.
 */
export async function finishedResult(id: string): Promise<AnalysisResult | null> {
  try {
    const response = await fetch(`${ENGINE_URL}/jobs/${encodeURIComponent(id)}/result`, {
      cache: "no-store",
      signal: AbortSignal.timeout(1500),
    });
    return response.ok ? ((await response.json()) as AnalysisResult) : null;
  } catch {
    return null;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${ENGINE_URL}${path}`, init);
  } catch {
    throw new EngineError("network");
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { error?: { code?: string } } | null;
    throw new EngineError(body?.error?.code ?? "internal_error");
  }
  return (await response.json()) as T;
}

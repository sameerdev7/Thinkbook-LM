import {
  clearAuth,
  getAccessToken,
  getRefreshToken,
  updateTokens,
  type Tokens,
} from "./auth-store";

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

interface ApiOptions {
  method?: string;
  body?: unknown;
  formData?: FormData;
  auth?: boolean;
  signal?: AbortSignal;
}

let refreshInFlight: Promise<boolean> | null = null;

async function doRefresh(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  const refresh_token = getRefreshToken();
  if (!refresh_token) return false;
  refreshInFlight = (async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token }),
      });
      if (!res.ok) return false;
      const data = (await res.json()) as Tokens;
      updateTokens(data);
      return true;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

async function request<T>(path: string, opts: ApiOptions = {}): Promise<T> {
  const { method = "GET", body, formData, auth = true, signal } = opts;
  const doFetch = async (): Promise<Response> => {
    const headers: Record<string, string> = {};
    if (auth) {
      const token = getAccessToken();
      if (token) headers["Authorization"] = `Bearer ${token}`;
    }
    let payload: BodyInit | undefined;
    if (formData) {
      payload = formData;
    } else if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      payload = JSON.stringify(body);
    }
    return fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: payload,
      signal,
    });
  };

  let res = await doFetch();
  if (res.status === 401 && auth) {
    const ok = await doRefresh();
    if (ok) {
      res = await doFetch();
    } else {
      clearAuth();
      if (typeof window !== "undefined" && !location.pathname.startsWith("/login")) {
        location.href = "/login";
      }
      throw new ApiError(401, "Unauthorized");
    }
  }

  const contentType = res.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const data = isJson ? await res.json().catch(() => null) : await res.text();
  if (!res.ok) {
    const msg =
      (isJson && data && typeof data === "object" && "detail" in (data as Record<string, unknown>)
        ? String((data as Record<string, unknown>).detail)
        : typeof data === "string" && data
          ? data
          : res.statusText) || "Request failed";
    throw new ApiError(res.status, msg, data);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string, opts?: Omit<ApiOptions, "method" | "body">) =>
    request<T>(path, { ...opts, method: "GET" }),
  post: <T>(path: string, body?: unknown, opts?: Omit<ApiOptions, "method" | "body">) =>
    request<T>(path, { ...opts, method: "POST", body }),
  postForm: <T>(path: string, formData: FormData, opts?: Omit<ApiOptions, "method" | "body" | "formData">) =>
    request<T>(path, { ...opts, method: "POST", formData }),
  patch: <T>(path: string, body?: unknown, opts?: Omit<ApiOptions, "method" | "body">) =>
    request<T>(path, { ...opts, method: "PATCH", body }),
  del: <T>(path: string, opts?: Omit<ApiOptions, "method" | "body">) =>
    request<T>(path, { ...opts, method: "DELETE" }),
};

// Domain types
export interface Session {
  id: string;
  name?: string;
  title?: string;
  created_at?: string;
  updated_at?: string;
  [k: string]: unknown;
}

export interface Source {
  id: string;
  source_type: string;
  source_file?: string;
  title?: string;
  name?: string;
  created_at?: string;
  [k: string]: unknown;
}

export type JobStatus = "pending" | "running" | "completed" | "failed";
export interface Job<TResult = unknown> {
  id: string;
  job_type: string;
  status: JobStatus;
  progress: number;
  step_message?: string;
  result?: TResult;
  error?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ChatSource {
  reference: string;
  source_file: string;
  source_type: string;
  page_number?: number | null;
  chunk_id: string;
  relevance_score: number;
}

export interface ChatResponse {
  query: string;
  response: string;
  sources: ChatSource[];
  retrieval_count: number;
}

export interface Chunk {
  chunk_id: string;
  content: string;
  source_file?: string;
  page_number?: number | null;
  [k: string]: unknown;
}

export interface FeatureConfig {
  features: {
    chat: boolean;
    document_upload: boolean;
    audio_upload: boolean;
    youtube: boolean;
    web_scraping: boolean;
    podcast_script: boolean;
    podcast_audio: boolean;
    memory: boolean;
  };
}

export type PodcastLine = Record<string, string>;

export interface PodcastScriptResult {
  script: PodcastLine[];
}

export interface PodcastAudioResult {
  audio_path: string;
}

export async function pollJob<T = unknown>(
  jobId: string,
  opts: { onUpdate?: (job: Job<T>) => void; signal?: AbortSignal; intervalMs?: number } = {},
): Promise<Job<T>> {
  const { onUpdate, signal, intervalMs = 1800 } = opts;
  while (true) {
    if (signal?.aborted) throw new Error("aborted");
    const job = await api.get<Job<T>>(`/jobs/${jobId}`, { signal });
    onUpdate?.(job);
    if (job.status === "completed" || job.status === "failed") return job;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

export function podcastAudioDownloadUrl(jobId: string): string {
  return `${API_BASE_URL}/podcast/audio/${jobId}/download`;
}
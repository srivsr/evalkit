import type {
  Project, HealthResponse, EvaluateRequest, EvaluateResponse,
  EvaluationListItem, CompareResponse, LegalDocument, CreateOrderResponse,
  ApiKeyItem, ApiKeyCreated, ContextItem, ChunkEvalResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let clerkToken: string | null = null;

export function setClerkToken(token: string | null) {
  clerkToken = token;
}

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...options?.headers as Record<string, string>,
  };
  if (clerkToken) {
    headers["Authorization"] = `Bearer ${clerkToken}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
  if (res.status === 401 && typeof window !== "undefined") {
    window.location.href = "/sign-in";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || err.error || `API error ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => fetchAPI<HealthResponse>("/v1/health"),

  projects: {
    list: () => fetchAPI<Project[]>("/v1/projects"),
    get: (id: string) => fetchAPI<Project>(`/v1/projects/${id}`),
    create: (name: string) =>
      fetchAPI<Project>("/v1/projects", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
  },

  evaluations: {
    list: (projectId: string) =>
      fetchAPI<EvaluationListItem[]>(`/v1/evaluations?project_id=${projectId}`),
    get: (runId: string) =>
      fetchAPI<EvaluateResponse>(`/v1/evaluations/${runId}`),
    create: (req: EvaluateRequest) =>
      fetchAPI<EvaluateResponse>("/v1/evaluate", {
        method: "POST",
        body: JSON.stringify(req),
      }),
    markBaseline: (runId: string) =>
      fetchAPI<{ run_id: string; is_baseline: boolean }>(
        `/v1/evaluations/${runId}/baseline`,
        { method: "POST" },
      ),
  },

  compare: (runA: string, runB: string) =>
    fetchAPI<CompareResponse>(`/v1/compare?run_a=${runA}&run_b=${runB}`),

  regressions: (projectId: string) =>
    fetchAPI<unknown[]>(`/v1/projects/${projectId}/regressions`),

  legal: {
    privacy: () => fetchAPI<LegalDocument>("/v1/legal/privacy"),
    terms: () => fetchAPI<LegalDocument>("/v1/legal/terms"),
    refund: () => fetchAPI<LegalDocument>("/v1/legal/refund"),
  },

  payments: {
    createOrder: (tier: string, provider: string, termsAccepted: boolean) =>
      fetchAPI<CreateOrderResponse>(`/v1/payments/${provider}/create-order`, {
        method: "POST",
        body: JSON.stringify({ tier, provider, terms_accepted: termsAccepted }),
      }),
  },

  chunks: {
    evaluate: (chunks: ContextItem[], sampleSize?: number, domain?: string) =>
      fetchAPI<ChunkEvalResponse>("/v1/evaluate/chunks", {
        method: "POST",
        body: JSON.stringify({ chunks, sample_size: sampleSize, domain }),
      }),
  },

  apiKeys: {
    list: () => fetchAPI<ApiKeyItem[]>("/v1/api-keys"),
    create: (name: string) =>
      fetchAPI<ApiKeyCreated>("/v1/api-keys", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    revoke: (id: string) =>
      fetchAPI<{ id: string; revoked: boolean }>(`/v1/api-keys/${id}`, {
        method: "DELETE",
      }),
  },
};

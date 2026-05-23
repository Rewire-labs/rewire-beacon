// BEACON API client — minimal fetch wrapper.
// Auto-attaches Authorization (JWT or API token) and X-Organization-Id headers.
// 401 -> redirect to /login.

export const API_BASE = import.meta.env.VITE_BEACON_API_BASE || "/v1";

type Token = string | null;

function getAuthToken(): Token {
  // Persisted by login flow; harmless if missing in mock dev.
  return localStorage.getItem("beacon_token");
}

function getOrgId(): string | null {
  return localStorage.getItem("beacon_org_id");
}

export interface RequestOpts extends Omit<RequestInit, "body"> {
  body?: unknown;
  skipOrgHeader?: boolean;
}

export class ApiError extends Error {
  constructor(public status: number, public detail: unknown) {
    super(typeof detail === "string" ? detail : `API error ${status}`);
  }
}

export async function api<T = unknown>(path: string, opts: RequestOpts = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Accept": "application/json",
    ...(opts.headers as Record<string, string> | undefined),
  };
  const token = getAuthToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const orgId = getOrgId();
  if (orgId && !opts.skipOrgHeader) headers["X-Organization-Id"] = orgId;

  const init: RequestInit = { ...opts, headers };
  if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(opts.body);
  }

  const resp = await fetch(`${API_BASE}${path}`, init);
  if (resp.status === 401) {
    // Soft redirect — keeps SPA navigation cheap.
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    throw new ApiError(401, "unauthenticated");
  }
  const text = await resp.text();
  let parsed: unknown = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }
  if (!resp.ok) {
    throw new ApiError(resp.status, parsed);
  }
  return parsed as T;
}

// ----- Domain endpoints --------------------------------------------------

export interface ApiToken {
  id: string;
  name: string;
  token_prefix: string;
  scopes: string[];
  last_used_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export const apiTokens = {
  list: () => api<ApiToken[]>("/api-tokens"),
  create: (body: { name: string; scopes?: string[]; expires_at?: string | null }) =>
    api<ApiToken & { token: string }>("/api-tokens", { method: "POST", body }),
  revoke: (id: string) => api<void>(`/api-tokens/${id}`, { method: "DELETE" }),
};

export interface EmailDomain {
  id: string;
  domain: string;
  verified: boolean;
  spf_status: string;
  dmarc_status: string;
  reputation_score: number;
  created_at: string;
  verified_at: string | null;
  dns_instructions?: Array<{ type: string; name: string; value: string; purpose: string }>;
}

export const domains = {
  list: () => api<EmailDomain[]>("/domains"),
  create: (domain: string) => api<EmailDomain>("/domains", { method: "POST", body: { domain } }),
  verify: (id: string) => api<EmailDomain>(`/domains/${id}/verify`, { method: "POST" }),
};

export const messages = {
  sendEmail: (body: unknown) => api<{ message_id: string; status: string; chain_hash: string }>(
    "/messages/email", { method: "POST", body },
  ),
  sendSms: (body: unknown) => api("/messages/sms", { method: "POST", body }),
  sendPush: (body: unknown) => api("/messages/push", { method: "POST", body }),
  sendWhatsapp: (body: unknown) => api("/messages/whatsapp", { method: "POST", body }),
  timeline: (id: string) => api<{ message_id: string; events: unknown[] }>(`/analytics/messages/${id}/events`),
};

export interface SuppressionEntry {
  id: string;
  identifier_type: string;
  identifier_value: string;
  reason: string;
  source_channel: string | null;
  created_at: string;
}

export const suppression = {
  list: (params?: { identifier_type?: string; limit?: number; offset?: number }) =>
    api<SuppressionEntry[]>(`/suppression${params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : ""}`),
  add: (body: { identifier_type: string; identifier_value: string; reason?: string }) =>
    api<SuppressionEntry>("/suppression", { method: "POST", body }),
  remove: (id: string) => api<void>(`/suppression/${id}`, { method: "DELETE" }),
};

export const analytics = {
  summary: (params: { from?: string; to?: string; channel?: string }) => {
    const q = new URLSearchParams();
    if (params.from) q.set("from", params.from);
    if (params.to) q.set("to", params.to);
    if (params.channel) q.set("channel", params.channel);
    return api<{ from: string; to: string; rows: Array<Record<string, unknown>> }>(`/analytics/messages?${q.toString()}`);
  },
};

export const billing = {
  usageMtd: () => api<{ month_starting: string; counts: Record<string, number> }>("/billing/usage-mtd"),
  invoices: () => api<{ invoices: unknown[] }>("/billing/invoices"),
  pricing: () => api<{ pricing: unknown; currency: string }>("/billing/pricing"),
};

export const lgpd = {
  requestDsar: (body: { subject_email?: string; subject_phone?: string }) =>
    api<{ id: string; status: string; eta_hours: number }>("/audit/lgpd/dsar", { method: "POST", body }),
  getDsar: (id: string) => api<{ id: string; status: string }>(`/audit/lgpd/dsar/${id}`),
};

export const journeys = {
  list: () => api<Array<{ id: string; name: string; status: string }>>("/journeys"),
  create: (body: unknown) => api<{ id: string; status: string }>("/journeys", { method: "POST", body }),
  pause: (id: string) => api(`/journeys/${id}/pause`, { method: "POST" }),
  resume: (id: string) => api(`/journeys/${id}/resume`, { method: "POST" }),
};

export const pushApps = {
  list: () => api<Array<{ id: string; name: string; platform: string }>>("/push-apps"),
  create: (body: unknown) => api("/push-apps", { method: "POST", body }),
  remove: (id: string) => api<void>(`/push-apps/${id}`, { method: "DELETE" }),
};

export const webpush = {
  getVapidPublicKey: () => api<{ public_key: string }>("/webpush/vapid-public-key"),
  subscribe: (sub: PushSubscriptionJSON) =>
    api("/webpush/subscriptions", { method: "POST", body: sub }),
};

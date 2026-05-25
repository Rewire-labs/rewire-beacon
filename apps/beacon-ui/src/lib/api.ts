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

// ----- Phase-13 UI wiring (BCN-230..248) extra surfaces -----------------
// These mirror endpoints exposed by the FastAPI control plane. Pages fall
// back to `@/content/beacon-mock` when the backend responds non-OK; the
// `useBeacon*` hooks in `@/lib/hooks/useBeacon.ts` orchestrate that
// graceful degradation with a "Modo demo" banner.

export interface OverviewSummary {
  mtd_email: number;
  mtd_sms: number;
  mtd_push: number;
  mtd_wa: number;
  mtd_spend_brl: number;
  delivered_rate: number;
  open_rate_email: number;
  verified_domains: number;
  total_domains: number;
  generated_at: string;
}

export const overview = {
  get: () => api<OverviewSummary>("/overview"),
};

export const templates = {
  list: () => api<Array<{ id: string; name: string; channel: string; enabled: boolean }>>("/templates"),
  get: (id: string) => api<{ id: string; name: string; body: string }>(`/templates/${id}`),
  upsert: (body: unknown) => api("/templates", { method: "POST", body }),
  remove: (id: string) => api<void>(`/templates/${id}`, { method: "DELETE" }),
};

export const smsNumbers = {
  list: () => api<Array<{ id: string; number: string; country: string; status: string }>>("/sms-numbers"),
};

export const whatsapp = {
  status: () => api<{ connected: boolean; quality_rating: string; templates_synced: number }>("/whatsapp"),
  templates: () => api<Array<{ id: string; name: string; category: string; status: string }>>("/whatsapp/templates"),
};

export const webhooksMgmt = {
  list: () => api<Array<{ id: string; url: string; events: string[]; status: string }>>("/webhooks"),
  create: (body: unknown) => api("/webhooks", { method: "POST", body }),
  remove: (id: string) => api<void>(`/webhooks/${id}`, { method: "DELETE" }),
};

export const team = {
  list: () => api<Array<{ id: string; email: string; role: string }>>("/team"),
};

export const settings = {
  get: () => api<{ org: Record<string, unknown> }>("/settings"),
  update: (body: unknown) => api("/settings", { method: "PATCH", body }),
};

export const chain = {
  list: (params?: { limit?: number }) =>
    api<{ entries: Array<{ hash: string; ref: string | null; created_at: string }> }>(
      `/chain${params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : ""}`,
    ),
  verify: (hash: string) => api<{ valid: boolean; anchored_at: string | null }>(`/chain/${hash}/verify`),
};

export const deliverability = {
  reputation: () =>
    api<{ ip_pool_score: number; domain_score: number; mailbox_provider_scores: Record<string, number> }>(
      "/deliverability/reputation",
    ),
};

export const antispam = {
  scores: () =>
    api<{ tenant_score: number; flagged_24h: number; samples: Array<Record<string, unknown>> }>(
      "/antispam/scores",
    ),
};

// ----- MSG-IMPL-002 (Lote 8): A/B tests + segments + notifications dispatcher

export interface AbVariant {
  id: string;
  name: string;
  weight: number;
  template_slug: string;
  subject_override?: string | null;
}

export interface AbTest {
  id: string;
  name: string;
  channel: "email" | "sms" | "push" | "whatsapp";
  status: string;
  primary_metric: "delivered" | "opened" | "clicked" | "unsubscribed";
  variants: AbVariant[];
  created_at: string;
}

export interface AbAssignResponse {
  test_id: string;
  variant_id: string;
  variant_name: string;
  template_slug: string;
  subject_override?: string | null;
}

export interface AbVariantResult {
  variant_id: string;
  name: string;
  delivered: number;
  opened: number;
  clicked: number;
  unsubscribed: number;
  ctr: number;
  is_winner: boolean;
}

export interface AbResults {
  test_id: string;
  name: string;
  primary_metric: string;
  total_assignments: number;
  confidence: number;
  has_significant_winner: boolean;
  variants: AbVariantResult[];
}

export const abTests = {
  list: () => api<AbTest[]>("/ab-tests"),
  get: (id: string) => api<AbTest>(`/ab-tests/${id}`),
  create: (body: {
    name: string;
    channel: AbTest["channel"];
    variants: Array<Omit<AbVariant, "id">>;
    audience_segment_id?: string | null;
    primary_metric?: AbTest["primary_metric"];
    min_sample_size?: number;
  }) => api<AbTest>("/ab-tests", { method: "POST", body }),
  assign: (id: string, recipient: string) =>
    api<AbAssignResponse>(`/ab-tests/${id}/assign`, { method: "POST", body: { recipient } }),
  recordEvent: (id: string, variant_id: string, event: AbVariantResult["name"] | string) =>
    api<void>(`/ab-tests/${id}/event`, { method: "POST", body: { variant_id, event } }),
  results: (id: string) => api<AbResults>(`/ab-tests/${id}/results`),
};

export interface Segment {
  id: string;
  name: string;
  description: string | null;
  channel: "email" | "sms" | "push" | "whatsapp" | "any";
  attributes: Record<string, unknown>;
  include_tags: string[];
  exclude_tags: string[];
  consent_basis: "consent" | "contract" | "legal_obligation" | "legitimate_interest";
  estimated_size: number;
  created_at: string;
  updated_at: string;
}

export const segments = {
  list: () => api<Segment[]>("/segments"),
  get: (id: string) => api<Segment>(`/segments/${id}`),
  create: (body: {
    name: string;
    description?: string | null;
    channel?: Segment["channel"];
    attributes?: Record<string, unknown>;
    include_tags?: string[];
    exclude_tags?: string[];
    consent_basis?: Segment["consent_basis"];
  }) => api<Segment>("/segments", { method: "POST", body }),
  update: (
    id: string,
    body: Partial<Pick<Segment, "name" | "description" | "attributes" | "include_tags" | "exclude_tags">>,
  ) => api<Segment>(`/segments/${id}`, { method: "PATCH", body }),
  remove: (id: string) => api<void>(`/segments/${id}`, { method: "DELETE" }),
  estimate: (id: string) =>
    api<{ segment_id: string; estimated_size: number; sample_recipients: string[]; computed_at: string }>(
      `/segments/${id}/estimate`,
      { method: "POST" },
    ),
};

export interface NotificationCreateBody {
  channel: "email" | "sms" | "whatsapp" | "push_mobile" | "push_web";
  recipient: string;
  template_id?: string;
  body?: string;
  subject?: string;
  sender?: string;
  consent_basis?: "consent" | "contract" | "legal_obligation" | "legitimate_interest";
  metadata?: Record<string, string>;
  push_title?: string;
  push_app_id?: string;
  template_vars?: Record<string, string>;
}

export interface NotificationAccepted {
  notification_id: string;
  status: string;
  channel: string;
  chain_hash: string;
  provider_route: string;
}

export const notifications = {
  send: (body: NotificationCreateBody) =>
    api<NotificationAccepted>("/notifications", { method: "POST", body }),
  channels: () =>
    api<{ organization_id: string | null; channels: Array<{ id: string; enabled: boolean; provider: string }> }>(
      "/channels",
    ),
};

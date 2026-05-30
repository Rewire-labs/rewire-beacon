// Beacon UI API client
//
// RW-FE-MESSAGING-02: authentication is Authentik OIDC (Authorization Code +
// PKCE), NOT a custom localStorage bearer token. Every request carries the
// standard Rewire headers: Authorization, X-Rewire-Audit, X-Rewire-MFA and
// Accept-Language.
//
// This module is framework-agnostic (no React imports) so it can be unit
// type-checked and reused by any caller.

// --------------------------------------------------------------------------- //
// Config
// --------------------------------------------------------------------------- //
export interface OidcConfig {
  authority: string; // Authentik issuer, e.g. https://auth.rewirelabs.dev/application/o/beacon/
  clientId: string;
  redirectUri: string;
  scope: string;
}

export interface ApiConfig {
  baseUrl: string;
  oidc: OidcConfig;
}

declare const importMetaEnv: Record<string, string | undefined>;

function env(key: string, fallback = ""): string {
  // Vite exposes import.meta.env; fall back gracefully when bundler injects it.
  const meta = (globalThis as { __BEACON_ENV__?: Record<string, string> })
    .__BEACON_ENV__;
  const value = meta ? meta[key] : undefined;
  return value ?? fallback;
}

// FE-MESSAGING-05: single canonical base-URL env var.
// Dev: set VITE_MESSAGING_URL=http://localhost:8030 (or leave blank, vite proxy
// rewrites /api/* to the control-plane). Prod: injected by Helm as the canonical
// https://messaging.rewirelabs.dev base.
export const apiConfig: ApiConfig = {
  baseUrl: env("VITE_MESSAGING_URL", env("VITE_BEACON_API", "")),
  oidc: {
    authority: env(
      "VITE_OIDC_AUTHORITY",
      "https://auth.rewirelabs.dev/application/o/beacon/",
    ),
    clientId: env("VITE_OIDC_CLIENT_ID", "beacon-ui"),
    redirectUri: env("VITE_OIDC_REDIRECT", `${location.origin}/auth/callback`),
    scope: "openid profile email offline_access",
  },
};

// --------------------------------------------------------------------------- //
// Token storage — short-lived access token kept in memory; refresh token in
// sessionStorage (cleared on tab close). We deliberately avoid persisting the
// access token in localStorage.
// --------------------------------------------------------------------------- //
export interface TokenSet {
  accessToken: string;
  refreshToken?: string;
  expiresAt: number; // epoch ms
  idToken?: string;
}

const REFRESH_KEY = "beacon.oidc.refresh";
let memoryTokens: TokenSet | null = null;

export function setTokens(t: TokenSet): void {
  memoryTokens = t;
  if (t.refreshToken) sessionStorage.setItem(REFRESH_KEY, t.refreshToken);
}

export function clearTokens(): void {
  memoryTokens = null;
  sessionStorage.removeItem(REFRESH_KEY);
}

export function isAuthenticated(): boolean {
  return !!memoryTokens && memoryTokens.expiresAt > Date.now();
}

// --------------------------------------------------------------------------- //
// PKCE helpers
// --------------------------------------------------------------------------- //
function base64UrlEncode(bytes: ArrayBuffer): string {
  const arr = new Uint8Array(bytes);
  let str = "";
  for (let i = 0; i < arr.length; i++) str += String.fromCharCode(arr[i]);
  return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function randomString(len = 64): string {
  const bytes = new Uint8Array(len);
  crypto.getRandomValues(bytes);
  return base64UrlEncode(bytes.buffer);
}

async function sha256(input: string): Promise<ArrayBuffer> {
  return crypto.subtle.digest("SHA-256", new TextEncoder().encode(input));
}

const PKCE_VERIFIER_KEY = "beacon.pkce.verifier";
const PKCE_STATE_KEY = "beacon.pkce.state";

// Kick off the OIDC Authorization Code + PKCE flow (redirects the browser).
export async function login(): Promise<void> {
  const verifier = randomString(64);
  const state = randomString(16);
  const challenge = base64UrlEncode(await sha256(verifier));
  sessionStorage.setItem(PKCE_VERIFIER_KEY, verifier);
  sessionStorage.setItem(PKCE_STATE_KEY, state);

  const u = new URL(`${apiConfig.oidc.authority}authorize/`);
  u.searchParams.set("response_type", "code");
  u.searchParams.set("client_id", apiConfig.oidc.clientId);
  u.searchParams.set("redirect_uri", apiConfig.oidc.redirectUri);
  u.searchParams.set("scope", apiConfig.oidc.scope);
  u.searchParams.set("state", state);
  u.searchParams.set("code_challenge", challenge);
  u.searchParams.set("code_challenge_method", "S256");
  location.assign(u.toString());
}

interface TokenResponse {
  access_token: string;
  refresh_token?: string;
  id_token?: string;
  expires_in: number;
}

function ingestTokenResponse(r: TokenResponse): TokenSet {
  const tokens: TokenSet = {
    accessToken: r.access_token,
    refreshToken: r.refresh_token,
    idToken: r.id_token,
    expiresAt: Date.now() + r.expires_in * 1000,
  };
  setTokens(tokens);
  return tokens;
}

// Complete the flow at the /auth/callback route.
export async function handleCallback(search: string): Promise<TokenSet> {
  const params = new URLSearchParams(search);
  const code = params.get("code");
  const state = params.get("state");
  const expectedState = sessionStorage.getItem(PKCE_STATE_KEY);
  const verifier = sessionStorage.getItem(PKCE_VERIFIER_KEY);
  if (!code) throw new Error("missing authorization code");
  if (!state || state !== expectedState) throw new Error("OIDC state mismatch");
  if (!verifier) throw new Error("missing PKCE verifier");

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: apiConfig.oidc.redirectUri,
    client_id: apiConfig.oidc.clientId,
    code_verifier: verifier,
  });
  const resp = await fetch(`${apiConfig.oidc.authority}token/`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!resp.ok) throw new Error(`token exchange failed: ${resp.status}`);
  sessionStorage.removeItem(PKCE_VERIFIER_KEY);
  sessionStorage.removeItem(PKCE_STATE_KEY);
  return ingestTokenResponse((await resp.json()) as TokenResponse);
}

async function refresh(): Promise<TokenSet | null> {
  const rt = sessionStorage.getItem(REFRESH_KEY);
  if (!rt) return null;
  const body = new URLSearchParams({
    grant_type: "refresh_token",
    refresh_token: rt,
    client_id: apiConfig.oidc.clientId,
  });
  const resp = await fetch(`${apiConfig.oidc.authority}token/`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!resp.ok) {
    clearTokens();
    return null;
  }
  return ingestTokenResponse((await resp.json()) as TokenResponse);
}

async function validAccessToken(): Promise<string | null> {
  if (memoryTokens && memoryTokens.expiresAt > Date.now() + 5000) {
    return memoryTokens.accessToken;
  }
  const refreshed = await refresh();
  return refreshed?.accessToken ?? null;
}

// --------------------------------------------------------------------------- //
// MFA / audit context — populated by the auth context after step-up.
// --------------------------------------------------------------------------- //
let mfaLevel = "none"; // "none" | "totp" | "webauthn"
export function setMfaLevel(level: string): void {
  mfaLevel = level;
}

function auditId(): string {
  return randomString(12);
}

// --------------------------------------------------------------------------- //
// Core fetch wrapper
// --------------------------------------------------------------------------- //
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface RequestOptions {
  method?: string;
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined>;
  signal?: AbortSignal;
}

export async function apiFetch<T = unknown>(
  path: string,
  opts: RequestOptions = {},
): Promise<T> {
  const token = await validAccessToken();
  if (!token) {
    await login();
    throw new ApiError(401, "not authenticated; redirecting to login");
  }

  const url = new URL(
    path.startsWith("http") ? path : `${apiConfig.baseUrl}${path}`,
    location.origin,
  );
  if (opts.query) {
    for (const [k, v] of Object.entries(opts.query)) {
      if (v !== undefined) url.searchParams.set(k, String(v));
    }
  }

  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "X-Rewire-Audit": auditId(),
    "X-Rewire-MFA": mfaLevel,
    "Accept-Language": navigator.language || "pt-BR",
    Accept: "application/json",
  };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";

  const resp = await fetch(url.toString(), {
    method: opts.method ?? (opts.body !== undefined ? "POST" : "GET"),
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    signal: opts.signal,
  });

  const text = await resp.text();
  const parsed = text ? safeJson(text) : undefined;
  if (!resp.ok) {
    throw new ApiError(resp.status, `${resp.status} ${resp.statusText}`, parsed);
  }
  return parsed as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export const api = {
  get: <T>(path: string, query?: RequestOptions["query"]) =>
    apiFetch<T>(path, { method: "GET", query }),
  post: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "POST", body }),
  put: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "PUT", body }),
  del: <T>(path: string) => apiFetch<T>(path, { method: "DELETE" }),
};

// --------------------------------------------------------------------------- //
// Typed resource clients (FE-MESSAGING-07) — each maps to a real backend
// router under /v1, replacing the previous FE-invented endpoints.
// --------------------------------------------------------------------------- //
export interface ChannelStat {
  channel: string;
  sent: number;
  delivered: number;
  failed: number;
}
export interface Overview {
  period: string;
  total_sent: number;
  total_delivered: number;
  total_failed: number;
  delivery_rate: number;
  channels: ChannelStat[];
}
export interface SmsNumber {
  id: string;
  phone_number: string;
  label: string;
  provider: string;
  verified: boolean;
}
export interface Deliverability {
  bounce_rate: number;
  complaint_rate: number;
  open_rate: number;
  click_rate: number;
  reputation_score: number;
}
export interface ChainStatus {
  length: number;
  head_hash: string;
  verified: boolean;
  last_verified_at: string | null;
}
export interface TeamMember {
  id: string;
  email: string;
  role: string;
}
export interface WorkspaceSettings {
  workspace_name: string;
  default_locale: string;
  timezone: string;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  rate_limit_per_minute: number;
}

export interface SendPayload {
  channel: string;
  recipient: string;
  category?: string;
  subject?: string;
  body?: string;
  template_id?: string;
  idempotency_key?: string;
}
export interface SendResult {
  decision: string;
  reason: string;
  accepted: boolean;
}

export const beaconApi = {
  send: (body: SendPayload) =>
    api.post<SendResult>("/v1/notifications/send", body),
  overview: (period = "7d") =>
    api.get<Overview>("/v1/overview", { period }),
  smsNumbers: {
    list: () => api.get<SmsNumber[]>("/v1/sms-numbers"),
    create: (body: { phone_number: string; label?: string; provider?: string }) =>
      api.post<SmsNumber>("/v1/sms-numbers", body),
  },
  deliverability: (period = "30d") =>
    api.get<Deliverability>("/v1/deliverability", { period }),
  chain: {
    status: () => api.get<ChainStatus>("/v1/chain"),
    verify: () => api.post<ChainStatus>("/v1/chain/verify"),
  },
  team: {
    list: () => api.get<TeamMember[]>("/v1/team"),
    invite: (body: { email: string; role?: string }) =>
      api.post<TeamMember>("/v1/team/invite", body),
  },
  settings: {
    get: () => api.get<WorkspaceSettings>("/v1/settings"),
    update: (body: WorkspaceSettings) =>
      api.put<WorkspaceSettings>("/v1/settings", body),
  },
};

// --------------------------------------------------------------------------- //
// Typed resource clients — named exports consumed by useBeacon hooks via
// `import * as api from "@/lib/api"`. Each maps to a real backend router.
// FE-MESSAGING-01/05/06/08: adds all missing exports so tsc -b passes clean.
// --------------------------------------------------------------------------- //

// --- Types ---

export interface AnalyticsSummary {
  from: string;
  to: string;
  rows: Array<Record<string, unknown>>;
}

export interface Template {
  id: string;
  slug: string;
  channel: string;
  locale: string;
  subject: string | null;
  body: string;
  version: number;
}

export interface Journey {
  id: string;
  name: string;
  status: string;
  steps?: number;
  trigger?: string;
}

export interface SuppressionEntry {
  id: string;
  identifier_type: string;
  identifier_value: string;
  reason: string;
  source_channel: string | null;
  created_at: string;
}

export interface EmailDomain {
  id: string;
  domain: string;
  verified: boolean;
  spf_status: string;
  dkim_status?: string;
  dmarc_status: string;
  reputation_score: number;
  created_at?: string;
  verified_at?: string | null;
  daily_limit?: number;
  sent_30d?: number;
}

export interface WaStatus {
  connected: boolean;
  quality_rating: string;
  templates_synced: number;
}

export interface WaTemplate {
  id: string;
  name: string;
  category: string;
  status: string;
  language: string;
}

export interface PushApp {
  id: string;
  name: string;
  platform: string;
  created_at?: string;
}

export interface WebhookEndpoint {
  id: string;
  name: string;
  url: string;
  events: string[];
  status: string;
}

export interface ApiToken {
  id: string;
  name: string;
  token_prefix: string;
  created_at: string;
  last_used_at: string | null;
}

export interface BillingUsage {
  month_starting: string;
  counts: Record<string, number>;
}

export interface BillingInvoices {
  invoices: unknown[];
}

export interface ChainEntries {
  entries: Array<{ hash: string; ref: string | null; created_at: string }>;
}

export interface DeliverabilityReputation {
  ip_pool_score: number;
  domain_score: number;
  mailbox_provider_scores: Record<string, number>;
}

export interface AntispamScores {
  tenant_score: number;
  flagged_24h: number;
  samples: Array<Record<string, unknown>>;
}

export interface AbTest {
  id: string;
  name: string;
  status: string;
  primary_metric: string;
  created_at: string;
}

export interface AbVariantResult {
  variant: string;
  assignments: number;
  conversions: number;
  conversion_rate: number;
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

export interface Segment {
  id: string;
  name: string;
  channel: string;
  estimated_size: number | null;
  created_at: string;
}

export interface ChannelInfo {
  id: string;
  enabled: boolean;
  provider: string;
}

export interface ChannelsResponse {
  organization_id?: string | null;
  channels: ChannelInfo[];
}

export interface DsarRequest {
  id: string;
  eta_hours: number;
}

// --- Resource clients ---

export const overview = {
  get: (period = "7d") => api.get<Record<string, unknown>>("/v1/overview", { period }),
};

export const analytics = {
  summary: (params: { from?: string; to?: string; channel?: string } = {}) =>
    api.get<AnalyticsSummary>("/v1/analytics/messages", params as Record<string, string>),
};

export const templates = {
  list: () => api.get<Template[]>("/v1/templates"),
  get: (id: string) => api.get<Template>(`/v1/templates/${id}`),
};

export const journeys = {
  list: () => api.get<Journey[]>("/v1/journeys"),
  create: (body: { name: string; trigger: string; channel: string }) =>
    api.post<Journey>("/v1/journeys", body),
  pause: (id: string) => api.post<Journey>(`/v1/journeys/${id}/pause`),
  resume: (id: string) => api.post<Journey>(`/v1/journeys/${id}/resume`),
};

export const suppression = {
  list: (params: { identifier_type?: string; limit?: number } = {}) =>
    api.get<SuppressionEntry[]>("/v1/suppression", params as Record<string, string | number>),
  add: (body: { identifier_type: string; identifier_value: string; reason: string; source_channel?: string }) =>
    api.post<SuppressionEntry>("/v1/suppression", body),
  remove: (id: string) => api.del<void>(`/v1/suppression/${id}`),
};

export const domains = {
  list: () => api.get<EmailDomain[]>("/v1/domains"),
  create: (domain: string) => api.post<EmailDomain>("/v1/domains", { domain }),
  verify: (id: string) => api.post<EmailDomain>(`/v1/domains/${id}/verify`),
};

export const smsNumbers = {
  list: () => api.get<SmsNumber[]>("/v1/sms-numbers"),
  create: (body: { phone_number: string; label?: string; provider?: string }) =>
    api.post<SmsNumber>("/v1/sms-numbers", body),
};

export const whatsapp = {
  status: () => api.get<WaStatus>("/v1/whatsapp/status"),
  // FE-MESSAGING-08: aligned to backend /v1/whatsapp/templates (new route)
  templates: () => api.get<WaTemplate[]>("/v1/whatsapp/templates"),
};

export const pushApps = {
  list: () => api.get<PushApp[]>("/v1/push-apps"),
  create: (body: { name: string; platform: string }) =>
    api.post<PushApp>("/v1/push-apps", body),
  remove: (id: string) => api.del<void>(`/v1/push-apps/${id}`),
};

export const webhooksMgmt = {
  list: () => api.get<WebhookEndpoint[]>("/v1/webhooks/endpoints"),
  create: (body: { name: string; url: string; events: string[]; secret?: string }) =>
    api.post<WebhookEndpoint>("/v1/webhooks/endpoints", body),
  remove: (id: string) => api.del<void>(`/v1/webhooks/endpoints/${id}`),
};

export const apiTokens = {
  list: () => api.get<ApiToken[]>("/v1/api-tokens"),
  create: (body: { name: string }) => api.post<{ token: string } & ApiToken>("/v1/api-tokens", body),
  revoke: (id: string) => api.del<void>(`/v1/api-tokens/${id}`),
};

export const billing = {
  usageMtd: () => api.get<BillingUsage>("/v1/billing/usage-mtd"),
  invoices: () => api.get<BillingInvoices>("/v1/billing/invoices"),
};

export const chain = {
  // Returns a status object; FE maps it to the chain visualisation.
  list: (_params: { limit?: number } = {}) =>
    api.get<ChainEntries>("/v1/chain"),
  verify: () => api.post<ChainEntries>("/v1/chain/verify"),
};

export const deliverability = {
  reputation: (period = "30d") =>
    api.get<DeliverabilityReputation>("/v1/deliverability", { period }),
};

// FE-MESSAGING-08: was scores() calling non-existent GET /antispam/scores;
// backend now exposes GET /v1/antispam/scores (tenant summary).
export const antispam = {
  scores: () => api.get<AntispamScores>("/v1/antispam/scores"),
  score: (body: { content: string; recipients_count?: number }) =>
    api.post<{ score: number; decision: string; reasons: string[] }>("/v1/antispam/score", body),
};

export const settings = {
  get: () => api.get<WorkspaceSettings>("/v1/settings"),
  update: (body: WorkspaceSettings) => api.put<WorkspaceSettings>("/v1/settings", body),
};

export const team = {
  list: () => api.get<TeamMember[]>("/v1/team"),
  invite: (body: { email: string; role?: string }) =>
    api.post<TeamMember>("/v1/team/invite", body),
};

export const abTests = {
  list: () => api.get<AbTest[]>("/v1/ab-tests"),
  get: (id: string) => api.get<AbTest>(`/v1/ab-tests/${id}`),
  create: (body: Record<string, unknown>) => api.post<AbTest>("/v1/ab-tests", body),
  assign: (testId: string, body: Record<string, unknown>) =>
    api.post<{ variant: string }>(`/v1/ab-tests/${testId}/assign`, body),
  recordEvent: (testId: string, body: Record<string, unknown>) =>
    api.post<void>(`/v1/ab-tests/${testId}/event`, body),
  results: (testId: string) => api.get<AbResults>(`/v1/ab-tests/${testId}/results`),
};

export const segments = {
  list: () => api.get<Segment[]>("/v1/segments"),
  create: (body: Record<string, unknown>) => api.post<Segment>("/v1/segments", body),
  update: (id: string, body: Record<string, unknown>) =>
    api.put<Segment>(`/v1/segments/${id}`, body),
  estimate: (id: string) =>
    api.post<{ estimated_size: number }>(`/v1/segments/${id}/estimate`),
};

export const notifications = {
  channels: () => api.get<ChannelsResponse>("/v1/notifications/channels"),
  send: (body: SendPayload) => api.post<SendResult>("/v1/notifications/send", body),
};

export const lgpd = {
  requestDsar: (body: { subject_email: string }) =>
    api.post<DsarRequest>("/v1/audit/lgpd/dsar", body),
  listDsars: () =>
    api.get<{ dsars: Array<Record<string, unknown>> }>("/v1/audit/lgpd/dsar"),
};

// Silence "unused" on the ambient declaration in environments without Vite.
void importMetaEnv;

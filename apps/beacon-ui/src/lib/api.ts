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

export const apiConfig: ApiConfig = {
  baseUrl: env("VITE_BEACON_API", "/api"),
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

// Silence "unused" on the ambient declaration in environments without Vite.
void importMetaEnv;

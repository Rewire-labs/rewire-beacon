// BCN-230..248: TanStack Query hooks for the 19 BEACON UI pages.
//
// Design:
// - One hook per page entrypoint, all returning the same `{ data, isLoading,
//   isError, isDemo }` envelope.
// - `isDemo` is true when the backend responded non-OK and we fell back to
//   `@/content/beacon-mock`. Pages render a yellow "Modo demo" banner via
//   `<DemoBanner />` (see `apps/beacon-ui/src/components/beacon/DemoBanner.tsx`).
// - Each hook supplies `initialData` from the mock module so the first paint
//   is never blank. The query is then retried in background; on success we
//   swap to real data.
//
// Pattern intentionally mirrors `apps/pulse-cloud-ui/src/lib/pulseApi.ts`
// (gold standard) — see ADR-0017 chat-orchestrator UI conventions.

import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import * as api from "@/lib/api";
import { api as rawApi } from "@/lib/api";
import * as mock from "@/content/beacon-mock";

export interface DemoEnvelope<T> {
  data: T;
  isLoading: boolean;
  isError: boolean;
  isDemo: boolean;
  refetch: () => void;
}

function envelope<T>(q: UseQueryResult<T, Error>, fallback: T): DemoEnvelope<T> {
  const isDemo = q.isError || (!q.isFetching && q.data === undefined);
  return {
    data: (q.data ?? fallback) as T,
    isLoading: q.isLoading,
    isError: q.isError,
    isDemo,
    refetch: () => void q.refetch(),
  };
}

// ----- BCN-230: Overview ----------------------------------------------------

export function useBeaconOverview() {
  const q = useQuery({
    queryKey: ["beacon-overview"],
    queryFn: () => api.overview.get(),
    retry: 1,
    staleTime: 30_000,
  });
  return envelope(q, {
    mtd_email: mock.BEACON_USER.mtd_email,
    mtd_sms: mock.BEACON_USER.mtd_sms,
    mtd_push: mock.BEACON_USER.mtd_push,
    mtd_wa: mock.BEACON_USER.mtd_wa,
    mtd_spend_brl: mock.BEACON_USER.mtd_spend_brl,
    delivered_rate: 0.98,
    open_rate_email: 0.62,
    verified_domains: mock.DOMAINS.filter((d) => d.verified).length,
    total_domains: mock.DOMAINS.length,
    generated_at: new Date().toISOString(),
  });
}

// ----- BCN-231: Messages ----------------------------------------------------

export function useBeaconMessages(params?: { channel?: string; status?: string; limit?: number }) {
  const q = useQuery({
    queryKey: ["beacon-messages", params ?? {}],
    queryFn: () => api.analytics.summary({ channel: params?.channel }).then((r) => r.rows),
    retry: 1,
    staleTime: 15_000,
  });
  return envelope(q, mock.MESSAGES as unknown as Array<Record<string, unknown>>);
}

// ----- BCN-232: Templates ---------------------------------------------------

export function useBeaconTemplates() {
  const q = useQuery({
    queryKey: ["beacon-templates"],
    queryFn: () => api.templates.list(),
    retry: 1,
    staleTime: 60_000,
  });
  return envelope(q, mock.TEMPLATES as unknown as Array<{ id: string; name: string; channel: string; enabled: boolean }>);
}

// ----- BCN-233: Journeys ----------------------------------------------------

export function useBeaconJourneys() {
  const q = useQuery({
    queryKey: ["beacon-journeys"],
    queryFn: () => api.journeys.list(),
    retry: 1,
    staleTime: 30_000,
  });
  return envelope(q, mock.JOURNEYS as unknown as Array<{ id: string; name: string; status: string }>);
}

// ----- BCN-234: Suppression -------------------------------------------------

export function useBeaconSuppression(params?: { identifier_type?: string; limit?: number }) {
  const q = useQuery({
    queryKey: ["beacon-suppression", params ?? {}],
    queryFn: () =>
      api.suppression.list({
        identifier_type: params?.identifier_type,
        limit: params?.limit,
      }),
    retry: 1,
    staleTime: 30_000,
  });
  return envelope(q, (mock.SUPPRESSIONS ?? []) as unknown as api.SuppressionEntry[]);
}

// ----- BCN-235: Domains -----------------------------------------------------

export function useBeaconDomains() {
  const q = useQuery({
    queryKey: ["beacon-domains"],
    queryFn: () => api.domains.list(),
    retry: 1,
    staleTime: 60_000,
  });
  return envelope(q, mock.DOMAINS as unknown as api.EmailDomain[]);
}

// ----- BCN-236: SMS numbers -------------------------------------------------

export function useBeaconSmsNumbers() {
  const q = useQuery({
    queryKey: ["beacon-sms-numbers"],
    queryFn: () => api.smsNumbers.list(),
    retry: 1,
    staleTime: 60_000,
  });
  return envelope(q, (mock.SMS_NUMBERS ?? []) as unknown as Array<{ id: string; number: string; country: string; status: string }>);
}

// ----- BCN-237: WhatsApp ----------------------------------------------------

export function useBeaconWhatsapp() {
  const status = useQuery({
    queryKey: ["beacon-wa-status"],
    queryFn: () => api.whatsapp.status(),
    retry: 1,
    staleTime: 30_000,
  });
  const templates = useQuery({
    queryKey: ["beacon-wa-templates"],
    queryFn: () => api.whatsapp.templates(),
    retry: 1,
    staleTime: 60_000,
  });
  const fallbackStatus = { connected: false, quality_rating: "demo", templates_synced: 0 };
  const fallbackTemplates: Array<{ id: string; name: string; category: string; status: string }> = [];
  return {
    status: envelope(status, fallbackStatus),
    templates: envelope(templates, fallbackTemplates),
    isDemo: status.isError || templates.isError,
  };
}

// ----- BCN-238: Push apps ---------------------------------------------------

export function useBeaconPushApps() {
  const q = useQuery({
    queryKey: ["beacon-push-apps"],
    queryFn: () => api.pushApps.list(),
    retry: 1,
    staleTime: 60_000,
  });
  return envelope(q, (mock.PUSH_APPS ?? []) as unknown as Array<{ id: string; name: string; platform: string }>);
}

// ----- BCN-239: Webhooks ----------------------------------------------------

export function useBeaconWebhooks() {
  const q = useQuery({
    queryKey: ["beacon-webhooks"],
    queryFn: () => api.webhooksMgmt.list(),
    retry: 1,
    staleTime: 30_000,
  });
  return envelope(q, (mock.WEBHOOKS ?? []) as unknown as Array<{ id: string; url: string; events: string[]; status: string }>);
}

// ----- BCN-240: Analytics ---------------------------------------------------

export function useBeaconAnalytics(params: { from?: string; to?: string; channel?: string }) {
  const q = useQuery({
    queryKey: ["beacon-analytics", params],
    queryFn: () => api.analytics.summary(params),
    retry: 1,
    staleTime: 60_000,
  });
  return envelope(q, {
    from: params.from ?? "",
    to: params.to ?? "",
    rows: mock.ANALYTICS_30D.by_channel as unknown as Array<Record<string, unknown>>,
  });
}

// ----- BCN-241: API keys ----------------------------------------------------

export function useBeaconApiKeys() {
  const q = useQuery({
    queryKey: ["beacon-api-tokens"],
    queryFn: () => api.apiTokens.list(),
    retry: 1,
    staleTime: 30_000,
  });
  return envelope(q, (mock.API_KEYS ?? []) as unknown as api.ApiToken[]);
}

// ----- BCN-242: LGPD (DSAR list — server-driven) ----------------------------

export function useBeaconLgpd() {
  // Most LGPD flows are write-only (`POST /audit/lgpd/dsar`). The page
  // shows recent DSARs via a list endpoint that's wired in V0.2; until then
  // we render the mock journey of opened DSARs.
  const q = useQuery({
    queryKey: ["beacon-lgpd-dsars"],
    queryFn: () => rawApi<{ dsars: Array<Record<string, unknown>> }>("/audit/lgpd/dsar"),
    retry: 1,
    staleTime: 60_000,
  });
  return envelope(q, { dsars: (mock.DSAR_REQUESTS ?? []) as unknown as Array<Record<string, unknown>> });
}

// ----- BCN-243: Billing -----------------------------------------------------

export function useBeaconBilling() {
  const usage = useQuery({
    queryKey: ["beacon-billing-usage"],
    queryFn: () => api.billing.usageMtd(),
    retry: 1,
    staleTime: 60_000,
  });
  const invoices = useQuery({
    queryKey: ["beacon-billing-invoices"],
    queryFn: () => api.billing.invoices(),
    retry: 1,
    staleTime: 60_000,
  });
  const fallbackUsage = {
    month_starting: new Date().toISOString().slice(0, 10),
    counts: {
      email: mock.BEACON_USER.mtd_email,
      sms: mock.BEACON_USER.mtd_sms,
      push: mock.BEACON_USER.mtd_push,
      whatsapp: mock.BEACON_USER.mtd_wa,
    } as Record<string, number>,
  };
  return {
    usage: envelope(usage, fallbackUsage),
    invoices: envelope(invoices, { invoices: (mock.BILLING_BREAKDOWN ?? []) as unknown[] }),
    isDemo: usage.isError || invoices.isError,
  };
}

// ----- BCN-244: Chain visualization -----------------------------------------

export function useBeaconChain(limit = 50) {
  const q = useQuery({
    queryKey: ["beacon-chain", limit],
    queryFn: () => api.chain.list({ limit }),
    retry: 1,
    staleTime: 30_000,
  });
  // mock ChainEntry shape differs slightly from API; map fields.
  const entries = (mock.CHAIN_ENTRIES ?? []).map((e) => ({
    hash: e.hash,
    ref: e.prev_hash ?? null,
    created_at: e.ts,
  }));
  return envelope(q, { entries });
}

// ----- BCN-245: Deliverability ----------------------------------------------

export function useBeaconDeliverability() {
  const q = useQuery({
    queryKey: ["beacon-deliverability"],
    queryFn: () => api.deliverability.reputation(),
    retry: 1,
    staleTime: 60_000,
  });
  return envelope(q, {
    ip_pool_score: 0.96,
    domain_score: 0.94,
    mailbox_provider_scores: { gmail: 0.97, outlook: 0.91, uol: 0.93 } as Record<string, number>,
  });
}

// ----- BCN-246: Antispam ML --------------------------------------------------

export function useBeaconAntispam() {
  const q = useQuery({
    queryKey: ["beacon-antispam"],
    queryFn: () => api.antispam.scores(),
    retry: 1,
    staleTime: 60_000,
  });
  return envelope(q, {
    tenant_score: 0.12,
    flagged_24h: 0,
    samples: [] as Array<Record<string, unknown>>,
  });
}

// ----- BCN-247: Settings ----------------------------------------------------

export function useBeaconSettings() {
  const q = useQuery({
    queryKey: ["beacon-settings"],
    queryFn: () => api.settings.get(),
    retry: 1,
    staleTime: 60_000,
  });
  return envelope(q, {
    org: {
      name: mock.BEACON_USER.org,
      cnpj: mock.BEACON_USER.cnpj,
      tier: mock.BEACON_USER.tier,
      region: mock.BEACON_USER.region,
    } as Record<string, unknown>,
  });
}

// ----- BCN-248: Team --------------------------------------------------------

export function useBeaconTeam() {
  const q = useQuery({
    queryKey: ["beacon-team"],
    queryFn: () => api.team.list(),
    retry: 1,
    staleTime: 60_000,
  });
  return envelope(q, (mock.TEAM ?? []) as unknown as Array<{ id: string; email: string; role: string }>);
}

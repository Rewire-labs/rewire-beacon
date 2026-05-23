// Mock data — BEACON Notification Platform Multi-Canal BR
export type Tier = "hobby" | "starter" | "growth" | "scale" | "enterprise";
export const TIER_LABELS: Record<Tier, string> = {
  hobby: "Hobby", starter: "Starter", growth: "Growth", scale: "Scale", enterprise: "Enterprise",
};

export const BEACON_USER = {
  name: "Camila Tessari",
  initial: "C",
  org: "Pampa Pay Tecnologia",
  cnpj: "39.221.448/0001-72",
  tier: "growth" as Tier,
  role: "Engineering Manager",
  mtd_email: 712_440,
  mtd_email_quota: 1_000_000,
  mtd_sms: 64_120,
  mtd_sms_quota: 100_000,
  mtd_push: 482_991,
  mtd_push_quota: 1_000_000,
  mtd_wa: 31_204,
  mtd_wa_quota: 50_000,
  mtd_spend_brl: 2_417.55,
  mtd_cap_brl: 4_000,
  region: "br-sp1",
};

export type Channel = "email" | "sms" | "whatsapp" | "push_ios" | "push_android" | "push_web";
export const CHANNEL_LABELS: Record<Channel, string> = {
  email: "Email", sms: "SMS", whatsapp: "WhatsApp",
  push_ios: "Push iOS", push_android: "Push Android", push_web: "Push Web",
};

// ---------- Messages (event log) ----------
export type Message = {
  id: string;
  channel: Channel;
  recipient: string;
  template?: string;
  subject_or_title?: string;
  status: "sent" | "delivered" | "opened" | "clicked" | "bounced" | "complained" | "failed";
  provider: "postal" | "aws_ses" | "zenvia" | "totalvoice" | "apns" | "fcm" | "webpush" | "connect_whatsapp";
  sent_at: string;
  delivered_at?: string;
  cost_brl: number;
  lawful_basis: "consent" | "contract" | "legal_obligation" | "legitimate_interest";
  chain_hash: string;
};

const now = Date.now();
const ago = (m: number) => new Date(now - m * 60_000).toISOString();

export const MESSAGES: Message[] = [
  { id: "msg_01HV9TZ", channel: "email", recipient: "joao.silva@uol.com.br", template: "order_confirmation", subject_or_title: "Pedido #28117 confirmado", status: "opened", provider: "postal", sent_at: ago(3), delivered_at: ago(2), cost_brl: 0.0015, lawful_basis: "contract", chain_hash: "b3:9f4e2c1a..." },
  { id: "msg_01HV9TX", channel: "sms", recipient: "+5511987654321", template: "otp_pix", subject_or_title: "Código: 391822", status: "delivered", provider: "zenvia", sent_at: ago(5), delivered_at: ago(4), cost_brl: 0.09, lawful_basis: "legal_obligation", chain_hash: "b3:7d3a1b88..." },
  { id: "msg_01HV9TQ", channel: "whatsapp", recipient: "+5521991122334", template: "shipping_update", status: "delivered", provider: "connect_whatsapp", sent_at: ago(7), delivered_at: ago(7), cost_brl: 0.18, lawful_basis: "contract", chain_hash: "b3:ec441099..." },
  { id: "msg_01HV9TM", channel: "push_ios", recipient: "ios:6fa3e1d8...4b", template: "abandoned_cart", subject_or_title: "Esqueceu algo no carrinho?", status: "delivered", provider: "apns", sent_at: ago(10), delivered_at: ago(10), cost_brl: 0.00001, lawful_basis: "consent", chain_hash: "b3:11883abc..." },
  { id: "msg_01HV9TJ", channel: "push_android", recipient: "fcm:eK4xQ...91", template: "campaign_friday", status: "clicked", provider: "fcm", sent_at: ago(14), delivered_at: ago(13), cost_brl: 0.00001, lawful_basis: "consent", chain_hash: "b3:5582cd00..." },
  { id: "msg_01HV9T7", channel: "email", recipient: "ana.dias@gmail.com", template: "password_reset", subject_or_title: "Redefinir sua senha", status: "delivered", provider: "postal", sent_at: ago(22), delivered_at: ago(21), cost_brl: 0.0015, lawful_basis: "contract", chain_hash: "b3:cc99af22..." },
  { id: "msg_01HV9SY", channel: "email", recipient: "diretoria@grupocafe.com.br", template: "weekly_report", subject_or_title: "Resumo semanal", status: "bounced", provider: "postal", sent_at: ago(34), cost_brl: 0.0015, lawful_basis: "legitimate_interest", chain_hash: "b3:3311aaff..." },
  { id: "msg_01HV9SS", channel: "sms", recipient: "+5547999881122", template: "appointment_reminder", subject_or_title: "Sua consulta é amanhã 14h", status: "delivered", provider: "totalvoice", sent_at: ago(45), delivered_at: ago(44), cost_brl: 0.08, lawful_basis: "consent", chain_hash: "b3:998ee311..." },
  { id: "msg_01HV9SK", channel: "push_web", recipient: "vapid:BNw1...zZ", template: "news_alert", status: "delivered", provider: "webpush", sent_at: ago(57), delivered_at: ago(57), cost_brl: 0.00001, lawful_basis: "consent", chain_hash: "b3:ff21eecc..." },
  { id: "msg_01HV9SC", channel: "whatsapp", recipient: "+5511933556677", template: "two_factor_auth", subject_or_title: "Código 4422", status: "delivered", provider: "connect_whatsapp", sent_at: ago(78), delivered_at: ago(78), cost_brl: 0.15, lawful_basis: "legal_obligation", chain_hash: "b3:228bb144..." },
  { id: "msg_01HV9S2", channel: "email", recipient: "fulano@empresa-x.com", template: "welcome_v3", subject_or_title: "Bem-vindo à Pampa Pay", status: "complained", provider: "postal", sent_at: ago(120), cost_brl: 0.0015, lawful_basis: "consent", chain_hash: "b3:bb8800cc..." },
  { id: "msg_01HV9R8", channel: "sms", recipient: "+5531987779922", template: "delivery_update", status: "failed", provider: "zenvia", sent_at: ago(180), cost_brl: 0, lawful_basis: "contract", chain_hash: "b3:0099aabb..." },
];

// ---------- Templates ----------
export type Template = {
  id: string;
  name: string;
  channel: Channel;
  category: "transactional" | "marketing" | "security" | "system";
  enabled: boolean;
  variables: string[];
  last_used: string;
  sent_30d: number;
  open_rate?: number;
  click_rate?: number;
};

export const TEMPLATES: Template[] = [
  { id: "tpl_otp_pix", name: "OTP PIX (SMS)", channel: "sms", category: "security", enabled: true, variables: ["codigo", "expires_min"], last_used: ago(5), sent_30d: 48_220 },
  { id: "tpl_order_confirmation", name: "Pedido confirmado", channel: "email", category: "transactional", enabled: true, variables: ["pedido_id", "total", "items"], last_used: ago(3), sent_30d: 122_881, open_rate: 0.62, click_rate: 0.28 },
  { id: "tpl_password_reset", name: "Reset de senha", channel: "email", category: "security", enabled: true, variables: ["nome", "magic_link"], last_used: ago(22), sent_30d: 18_400, open_rate: 0.78, click_rate: 0.71 },
  { id: "tpl_welcome_v3", name: "Welcome v3", channel: "email", category: "transactional", enabled: true, variables: ["nome"], last_used: ago(120), sent_30d: 9_410, open_rate: 0.55, click_rate: 0.18 },
  { id: "tpl_abandoned_cart", name: "Abandono de carrinho", channel: "push_ios", category: "marketing", enabled: true, variables: ["produto", "valor"], last_used: ago(10), sent_30d: 38_882 },
  { id: "tpl_shipping_update", name: "Atualização de envio (WA)", channel: "whatsapp", category: "transactional", enabled: true, variables: ["rastreio", "previsao"], last_used: ago(7), sent_30d: 17_022 },
  { id: "tpl_two_factor_auth", name: "2FA WhatsApp", channel: "whatsapp", category: "security", enabled: true, variables: ["codigo"], last_used: ago(78), sent_30d: 9_801 },
  { id: "tpl_campaign_friday", name: "Black Friday push", channel: "push_android", category: "marketing", enabled: false, variables: ["desconto"], last_used: ago(14), sent_30d: 4_280 },
  { id: "tpl_news_alert", name: "Alerta de notícia web", channel: "push_web", category: "marketing", enabled: true, variables: ["headline", "url"], last_used: ago(57), sent_30d: 11_900 },
  { id: "tpl_weekly_report", name: "Resumo semanal", channel: "email", category: "transactional", enabled: true, variables: ["semana", "metricas"], last_used: ago(34), sent_30d: 1_220, open_rate: 0.41, click_rate: 0.09 },
];

// ---------- Journeys (Temporal multi-step) ----------
export type Journey = {
  id: string; name: string; enabled: boolean; steps: number;
  trigger: string; active_runs: number; completed_30d: number; conversion_rate: number;
};
export const JOURNEYS: Journey[] = [
  { id: "jrn_winback", name: "Win-back cliente inativo", enabled: true, steps: 4, trigger: "user.inactive_30d", active_runs: 1_881, completed_30d: 4_212, conversion_rate: 0.18 },
  { id: "jrn_onboarding", name: "Onboarding novo cliente", enabled: true, steps: 6, trigger: "user.created", active_runs: 412, completed_30d: 1_910, conversion_rate: 0.72 },
  { id: "jrn_cart_abandon", name: "Recuperar carrinho", enabled: true, steps: 3, trigger: "cart.abandoned_2h", active_runs: 902, completed_30d: 8_410, conversion_rate: 0.31 },
  { id: "jrn_dunning", name: "Cobrança fatura atrasada", enabled: true, steps: 5, trigger: "invoice.overdue", active_runs: 188, completed_30d: 612, conversion_rate: 0.64 },
  { id: "jrn_renewal", name: "Renovação anual", enabled: false, steps: 4, trigger: "subscription.renewing_30d", active_runs: 0, completed_30d: 187, conversion_rate: 0.81 },
];

// ---------- Domains (Email senders) ----------
export type EmailDomain = {
  id: string; domain: string; verified: boolean; dkim_verified: boolean;
  spf_verified: boolean; dmarc_verified: boolean; reputation: number;
  dedicated_ip?: string; daily_limit: number; sent_30d: number;
};
export const DOMAINS: EmailDomain[] = [
  { id: "dom_pampa", domain: "pampapay.com.br", verified: true, dkim_verified: true, spf_verified: true, dmarc_verified: true, reputation: 96, dedicated_ip: "200.18.42.11", daily_limit: 250_000, sent_30d: 612_000 },
  { id: "dom_pampa_app", domain: "notify.pampapay.com.br", verified: true, dkim_verified: true, spf_verified: true, dmarc_verified: false, reputation: 88, daily_limit: 50_000, sent_30d: 88_400 },
  { id: "dom_pampa_mkt", domain: "mkt.pampapay.com.br", verified: false, dkim_verified: false, spf_verified: true, dmarc_verified: false, reputation: 0, daily_limit: 5_000, sent_30d: 0 },
];

// ---------- SMS numbers ----------
export type SmsNumber = {
  id: string; type: "short_code" | "long_code"; number: string;
  provider: "zenvia" | "totalvoice"; country: "BR"; two_way: boolean; sent_30d: number;
};
export const SMS_NUMBERS: SmsNumber[] = [
  { id: "sms_28991", type: "short_code", number: "28991", provider: "zenvia", country: "BR", two_way: true, sent_30d: 48_220 },
  { id: "sms_long_sp", type: "long_code", number: "+551140025522", provider: "zenvia", country: "BR", two_way: true, sent_30d: 14_882 },
  { id: "sms_long_rs", type: "long_code", number: "+555133887700", provider: "totalvoice", country: "BR", two_way: false, sent_30d: 1_018 },
];

// ---------- WhatsApp numbers (via CONNECT) ----------
export type WaNumber = {
  id: string; number: string; quality: "green" | "yellow" | "red";
  tier: "tier_1k" | "tier_10k" | "tier_100k" | "tier_unlimited";
  templates_approved: number; sent_30d: number;
};
export const WA_NUMBERS: WaNumber[] = [
  { id: "wa_main", number: "+551140025500", quality: "green", tier: "tier_100k", templates_approved: 17, sent_30d: 28_991 },
  { id: "wa_support", number: "+551140025501", quality: "yellow", tier: "tier_10k", templates_approved: 6, sent_30d: 2_213 },
];

// ---------- Push apps ----------
export type PushApp = {
  id: string; name: string; platform: "ios" | "android" | "web";
  bundle: string; configured: boolean; subscribers: number; sent_30d: number;
};
export const PUSH_APPS: PushApp[] = [
  { id: "push_ios_main", name: "Pampa Pay iOS", platform: "ios", bundle: "br.com.pampapay.app", configured: true, subscribers: 188_400, sent_30d: 412_018 },
  { id: "push_and_main", name: "Pampa Pay Android", platform: "android", bundle: "br.com.pampapay.app", configured: true, subscribers: 312_811, sent_30d: 712_400 },
  { id: "push_web_main", name: "Portal Web", platform: "web", bundle: "portal.pampapay.com.br", configured: true, subscribers: 44_120, sent_30d: 28_810 },
  { id: "push_ios_dash", name: "Pampa Dashboard iOS", platform: "ios", bundle: "br.com.pampapay.dashboard", configured: false, subscribers: 0, sent_30d: 0 },
];

// ---------- Suppression list ----------
export type Suppression = {
  id: string; identifier_type: "email" | "phone" | "device_token";
  identifier_value: string; channels: string[];
  reason: "user_unsubscribed" | "hard_bounce" | "complaint" | "manual" | "dpo_request";
  added_at: string;
};
export const SUPPRESSIONS: Suppression[] = [
  { id: "sup_1", identifier_type: "email", identifier_value: "fulano@empresa-x.com", channels: ["email"], reason: "complaint", added_at: ago(120) },
  { id: "sup_2", identifier_type: "email", identifier_value: "diretoria@grupocafe.com.br", channels: ["email"], reason: "hard_bounce", added_at: ago(34) },
  { id: "sup_3", identifier_type: "phone", identifier_value: "+5511955334411", channels: ["sms", "whatsapp"], reason: "user_unsubscribed", added_at: ago(880) },
  { id: "sup_4", identifier_type: "email", identifier_value: "lgpd@pessoa-dpo.com", channels: ["email", "sms", "whatsapp", "push_ios", "push_android", "push_web"], reason: "dpo_request", added_at: ago(2880) },
  { id: "sup_5", identifier_type: "device_token", identifier_value: "ios:expired-token-22", channels: ["push_ios"], reason: "hard_bounce", added_at: ago(4400) },
];

// ---------- Webhooks ----------
export type Webhook = {
  id: string; url: string; events: string[]; enabled: boolean;
  last_delivery: string; success_rate_30d: number; deliveries_30d: number;
};
export const WEBHOOKS: Webhook[] = [
  { id: "wh_main", url: "https://api.pampapay.com.br/webhooks/beacon", events: ["message.delivered", "message.opened", "message.clicked", "message.bounced", "message.complained"], enabled: true, last_delivery: ago(2), success_rate_30d: 0.998, deliveries_30d: 818_412 },
  { id: "wh_analytics", url: "https://analytics.pampapay.com.br/in/beacon", events: ["message.opened", "message.clicked"], enabled: true, last_delivery: ago(6), success_rate_30d: 0.991, deliveries_30d: 412_002 },
  { id: "wh_dr", url: "https://dr.pampapay.com.br/beacon-mirror", events: ["*"], enabled: false, last_delivery: ago(7200), success_rate_30d: 0.42, deliveries_30d: 0 },
];

// ---------- Analytics ----------
export const ANALYTICS_30D = {
  by_channel: [
    { channel: "email", sent: 712_440, delivered: 698_011, opened: 322_881, clicked: 88_142, bounced: 14_429, complained: 412 },
    { channel: "sms", sent: 64_120, delivered: 63_018, opened: 0, clicked: 0, bounced: 1_102, complained: 0 },
    { channel: "whatsapp", sent: 31_204, delivered: 30_991, opened: 28_410, clicked: 12_880, bounced: 213, complained: 0 },
    { channel: "push_ios", sent: 412_018, delivered: 408_002, opened: 88_400, clicked: 22_881, bounced: 4_016, complained: 0 },
    { channel: "push_android", sent: 712_400, delivered: 698_122, opened: 188_400, clicked: 44_001, bounced: 14_278, complained: 0 },
    { channel: "push_web", sent: 28_810, delivered: 28_440, opened: 8_812, clicked: 1_802, bounced: 370, complained: 0 },
  ],
  sparkline: [42, 51, 48, 67, 72, 81, 73, 79, 88, 92, 86, 91, 97, 102],
};

// ---------- Anti-spam alerts ----------
export type AntiSpamAlert = {
  id: string; org_affected: string; severity: "low" | "medium" | "high" | "critical";
  pattern: string; detected_at: string; status: "investigating" | "blocked" | "whitelisted";
  messages_held: number;
};
export const ANTISPAM_ALERTS: AntiSpamAlert[] = [
  { id: "as_1", org_affected: "Pampa Pay Tecnologia", severity: "low", pattern: "Padrão normal — sem alertas ativos", detected_at: ago(2400), status: "whitelisted", messages_held: 0 },
];

// ---------- Deliverability per provider ----------
export const DELIVERABILITY = [
  { provider: "Postal (IPs próprios)", channel: "email", delivered_rate: 0.984, bounce_rate: 0.020, complaint_rate: 0.0006, reputation: 96 },
  { provider: "AWS SES sa-east-1", channel: "email", delivered_rate: 0.979, bounce_rate: 0.018, complaint_rate: 0.0008, reputation: 92 },
  { provider: "Zenvia", channel: "sms", delivered_rate: 0.983, bounce_rate: 0.017, complaint_rate: 0, reputation: 95 },
  { provider: "TotalVoice", channel: "sms", delivered_rate: 0.971, bounce_rate: 0.029, complaint_rate: 0, reputation: 88 },
  { provider: "APNs", channel: "push_ios", delivered_rate: 0.990, bounce_rate: 0.010, complaint_rate: 0, reputation: 99 },
  { provider: "FCM", channel: "push_android", delivered_rate: 0.980, bounce_rate: 0.020, complaint_rate: 0, reputation: 97 },
  { provider: "WebPush", channel: "push_web", delivered_rate: 0.987, bounce_rate: 0.013, complaint_rate: 0, reputation: 96 },
  { provider: "CONNECT WhatsApp", channel: "whatsapp", delivered_rate: 0.993, bounce_rate: 0.007, complaint_rate: 0, reputation: 98 },
];

// ---------- API keys ----------
export type ApiKey = {
  id: string; name: string; prefix: string; scopes: string[];
  created_at: string; last_used: string; created_by: string;
};
export const API_KEYS: ApiKey[] = [
  { id: "key_1", name: "Backend produção", prefix: "bcn_live_4k9...", scopes: ["messages:send", "analytics:read"], created_at: ago(40_000), last_used: ago(2), created_by: "Camila Tessari" },
  { id: "key_2", name: "App mobile iOS", prefix: "bcn_live_88x...", scopes: ["messages:send:push"], created_at: ago(28_000), last_used: ago(8), created_by: "Rafael Lima" },
  { id: "key_3", name: "Marketing CI", prefix: "bcn_live_xa2...", scopes: ["templates:write", "journeys:write"], created_at: ago(14_000), last_used: ago(220), created_by: "Marina Soares" },
];

// ---------- LGPD ----------
export type DsarRequest = {
  id: string; identifier: string; type: "access" | "deletion" | "portability";
  status: "received" | "in_progress" | "fulfilled";
  received_at: string; deadline_at: string; messages_found?: number;
};
export const DSAR_REQUESTS: DsarRequest[] = [
  { id: "dsar_1", identifier: "alessandro@profitor.com.br", type: "access", status: "fulfilled", received_at: ago(8800), deadline_at: ago(-100), messages_found: 412 },
  { id: "dsar_2", identifier: "+5511944556677", type: "deletion", status: "in_progress", received_at: ago(1400), deadline_at: ago(-7200) },
  { id: "dsar_3", identifier: "natalia.borges@example.com.br", type: "access", status: "received", received_at: ago(60), deadline_at: ago(-21000) },
];

// ---------- Audit chain ----------
export type ChainEntry = {
  id: string; ts: string; actor: string; action: string;
  target: string; hash: string; prev_hash: string;
};
export const CHAIN_ENTRIES: ChainEntry[] = [
  { id: "ch_1", ts: ago(2), actor: "api:key_1", action: "message.send.email", target: "msg_01HV9TZ", hash: "b3:9f4e2c1a8d2c...", prev_hash: "b3:7d3a1b88..." },
  { id: "ch_2", ts: ago(5), actor: "api:key_1", action: "message.send.sms", target: "msg_01HV9TX", hash: "b3:7d3a1b8898ef...", prev_hash: "b3:ec441099..." },
  { id: "ch_3", ts: ago(20), actor: "user:camila@pampapay.com.br", action: "template.update", target: "tpl_welcome_v3", hash: "b3:331199aabbcc...", prev_hash: "b3:88aacc11..." },
  { id: "ch_4", ts: ago(120), actor: "system:antispam", action: "suppression.add", target: "fulano@empresa-x.com", hash: "b3:bb8800cc22ee...", prev_hash: "b3:118822ff..." },
  { id: "ch_5", ts: ago(1400), actor: "user:dpo@pampapay.com.br", action: "dsar.received", target: "+5511944556677", hash: "b3:dd44ee88aa11...", prev_hash: "b3:01122334..." },
];

// ---------- Billing ----------
export const BILLING_BREAKDOWN = [
  { item: "Plano Growth (R$ 1.997 mensal)", qty: 1, unit: "—", total_brl: 1997.00 },
  { item: "Email overage (acima de 1M)", qty: 0, unit: "R$ 1,50 / 1k", total_brl: 0 },
  { item: "SMS BR Zenvia (markup 30%)", qty: 4_120, unit: "R$ 0,09", total_brl: 370.80 },
  { item: "WhatsApp utility (Meta + 30%)", qty: 412, unit: "R$ 0,15", total_brl: 61.80 },
  { item: "Push (APNs + FCM + Web)", qty: 1_153_228, unit: "R$ 0,01 / 1k", total_brl: 11.53 },
  { item: "Dedicated IP email (1)", qty: 1, unit: "R$ 297", total_brl: 297.00 },
];

// ---------- Team ----------
export type TeamMember = {
  id: string; name: string; email: string; role: "owner" | "admin" | "developer" | "marketer" | "viewer";
  sso: boolean; last_active: string;
};
export const TEAM: TeamMember[] = [
  { id: "u1", name: "Camila Tessari", email: "camila@pampapay.com.br", role: "owner", sso: true, last_active: ago(2) },
  { id: "u2", name: "Rafael Lima", email: "rafael@pampapay.com.br", role: "developer", sso: true, last_active: ago(40) },
  { id: "u3", name: "Marina Soares", email: "marina@pampapay.com.br", role: "marketer", sso: true, last_active: ago(180) },
  { id: "u4", name: "Eduardo Pacheco (DPO)", email: "dpo@pampapay.com.br", role: "admin", sso: true, last_active: ago(1400) },
  { id: "u5", name: "Auditoria externa", email: "audit@deloitte.com.br", role: "viewer", sso: false, last_active: ago(8000) },
];

// ---------- Cross-sell ----------
export const CROSS_SELL = [
  { product: "CONNECT", status: "active", from: "WhatsApp Channel" },
  { product: "CITADEL", status: "active", from: "Audit Chain" },
  { product: "AUDIT TRAIL", status: "active", from: "Compliance Evidence" },
  { product: "GUARDIAN", status: "trial", from: "Alert routing" },
  { product: "FOUNDRY", status: "available", from: "Golden paths" },
  { product: "HOST", status: "active", from: "SDK pré-instalado" },
];

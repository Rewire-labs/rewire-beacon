# BEACON — API Specification

> Backend contract para substituir os dados mockados em `src/content/beacon-mock.ts` e abastecer as 19 telas em `src/pages/beacon/*`.
> Stack alvo: FastAPI 0.115 + Postgres 17 + ClickHouse 24 + Redis 7.4 + Kafka (Strimzi) + Temporal 1.25 + Authentik OIDC + OpenBao.
> Base URL: `https://api.beacon.rewirelabs.dev/v1`
> Auth: `Authorization: Bearer <jwt_oidc>` (UI) ou `Authorization: Bearer bcn_live_…` (API token por tenant).
> Multi-tenant: header obrigatório `X-Organization-Id` para tokens com escopo cross-org; RLS no Postgres por `organization_id`.
> Erros: RFC 7807 (`application/problem+json`) com `type`, `title`, `status`, `detail`, `instance`, `trace_id`.

---

## 0. Convenções

| Recurso | Prefixo de ID | Notas |
|---|---|---|
| Organization | `org_` | tenant raiz |
| Message | `msg_01H…` | ULID 26 chars |
| Template | `tpl_` | slug-friendly |
| Journey | `jrn_` | Temporal workflow id |
| Domain | `dom_` | email sender |
| SMS number | `sms_` | E.164 normalizado |
| WhatsApp number | `wa_` | espelho do CONNECT |
| Push app | `push_` | iOS/Android/Web |
| Suppression entry | `sup_` | cross-canal |
| Webhook endpoint | `wh_` | |
| API key | `key_` | prefix público `bcn_live_…` |
| DSAR request | `dsar_` | LGPD Art. 18 |
| Chain entry | `ch_` | hash BLAKE3 |

Paginação cursor-based: `?limit=50&cursor=…`. Resposta: `{ data: [...], next_cursor, total_estimate }`.
Timestamps em ISO 8601 UTC. Valores monetários em `Decimal` string (`"0.0015"`) em BRL.
Idempotência: header `Idempotency-Key` aceito em todos os `POST /messages/*`, TTL 24h.

---

## 1. Auth & Session

- `POST /auth/oidc/exchange` — troca authorization code Authentik por session JWT BEACON.
- `GET /me` → `BEACON_USER` (`name`, `org`, `cnpj`, `tier`, `role`, quotas MTD, spend MTD/cap).
- `GET /org/quotas/mtd` → `{ email, sms, push, whatsapp, spend_brl, cap_brl, period_start, period_end }` (drives Topbar e Overview).

---

## 2. Messages (hot path · envio)

Endpoints assíncronos (`202 Accepted`) que enfileiram no Kafka topic `beacon.send.<channel>.<tier>` após: rate limit → suppression check → frequency cap → anti-spam ML → template render → CITADEL anchor.

| Verbo | Rota | Notas |
|---|---|---|
| POST | `/messages/email` | `from, to, subject, html_body|text_body|template_id, template_variables, attachments, headers, tags, lawful_basis, tracking{opens,clicks}` |
| POST | `/messages/sms` | `from, to (E.164), body|template_id, lawful_basis` |
| POST | `/messages/whatsapp` | delega para CONNECT `POST /internal/whatsapp/send` |
| POST | `/messages/push` | `app_id, to{device_tokens|topic|user_ids}, title, body, image_url, deep_link, actions, template_id` |
| GET | `/messages` | filtros: `channel, status, from_date, to_date, template_id, recipient` (para tela **Mensagens**) |
| GET | `/messages/{id}` | inclui `chain_hash`, `provider_used`, `cost_brl_billed`, `lawful_basis` |
| GET | `/messages/{id}/events` | timeline ClickHouse (sent, delivered, opened, clicked, bounced, complained, unsubscribed) |

SLA: p95 < 2s do API call à entrega no provider downstream. Retorna `message_id` + `chain_hash` provisórios.

---

## 3. Journeys (Temporal)

Mock: `JOURNEYS` (id, name, trigger, steps, active_runs, completed_30d, conversion_rate).

| Verbo | Rota | Notas |
|---|---|---|
| GET | `/journeys` | lista com `active_runs` agregado |
| POST | `/journeys` | cria definição (visual flow JSON) e versiona |
| POST | `/journeys/{id}/start` | inicia workflow Temporal — body = `journey_config` (recipient, variables) |
| POST | `/journeys/{id}/pause` · `/resume` · `/disable` | controle |
| GET | `/journeys/{id}/runs?status=running` | lista execuções (alimenta tela detalhada) |
| GET | `/journeys/{run_id}` | timeline de steps + signals + waits |

---

## 4. Templates

Mock: `TEMPLATES`.

| Verbo | Rota | Notas |
|---|---|---|
| GET | `/templates?channel=email&category=transactional` | filtra por canal/categoria |
| POST | `/templates/email` | body inclui `mjml_source`, `subject_template`, `variables_schema` |
| POST | `/templates/sms` | `body_template`, valida `<=160` chars (ou 70 unicode) |
| POST | `/templates/push` | `title_template, body_template, image_url, deep_link, actions` |
| POST | `/templates/{id}/preview` | renderiza com `template_variables` para preview no editor |
| POST | `/templates/{id}/ab-test` | configura split 50/50 com winner automático |

---

## 5. Suppression list (cross-canal)

Mock: `SUPPRESSIONS`. Latência de check obrigatória `<2ms` (Postgres index em `(organization_id, identifier_type, identifier_value)`).

| Verbo | Rota |
|---|---|
| GET | `/suppression?channel=email&reason=hard_bounce` |
| POST | `/suppression` — `{identifier_type, identifier_value, channels[], reason, notes}` |
| DELETE | `/suppression/{id}` — só `manual` e `dpo_request` são removíveis manualmente |
| POST | `/suppression/import` — upload CSV multipart |
| GET | `/u/{unsubscribe_token}` — portal público centralizado (LGPD Art. 18) |

---

## 6. Senders

### 6.1 Email domains (`DOMAINS`)

| Verbo | Rota |
|---|---|
| GET | `/domains` |
| POST | `/domains` — `{domain}` → retorna DNS records (TXT DKIM + SPF + DMARC) |
| POST | `/domains/{id}/verify` — força revalidação DNS |
| GET | `/domains/{id}/dns-records` — alimenta tabela "DNS records sugeridos" |
| GET | `/domains/{id}/reputation` — score 0-100 do Postal + histórico |
| POST | `/domains/{id}/dedicated-ip` — provisiona IP dedicado (Scale+) com warmup gradual 30d |

### 6.2 SMS numbers (`SMS_NUMBERS`)

| Verbo | Rota |
|---|---|
| GET | `/sms-numbers` |
| POST | `/sms-numbers` — `{type: short_code|long_code, provider, two_way}` |
| POST | `/sms-numbers/{id}/inbound-webhook` — config webhook para two-way SMS |

### 6.3 WhatsApp (proxy CONNECT) (`WA_NUMBERS`)

| Verbo | Rota |
|---|---|
| GET | `/whatsapp/numbers` — espelha CONNECT, inclui `quality_rating`, `messaging_limit_tier`, `templates_approved` |
| POST | `/whatsapp/numbers/{id}/sync` — re-sync templates aprovados Meta |

### 6.4 Push apps (`PUSH_APPS`)

| Verbo | Rota |
|---|---|
| GET | `/push-apps` |
| POST | `/push-apps` — `{name, platform, bundle}` |
| POST | `/push-apps/{id}/credentials` — upload APNs `.p8` ou FCM service account JSON; gera VAPID p/ web. Secrets vão para OpenBao. |
| POST | `/push-apps/{id}/test` — envio de teste para token específico |

---

## 7. Analytics (`ANALYTICS_30D`)

Materialized views ClickHouse (`daily_stats_by_org_channel`).

| Verbo | Rota |
|---|---|
| GET | `/analytics/messages?from=…&to=…&group_by=day|hour|template|channel` |
| GET | `/analytics/summary?period=30d` → `by_channel[]` + `sparkline[]` |
| GET | `/analytics/funnel?template_id=…` → sent → delivered → opened → clicked → converted |
| GET | `/analytics/export?format=csv|parquet` — async, retorna `export_id` |

---

## 8. Webhooks (`WEBHOOKS`)

Eventos publicados: `message.sent`, `message.delivered`, `message.opened`, `message.clicked`, `message.bounced`, `message.complained`, `message.unsubscribed`, `message.failed`, `journey.completed`.

| Verbo | Rota |
|---|---|
| GET | `/webhooks` |
| POST | `/webhooks` — `{url, events[], signing_secret?}` (auto-gera se omitido, persiste no OpenBao) |
| POST | `/webhooks/{id}/test` — dispara evento sintético |
| GET | `/webhooks/{id}/deliveries?status=failed` — para debugging (tela mostra success_rate_30d) |
| POST | `/webhooks/{id}/deliveries/{delivery_id}/retry` |

Assinatura: header `X-Beacon-Signature: <hex hmac-sha256(rawBody, signing_secret)>` + `X-Beacon-Timestamp` (replay window 5min).

---

## 9. Deliverability (`DELIVERABILITY`)

| Verbo | Rota |
|---|---|
| GET | `/deliverability/providers` — agrega delivered/bounce/complaint/reputation por provider |
| GET | `/deliverability/ips` — pool Postal + IPs dedicados + status warmup |
| GET | `/deliverability/dmarc-reports?domain=…` — RUA reports agregados |

---

## 10. Anti-spam ML (`ANTISPAM_ALERTS`)

| Verbo | Rota |
|---|---|
| GET | `/antispam/status` — score 0-100 da org + holds ativos |
| GET | `/antispam/alerts?status=investigating` |
| POST | `/antispam/alerts/{id}/release` — human review fast-track (libera mensagens em hold) |
| POST | `/antispam/alerts/{id}/block` |
| POST | `/antispam/whitelist` — adiciona padrão à whitelist gerenciada |

---

## 11. API keys (`API_KEYS`)

| Verbo | Rota |
|---|---|
| GET | `/api-keys` — nunca retorna o segredo completo, só `prefix` |
| POST | `/api-keys` — `{name, scopes[]}` → retorna token claro UMA ÚNICA VEZ |
| DELETE | `/api-keys/{id}` — revoga imediatamente |

Scopes suportados: `messages:send`, `messages:send:email|sms|whatsapp|push`, `messages:read`, `templates:write`, `templates:read`, `journeys:write`, `analytics:read`, `webhooks:write`, `suppression:write`, `*` (owner only).

---

## 12. LGPD · DSAR (`DSAR_REQUESTS`)

| Verbo | Rota |
|---|---|
| GET | `/lgpd/dsar?status=pending` |
| POST | `/lgpd/dsar` — `{identifier_type, identifier_value, type: access|deletion|portability}` |
| GET | `/lgpd/dsar/{id}` — inclui `messages_found`, `deadline_at` (ANPD 15 dias) |
| POST | `/lgpd/dsar/{id}/fulfill` — gera ZIP com todas mensagens (acessível ao titular) |
| POST | `/lgpd/breach-notification` — endpoint interno para automação 3-day rule |
| GET | `/lgpd/lawful-basis-stats` — distribuição consent/contract/legal_obligation/legitimate_interest |

---

## 13. Audit chain (`CHAIN_ENTRIES`)

Hash BLAKE3 de `content_hash + recipient + timestamp + lawful_basis + prev_hash`. Anchored em CITADEL a cada 60s.

| Verbo | Rota |
|---|---|
| GET | `/chain/entries?actor=…&action=…&from=…` |
| GET | `/chain/entries/{id}` |
| GET | `/chain/integrity` — verifica chain completa, retorna `{ok: true, verified_at, total_entries}` |
| POST | `/chain/verify-message/{message_id}` — prova jurídica para uma mensagem específica |

---

## 14. Billing (`BILLING_BREAKDOWN`)

Integração Asaas BR + NF-e automática.

| Verbo | Rota |
|---|---|
| GET | `/billing/mtd` — breakdown linha-a-linha (plano + overages + add-ons) |
| GET | `/billing/invoices?year=2026` |
| GET | `/billing/invoices/{id}/nfe` — XML + PDF NF-e |
| POST | `/billing/cap` — atualiza anti-bill-shock cap mensal (R$) |
| GET | `/billing/usage/realtime` — uso last 24h por canal |
| POST | `/billing/payment-method` — PIX (default, 2% off) ou boleto |

---

## 15. Team & SSO (`TEAM`)

Authentik OIDC. Roles: `owner | admin | developer | marketer | viewer`.

| Verbo | Rota |
|---|---|
| GET | `/team` |
| POST | `/team/invite` — `{email, role}` envia magic link via BEACON (dogfood) |
| PATCH | `/team/{user_id}` — muda role |
| DELETE | `/team/{user_id}` |
| GET | `/team/sso/config` — SAML/OIDC metadata para download |

---

## 16. Settings

| Verbo | Rota |
|---|---|
| GET · PATCH | `/settings/quiet-hours` — `{start: "22:00", end: "07:00", channels: [sms, push_*]}` |
| GET · PATCH | `/settings/frequency-cap` — `{max_per_user_per_day, cross_channel: true}` |
| GET · PATCH | `/settings/region` — `primary: br-sp1`, `dr: br-rj1` (read-only V0) |
| GET · POST | `/settings/byok` — Scale+; integra OpenBao/VAULT-BR com KMS do cliente |

---

## 17. Cross-product integrations

| Produto | Direção | Endpoint |
|---|---|---|
| CONNECT | BEACON → CONNECT | `POST connect.rewirelabs.dev/internal/v1/whatsapp/send` (mTLS) |
| CITADEL | BEACON → CITADEL | `POST citadel.rewirelabs.dev/chain/append` (BLAKE3 anchor) |
| AUDIT TRAIL | BEACON → AUDIT | event stream `beacon.messages.lgpd` → Kafka topic `audit.compliance.evidence` |
| GUARDIAN | GUARDIAN → BEACON | `POST /messages/multi-channel` com `severity=critical` dispara email+sms+wa+push simultâneo |
| FOUNDRY | FOUNDRY → BEACON | golden paths injetam `@rewirelabs/beacon-sdk` + envvars |
| HOST | HOST cloud-init | flag `--with-beacon-sdk` pré-instala CLI + envvars |

---

## 18. Webhooks payload schema (referência)

```json
{
  "id": "evt_01HV…",
  "type": "message.delivered",
  "created_at": "2026-05-23T14:21:08.412Z",
  "organization_id": "org_pampa",
  "data": {
    "message_id": "msg_01HV9TZ",
    "channel": "email",
    "recipient": "joao.silva@uol.com.br",
    "template_id": "tpl_order_confirmation",
    "provider": "postal",
    "lawful_basis": "contract",
    "chain_hash": "b3:9f4e2c1a8d2c…",
    "cost_brl": "0.0015",
    "metadata": {"order_id": "28117"}
  }
}
```

---

## 19. Critérios de aceitação técnicos

- **Latência envio**: p95 < 2s API call → handoff provider.
- **Deliverability email**: > 98% (Postal IPs próprios) — monitorado via `/deliverability/providers`.
- **Suppression check**: < 2ms (Postgres index único composto).
- **Audit chain**: 100% das mensagens ancoradas, verificação batch a cada 60s.
- **LGPD DSAR**: fulfillment automático em <24h (alvo legal 15d ANPD).
- **Multi-tenant**: RLS por `organization_id` em todas as tabelas Postgres + databases isolados ClickHouse + topics Kafka por tenant.
- **Idempotência**: `Idempotency-Key` em `POST /messages/*` (TTL 24h, retorna mesma resposta).
- **Anti-spam ML**: bloqueio preventivo + human review fast-track <2h.
- **Rate limiting**: por tier (Hobby 10 req/s, Starter 100, Growth 500, Scale 2k, Enterprise sob acordo); 429 com `Retry-After`.
- **OIDC**: Authentik `2026.3+` como único IdP.
- **Secrets**: nada de credencial em Postgres; OpenBao/VAULT-BR como única fonte (DKIM keys, APNs cert, FCM SA, VAPID, signing secrets, BSP API keys).

---

## 20. Mapeamento mock → endpoint

| Constante em `beacon-mock.ts` | Endpoint produtivo |
|---|---|
| `BEACON_USER` | `GET /me` |
| `MESSAGES` | `GET /messages` |
| `TEMPLATES` | `GET /templates` |
| `JOURNEYS` | `GET /journeys` |
| `DOMAINS` | `GET /domains` |
| `SMS_NUMBERS` | `GET /sms-numbers` |
| `WA_NUMBERS` | `GET /whatsapp/numbers` |
| `PUSH_APPS` | `GET /push-apps` |
| `SUPPRESSIONS` | `GET /suppression` |
| `WEBHOOKS` | `GET /webhooks` |
| `ANALYTICS_30D` | `GET /analytics/summary?period=30d` |
| `ANTISPAM_ALERTS` | `GET /antispam/alerts` |
| `DELIVERABILITY` | `GET /deliverability/providers` |
| `API_KEYS` | `GET /api-keys` |
| `DSAR_REQUESTS` | `GET /lgpd/dsar` |
| `CHAIN_ENTRIES` | `GET /chain/entries` |
| `BILLING_BREAKDOWN` | `GET /billing/mtd` |
| `TEAM` | `GET /team` |
| `CROSS_SELL` | `GET /org/integrations` (status cross-product) |

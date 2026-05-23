# ADR 0003 — Auth pattern: Authentik OIDC (UI) + API tokens per tenant (SDK/REST)

> **Status**: Aceita
> **Data**: 2026-05-23
> **Autores**: Alessandro Queiroz + agente de documentação
> **Tags**: auth, authentik, api-tokens, multi-tenancy

## Contexto

BEACON tem **duas classes de consumidores**:

1. **UI BEACON (humanos)**: developers/marketing acessam dashboard
   `app.beacon.rewirelabs.dev` para gerenciar templates, ver analytics,
   configurar webhooks
2. **API/SDK programático**: aplicações cliente chamam `/v1/messages/email`
   em alta frequência via REST API

Esses dois usos têm requisitos diferentes:

| Aspecto | UI (humano) | API/SDK |
|---|---|---|
| Frequência | Esporádica | Alta (10k+ RPS por cliente Scale) |
| Identidade | Pessoa + org | App + org |
| Sessão | Long-lived (8h) | Per-request stateless |
| Revogação | Logout + Authentik admin | Token revoke imediato |
| MFA | Sim (decisão Authentik) | Não aplicável |

## Decisão

**Adotamos modelo híbrido**: Authentik OIDC para UI + API tokens BEACON
nativos para SDK/REST.

Especificação:

### UI auth (Authentik OIDC)

- **Provider**: Authentik OIDC client `beacon-ui` (BEACON.md §2.0
  decisão 18)
- **Flow**: Authorization Code + PKCE
- **Tokens**: JWT RS256; access TTL 15min em memória, refresh TTL 7d em
  cookie HttpOnly Secure SameSite=Lax
- **MFA**: obrigatório para roles `org_admin`, `dpo`
- **Claims relevantes**: `sub` (user_id), `email`, `organization_id`,
  `roles` (membership)

### API/SDK auth (BEACON API tokens)

- **Formato**: `bcn_<env>_<base64url-32-bytes>` onde `<env>` é
  `live`/`test` (ex: `bcn_live_abc123...`)
- **Storage**: bcrypt cost-12 hash em `api_tokens` table; raw mostrado
  só uma vez na criação
- **Header**: `Authorization: Bearer bcn_live_...`
- **Validation**: cache Redis 60s TTL para evitar bcrypt por request
- **Rate limit**: per-token (não per-user) via Redis sliding window
  (limit configurável: Hobby 100 RPS, Scale 10k RPS)
- **Scopes**: `messages:send`, `messages:read`, `templates:write`,
  `analytics:read`, `dsar:read`, etc
- **TTL**: 365 dias default; renovável; revogação imediata via
  DEL Redis cache + UPDATE Postgres
- **Audit**: cada call autenticada com API token emite evento
  `api_token.used` (forwarded para CITADEL audit chain)

### Server-to-server (cross-product)

- **JWT m2m** (machine-to-machine): outros produtos Rewire (FOUNDRY,
  HOST, AUDIT-TRAIL) chamam BEACON via JWT com claim `iss=rewire-foundry`,
  `iss=rewire-host`, etc
- **Validation**: `AuthentikJWTValidator` aceita lista `accepted_issuers`
- **NetworkPolicy**: ingress permitido apenas dos namespaces específicos

## Justificativa

### Por que Authentik OIDC (não outro IdP)

- **Pattern Rewire cluster**: Authentik é canonical (Admin, App, Audit
  Trail usam mesmo); reuso de cluster service evita ferramenta nova
- **MFA built-in**: TOTP + WebAuthn sem dev custom
- **Cross-product SSO**: usuário logado em rewire-app passa para BEACON
  sem re-prompt

### Por que API tokens custom (não OAuth2 client credentials)

- **DX**: cliente integra com `Authorization: Bearer bcn_live_...` em 1
  linha; OAuth2 exige token endpoint + refresh flow
- **Performance**: validação cache Redis ~1ms vs OAuth2 introspection
  ~50ms
- **Revogação**: imediata (DEL Redis); OAuth2 introspection cache pode
  vazar
- **Pattern indústria**: SendGrid, Twilio, Mailgun usam mesmo
  (`sk_live_*`, `SG.*`, etc); developers familiarizados

### Por que bcrypt cost-12 (não SHA256 puro)

- **Constant-time comparison**: bcrypt.checkpw built-in
- **Brute-force resistance**: ~250ms por tentativa offline
- **Padrão**: GitHub PATs, Stripe usam bcrypt

### Por que JWT m2m cross-product (não API token)

- **Federated identity**: cluster ADR sobre JWT cross-product
- **Scopes ricos**: JWT pode carregar claims complexos sem lookup
- **Network isolation**: NetworkPolicy reforça quem pode chamar

## Consequências

### Positivas

- DX excelente para developers integrando SDK
- SSO entre UIs Rewire mantido
- Performance auth ~1ms cache hit
- Revogação imediata API tokens
- Padrão indústria familiar
- Cross-product JWT alinhado cluster pattern

### Negativas

- Dois sistemas auth para operar (mitigação: ambos são clientes
  Authentik; backend de fato é único)
- Cache Redis inconsistente com Postgres = janela 60s revogação
  (mitigação: revogação manual força DEL síncrono)
- bcrypt cost-12 = ~250ms primeira validação (mitigação: cache cobre
  99%+ subsequentes)

### Neutras

- API token vazado é destrutivo dentro do escopo; mitigação: scope
  granular + rate limit per-token + IP allowlist opcional
- TTL 365d longo; UI permite criar com menor (mínimo 7d)

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Authentik OIDC para SDK também** | OAuth2 client_credentials flow é complexo; DX ruim |
| **API key sem hash (raw em DB)** | Vazamento DB = todos tokens leaked |
| **JWT auto-emitido para SDK** | Sem revogação imediata; expiração rígida |
| **mTLS para SDK** | Distribuição certs cliente fricção alta |
| **Webhook signing only (sem token)** | Não cobre call inbound do cliente |

## Plano de implementação

1. ✅ Authentik client `beacon-ui` criado (V0.1 — confirmar via runbook)
2. ⚠ Middleware `auth.py` valida JWT Authentik (UI) ou API token (SDK)
3. ⚠ Service `services/api_tokens.py` (criação + bcrypt + revogação)
4. ⚠ Endpoint `POST /v1/api-tokens` (criar com scope subset role)
5. ⚠ Cache Redis hash → metadata TTL 60s
6. ⚠ Rate limit per-token via Redis sliding window
7. ⚠ Endpoint `DELETE /v1/api-tokens/{id}` (revoga)
8. ⚠ UI `BeaconApiKeys.tsx` página (já existe scaffolding) wire backend
9. ⚠ JWT m2m: estender validator para aceitar issuers `rewire-foundry`,
   `rewire-host`, `rewire-audit-trail` etc
10. ⚠ Audit emit `api_token.used` em cada call → CITADEL chain

## Compliance e segurança

- Revogação ≤60s alinhado SOX-BR / ISO 27001 A.9.2.6
- Audit forensics via BLAKE3 chain CITADEL
- Token rotation forçada anual (alerta UI 30d antes do TTL)
- Vault path: `secret/rewire/beacon/api-token-encrypt-key` para keys de
  encryption de configs sensíveis (vault paths SMS providers etc)

## Referências

- [BEACON.md §2.0 decisão 18 (Authentik)](../../BEACON.md)
- [docs/api/API_SPEC.md §1 Auth & Session](../api/API_SPEC.md)
- ADR rewire-app/0013 — PAT cross-product (pattern similar)
- ADR rewire-admin/0015 — CF Access zero-trust (pattern edge auth)

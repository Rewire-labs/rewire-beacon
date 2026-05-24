# ADR 0004 — HMAC Alertmanager opt-in para webhook intake

- **Status**: Accepted
- **Data**: 2026-05-18
- **Decisores**: Alessandro Queiroz

## Contexto

Endpoint `POST /alerts/telegram` recebe webhook do Alertmanager. Sem
auth, qualquer pod no cluster pode spammar alerts. ClusterIP isolation
mitiga mas defense-in-depth eh melhor.

Alertmanager nativo nao suporta JWT bearer; suporta HTTP basic auth
ou custom headers.

## Decisao

Adotar **HMAC opt-in** via header `X-Rewire-Signature: sha256=<hex>`.
Secret compartilhado em ENV `REWIRE_NOTIFY_ALERTMANAGER_HMAC_SECRET`.
Empty secret = HMAC desabilitado (trust ClusterIP).

GitHub-style signature: HMAC-SHA256 do body com secret, comparado via
`hmac.compare_digest`.

## Alternativas consideradas

1. **mTLS client cert**
   - Pros: defense ideal.
   - Contras: Alertmanager helm chart complexity para client cert;
     overhead minimo de seguranca em ClusterIP.
   - Descartada.

2. **Sem auth, confiar em ClusterIP**
   - Pros: simplicidade.
   - Contras: insider attack trivial; LGPD audit fraco.
   - Descartada: combine com opt-in HMAC.

3. **JWT bearer**
   - Pros: stack canonical.
   - Contras: Alertmanager nao tem JWT generator nativo.
   - Descartada.

## Consequencias

- **Positivas**: defense-in-depth; opt-in flag para dev local;
  GitHub-style padrao bem conhecido.
- **Negativas**: secret rotation manual (sem auto-rotate hoje);
  Alertmanager helm precisa custom `http_config` para enviar header.
- **Neutras**: empty secret retorna True (defensive default sandbox).

## Proximas acoes

- Ticket [[NTF-006]] — doc setup Alertmanager + HMAC.

## Referencias

- `src/rewire_notify/api.py` (`_verify_hmac`)

## Historico de revisoes

| Data | Autor | Mudanca |
|---|---|---|
| 2026-05-23 | audit-agent | criacao retroativa |

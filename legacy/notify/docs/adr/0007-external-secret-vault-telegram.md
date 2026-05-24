# ADR 0007 — ExternalSecret `rewire-notify-telegram` Vault

- **Status**: Accepted
- **Data**: 2026-05-18
- **Decisores**: Alessandro Queiroz
- **Consulta tecnica**: cluster ADR 0002 (Vault prod), ExternalSecrets Operator

## Contexto

Bot token Telegram eh secret. Sem Vault, plaintext em manifest
deployado eh leak via `kubectl get configmap`. Alem disso operador
precisa rotacionar token quando @RewireLabsBot owner change.

## Decisao

Adotar **ExternalSecret** sync de Vault para K8s Secret:

- Vault paths: `kv/rewire/notify/telegram-{bot-token,chat-id-private,chat-id-group}`.
- K8s Secret name: `rewire-notify-telegram`.
- Mountado em `Deployment` via `envFrom`.

Env prefix `REWIRE_NOTIFY_` para todas as settings (Pydantic-Settings).
Mappings em `settings.Settings`.

## Alternativas consideradas

1. **Secret K8s diretamente sem Vault**
   - Pros: simples.
   - Contras: tem que ser criado fora do GitOps; rotation manual;
     audit nao centralizado.
   - Descartada.

2. **Sealed Secrets**
   - Pros: GitOps-friendly.
   - Contras: cluster ja usa Vault como source of truth (cluster ADR
     0002); sealed encrypts apenas value, sem audit logs.
   - Descartada.

## Consequencias

- **Positivas**: rotation atomic via Vault; audit log Vault central;
  alinhado pattern Rewire (todos produtos).
- **Negativas**: ExternalSecrets Operator dep; sync interval delay
  (~1min default — aceitavel).
- **Neutras**: dev local pode usar `.env` file via Pydantic
  `env_file`.

## Proximas acoes

- Ticket [[NTF-014]] — Helm chart ExternalSecret manifest.

## Referencias

- README.md secao "Configuration"
- `src/rewire_notify/settings.py`
- `deploy/helm/rewire-notify/values.yaml`

## Historico de revisoes

| Data | Autor | Mudanca |
|---|---|---|
| 2026-05-23 | audit-agent | criacao retroativa |

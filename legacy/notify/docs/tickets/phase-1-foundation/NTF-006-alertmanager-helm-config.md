# NTF-006 — Doc Alertmanager helm config + HMAC

- **Owner**: @alessandro
- **Estimativa**: S
- **Pre-reqs**: [[NTF-003]]
- **Status**: [ ] open

## Definicao

Documentar e configurar Alertmanager (kube-prometheus-stack helm chart)
para enviar webhooks para `rewire-notify` com HMAC header.

## Aceite

- [ ] Snippet values.yaml `alertmanager.config.receivers` com URL +
  `http_config.authorization` (custom header).
- [ ] Secret `rewire-notify-alertmanager-hmac` ExternalSecret Vault.
- [ ] Doc em `docs/setup-alertmanager.md`.
- [ ] Test end-to-end: alert fires → notify → telegram.

## Refs

- [ADR 0004](../../adr/0004-hmac-alertmanager-opt-in.md)

## Notas

Coordenado com cluster observability team.

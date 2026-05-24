# BCN-V2003 — Postal cluster deploy 8 nodes + IP pool 60 BR (BCN-020)

**Owner**: infra
**Estimativa**: L (2 sprints)
**Pré-requisitos**: bare-metal nodes provisionados + DNS Cloudflare delegated
**Detected by**: audit pass-2 (2026-05-24, ainda em backlog BCN-020)

## Contexto

BCN-020 marked [ ] (não feito). Postal é o provider primário para email.
Sem cluster Postal:
- Falta DNS reverse PTR per IP
- IP warmup workflow não executável
- Bounce/complaint webhook receiver fica órfão

## Definição

1. Helm chart Postal 8 nodes (`postal-1` a `postal-8`) com:
   - Pool 60 IPs BR (8 IPs primary + 7 IPs warmup per node)
   - Reverse PTR per IP `mail-<n>.beacon.rewirelabs.dev`
   - Hashicorp Vault populate Postal admin token + MySQL creds
2. MySQL Galera 3-node cluster (Postal storage backend).
3. Click handler webhook → `https://api.beacon.rewirelabs.dev/v1/webhooks/postal/{bounce,complaint,delivery,click,open}`
4. Per-tenant vhost provisioning automation (BCN-027 já feito — wire ao cluster).
5. IP warmup Temporal cron escalonada (30d schedule daily ramp up).
6. Runbook `docs/runbooks/postal-cluster-bootstrap.md`.

## Critérios de aceite

- [ ] 8 nodes saudáveis (`kubectl get pods -n postal -l app=postal`)
- [ ] 60 IPs com PTR resolvendo (`dig -x <IP> +short`)
- [ ] Mail Tester score >9/10 após warmup completo
- [ ] Bounce webhook recebe payload Postal em <500ms

## Referências

- BCN-020 (original ticket marked [ ])
- BCN-027 vhost provisioning (concluído mas órfão sem cluster)
- BEACON.md §2.1.2 Postal architecture

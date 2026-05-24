# ADR 0008 — ArgoCD deploy via observability ApplicationSet, namespace `observability`

- **Status**: Accepted
- **Data**: 2026-05-18
- **Decisores**: Alessandro Queiroz, cluster team
- **Consulta tecnica**: cluster ADR 0001 (GitOps), cluster ADR 0017 (observability stack)

## Contexto

rewire-notify recebe alerts do Alertmanager (parte do observability
stack: Prometheus, Loki, Tempo, Grafana, Alertmanager). Faz sentido
colocalizar.

Argumento alternativo: notify eh produto cross-cutting (recebe eventos
de qualquer produto), poderia ficar em namespace neutro como
`rewire-system`.

## Decisao

Deploy via **`argocd/applicationsets/observability.yaml`** ApplicationSet
(wave 5) no namespace **`observability`**. Helm chart em
`deploy/helm/rewire-notify/`. Application manifest standalone disponivel
em `deploy/argocd/application.yaml` para ad-hoc syncs.

## Alternativas consideradas

1. **Namespace `rewire-system`**
   - Pros: notify eh cross-cutting.
   - Contras: NetworkPolicy alerta → notify cross-namespace mais
     restritiva; Alertmanager same-namespace eh trivial.
   - Descartada: latency + NP simplicity.

2. **Namespace dedicado `rewire-notify`**
   - Pros: isolation.
   - Contras: 1 namespace para 1 pod eh waste.
   - Descartada.

## Consequencias

- **Positivas**: Alertmanager → notify same-namespace network; alerta
  observability scope; ApplicationSet generator auto.
- **Negativas**: notify nao eh strictly observability — leitor pode
  procurar em rewire-system.
- **Neutras**: sync wave 5 garante Alertmanager + Loki ja UP.

## Proximas acoes

- Doc README.md secao "Deployment" mantida.
- Ticket [[NTF-014]] — Helm chart prod values.

## Referencias

- README.md secao "Deployment"
- `deploy/argocd/application.yaml`
- cluster ADR 0017

## Historico de revisoes

| Data | Autor | Mudanca |
|---|---|---|
| 2026-05-23 | audit-agent | criacao retroativa |

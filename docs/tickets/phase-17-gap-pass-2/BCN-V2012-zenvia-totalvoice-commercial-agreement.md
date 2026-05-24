# BCN-V2012 — Acordo comercial Zenvia/TotalVoice revenue share (BCN-056)

**Owner**: comercial + tech lead
**Estimativa**: M (1 sprint, gating commercial)
**Pré-requisitos**: nenhum técnico
**Detected by**: audit pass-2 (2026-05-24, ainda em backlog BCN-056)

## Contexto

BCN-056 marked [ ]: "Acordo comercial Zenvia/TotalVoice (revenue share)".
Sem acordo, SMS é um pass-through cost direto — margem zero, billing
exposed ao volume bruto sem buffer.

## Definição

1. Negociar com Zenvia BR: tier discount com volume + revenue share 5-15%.
2. Negociar com TotalVoice BR: equivalente (fallback BSP).
3. Documentar pricing matrix `docs/business/sms-pricing-matrix.md`.
4. Wire pricing markup transparente em BCN-055 (já feito) usando taxas reais.
5. SLA BSP contratual (uptime ≥99.5%, latência delivery <30s p95).

## Critérios de aceite

- [ ] Contrato assinado Zenvia + TotalVoice
- [ ] Pricing matrix documentado
- [ ] Markup configurado per-tier values.yaml
- [ ] SLA monitorado via PrometheusRule

## Referências

- BCN-056 (original)
- BCN-055 markup transparente
- BEACON.md §2.2.2 pricing

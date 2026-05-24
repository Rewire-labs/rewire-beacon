# BCN-V2011 — Deliverability Mail Tester CI check (BCN-203)

**Owner**: qa
**Estimativa**: S (2-3d)
**Pré-requisitos**: BCN-V2003 Postal cluster + IP warmed
**Detected by**: audit pass-2 (2026-05-24, ainda em backlog BCN-203)

## Contexto

BCN-203 marked [ ]: "Deliverability test: enviar para Mail Tester +
verificar score >9/10". Sem CI check de deliverability, regressões DNS/
DKIM/SPF/DMARC passam silenciosas.

## Definição

1. Pytest job `tests/deliverability/test_mail_tester.py`:
   - Cria org test
   - Send para email Mail Tester dinâmico (API key paga)
   - Poll Mail Tester API ate score available
   - Assert score >=9/10
2. CI nightly schedule (não bloqueia PR — custo Mail Tester por chamada).
3. Alert Slack #cluster-team se score drop <9 dois dias consecutivos.
4. Vault `secret/rewire/beacon/mail-tester-api-key`.

## Critérios de aceite

- [ ] CI nightly running 7d straight com score >=9
- [ ] Alert wired em Slack
- [ ] Document em `docs/runbooks/deliverability-score-drop.md`

## Referências

- BCN-203 (original)
- BCN-V2003 prerequisite Postal cluster

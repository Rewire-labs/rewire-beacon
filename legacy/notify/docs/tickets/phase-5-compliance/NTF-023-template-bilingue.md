# NTF-023 — Templates bilingue PT-BR + EN-US

- **Owner**: @alessandro
- **Estimativa**: S
- **Pre-reqs**: [[NTF-002]]
- **Status**: [ ] open

## Definicao

Todos os templates do formatter (12 kinds) tem versao PT-BR (default)
+ EN-US. Recipient locale resolve via:

1. Recipient profile setting (Authentik attribute).
2. Tenant default locale.
3. Fallback PT-BR.

## Aceite

- [ ] Templates Jinja2 com structure `templates/{locale}/{kind}.j2`.
- [ ] Formatter selecciona template via recipient.locale.
- [ ] PT-BR e EN-US para todos 12 kinds.
- [ ] Pytest cobertura.

## Refs

- [ADR 0002](../../adr/0002-12-event-kinds-canonical.md)

## Notas

ES-LATAM como V0.3+ se MSP LatAm entrar.

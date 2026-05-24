# NTF-010 — V0.2 Postal email channel

- **Owner**: @alessandro
- **Estimativa**: XL
- **Pre-reqs**: Postal 3.x deployment, ClickHouse UP
- **Status**: [ ] open (V0.2 — Q3 2026)

## Definicao

Adicionar canal `email` via Postal 3.x self-hosted. API unificada
`POST /v1/notifications` com `channel=email`. Templates HTML
multilingual.

## Aceite

- [ ] Postal helm deploy + SMTP cluster-internal.
- [ ] EmailAdapter implements `Adapter` interface.
- [ ] Template engine Jinja2 + MJML.
- [ ] Click tracking + bounce handling via Postal webhook.
- [ ] ClickHouse event analytics integration.
- [ ] Pytest cobertura.

## Refs

- [ADR 0009](../../adr/0009-beacon-v0-2-multi-canal-roadmap.md)
- README.md "Roadmap evolutivo BEACON"

## Notas

OSS self-hosted alinhamento feedback memory.

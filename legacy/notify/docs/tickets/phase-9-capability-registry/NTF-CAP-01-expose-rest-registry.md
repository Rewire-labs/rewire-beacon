# NTF-CAP-01 - Expor GET /api/v1/capabilities canonical

**Fase**: phase-9-capability-registry
**Owner**: platform
**Estimativa**: S (4-8h)
**PrÃƒÂ©-requisitos**: [[CAPABILITY_REGISTRY_SPEC]] (services/), [[ADR-0106]] (cluster), [[MCP-012]] (aggregator)

## Objetivo

Implementar endpoint canonical `GET /api/v1/capabilities` em
`rewire-notify` retornando a lista de capabilities deste service conforme
schema canonical em `services/CAPABILITY_REGISTRY_SPEC.md`.

## Definicao

1. Criar arquivo `capabilities.yaml` em raiz do service (ou
   `app/capabilities.yaml` conforme stack) listando 1 entrada por
   capability publica que este service expoe.
2. Para cada capability, preencher TODOS campos obrigatorios do
   schema canonical:
   - `id` (regex `rewire\.notify\.<nome>`)
   - `name`, `description`, `version`, `category`
   - `invoke.transport`: `rest` (este ticket cobre apenas REST)
   - `invoke.endpoint` + `invoke.schema.input` + `invoke.schema.output` (jsonschema 2020-12)
   - `budget` (per_call_tokens se LLM; per_call_max_seconds sempre)
   - `permissions` (requires_oauth, scopes, requires_hitl, sensitivity)
   - `audit.emit_event` (formato `rewire.<svc>.<cap>.invoked`)
   - `deprecation` (deprecated_at + sunset_at = null)
3. Implementar handler `GET /api/v1/capabilities` que:
   - Le `capabilities.yaml` no boot.
   - Valida contra jsonschema canonical (lib shared `rewire_shared/python/capability_schema.py` a criar).
   - Responde `200 application/json` com `{service, version, capabilities[], etag}`.
   - ETag derivado de `sha256(canonical_json)`; suporta `If-None-Match: 304`.
4. Webhook outbound apos deploy:
   - Executar `POST {aggregator}/aggregator/invalidate` body
     `{ "service": "rewire-notify", "reason": "deploy" }`.
   - URL aggregator em env `REWIRE_AGGREGATOR_URL`.
   - Disparado pelo init container / lifecycle postStart.
5. Teste integracao validando schema canonical via fixture.

## Criterios de aceite

- [ ] `capabilities.yaml` populado com >=1 capability.
- [ ] `GET /api/v1/capabilities` retorna 200 + body valido.
- [ ] ETag + 304 funcionando.
- [ ] Schema validation via shared lib passa.
- [ ] Webhook invalidate disparado em `postStart` (teste em deploy mock).
- [ ] Doc curta em `docs/capability-registry.md` listando capabilities expostas.

## Referencias

- [[CAPABILITY_REGISTRY_SPEC]] (services/CAPABILITY_REGISTRY_SPEC.md)
- [[ADR-0106]] (cluster) - decisao hibrida MCP+REST
- [[MCP-012]] (rewire-mcp ADR 0012) - aggregator central
- MCP spec V2025-11-25 (referencia para schema future MCP)

## Notas

Este ticket NAO cobre MCP server transport. Para services IA-heavy
ver ticket complementar NTF-CAP-02.

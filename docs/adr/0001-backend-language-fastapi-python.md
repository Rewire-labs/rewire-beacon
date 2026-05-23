# ADR 0001 — Backend BEACON em FastAPI + Python 3.13 (e não Go/Node)

> **Status**: Aceita
> **Data**: 2026-05-23
> **Autores**: Alessandro Queiroz + agente de documentação
> **Tags**: backend, language, framework

## Contexto

BEACON é a notification platform multi-canal BR (email + SMS + WhatsApp +
push). Para o **control plane** (API + business logic + workflow
orchestration) precisamos escolher linguagem/framework. BEACON.md
§2.0 decisão 12 já estabeleceu **FastAPI 0.115+ + Python 3.13**,
mas falta justificar formalmente.

Volumetria projetada:

- API requests: ~5k-20k RPS sustained em GA (clientes Growth/Scale)
- Hot path envio: workers separados (Kafka consumers em containers
  dedicados) — não é responsabilidade do control plane
- Throughput de eventos analytics: ClickHouse (separado)

Linguagens consideradas:

- **Python FastAPI**: pattern Rewire (rewire-admin, rewire-app, audit-trail
  control plane). Ecossistema ML rico (anti-spam ML decisão 14).
- **Node.js Fastify**: alta performance, mas ecossistema ML fraco
- **Go Echo**: ideal para hot path mas business logic verbosa
- **Java Spring**: maturidade enterprise mas heavy

## Decisão

**Adotamos FastAPI 0.115+ + Python 3.13** para o control plane.

Especificação:

- **Runtime**: Python 3.13 (alinhado decisão BEACON.md §2.0)
- **Framework**: FastAPI 0.115+ + Pydantic v2 + uvicorn
- **ORM**: SQLAlchemy 2.x async + asyncpg (PostgreSQL 17 driver)
- **Cache**: redis-py async (Redis 7.4)
- **Workflow**: Temporal Python SDK 1.5+ (multi-step journeys)
- **HTTP client**: httpx async + tenacity retry
- **Logging**: structlog + JSON to Loki
- **Observability**: OpenTelemetry SDK (PULSE-CLOUD shared collector)
- **Tests**: pytest + pytest-asyncio + httpx.AsyncClient

**Não-decisões**: linguagens dos workers de envio fan-out (email/sms/
push/wa) ficam a cargo do contexto (anti-spam ML = Python; alto throughput
producer Kafka = pode ser Go/Rust). Decisão escalonada quando workers
forem implementados (V0.2+).

## Justificativa

### Por que Python FastAPI (não Node.js)

- **Pattern Rewire**: 4 produtos cluster (Admin, App, Audit Trail
  control plane, etc) usam FastAPI; operadores familiares
- **Ecossistema ML**: scikit-learn + sentence-transformers (decisão 14
  anti-spam) é Python-native; Node.js teria que reescrever ou usar APIs
  externas
- **Pydantic v2**: validação rigorosa de schemas; perfeito para multi-canal
  com payloads heterogêneos (email vs SMS vs push)
- **Async support**: asyncio + asyncpg suporta 5-20k RPS sustained em
  uvicorn multi-worker

### Por que NÃO Go (para control plane)

- **Verbosity business logic**: cada endpoint com error handling,
  validation, ORM queries em Go é 2-3× mais código que Python
- **Pydantic equivalente fraco**: Go structs + validators não chegam
  perto da expressividade Pydantic v2
- **Workers em Go OK**: Go é decisão correta para hot path producers
  Kafka (ADR futura quando workers forem escritos)

### Por que NÃO Java Spring

- **Tempo boot**: pod cold start 30-60s; Lambda-like scaling sofre
- **Memória**: JVM ~500MB baseline; Python ~150MB
- **Heterogeneidade**: introduzir Java no cluster aumenta complexidade
  ops (JVM tuning, mvn vs uv)

### Por que NÃO Rust Actix-web

- **Curva aprendizado**: time atual sem expertise Rust
- **Overkill para control plane**: throughput 5-20k RPS é confortável
  para Python; otimizar mais não muda economics

### Por que Python 3.13 (não 3.12)

- **Free-threaded experimental**: 3.13 introduz no-GIL build (PEP 703);
  embora opcional, prepara para workloads CPU-bound (anti-spam ML)
- **Pattern emergente Rewire**: audit-trail e novos produtos pós
  2026-Q1 adotam 3.13 (incluindo Admin migration roadmap)

## Consequências

### Positivas

- Time familiar com stack (zero ramp-up)
- Ecossistema ML pronto para anti-spam
- Pydantic v2 garante contracts rigorosos cross-canal
- Async support handle alto RPS sem multi-threading complexidade
- Pattern Rewire reusado: deploy, observability, secrets management
  idênticos a outros produtos

### Negativas

- GIL ainda dominante em 3.13 builds standard (mitigation: workers
  CPU-bound rodam em processos separados via Celery/Temporal)
- Python ~3× mais lento que Go para serialization JSON (mitigation:
  uvicorn + httptools + orjson cobre ~95% diferença)
- Boot time Python 1-2s vs Go 100ms (mitigation: pre-warming + minReplicas
  no HPA evita cold start)

### Neutras

- 3.13 ainda recente; algumas libraries não migraram completamente
  (validar compatibilidade no setup inicial)
- Python ecosystem dependa de wheels pré-compilados (Pydantic, asyncpg);
  Docker multi-stage com `uv pip install` cuida disso

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Node.js Fastify** | ML ecossistema fraco; quebra pattern Rewire |
| **Go Echo control plane** | Verbosity business logic; ML em outra linguagem |
| **Java Spring Boot** | Heavy (JVM, mem, boot); heterogeneidade |
| **Rust Actix-web** | Time sem Rust expertise; overkill |
| **Django + DRF** | Mais opinionated; FastAPI tem perf melhor + async nativo |

## Plano de implementação

1. ✅ Skeleton V0 em `apps/control-plane/src/beacon/main.py` (já criado)
2. ✅ Pydantic Settings em `settings.py`
3. ✅ Stub routers em `api/notifications.py`, `templates.py`, etc
4. ⚠ Implementar middleware: auth (Authentik) + tenancy (RLS GUC) +
   request_id + idempotency
5. ⚠ SQLAlchemy 2 async setup + Alembic migration 0001 (já existe)
6. ⚠ Implementar bodies reais dos endpoints (V0.2+)
7. ⚠ Temporal Python SDK + worker setup (V0.3+ multi-step journeys)

## Referências

- [BEACON.md §2.0 decisão 12](../../BEACON.md)
- [docs/api/API_SPEC.md](../api/API_SPEC.md)
- ADR equivalente em rewire-admin/rewire-app (mesmo pattern)
- FastAPI docs: https://fastapi.tiangolo.com/

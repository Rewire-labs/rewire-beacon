# BCN-V2009 — Anti-spam ML training data pipeline (BCN-115)

**Owner**: data + backend
**Estimativa**: L (2 sprints)
**Pré-requisitos**: BCN-110..114 (ML service existente)
**Detected by**: audit pass-2 (2026-05-24, ainda em backlog BCN-115)

## Contexto

BCN-115 marked [ ]: "Training data labeled (BEACON.md §2.13 CapEx Enterprise)".
Service ML existe mas SEM training data → model serving baseline heurística
apenas (não aprende com bounces reais Postal).

## Definição

1. ETL pipeline `etl/anti_spam_training_extract.py`:
   - Pull bounces/complaints históricos Postal últimos 90d
   - Label automático: hard_bounce=spam, complaint=spam, delivered+clicked=ham
   - Manual review queue para edge cases (5% random sample)
2. Storage: MinIO bucket `beacon-ml-training/{date}/labeled.parquet`.
3. Retraining job CronJob weekly:
   - Pull latest 90d labels
   - Train scikit-learn pipeline + sentence-transformers embeddings
   - Validate hold-out >F1 0.85
   - Promote model artifact MinIO `beacon-ml-models/v{N}.pkl`
4. A/B test infra: shadow model em paralelo 7d antes promote.
5. LGPD: tudo training data anonymized (hash recipients).

## Critérios de aceite

- [ ] Pipeline rodando weekly success rate >95%
- [ ] Model F1 score baseline ≥0.80, retraining ≥0.85
- [ ] Shadow mode metric `beacon_antispam_shadow_disagree_total`
- [ ] LGPD-compliant: zero PII em training dataset

## Referências

- BCN-115 (original)
- BCN-110..114 ML stack existente

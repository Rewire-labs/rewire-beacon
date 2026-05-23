-- BEACON ClickHouse schema (beacon_events database).
-- Apply via clickhouse-client or kubectl exec on ClickHouse pod.
-- This file is canonical; ADR 0002 references it.

CREATE DATABASE IF NOT EXISTS beacon_events;

-- 1) Raw message dispatches ---------------------------------------------------
CREATE TABLE IF NOT EXISTS beacon_events.messages (
  organization_id String,
  message_id      String,
  channel         LowCardinality(String),  -- email|sms|whatsapp|push_ios|push_android|push_web
  recipient       String,
  template_slug   LowCardinality(String),
  consent_basis   LowCardinality(String),
  chain_hash      String,
  sent_at         DateTime64(3, 'UTC')
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(sent_at)
ORDER BY (organization_id, sent_at, message_id)
TTL sent_at + INTERVAL 13 MONTH
SETTINGS index_granularity = 8192;

-- 2) Per-event timeline -------------------------------------------------------
CREATE TABLE IF NOT EXISTS beacon_events.message_events (
  organization_id String,
  message_id      String,
  channel         LowCardinality(String),
  event_type      LowCardinality(String),  -- sent|delivered|opened|clicked|bounced|complained|unsubscribed
  event_at        DateTime64(3, 'UTC'),
  metadata        String
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_at)
ORDER BY (organization_id, event_at, message_id, event_type)
TTL event_at + INTERVAL 13 MONTH
SETTINGS index_granularity = 8192;

-- 3) Daily stats Materialized View -------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS beacon_events.daily_stats_by_org_channel
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(day)
ORDER BY (organization_id, day, channel, event_type)
AS
SELECT
  organization_id,
  toDate(event_at) AS day,
  channel,
  event_type,
  count() AS events
FROM beacon_events.message_events
GROUP BY organization_id, day, channel, event_type;

-- 4) Kafka engine tables (consume from Redpanda/Kafka topics) ----------------
CREATE TABLE IF NOT EXISTS beacon_events.messages_kafka (
  organization_id String,
  message_id      String,
  channel         String,
  recipient       String,
  template_slug   String,
  consent_basis   String,
  chain_hash      String,
  sent_at         DateTime64(3, 'UTC')
) ENGINE = Kafka()
SETTINGS
  kafka_broker_list = 'redpanda-0.redpanda.brokers.svc:9092',
  kafka_topic_list  = 'beacon.events.messages',
  kafka_group_name  = 'clickhouse-beacon-events-messages',
  kafka_format      = 'JSONEachRow',
  kafka_num_consumers = 2;

CREATE MATERIALIZED VIEW IF NOT EXISTS beacon_events.mv_messages_ingest
TO beacon_events.messages
AS SELECT * FROM beacon_events.messages_kafka;

CREATE TABLE IF NOT EXISTS beacon_events.message_events_kafka (
  organization_id String,
  message_id      String,
  channel         String,
  event_type      String,
  event_at        DateTime64(3, 'UTC'),
  metadata        String
) ENGINE = Kafka()
SETTINGS
  kafka_broker_list = 'redpanda-0.redpanda.brokers.svc:9092',
  kafka_topic_list  = 'beacon.events.message_events',
  kafka_group_name  = 'clickhouse-beacon-events-events',
  kafka_format      = 'JSONEachRow',
  kafka_num_consumers = 2;

CREATE MATERIALIZED VIEW IF NOT EXISTS beacon_events.mv_message_events_ingest
TO beacon_events.message_events
AS SELECT * FROM beacon_events.message_events_kafka;

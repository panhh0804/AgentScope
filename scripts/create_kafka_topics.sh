#!/usr/bin/env bash
set -euo pipefail

KAFKA_BIN="${KAFKA_BIN:-/usr/local/kafka_2.11-2.1.0/bin}"
ZOOKEEPER="${KAFKA_ZOOKEEPER_CONNECT:-middleware:2181}"
TOPIC="${KAFKA_TOPIC:-agent-events}"
PARTITIONS="${KAFKA_PARTITIONS:-1}"
REPLICATION_FACTOR="${KAFKA_REPLICATION_FACTOR:-1}"

"${KAFKA_BIN}/kafka-topics.sh" \
  --zookeeper "${ZOOKEEPER}" \
  --create \
  --if-not-exists \
  --topic "${TOPIC}" \
  --partitions "${PARTITIONS}" \
  --replication-factor "${REPLICATION_FACTOR}"

"${KAFKA_BIN}/kafka-topics.sh" --zookeeper "${ZOOKEEPER}" --describe --topic "${TOPIC}"


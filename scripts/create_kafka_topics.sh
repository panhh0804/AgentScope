#!/usr/bin/env bash
set -euo pipefail

KAFKA_BIN="${KAFKA_BIN:-/usr/local/kafka/bin}"
BOOTSTRAP="${KAFKA_BOOTSTRAP_SERVERS:-middleware:9092}"
TOPIC="${KAFKA_TOPIC:-agent-events}"
PARTITIONS="${KAFKA_PARTITIONS:-3}"
REPLICATION_FACTOR="${KAFKA_REPLICATION_FACTOR:-1}"

"${KAFKA_BIN}/kafka-topics.sh" \
  --bootstrap-server "${BOOTSTRAP}" \
  --create \
  --if-not-exists \
  --topic "${TOPIC}" \
  --partitions "${PARTITIONS}" \
  --replication-factor "${REPLICATION_FACTOR}"

"${KAFKA_BIN}/kafka-topics.sh" --bootstrap-server "${BOOTSTRAP}" --describe --topic "${TOPIC}"


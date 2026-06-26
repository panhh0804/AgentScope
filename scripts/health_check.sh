#!/usr/bin/env bash
set -euo pipefail

echo "== Java =="
java -version 2>&1 | head -n 1 || true

echo "== HDFS =="
hdfs dfsadmin -report 2>/dev/null | grep -E "Live datanodes|Dead datanodes" || true

echo "== YARN =="
yarn node -list 2>/dev/null | head -n 10 || true

echo "== Spark =="
jps -l | grep -E "Master|Worker|CoarseGrainedExecutorBackend" || true

echo "== Kafka topic =="
KAFKA_BIN="${KAFKA_BIN:-/usr/local/kafka_2.11-2.1.0/bin}"
KAFKA_ZOOKEEPER="${KAFKA_ZOOKEEPER:-middleware:2181}"
KAFKA_TOPIC="${KAFKA_TOPIC:-agent-events}"
"${KAFKA_BIN}/kafka-topics.sh" --zookeeper "${KAFKA_ZOOKEEPER}" --list 2>/dev/null | grep "${KAFKA_TOPIC}" || true

echo "== Redis =="
redis-cli -h "${REDIS_HOST:-middleware}" -p "${REDIS_PORT:-6379}" ping 2>/dev/null || true

echo "== Backend =="
curl -fsS "http://${BACKEND_HOST:-localhost}:${BACKEND_PORT:-8000}/health" 2>/dev/null || true
echo


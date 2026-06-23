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
KAFKA_BIN="${KAFKA_BIN:-/usr/local/kafka/bin}"
"${KAFKA_BIN}/kafka-topics.sh" --bootstrap-server "${KAFKA_BOOTSTRAP_SERVERS:-middleware:9092}" --list 2>/dev/null | grep agent-events || true

echo "== Redis =="
redis-cli -h "${REDIS_HOST:-middleware}" -p "${REDIS_PORT:-6379}" ping 2>/dev/null || true

echo "== Backend =="
curl -fsS "http://${BACKEND_HOST:-localhost}:${BACKEND_PORT:-8000}/health" 2>/dev/null || true
echo


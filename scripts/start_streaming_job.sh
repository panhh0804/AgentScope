#!/usr/bin/env bash
set -euo pipefail

SPARK_HOME="${SPARK_HOME:-/usr/local/spark}"
APP_JAR="${APP_JAR:-spark-streaming/target/agentscope-spark-streaming-0.1.0.jar}"
MASTER_URL="${SPARK_MASTER:-${SPARK_MASTER_URL:-yarn}}"
DEPLOY_MODE="${SPARK_DEPLOY_MODE:-client}"
export HADOOP_CONF_DIR="${HADOOP_CONF_DIR:-/usr/local/hadoop-2.7.6/etc/hadoop}"
export YARN_CONF_DIR="${YARN_CONF_DIR:-${HADOOP_CONF_DIR}}"
export PATH="${SPARK_HOME}/bin:${PATH}"
KAFKA_BOOTSTRAP="${KAFKA_BOOTSTRAP_SERVERS:-middleware:9092}"
KAFKA_TOPIC="${KAFKA_TOPIC:-agent-events}"
REDIS_HOST="${REDIS_HOST:-middleware}"
REDIS_PORT="${REDIS_PORT:-6379}"

"${SPARK_HOME}/bin/spark-submit" \
  --class com.agentscope.streaming.AgentEventStreamingJob \
  --master "${MASTER_URL}" \
  --deploy-mode "${DEPLOY_MODE}" \
  --driver-memory 512m \
  --executor-memory 512m \
  "${APP_JAR}" \
  --kafka-bootstrap "${KAFKA_BOOTSTRAP}" \
  --topic "${KAFKA_TOPIC}" \
  --redis-host "${REDIS_HOST}" \
  --redis-port "${REDIS_PORT}"

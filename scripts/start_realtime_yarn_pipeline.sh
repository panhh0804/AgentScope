#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"

export SPARK_MASTER="${SPARK_MASTER:-yarn}"
export SPARK_DEPLOY_MODE="${SPARK_DEPLOY_MODE:-client}"
export HADOOP_CONF_DIR="${HADOOP_CONF_DIR:-/usr/local/hadoop-2.7.6/etc/hadoop}"
export YARN_CONF_DIR="${YARN_CONF_DIR:-/usr/local/hadoop-2.7.6/etc/hadoop}"
export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-middleware:9092}"
export KAFKA_TOPIC="${KAFKA_TOPIC:-agent-events}"
export REALTIME_RATE="${REALTIME_RATE:-15}"

APP_NAME="${APP_NAME:-AgentScopeStreaming}"

mkdir -p "${LOG_DIR}"
cd "${PROJECT_ROOT}"

simulator_pids="$(pgrep -f "simulator/main.py.*--mode realtime" || true)"
if [[ -n "${simulator_pids}" ]]; then
  echo "[skip] simulator realtime producer is already running:"
  ps -fp ${simulator_pids} || true
else
  echo "[start] simulator realtime producer -> ${LOG_DIR}/realtime_producer.log"
  nohup python3 simulator/main.py \
    --mode realtime \
    --kafka-bootstrap "${KAFKA_BOOTSTRAP_SERVERS}" \
    --kafka-topic "${KAFKA_TOPIC}" \
    --rate "${REALTIME_RATE}" \
    > "${LOG_DIR}/realtime_producer.log" 2>&1 &
  echo "$!" > "${LOG_DIR}/realtime_producer.pid"
fi

running_apps="$(
  yarn application -list 2>/dev/null \
    | awk -v app="${APP_NAME}" '$1 ~ /^application_/ && $0 ~ app && $0 ~ /RUNNING/ {print $1}' \
    || true
)"
if [[ -n "${running_apps}" ]]; then
  echo "[skip] ${APP_NAME} is already RUNNING on YARN:"
  echo "${running_apps}"
else
  echo "[start] Spark Streaming on YARN -> ${LOG_DIR}/streaming_yarn.log"
  nohup bash scripts/start_streaming_job.sh > "${LOG_DIR}/streaming_yarn.log" 2>&1 &
  echo "$!" > "${LOG_DIR}/streaming_yarn.pid"
fi

cat <<EOF

[ok] AgentScope realtime pipeline startup requested.

Verify with:
  ps -ef | grep simulator/main.py
  yarn application -list
  redis-cli -h middleware -p 6379 get agentscope:realtime:overview

After the frontend refreshes, realtime throughput, Token, alerts, and YARN 1 apps metrics should change if Kafka, Redis, and FastAPI are healthy.
EOF

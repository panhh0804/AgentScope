#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <biz_date: yyyy-MM-dd>" >&2
  exit 1
fi

BIZ_DATE="$1"
SPARK_HOME="${SPARK_HOME:-/usr/local/spark}"
APP_JAR="${APP_JAR:-spark-batch/target/agentscope-spark-batch-0.1.0.jar}"
MASTER_URL="${SPARK_MASTER_URL:-spark://master:7077}"
HDFS_RAW_BASE="${HDFS_RAW_BASE:-/agentscope/raw/agent_events}"
HDFS_CLEAN_BASE="${HDFS_CLEAN_BASE:-/agentscope/clean/agent_events}"

MYSQL_HOST="${MYSQL_HOST:-middleware}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_DB="${MYSQL_ANALYTICS_DB:-agentscope_analytics}"
MYSQL_USER="${MYSQL_USER:-agentscope}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-agentscope_pass}"

"${SPARK_HOME}/bin/spark-submit" \
  --class com.agentscope.batch.CleanAgentEventJob \
  --master "${MASTER_URL}" \
  "${APP_JAR}" \
  --input "${HDFS_RAW_BASE}/dt=${BIZ_DATE}" \
  --output "${HDFS_CLEAN_BASE}/dt=${BIZ_DATE}" \
  --date "${BIZ_DATE}" \
  --jdbc-url "jdbc:mysql://${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DB}?useSSL=false&useUnicode=true&characterEncoding=utf8" \
  --jdbc-user "${MYSQL_USER}" \
  --jdbc-password "${MYSQL_PASSWORD}"


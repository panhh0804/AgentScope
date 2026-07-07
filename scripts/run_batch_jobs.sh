#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <biz_date: yyyy-MM-dd>" >&2
  exit 1
fi

BIZ_DATE="$1"
SPARK_HOME="${SPARK_HOME:-/usr/local/spark}"
APP_JAR="${APP_JAR:-spark-batch/target/agentscope-spark-batch-0.1.0.jar}"
MASTER_URL="${SPARK_MASTER_URL:-yarn}"
DEPLOY_MODE="${SPARK_DEPLOY_MODE:-client}"
export HADOOP_CONF_DIR="${HADOOP_CONF_DIR:-/usr/local/hadoop-2.7.6/etc/hadoop}"
export YARN_CONF_DIR="${YARN_CONF_DIR:-${HADOOP_CONF_DIR}}"
HDFS_CLEAN_BASE="${HDFS_CLEAN_BASE:-/agentscope/clean/agent_events}"
HDFS_METRIC_BASE="${HDFS_METRIC_BASE:-/agentscope/metric}"
MYSQL_HOST="${MYSQL_HOST:-middleware}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_DB="${MYSQL_ANALYTICS_DB:-agentscope_analytics}"
MYSQL_USER="${MYSQL_USER:-agentscope}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-agentscope_pass}"

COMMON_ARGS=(
  --input "${HDFS_CLEAN_BASE}/dt=${BIZ_DATE}"
  --metric-base "${HDFS_METRIC_BASE}"
  --date "${BIZ_DATE}"
  --jdbc-url "jdbc:mysql://${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DB}?useSSL=false&useUnicode=true&characterEncoding=utf8"
  --jdbc-user "${MYSQL_USER}"
  --jdbc-password "${MYSQL_PASSWORD}"
)

for job in DailyMetricJob AgentRankingJob ErrorAnalysisJob RelationGraphJob HistoricalAlertJob; do
  "${SPARK_HOME}/bin/spark-submit" \
    --class "com.agentscope.batch.${job}" \
    --master "${MASTER_URL}" \
    --deploy-mode "${DEPLOY_MODE}" \
    "${APP_JAR}" \
    "${COMMON_ARGS[@]}"
done

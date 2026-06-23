#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <biz_date: yyyy-MM-dd>" >&2
  exit 1
fi

BIZ_DATE="$1"
MYSQL_HOST="${MYSQL_HOST:-middleware}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-agentscope}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-agentscope_pass}"
MYSQL_DB="${MYSQL_SOURCE_DB:-agentscope_source}"
HDFS_RAW_BASE="${HDFS_RAW_BASE:-/agentscope/raw/agent_events}"
TARGET_DIR="${HDFS_RAW_BASE}/dt=${BIZ_DATE}"

hdfs dfs -rm -r -f "${TARGET_DIR}" >/dev/null 2>&1 || true

sqoop import \
  --connect "jdbc:mysql://${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DB}?useSSL=false&useUnicode=true&characterEncoding=utf8" \
  --username "${MYSQL_USER}" \
  --password "${MYSQL_PASSWORD}" \
  --query "SELECT * FROM agent_events_source WHERE DATE(event_time) = '${BIZ_DATE}' AND \$CONDITIONS" \
  --target-dir "${TARGET_DIR}" \
  --fields-terminated-by '\t' \
  --lines-terminated-by '\n' \
  --null-string '\\N' \
  --null-non-string '\\N' \
  --num-mappers 1

hdfs dfs -touchz "${TARGET_DIR}/_SUCCESS"


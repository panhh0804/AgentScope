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
DATAX_HOME="${DATAX_HOME:-/usr/local/datax}"
DATAX_PY="${DATAX_PY:-}"

if ! command -v hdfs >/dev/null 2>&1; then
  echo "hdfs command not found. Load the Hadoop environment first." >&2
  exit 1
fi

if [[ -z "${DATAX_PY}" ]]; then
  if [[ -x "${DATAX_HOME}/bin/datax.py" ]]; then
    DATAX_PY="${DATAX_HOME}/bin/datax.py"
  elif command -v datax.py >/dev/null 2>&1; then
    DATAX_PY="$(command -v datax.py)"
  else
    echo "DataX launcher not found. Set DATAX_HOME or DATAX_PY." >&2
    exit 1
  fi
fi

if [[ -z "${HADOOP_CONF_DIR:-}" ]]; then
  hdfs_bin="$(command -v hdfs)"
  hadoop_home="${HADOOP_HOME:-$(cd "$(dirname "${hdfs_bin}")/.." && pwd)}"
  export HADOOP_CONF_DIR="${hadoop_home}/etc/hadoop"
fi

DEFAULT_FS="${HDFS_DEFAULT_FS:-}"
if [[ -z "${DEFAULT_FS}" ]]; then
  DEFAULT_FS="$(hdfs getconf -confKey fs.defaultFS 2>/dev/null || true)"
  if [[ -z "${DEFAULT_FS}" ]]; then
    DEFAULT_FS="hdfs://master:9000"
  fi
fi

hdfs dfs -rm -r -f "${TARGET_DIR}" >/dev/null 2>&1 || true
hdfs dfs -mkdir -p "${TARGET_DIR}"

job_conf="$(mktemp)"
trap 'rm -f "${job_conf}"' EXIT

cat >"${job_conf}" <<EOF
{
  "job": {
    "setting": {
      "speed": {
        "channel": 1
      },
      "errorLimit": {
        "record": 0,
        "percentage": 0.02
      }
    },
    "content": [
      {
        "reader": {
          "name": "mysqlreader",
          "parameter": {
            "username": "${MYSQL_USER}",
            "password": "${MYSQL_PASSWORD}",
            "column": [
              "id",
              "event_id",
              "trace_id",
              "run_id",
              "parent_run_id",
              "agent_id",
              "parent_agent_id",
              "agent_role",
              "event_type",
              "status",
              "event_time",
              "latency_ms",
              "prompt_tokens",
              "completion_tokens",
              "total_tokens",
              "cost_usd",
              "model_name",
              "tool_name",
              "error_type",
              "retry_count",
              "metadata_json",
              "created_at"
            ],
            "where": "DATE(event_time) = '${BIZ_DATE}'",
            "connection": [
              {
                "jdbcUrl": [
                  "jdbc:mysql://${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DB}?useSSL=false&useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai"
                ],
                "table": [
                  "agent_events_source"
                ]
              }
            ]
          }
        },
        "writer": {
          "name": "hdfswriter",
          "parameter": {
            "defaultFS": "${DEFAULT_FS}",
            "fileType": "text",
            "path": "${TARGET_DIR}",
            "fileName": "part",
            "writeMode": "nonConflict",
            "fieldDelimiter": "\t",
            "encoding": "UTF-8",
            "nullFormat": "\\\\N",
            "column": [
              {"name": "id", "type": "string"},
              {"name": "event_id", "type": "string"},
              {"name": "trace_id", "type": "string"},
              {"name": "run_id", "type": "string"},
              {"name": "parent_run_id", "type": "string"},
              {"name": "agent_id", "type": "string"},
              {"name": "parent_agent_id", "type": "string"},
              {"name": "agent_role", "type": "string"},
              {"name": "event_type", "type": "string"},
              {"name": "status", "type": "string"},
              {"name": "event_time", "type": "string"},
              {"name": "latency_ms", "type": "string"},
              {"name": "prompt_tokens", "type": "string"},
              {"name": "completion_tokens", "type": "string"},
              {"name": "total_tokens", "type": "string"},
              {"name": "cost_usd", "type": "string"},
              {"name": "model_name", "type": "string"},
              {"name": "tool_name", "type": "string"},
              {"name": "error_type", "type": "string"},
              {"name": "retry_count", "type": "string"},
              {"name": "metadata_json", "type": "string"},
              {"name": "created_at", "type": "string"}
            ]
          }
        }
      }
    ]
  }
}
EOF

"${DATAX_PY}" "${job_conf}"

hdfs dfs -touchz "${TARGET_DIR}/_SUCCESS"

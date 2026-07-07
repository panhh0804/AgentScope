#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

APP_NAME="${APP_NAME:-AgentScopeStreaming}"

cd "${PROJECT_ROOT}"

simulator_pids="$(pgrep -f "simulator/main.py.*--mode realtime" || true)"
if [[ -n "${simulator_pids}" ]]; then
  echo "[stop] simulator realtime producer:"
  ps -fp ${simulator_pids} || true
  kill ${simulator_pids} || true
else
  echo "[skip] no simulator realtime producer is running."
fi

running_apps="$(
  yarn application -list 2>/dev/null \
    | awk -v app="${APP_NAME}" '$1 ~ /^application_/ && $0 ~ app && $0 ~ /RUNNING/ {print $1}' \
    || true
)"
if [[ -n "${running_apps}" ]]; then
  echo "[stop] killing RUNNING ${APP_NAME} applications on YARN:"
  while read -r app_id; do
    [[ -z "${app_id}" ]] && continue
    echo "  yarn application -kill ${app_id}"
    yarn application -kill "${app_id}"
  done <<< "${running_apps}"
else
  echo "[skip] no RUNNING ${APP_NAME} application found on YARN."
fi

cat <<EOF

[ok] AgentScope realtime pipeline stop requested.

Verify with:
  ps -ef | grep simulator/main.py
  yarn application -list
EOF

#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${APP_NAME:-AgentScopeStreaming}"

jps -l | awk -v app="${APP_NAME}" '$0 ~ app {print $1}' | while read -r pid; do
  if [[ -n "${pid}" ]]; then
    kill "${pid}"
    echo "stopped ${APP_NAME} pid=${pid}"
  fi
done


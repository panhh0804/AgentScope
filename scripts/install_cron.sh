#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CRON_FILE="${CRON_FILE:-${PROJECT_ROOT}/deploy/agentscope.cron}"

if [[ ! -f "${CRON_FILE}" ]]; then
  echo "[ERROR] Cron file not found: ${CRON_FILE}" >&2
  exit 1
fi

if ! command -v crontab >/dev/null 2>&1; then
  echo "[ERROR] crontab command not found on this machine." >&2
  exit 1
fi

tmp_file="$(mktemp)"
trap 'rm -f "${tmp_file}"' EXIT

crontab -l 2>/dev/null > "${tmp_file}" || true

if ! grep -Fq "run_daily_offline_pipeline.sh" "${tmp_file}"; then
  cat "${CRON_FILE}" >> "${tmp_file}"
fi

crontab "${tmp_file}"

echo "[OK] Cron installed from ${CRON_FILE}"
echo "[OK] Current crontab:"
crontab -l

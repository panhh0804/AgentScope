#!/usr/bin/env bash
# ============================================================================
# run_daily_offline_pipeline.sh
# AgentScope 离线批处理链路 —— 一键总控脚本
#
# 执行顺序（严格依赖，前一步失败则中止）：
#   阶段 1：DataX 导入  (MySQL Source -> HDFS Raw)
#   阶段 2：Spark 清洗  (HDFS Raw -> HDFS Clean)
#   阶段 3：Spark 批量分析 (HDFS Clean -> HDFS Metric + MySQL Analytics)
#
# 用法：
#   ./run_daily_offline_pipeline.sh                # 默认处理昨天的数据
#   ./run_daily_offline_pipeline.sh 2026-06-25     # 指定业务日期
#
# Crontab 配置（每天凌晨 2:00 自动执行）：
#   0 2 * * * cd /root/agentscope && bash scripts/run_daily_offline_pipeline.sh >> logs/daily_pipeline.log 2>&1
# ============================================================================
set -euo pipefail

# ─────────────────────────────────────────────
# 加载环境变量（crontab / 非交互式 SSH 不会自动加载）
# ─────────────────────────────────────────────
set +u
[[ -f /etc/profile ]] && source /etc/profile 2>/dev/null || true
[[ -f ~/.bashrc ]]    && source ~/.bashrc 2>/dev/null || true
set -u

# ─────────────────────────────────────────────
# 1. 基础变量
# ─────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"

mkdir -p "${LOG_DIR}"

# 业务日期：如果用户没传参数，则自动取昨天
if [[ $# -ge 1 ]]; then
  BIZ_DATE="$1"
else
  BIZ_DATE="$(date -d 'yesterday' '+%Y-%m-%d' 2>/dev/null || date -v-1d '+%Y-%m-%d')"
fi

# 日期格式校验（必须是 yyyy-MM-dd）
if ! echo "${BIZ_DATE}" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'; then
  echo "[ERROR] 无效的日期格式: ${BIZ_DATE}，请使用 yyyy-MM-dd" >&2
  exit 1
fi

# ─────────────────────────────────────────────
# 2. 日志与计时工具函数
# ─────────────────────────────────────────────
log_info()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO]  $*"; }
log_warn()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN]  $*"; }
log_error() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" >&2; }

# 计算耗时（秒）
timer_start() { date +%s; }
timer_elapsed() {
  local start=$1
  local end
  end=$(date +%s)
  echo $(( end - start ))
}

# ─────────────────────────────────────────────
# 3. Pipeline 启动
# ─────────────────────────────────────────────
PIPELINE_START=$(timer_start)

log_info "============================================================"
log_info "AgentScope 离线批处理链路启动"
log_info "业务日期: ${BIZ_DATE}"
log_info "项目根目录: ${PROJECT_ROOT}"
log_info "============================================================"

# ─────────────────────────────────────────────
# 阶段 1/3：DataX 导入 (MySQL Source -> HDFS Raw)
# ─────────────────────────────────────────────
log_info "────── 阶段 1/3：DataX 数据导入 ──────"
STAGE_START=$(timer_start)

if bash "${SCRIPT_DIR}/datax_import_agent_events.sh" "${BIZ_DATE}"; then
  log_info "阶段 1 完成 ✓  DataX 导入成功 (耗时: $(timer_elapsed ${STAGE_START})s)"
else
  log_error "阶段 1 失败 ✗  DataX 导入出错，Pipeline 中止！"
  log_error "请检查 MySQL Source 连接和 HDFS 可用性后重试。"
  exit 1
fi

# ─────────────────────────────────────────────
# 阶段 2/3：Spark 清洗 (HDFS Raw -> HDFS Clean)
# ─────────────────────────────────────────────
log_info "────── 阶段 2/3：Spark 数据清洗 ──────"
STAGE_START=$(timer_start)

if bash "${SCRIPT_DIR}/run_clean_job.sh" "${BIZ_DATE}"; then
  log_info "阶段 2 完成 ✓  Spark 清洗成功 (耗时: $(timer_elapsed ${STAGE_START})s)"
else
  log_error "阶段 2 失败 ✗  Spark 清洗出错，Pipeline 中止！"
  log_error "请检查 HDFS Raw 区 /agentscope/raw/agent_events/dt=${BIZ_DATE} 是否存在数据。"
  exit 1
fi

# ─────────────────────────────────────────────
# 阶段 3/3：Spark 批量分析
#   (HDFS Clean -> HDFS Metric + MySQL Analytics)
#   依次运行: DailyMetricJob, AgentRankingJob,
#             ErrorAnalysisJob, RelationGraphJob,
#             HistoricalAlertJob
# ─────────────────────────────────────────────
log_info "────── 阶段 3/3：Spark 批量分析 ──────"
STAGE_START=$(timer_start)

if bash "${SCRIPT_DIR}/run_batch_jobs.sh" "${BIZ_DATE}"; then
  log_info "阶段 3 完成 ✓  Spark 批量分析成功 (耗时: $(timer_elapsed ${STAGE_START})s)"
else
  log_error "阶段 3 失败 ✗  Spark 批量分析出错，Pipeline 中止！"
  log_error "请检查 HDFS Clean 区和 MySQL Analytics 连接。"
  exit 1
fi

# ─────────────────────────────────────────────
# 4. Pipeline 完成汇总
# ─────────────────────────────────────────────
TOTAL_ELAPSED=$(timer_elapsed ${PIPELINE_START})

log_info "============================================================"
log_info "全部 3 个阶段执行完毕 ✓"
log_info "业务日期: ${BIZ_DATE}"
log_info "总耗时: ${TOTAL_ELAPSED} 秒"
log_info ""
log_info "数据流向:"
log_info "  MySQL Source (agentscope_source.agent_events_source)"
log_info "    ↓ DataX"
log_info "  HDFS Raw (/agentscope/raw/agent_events/dt=${BIZ_DATE})"
log_info "    ↓ Spark CleanAgentEventJob"
log_info "  HDFS Clean (/agentscope/clean/agent_events/dt=${BIZ_DATE})"
log_info "    ↓ Spark Batch (5 个分析作业)"
log_info "  HDFS Metric (/agentscope/metric/*)"
log_info "  MySQL Analytics (agentscope_analytics.*)"
log_info ""
log_info "现在可以通过 FastAPI 后端查询 ${BIZ_DATE} 的历史分析结果了。"
log_info "============================================================"

#!/usr/bin/env bash
# ============================================================================
# benchmark.sh
# AgentScope 实时链路阶梯式压测脚本
#
# 功能：
#   对 AgentScope 实时流处理链路进行阶梯式加压测试，依次使用
#   5、10、20、50 Events/s 的并发速率运行模拟器，每个梯度运行
#   固定时长后自动终止并清理。
#
# 实时链路：
#   Agent 模拟器 -> Kafka -> Spark Streaming -> Redis -> FastAPI -> 前端
#
# 用法：
#   ./scripts/benchmark.sh                          # 默认 180 秒/梯度
#   ./scripts/benchmark.sh --duration 300           # 自定义 300 秒/梯度
#   ./scripts/benchmark.sh --duration 180 --dry-run # 仅打印要执行的命令
#
# 环境变量（可选覆盖）：
#   KAFKA_BOOTSTRAP    Kafka 地址（默认 middleware:9092）
#   KAFKA_TOPIC        Topic 名称（默认 agent-events）
#   KAFKA_BIN          Kafka 工具目录（默认 /usr/local/kafka_2.11-2.1.0/bin）
#   SPARK_UI_URL       YARN ResourceManager 地址（默认 http://master:8088）
# ============================================================================
set -euo pipefail

# ─────────────────────────────────────────────
# 0. 基础变量与默认值
# ─────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"
REPORT_DIR="${PROJECT_ROOT}/docs"

# 压测参数
RATES=(5 10 20 50)                          # 依次遍历的并发速率（Events/s）
TEST_DURATION_SEC=180                        # 每个速率梯度的运行时长（秒）
DRY_RUN=false

# 集群组件地址（可通过环境变量覆盖）
KAFKA_BOOTSTRAP="${KAFKA_BOOTSTRAP:-middleware:9092}"
KAFKA_TOPIC="${KAFKA_TOPIC:-agent-events}"
KAFKA_BIN="${KAFKA_BIN:-/usr/local/kafka_2.11-2.1.0/bin}"
SPARK_UI_URL="${SPARK_UI_URL:-http://master:8088}"

# ─────────────────────────────────────────────
# 1. 前置检测
# ─────────────────────────────────────────────

# 检测是否在项目根目录（通过查找 simulator/main.py 的存在性判断）
if [[ ! -f "${PROJECT_ROOT}/simulator/main.py" ]]; then
  echo "[ERROR] 未检测到项目根目录，请确保在 AgentScope 项目根目录下执行此脚本。" >&2
  echo "[ERROR] 期望找到 simulator/main.py，但在 ${PROJECT_ROOT}/simulator/ 下未找到。" >&2
  exit 1
fi

# 创建日志目录
mkdir -p "${LOG_DIR}"

# Python 虚拟环境加载（优先加载 backend/.venv，其次全局环境）
# 如果存在虚拟环境则激活，否则使用系统 Python
if [[ -f "${PROJECT_ROOT}/backend/.venv/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "${PROJECT_ROOT}/backend/.venv/bin/activate"
  echo "[INFO] 已加载 Python 虚拟环境: ${PROJECT_ROOT}/backend/.venv"
elif [[ -f "${PROJECT_ROOT}/.venv/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "${PROJECT_ROOT}/.venv/bin/activate"
  echo "[INFO] 已加载 Python 虚拟环境: ${PROJECT_ROOT}/.venv"
else
  echo "[WARN] 未找到 Python 虚拟环境，将使用全局 Python 环境。"
  echo "[WARN] 建议创建虚拟环境: python -m venv backend/.venv"
fi

# ─────────────────────────────────────────────
# 2. 参数解析
# ─────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --duration)
      TEST_DURATION_SEC="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --help|-h)
      echo "用法: $0 [--duration 秒] [--dry-run]"
      echo "  --duration    每个速率梯度的运行时长（默认 180 秒）"
      echo "  --dry-run     仅打印要执行的命令，不实际运行"
      exit 0
      ;;
    *)
      echo "[ERROR] 未知参数: $1" >&2
      echo "用法: $0 [--duration 秒] [--dry-run]" >&2
      exit 1
      ;;
  esac
done

# ─────────────────────────────────────────────
# 3. 工具函数
# ─────────────────────────────────────────────

# 日志输出（带时间戳）
log_info()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO]  $*"; }
log_warn()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN]  $*"; }
log_error() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" >&2; }

# 高亮分隔线打印
print_banner() {
  echo ""
  echo "========================================================================"
  echo "  $*"
  echo "========================================================================"
}

# 计时器
timer_start() { date +%s; }
timer_elapsed() {
  local start=$1
  local end
  end=$(date +%s)
  echo $(( end - start ))
}

# ─────────────────────────────────────────────
# 4. 信号处理（极其关键）
# ─────────────────────────────────────────────
# 使用全局数组保存所有后台模拟器进程的 PID
SIMULATOR_PIDS=()

# 清理函数：终止所有后台运行的模拟器进程
cleanup() {
  local sig_name="$1"
  log_warn "收到 ${sig_name} 信号，正在清理后台进程..."

  if [[ ${#SIMULATOR_PIDS[@]} -gt 0 ]]; then
    for pid in "${SIMULATOR_PIDS[@]}"; do
      if kill -0 "$pid" 2>/dev/null; then
        log_info "正在终止模拟器进程 PID: $pid"
        kill -TERM "$pid" 2>/dev/null || true
        # 等待进程退出（最多等 5 秒）
        wait "$pid" 2>/dev/null || true
      fi
    done
  fi

  # 额外安全措施：查找并清理任何残留的 simulator/main.py 进程
  remaining_pids=$(pgrep -f "simulator/main.py" 2>/dev/null || true)
  if [[ -n "$remaining_pids" ]]; then
    log_warn "发现残留的模拟器进程，正在强制清理..."
    echo "$remaining_pids" | xargs kill -TERM 2>/dev/null || true
    sleep 2
    # 如果还有残留，使用 SIGKILL
    remaining_pids=$(pgrep -f "simulator/main.py" 2>/dev/null || true)
    if [[ -n "$remaining_pids" ]]; then
      echo "$remaining_pids" | xargs kill -KILL 2>/dev/null || true
    fi
  fi

  log_info "清理完成，退出脚本。"
  exit 0
}

# 注册信号处理函数
trap 'cleanup SIGINT'  SIGINT
trap 'cleanup SIGTERM' SIGTERM
trap 'cleanup SIGQUIT' SIGQUIT

# ─────────────────────────────────────────────
# 5. 压测主流程
# ─────────────────────────────────────────────
BENCHMARK_START=$(timer_start)

print_banner "AgentScope 实时链路阶梯式压测启动"
log_info "测试参数:"
log_info "  并发速率梯度: ${RATES[*]} Events/s"
log_info "  每梯度时长: ${TEST_DURATION_SEC} 秒"
log_info "  Kafka Bootstrap: ${KAFKA_BOOTSTRAP}"
log_info "  Kafka Topic: ${KAFKA_TOPIC}"
log_info "  Spark UI: ${SPARK_UI_URL}"
log_info "  日志目录: ${LOG_DIR}"
echo ""

GRADE_INDEX=1
for rate in "${RATES[@]}"; do
  GRADE_START=$(timer_start)
  LOG_FILE="${LOG_DIR}/benchmark_rate_${rate}.log"

  print_banner "梯度测试: ${rate} Events/s (第 ${GRADE_INDEX} / ${#RATES[@]} 轮)"

  # ─────────────────────────────────────────
  # 5.1 启动模拟器
  # ─────────────────────────────────────────
  log_info "启动模拟器，速率: ${rate} events/s..."

  if [[ "$DRY_RUN" == true ]]; then
    echo "[DRY-RUN] cd ${PROJECT_ROOT} && python simulator/main.py \\"
    echo "  --mode realtime --kafka-bootstrap ${KAFKA_BOOTSTRAP} \\"
    echo "  --kafka-topic ${KAFKA_TOPIC} --rate ${rate} \\"
    echo "  > ${LOG_FILE} 2>&1 &"
    SIMULATOR_PID=99999
  else
    # 后台启动模拟器（在子 shell 中运行，防止 cd 影响当前目录）
    cd "${PROJECT_ROOT}" && python simulator/main.py \
      --mode realtime \
      --kafka-bootstrap "${KAFKA_BOOTSTRAP}" \
      --kafka-topic "${KAFKA_TOPIC}" \
      --rate "${rate}" \
      > "${LOG_FILE}" 2>&1 &
    SIMULATOR_PID=$!
    log_info "模拟器已启动，PID: ${SIMULATOR_PID}，日志: ${LOG_FILE}"
  fi

  SIMULATOR_PIDS+=("${SIMULATOR_PID}")

  # ─────────────────────────────────────────
  # 5.2 运行中段提示（约 50% 进度处）
  # ─────────────────────────────────────────
  MID_POINT=$(( TEST_DURATION_SEC / 2 ))

  log_info "等待 ${MID_POINT} 秒后输出中段监控提示..."
  sleep "${MID_POINT}"

  # 打印中段提示（高亮显示，告知用户手动观察监控指标）
  echo ""
  echo "============================================================"
  echo "  [INFO] 正在以速率 ${rate} events/s 运行压测..."
  echo "  [INFO] 已运行约 ${MID_POINT}s / ${TEST_DURATION_SEC}s"
  echo ""
  echo "  [ACTION] 请打开新的终端执行以下命令，观察 Kafka 消费堆积 (LAG):"
  echo ""
  echo "      ${KAFKA_BIN}/kafka-consumer-groups.sh \\"
  echo "        --bootstrap-server ${KAFKA_BOOTSTRAP} \\"
  echo "        --describe \\"
  echo "        --group agentscope-streaming-group"
  echo ""
  echo "  [ACTION] 请在浏览器打开 Spark UI (${SPARK_UI_URL})，观察："
  echo ""
  echo "      1. Processing Time（批次处理耗时，应低于批次间隔）"
  echo "      2. Scheduling Delay（调度延迟，应保持平稳）"
  echo ""
  echo "  [ACTION] 观察 Redis 实时指标:"
  echo ""
  echo "      redis-cli -h middleware -p 6379 GET agentscope:realtime:overview"
  echo ""
  echo "============================================================"
  echo ""

  # ─────────────────────────────────────────
  # 5.3 等待剩余时间
  # ─────────────────────────────────────────
  REMAINING=$(( TEST_DURATION_SEC - MID_POINT ))
  log_info "继续运行，剩余 ${REMAINING} 秒..."
  sleep "${REMAINING}"

  # ─────────────────────────────────────────
  # 5.4 终止模拟器 & 等待 Spark 消费缓冲
  # ─────────────────────────────────────────
  log_info "梯度时间到，正在终止模拟器 (PID: ${SIMULATOR_PID})..."

  if [[ "$DRY_RUN" == false ]]; then
    kill -TERM "${SIMULATOR_PID}" 2>/dev/null || true
    wait "${SIMULATOR_PID}" 2>/dev/null || true
  fi

  GRADE_ELAPSED=$(timer_elapsed ${GRADE_START})
  log_info "模拟器已终止，运行耗时: ${GRADE_ELAPSED}s"

  # ─────────────────────────────────────────
  # 5.5 等待 Spark 消费完堆积余量（关键！）
  # ─────────────────────────────────────────
  log_info "等待 15 秒，让 Spark 集群消费完堆积的余量数据..."
  sleep 15

  # 提取结果摘要（从模拟器日志中获取发送事件数）
  if [[ "$DRY_RUN" == false && -f "${LOG_FILE}" ]]; then
    sent_count=$(grep -c "sent" "${LOG_FILE}" 2>/dev/null || echo "N/A")
    log_info "梯度 ${rate} events/s 日志摘要: 日志共 $(wc -l < "${LOG_FILE}") 行"
  fi

  log_info "梯度 ${rate} events/s 测试完成 ✓"
  echo ""

  GRADE_INDEX=$(( GRADE_INDEX + 1 ))
done

# ─────────────────────────────────────────────
# 6. 压测汇总
# ─────────────────────────────────────────────
TOTAL_ELAPSED=$(timer_elapsed ${BENCHMARK_START})

print_banner "阶梯式压测全部完成"
log_info "总耗时: ${TOTAL_ELAPSED} 秒"
echo ""

if [[ "$DRY_RUN" == false ]]; then
  echo "各梯度测试日志:"
  for rate in "${RATES[@]}"; do
    log_file="${LOG_DIR}/benchmark_rate_${rate}.log"
    if [[ -f "${log_file}" ]]; then
      line_count=$(wc -l < "${log_file}")
      echo "  ${rate} events/s -> ${log_file} (${line_count} 行)"
    fi
  done
  echo ""
  echo "请参考以下数据记录表格，编写性能测试报告:"
  echo "  ${REPORT_DIR}/performance_test_report.md"
fi

echo ""
log_info "提示: 如需生成性能测试报告，请参照 docs/performance_test_report.md 模板。"
log_info "脚本退出。"

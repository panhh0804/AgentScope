#!/usr/bin/env bash
# ============================================================================
# test_fault_tolerance.sh
# AgentScope 异常容错演示脚本
#
# 用途：向 Kafka 发送各种"畸形"事件，验证 Spark Streaming 不会崩溃
#       而是优雅地跳过/记录异常消息，继续处理后续正常数据。
#
# 前置条件：
#   1. Kafka 已启动，Topic agent-events 存在
#   2. Spark Streaming 作业正在运行
#
# 用法：
#   bash scripts/test_fault_tolerance.sh
#
# 演示效果（答辩时展示）：
#   1. 先发送一条正常事件，确认链路正常
#   2. 依次发送 6 种异常事件（字段缺失、类型错误、空 JSON 等）
#   3. 最后再发一条正常事件，证明 Streaming 仍然存活
#   4. 检查 Redis 中正常事件的指标有更新，异常事件被安全丢弃
# ============================================================================
set -uo pipefail

KAFKA_BIN="${KAFKA_BIN:-/usr/local/kafka_2.11-2.1.0/bin}"
KAFKA_BOOTSTRAP="${KAFKA_BOOTSTRAP_SERVERS:-middleware:9092}"
KAFKA_TOPIC="${KAFKA_TOPIC:-agent-events}"
REDIS_HOST="${REDIS_HOST:-middleware}"
REDIS_PORT="${REDIS_PORT:-6379}"

PRODUCER="${KAFKA_BIN}/kafka-console-producer.sh --broker-list ${KAFKA_BOOTSTRAP} --topic ${KAFKA_TOPIC}"

# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────
TS=$(date '+%Y-%m-%dT%H:%M:%S')
TRACE_NORMAL_1="trace_fault_test_normal_1_$$"
TRACE_NORMAL_2="trace_fault_test_normal_2_$$"

send_event() {
  local description="$1"
  local payload="$2"
  
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📤  ${description}"
  echo "    Payload: ${payload:0:120}..."
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  
  echo "$payload" | ${PRODUCER} 2>/dev/null
  sleep 2
}

# ─────────────────────────────────────────────
# 正常事件模板
# ─────────────────────────────────────────────
make_normal_event() {
  local trace_id="$1"
  local agent_id="$2"
  cat <<EOF
{"event_id":"evt_fault_test_${RANDOM}","trace_id":"${trace_id}","run_id":"run_fault_test_${RANDOM}","parent_run_id":"","agent_id":"${agent_id}","parent_agent_id":"","agent_role":"worker","event_type":"llm_request","status":"success","timestamp":"${TS}","latency_ms":150,"prompt_tokens":100,"completion_tokens":50,"total_tokens":150,"cost_usd":0.003,"model_name":"gpt-4","tool_name":"","error_type":"","retry_count":0,"metadata_json":"{}"}
EOF
}

# ─────────────────────────────────────────────
# 开始测试
# ─────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       AgentScope 异常容错演示                            ║"
echo "║       $(date '+%Y-%m-%d %H:%M:%S')                               ║"
echo "╚══════════════════════════════════════════════════════════╝"

# ───── 测试 0：先发一条正常事件，确认链路畅通 ─────
send_event \
  "测试 0/7：正常事件（基准测试，确认链路畅通）" \
  "$(make_normal_event "$TRACE_NORMAL_1" "agent_baseline")"

# ───── 测试 1：完全缺失 agent_id 字段 ─────
send_event \
  "测试 1/7：❌ 缺失 agent_id 字段（应被安全跳过）" \
  '{"event_id":"evt_bad_1","trace_id":"trace_bad_1","run_id":"run_bad_1","event_type":"llm_request","status":"success","timestamp":"'"${TS}"'","latency_ms":100,"total_tokens":50}'

# ───── 测试 2：latency_ms 为字符串而非数字 ─────
send_event \
  "测试 2/7：❌ latency_ms 类型错误（字符串 'abc'，应被安全跳过）" \
  '{"event_id":"evt_bad_2","trace_id":"trace_bad_2","run_id":"run_bad_2","agent_id":"agent_bad_type","agent_role":"worker","event_type":"llm_request","status":"success","timestamp":"'"${TS}"'","latency_ms":"abc","total_tokens":50}'

# ───── 测试 3：空 JSON ─────
send_event \
  "测试 3/7：❌ 空 JSON 对象（应被安全跳过）" \
  '{}'

# ───── 测试 4：非 JSON 纯文本垃圾数据 ─────
send_event \
  "测试 4/7：❌ 非 JSON 纯文本（应被安全跳过）" \
  'this is not json at all!!!'

# ───── 测试 5：event_time 为非法日期格式 ─────
send_event \
  "测试 5/7：❌ event_time 格式非法（应被安全跳过）" \
  '{"event_id":"evt_bad_5","trace_id":"trace_bad_5","run_id":"run_bad_5","agent_id":"agent_bad_time","agent_role":"worker","event_type":"llm_request","status":"success","timestamp":"not-a-date","latency_ms":100,"total_tokens":50}'

# ───── 测试 6：超大 total_tokens 触发告警 ─────
send_event \
  "测试 6/7：⚠️  超大 total_tokens=999999（应触发 token_overuse 告警但不崩溃）" \
  '{"event_id":"evt_bad_6","trace_id":"trace_bad_6","run_id":"run_bad_6","agent_id":"agent_token_bomb","agent_role":"worker","event_type":"llm_request","status":"success","timestamp":"'"${TS}"'","latency_ms":100,"prompt_tokens":500000,"completion_tokens":499999,"total_tokens":999999,"cost_usd":99.99,"model_name":"gpt-4","tool_name":"","error_type":"","retry_count":0,"metadata_json":"{}"}'

# ───── 测试 7：再发一条正常事件，证明 Streaming 仍然存活 ─────
send_event \
  "测试 7/7：✅ 正常事件（验证 Streaming 在经历 6 次异常后仍然存活）" \
  "$(make_normal_event "$TRACE_NORMAL_2" "agent_survivor")"

# ─────────────────────────────────────────────
# 验证结果
# ─────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════"
echo "⏳  等待 10 秒，让 Spark Streaming 处理完所有消息..."
echo "════════════════════════════════════════════════════════════"
sleep 10

echo ""
echo "────── 验证 Redis 数据 ──────"

# 检查 Streaming 是否仍在往 Redis 写入
echo ""
echo "📊  Redis 中的实时指标 Key："
redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" KEYS "agentscope:*" 2>/dev/null | head -n 20 || echo "  （无法连接 Redis 或无相关 Key）"

echo ""
echo "📊  Redis 中的最近告警（应包含 token_overuse）："
redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" GET "agentscope:realtime:alerts" 2>/dev/null || echo "  （无法读取告警数据）"

# ─────────────────────────────────────────────
# 结论
# ─────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  异常容错演示完成                                        ║"
echo "║                                                          ║"
echo "║  如果 Spark Streaming 仍在运行且 Redis 指标正常更新，    ║"
echo "║  则说明系统具备良好的异常容错能力：                       ║"
echo "║    • 畸形 JSON、缺失字段、类型错误 → 安全跳过            ║"
echo "║    • 超阈值数据 → 触发告警但不崩溃                       ║"
echo "║    • 异常后的正常数据 → 继续正常处理                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "💡  请同时检查 YARN UI (http://master:8088) 确认 Spark Streaming application 状态为 RUNNING。"

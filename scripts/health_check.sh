#!/usr/bin/env bash
# ============================================================================
# health_check.sh
# AgentScope 集群健康检查 —— 一键诊断所有组件存活状态
#
# 用法：
#   bash scripts/health_check.sh
#
# 检查项（共 8 项）：
#   1. HDFS       — NameNode 存活 + Live DataNode 数量
#   2. YARN       — ResourceManager 存活 + Active NodeManager 数量
#   3. Spark      — Master 存活 + Alive Worker 数量
#   4. Kafka      — Broker 可达 + agent-events Topic 存在
#   5. ZooKeeper  — 可连接
#   6. Redis      — PING 响应
#   7. MySQL      — 连接测试 (Source 库 + Analytics 库)
#   8. FastAPI    — /health 端点响应
# ============================================================================
set -uo pipefail

# ─────────────────────────────────────────────
# 加载环境变量（crontab / 非交互式 SSH 不会自动加载）
# ─────────────────────────────────────────────
set +u
[[ -f /etc/profile ]] && source /etc/profile 2>/dev/null || true
[[ -f ~/.bashrc ]]    && source ~/.bashrc 2>/dev/null || true
set -u

# ─────────────────────────────────────────────
# 环境变量默认值
# ─────────────────────────────────────────────
KAFKA_BIN="${KAFKA_BIN:-/usr/local/kafka_2.11-2.1.0/bin}"
KAFKA_ZOOKEEPER="${KAFKA_ZOOKEEPER:-middleware:2181}"
KAFKA_BOOTSTRAP="${KAFKA_BOOTSTRAP_SERVERS:-middleware:9092}"
KAFKA_TOPIC="${KAFKA_TOPIC:-agent-events}"
REDIS_HOST="${REDIS_HOST:-middleware}"
REDIS_PORT="${REDIS_PORT:-6379}"
MYSQL_HOST="${MYSQL_HOST:-middleware}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-agentscope}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-agentscope_pass}"
BACKEND_HOST="${BACKEND_PUBLIC_HOST:-${BACKEND_HOST:-master}}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

# ─────────────────────────────────────────────
# 输出工具
# ─────────────────────────────────────────────
PASS=0
FAIL=0
WARN=0

print_header() {
  echo ""
  echo "╔══════════════════════════════════════════════════════╗"
  echo "║       AgentScope 集群健康检查报告                    ║"
  echo "║       $(date '+%Y-%m-%d %H:%M:%S')                           ║"
  echo "╚══════════════════════════════════════════════════════╝"
  echo ""
}

check_pass() {
  echo "  [✅ PASS] $*"
  PASS=$((PASS + 1))
}

check_fail() {
  echo "  [❌ FAIL] $*"
  FAIL=$((FAIL + 1))
}

check_warn() {
  echo "  [⚠️  WARN] $*"
  WARN=$((WARN + 1))
}

section() {
  echo ""
  echo "────── $1 ──────"
}

# ─────────────────────────────────────────────
# 1. HDFS 检查
# ─────────────────────────────────────────────
check_hdfs() {
  section "1/8  HDFS"
  
  local report
  report=$(hdfs dfsadmin -report 2>/dev/null) || { check_fail "HDFS NameNode 不可达"; return; }
  
  local live_nodes
  live_nodes=$(echo "$report" | grep -c "^Name:" || echo "0")
  
  if [[ "$live_nodes" -ge 2 ]]; then
    check_pass "HDFS NameNode 正常，Live DataNode: ${live_nodes}"
  elif [[ "$live_nodes" -ge 1 ]]; then
    check_warn "HDFS 运行中，但 Live DataNode 仅 ${live_nodes} 个（预期 2）"
  else
    check_fail "HDFS 无 Live DataNode"
  fi
}

# ─────────────────────────────────────────────
# 2. YARN 检查
# ─────────────────────────────────────────────
check_yarn() {
  section "2/8  YARN"
  
  local node_list
  node_list=$(yarn node -list 2>/dev/null) || { check_fail "YARN ResourceManager 不可达"; return; }
  
  local active_nodes
  active_nodes=$(echo "$node_list" | grep -c "RUNNING" || echo "0")
  
  if [[ "$active_nodes" -ge 2 ]]; then
    check_pass "YARN ResourceManager 正常，Active NodeManager: ${active_nodes}"
  elif [[ "$active_nodes" -ge 1 ]]; then
    check_warn "YARN 运行中，但 Active NodeManager 仅 ${active_nodes} 个（预期 2）"
  else
    check_fail "YARN 无 Active NodeManager"
  fi
}

# ─────────────────────────────────────────────
# 3. Spark 检查
# ─────────────────────────────────────────────
check_spark() {
  section "3/8  Spark Standalone"
  
  # 检查 Master
  if jps -l 2>/dev/null | grep -q "org.apache.spark.deploy.master.Master"; then
    check_pass "Spark Master 运行中"
  else
    check_fail "Spark Master 未运行"
    return
  fi
  
  # 通过 Spark UI 检查 Worker
  local ui_html
  ui_html=$(curl -s --connect-timeout 5 "http://localhost:8080" 2>/dev/null) || { check_warn "Spark Master UI 不可访问"; return; }
  
  local alive_workers
  alive_workers=$(echo "$ui_html" | grep -oP 'Alive Workers.*?(\d+)' | grep -oP '\d+$' || echo "0")
  
  if [[ "$alive_workers" -ge 2 ]]; then
    check_pass "Spark Alive Workers: ${alive_workers}"
  elif [[ "$alive_workers" -ge 1 ]]; then
    check_warn "Spark Worker 仅 ${alive_workers} 个存活（预期 2）"
  else
    # fallback: 尝试通过 SSH 检查 worker 上的 jps
    check_warn "无法从 UI 获取 Worker 数量，请手动检查 worker 节点"
  fi
}

# ─────────────────────────────────────────────
# 4. Kafka 检查
# ─────────────────────────────────────────────
check_kafka() {
  section "4/8  Kafka"
  
  local topic_list
  topic_list=$("${KAFKA_BIN}/kafka-topics.sh" --zookeeper "${KAFKA_ZOOKEEPER}" --list 2>/dev/null) || {
    check_fail "Kafka Broker 不可达（ZooKeeper: ${KAFKA_ZOOKEEPER}）"
    return
  }
  
  if echo "$topic_list" | grep -q "${KAFKA_TOPIC}"; then
    check_pass "Kafka Broker 正常，Topic '${KAFKA_TOPIC}' 存在"
  else
    check_fail "Kafka 可用但 Topic '${KAFKA_TOPIC}' 不存在，请运行 create_kafka_topics.sh"
  fi
}

# ─────────────────────────────────────────────
# 5. ZooKeeper 检查
# ─────────────────────────────────────────────
check_zookeeper() {
  section "5/8  ZooKeeper"
  
  local zk_host="${KAFKA_ZOOKEEPER%%:*}"
  local zk_port="${KAFKA_ZOOKEEPER##*:}"
  
  local zk_response
  zk_response=$(echo ruok | nc -w 3 "$zk_host" "$zk_port" 2>/dev/null) || { check_fail "ZooKeeper 不可达（${KAFKA_ZOOKEEPER}）"; return; }
  
  if [[ "$zk_response" == "imok" ]]; then
    check_pass "ZooKeeper 正常（${KAFKA_ZOOKEEPER}）"
  else
    check_warn "ZooKeeper 响应异常: ${zk_response}"
  fi
}

# ─────────────────────────────────────────────
# 6. Redis 检查
# ─────────────────────────────────────────────
check_redis() {
  section "6/8  Redis"
  
  local pong
  pong=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ping 2>/dev/null) || { check_fail "Redis 不可达（${REDIS_HOST}:${REDIS_PORT}）"; return; }
  
  if [[ "$pong" == "PONG" ]]; then
    # 顺便检查一下是否有实时指标数据
    local key_count
    key_count=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" DBSIZE 2>/dev/null | grep -oP '\d+' || echo "0")
    check_pass "Redis 正常（PONG），当前 Key 数量: ${key_count}"
  else
    check_fail "Redis 响应异常: ${pong}"
  fi
}

# ─────────────────────────────────────────────
# 7. MySQL 检查
# ─────────────────────────────────────────────
check_mysql() {
  section "7/8  MySQL"
  
  # 优先使用 mysql 客户端，不存在则尝试 mysqladmin
  if command -v mysql >/dev/null 2>&1; then
    # 检查 Source 库
    if mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1" "$MYSQL_SOURCE_DB" >/dev/null 2>&1; then
      local src_count
      src_count=$(mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -N -e "SELECT COUNT(*) FROM agent_events_source" "agentscope_source" 2>/dev/null || echo "?")
      check_pass "MySQL Source 库正常（agentscope_source，数据量: ${src_count} 条）"
    else
      check_fail "MySQL Source 库连接失败"
    fi
    
    # 检查 Analytics 库
    if mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1" "agentscope_analytics" >/dev/null 2>&1; then
      check_pass "MySQL Analytics 库正常（agentscope_analytics）"
    else
      check_fail "MySQL Analytics 库连接失败"
    fi
  elif command -v mysqladmin >/dev/null 2>&1; then
    if mysqladmin -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" ping >/dev/null 2>&1; then
      check_pass "MySQL 可达（mysqladmin ping 成功，无 mysql 客户端无法检查库表）"
    else
      check_fail "MySQL 不可达"
    fi
  else
    # 最终兜底：用 nc 探测端口
    if nc -z -w 3 "$MYSQL_HOST" "$MYSQL_PORT" 2>/dev/null; then
      check_warn "MySQL 端口 ${MYSQL_HOST}:${MYSQL_PORT} 可达（无 mysql 客户端，无法深度检查）"
    else
      check_fail "MySQL 端口 ${MYSQL_HOST}:${MYSQL_PORT} 不可达"
    fi
  fi
}

# ─────────────────────────────────────────────
# 8. FastAPI 后端检查
# ─────────────────────────────────────────────
check_backend() {
  section "8/8  FastAPI 后端"
  
  local response
  response=$(curl -fsS --connect-timeout 5 "http://${BACKEND_HOST}:${BACKEND_PORT}/health" 2>/dev/null) || {
    check_warn "FastAPI 后端不可达（http://${BACKEND_HOST}:${BACKEND_PORT}/health）—— 可能尚未启动"
    return
  }
  check_pass "FastAPI 后端正常：${response}"
}

# ─────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────
print_header

check_hdfs
check_yarn
check_spark
check_kafka
check_zookeeper
check_redis
check_mysql
check_backend

# ─────────────────────────────────────────────
# 汇总
# ─────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  汇总：✅ 通过 ${PASS}  ⚠️  警告 ${WARN}  ❌ 失败 ${FAIL}              ║"
echo "╚══════════════════════════════════════════════════════╝"

if [[ "$FAIL" -gt 0 ]]; then
  echo ""
  echo "存在失败项，请排查后再启动业务链路。"
  exit 1
fi

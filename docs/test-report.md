# 测试记录

## 实时链路

| 测试项 | 预期结果 | 实际结果 |
|---|---|---|
| 实时模拟器发送事件 | Kafka 持续收到消息 | 已验证 |
| Spark Streaming 消费 | 批次持续处理 | 已验证 |
| Redis 指标写入 | 指标持续更新 | 已验证 |
| 实时 API | 返回最新数据 | 已验证 |
| 异常模拟 | Redis 出现最近告警 | 已验证 |

## 实时链路后端闭环验证记录

本轮验证范围：

```text
Agent 模拟器 -> Kafka -> Spark Streaming -> Redis -> FastAPI realtime API
```

本轮未做 Vue/ECharts 前端联调。

### 1. 基础服务检查

middleware 节点基础服务已启动：

```text
ZooKeeper: middleware:2181
Kafka: middleware:9092
Redis: middleware:6379
```

### 2. Kafka topic 创建

topic 名称：

```text
agent-events
```

Kafka 版本：

```text
kafka_2.11-2.1.0
```

该版本 `kafka-topics.sh` 创建和查看 topic 使用 `--zookeeper`：

```bash
/usr/local/kafka_2.11-2.1.0/bin/kafka-topics.sh --zookeeper middleware:2181 --list
/usr/local/kafka_2.11-2.1.0/bin/kafka-topics.sh --create --zookeeper middleware:2181 --replication-factor 1 --partitions 1 --topic agent-events
```

验证结论：`agent-events` topic 已创建成功。

### 3. 模拟器写入 Kafka

Kafka consumer 验证命令：

```bash
/usr/local/kafka_2.11-2.1.0/bin/kafka-console-consumer.sh --bootstrap-server middleware:9092 --topic agent-events --from-beginning --max-messages 5
```

验证结果：

```text
成功消费 5 条 JSON 事件。
事件包含 agent_id、agent_role、event_type、latency_ms、status、trace_id、run_id、timestamp 等字段。
```

验证结论：

```text
Agent 模拟器 -> Kafka 已跑通。
```

### 4. Spark Streaming 打包

打包产物：

```text
spark-streaming/target/agentscope-spark-streaming-0.1.0.jar
```

验证结论：Spark Streaming 作业已成功打包。

### 5. Spark Streaming 运行

主类：

```text
com.agentscope.streaming.AgentEventStreamingJob
```

启动参数：

```text
--kafka-bootstrap middleware:9092
--topic agent-events
--redis-host middleware
--redis-port 6379
```

运行模式：

```text
spark://master:7077
```

验证结论：

```text
Spark Streaming 能消费 Kafka，并将实时指标写入 Redis。
```

### 6. Redis key 验证

Redis 中已产生实时数据 key：

```text
agentscope:realtime:overview
agentscope:realtime:agents
agentscope:realtime:alerts
```

`agentscope:realtime:overview` 示例字段包括：

```text
success_count
token_total_5m
error_rate
avg_latency_ms
events_per_minute
estimated_cost_5m
running_tasks
open_alerts
active_agents
retry_tasks
failed_count
```

验证结论：

```text
Spark Streaming -> Redis 已跑通。
```

### 7. FastAPI realtime API 验证

健康检查：

```text
GET /health
返回 {"status":"ok"}
```

实时总览：

```text
GET /api/v1/realtime/overview
```

返回字段包括：

```text
success_count
token_total_5m
error_rate
avg_latency_ms
events_per_minute
running_tasks
open_alerts
active_agents
retry_tasks
failed_count
```

Agent 状态：

```text
GET /api/v1/realtime/agents
```

已返回以下 Agent 的实时状态、成功率、平均延迟、`token_total` 和 `retry_count`：

```text
analysis_agent
search_agent
reviewer_agent
writer_agent
planner_agent
```

实时告警：

```text
GET /api/v1/realtime/alerts
```

已返回：

```text
high_latency
frequent_retry
```

告警来源：

```text
source = streaming
```

最终结论：

```text
实时链路后端闭环已跑通：Agent 模拟器 -> Kafka -> Spark Streaming -> Redis -> FastAPI realtime API。
```

### 💡 优化项与新增特性验证

- **实时告警去重机制**：
  - *原风险*：以前同一窗口内的相同告警会在每个批次重复写入 Redis 造成刷屏。
  - *处理结果*：已优化为生成确定性的 `alert_id`（结构：`alert_type + agent_id + run_id + window_start`），并在 Redis 中配合使用 `SETNX` 及 `TTL` 缓存。在相同滑窗期内重复告警被过滤丢弃，仅写入一次，彻底解决了重复告警的风险。
- **数仓指标口径精准化**：
  - *原口径风险*：以前 Spark 批计算中 `execution_count` 和协作调用次数是按照原始日志事件条数计算的，导致指标虚高。
  - *处理结果*：现均已改造为按 `run_id` 去重计算，确保同一 run 周期内只计入 1 次执行。并且限制 `total_tokens` 及 `cost_usd` 指标仅聚合自微观 `llm_response` 事件，非 LLM 回答的普通系统调度事件指标强制归零，数仓计算更符合真实业务规范。
- **DATA_MODE 模式切换**：
  - 新增 `DATA_MODE` 变量。当设为 `strict` 模式时，如若 Redis 或 MySQL 无真实数据，平台直接返回空数据，禁止伪装。而在 `demo` 模式下，系统在缺失数据时自动进行回退保护，返回高质量仿真 Mock 数据。
- **一键自动化自检**：
  - 提供 `scripts/run_local_checks.sh` 自检脚本，一键覆盖 Python 语法检查、离线数据模拟、以及模拟器规则合规校验。

## 离线链路

| 测试项 | 预期结果 | 实际结果 |
|---|---|---|
| 离线模拟器 | Source 表出现批量数据 | 已验证 |
| DataX 导入 | HDFS Raw 出现文件 | 已验证 |
| Spark 清洗 | HDFS Clean 出现结果 | 已验证 |
| Spark 分析 | Metric 和 Analytics 有结果 | 已验证 |
| 历史 API | 返回趋势与排行 | 已验证 |
| AI 报告 | 生成 Markdown 报告 | 待测试 |

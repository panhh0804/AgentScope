# AgentScope 多智能体运行监测与效能分析平台

AgentScope 是一个面向大数据课程综合实践的多 Agent 运行观测与效能分析项目。仓库按设计说明书初始化为“实时 + 离线”双链路：

```text
实时链路：
Agent 模拟器 -> Kafka -> Spark Streaming -> Redis -> FastAPI -> Vue/ECharts

离线链路：
Agent 模拟器 -> MySQL Source -> DataX -> HDFS Raw
-> Spark Batch -> HDFS Clean/Metric + MySQL Analytics -> FastAPI -> Vue/ECharts
```

## 当前状态

离线链路已经完成闭环验证：

- `MySQL Source -> DataX -> HDFS Raw`
- `HDFS Raw -> Spark Clean -> HDFS Clean`
- `HDFS Clean -> Spark Batch -> HDFS Metric + MySQL Analytics`
- `FastAPI -> 读取 MySQL Analytics 并返回历史分析接口`

已验证的结果包括：

- `2026-06-24` 的 raw、clean、metric 产物已生成
- `agentscope_analytics` 中的离线分析表已写入真实数据
- 后端 `http://59.110.123.179:8000/health` 和历史指标接口可正常访问

### 实时链路后端闭环状态

实时链路后端闭环已经在真实集群完成验证：

```text
Agent 模拟器 -> Kafka -> Spark Streaming -> Redis -> FastAPI realtime API
```

本轮验证范围到 FastAPI realtime API 为止，不包含 Vue/ECharts 前端联调，不表示前端实时页面已经完成。

已验证的基础服务：

- ZooKeeper：`middleware:2181`
- Kafka：`middleware:9092`
- Redis：`middleware:6379`

Kafka topic：

```text
agent-events
```

当前 Kafka 版本为 `kafka_2.11-2.1.0`。该版本的 `kafka-topics.sh` 创建和查看 topic 时使用 ZooKeeper 参数：

```bash
/usr/local/kafka_2.11-2.1.0/bin/kafka-topics.sh --zookeeper middleware:2181 --list
/usr/local/kafka_2.11-2.1.0/bin/kafka-topics.sh --create --zookeeper middleware:2181 --replication-factor 1 --partitions 1 --topic agent-events
```

Redis 实时 key：

```text
agentscope:realtime:overview
agentscope:realtime:agents
agentscope:realtime:alerts
```

FastAPI realtime API：

```text
GET /health
GET /api/v1/realtime/overview
GET /api/v1/realtime/agents
GET /api/v1/realtime/alerts
```

其中 `/api/v1/realtime/overview` 已验证返回 Redis 中的真实实时指标，包括：

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

## 目录结构

```text
agentscope/
├── docs/                 # 设计摘要、部署、API、数据字典、测试记录
├── simulator/            # Python Agent 事件模拟器，支持 realtime/offline
├── spark-streaming/      # Spark 2.4 + Scala 2.11 实时作业
├── spark-batch/          # Spark 2.4 + Scala 2.11 离线清洗与分析作业
├── backend/              # FastAPI 后端与 AI 报告服务
├── frontend/             # Vue 3 + ECharts 可视化前端
├── sql/                  # MySQL Source / Analytics 建表脚本
├── scripts/              # Kafka、DataX、Spark 作业脚本
└── deploy/               # Nginx、systemd、环境模板
```

## 本地快速预览

本地机器通常没有 Hadoop/Kafka/Spark 集群，因此默认代码提供 mock 降级数据，便于先开发后端和前端。

### 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

打开：

```text
http://localhost:8000/docs
```

### 前端

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

打开：

```text
http://localhost:5173
```

## 模拟器

实时模式发送 Kafka 事件：

```bash
cd simulator
python main.py --mode realtime --kafka-bootstrap middleware:9092 --rate 10
```

离线模式生成历史事件并写入 MySQL Source：

```bash
cd simulator
python main.py --mode offline --count 10000 --start-date 2026-06-01 --end-date 2026-06-23
```

没有安装 Kafka/MySQL 依赖时，可先输出 JSONL 样例：

```bash
cd simulator
python main.py --mode offline --count 100 --output ../tmp/agent_events.jsonl
```

## 集群运行顺序

1. 在 `middleware` 启动 MySQL、Redis、ZooKeeper、Kafka。
2. 在 `master` 启动 HDFS、YARN、Spark。
3. 执行 `sql/source_schema.sql` 和 `sql/analytics_schema.sql`。
4. 执行 `scripts/create_kafka_topics.sh`。
5. 启动 Spark Streaming：`scripts/start_streaming_job.sh`。
6. 启动实时模拟器。
7. 离线链路按顺序运行：离线模拟器、DataX、Clean Job、Batch Jobs、报告生成。

## 设计来源

本仓库根据《AgentScope 多智能体运行监测与效能分析平台设计说明书》初始化，当前目标是提供清晰、可扩展、可答辩的工程起点。后续开发优先级：

1. 实时链路联调：Kafka、Spark Streaming 和 Redis。
2. 前端页面联调：实时总览、历史分析、告警中心和 AI 报告。
3. 补充 AI 报告、异常规则和部署测试文档。

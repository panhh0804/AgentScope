# 部署说明

## 环境版本

- Ubuntu 20.04
- Java 8
- Hadoop 2.7.6
- Spark 2.4.0
- Scala 2.11
- DataX
- Kafka + ZooKeeper
- Redis
- MySQL
- Python 3.8+
- Node.js 18+

## 启动顺序

### master

```bash
start-dfs.sh
start-yarn.sh
/usr/local/spark/sbin/start-all.sh
```

### middleware

```text
MySQL -> Redis -> ZooKeeper -> Kafka
```

## 实时链路启动顺序

实时链路后端闭环：

```text
Agent 模拟器 -> Kafka -> Spark Streaming -> Redis -> FastAPI realtime API
```

本节只覆盖后端闭环启动与验证，不包含 Vue/ECharts 前端联调。

### 1. middleware 启动 Redis

```bash
redis-server
```

验证：

```bash
redis-cli -h middleware -p 6379 ping
```

预期返回：

```text
PONG
```

### 2. middleware 启动 ZooKeeper

当前 Kafka 版本为 `kafka_2.11-2.1.0`：

```bash
/usr/local/kafka_2.11-2.1.0/bin/zookeeper-server-start.sh -daemon /usr/local/kafka_2.11-2.1.0/config/zookeeper.properties
```

### 3. middleware 启动 Kafka

```bash
/usr/local/kafka_2.11-2.1.0/bin/kafka-server-start.sh -daemon /usr/local/kafka_2.11-2.1.0/config/server.properties
```

验证端口：

```bash
ss -lntp | grep 9092
```

### 4. master 创建 agent-events topic

注意：当前 Kafka 2.1.0 的 `kafka-topics.sh` 不支持使用 `--bootstrap-server` 创建和查看 topic，应使用 `--zookeeper middleware:2181`。

查看 topic：

```bash
/usr/local/kafka_2.11-2.1.0/bin/kafka-topics.sh --zookeeper middleware:2181 --list
```

创建 topic：

```bash
/usr/local/kafka_2.11-2.1.0/bin/kafka-topics.sh \
  --create \
  --zookeeper middleware:2181 \
  --replication-factor 1 \
  --partitions 1 \
  --topic agent-events
```

### 5. master 启动 Spark Streaming

确认已打包：

```text
spark-streaming/target/agentscope-spark-streaming-0.1.0.jar
```

启动作业：

```bash
/usr/local/spark/bin/spark-submit \
  --class com.agentscope.streaming.AgentEventStreamingJob \
  --master spark://master:7077 \
  --deploy-mode client \
  --driver-memory 512m \
  --executor-memory 512m \
  spark-streaming/target/agentscope-spark-streaming-0.1.0.jar \
  --kafka-bootstrap middleware:9092 \
  --topic agent-events \
  --redis-host middleware \
  --redis-port 6379
```

也可以使用脚本：

```bash
scripts/start_streaming_job.sh
```

### 6. master 启动 simulator

实时模式写入 Kafka：

```bash
cd simulator
python3 main.py \
  --mode realtime \
  --kafka-bootstrap middleware:9092 \
  --kafka-topic agent-events \
  --rate 10
```

Kafka consumer 验证：

```bash
/usr/local/kafka_2.11-2.1.0/bin/kafka-console-consumer.sh \
  --bootstrap-server middleware:9092 \
  --topic agent-events \
  --from-beginning \
  --max-messages 5
```

### 7. master 验证 Redis

```bash
redis-cli -h middleware -p 6379 get agentscope:realtime:overview
redis-cli -h middleware -p 6379 get agentscope:realtime:agents
redis-cli -h middleware -p 6379 get agentscope:realtime:alerts
```

应能看到实时 overview、Agent 状态和 streaming 告警数据。

### 8. master 验证 FastAPI

健康检查：

```bash
curl http://59.110.123.179:8000/health
```

实时接口：

```bash
curl http://59.110.123.179:8000/api/v1/realtime/overview
curl http://59.110.123.179:8000/api/v1/realtime/agents
curl http://59.110.123.179:8000/api/v1/realtime/alerts
```

预期结果：

```text
FastAPI 返回 Redis 中的真实实时指标、Agent 状态和 streaming 告警。
```

### visualization

```bash
cd /data2/panhaohao/phh-codes/research/agentscope/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

cd /data2/panhaohao/phh-codes/research/agentscope/frontend
npm run build
```

## 离线任务顺序

```text
离线模拟器 -> DataX Import -> Clean Job -> Daily/Ranking/Error/Relation/Alert Jobs -> AI 报告
```

## 停止顺序

```text
Agent 模拟器 -> Spark Streaming -> 前后端 -> Kafka -> ZooKeeper
-> Redis/MySQL -> Spark -> YARN -> HDFS
```

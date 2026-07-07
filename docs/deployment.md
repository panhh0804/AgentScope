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
  --master yarn \
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
curl http://your_server_ip:8000/health
```

实时接口：

```bash
curl http://your_server_ip:8000/api/v1/realtime/overview
curl http://your_server_ip:8000/api/v1/realtime/agents
curl http://your_server_ip:8000/api/v1/realtime/alerts
```

预期结果：

```text
FastAPI 返回 Redis 中的真实实时指标、Agent 状态和 streaming 告警。
```

## 前后端联调启动流程

本项目后端 API 前缀为 `/api/v1`，正式部署时由 Nginx 统一暴露前端静态页面，并把 `/api/` 转发到本机 FastAPI 后端。

### 1. 启动后端

```bash
cd /root/projects/agentscope/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

验证后端健康检查：

```bash
curl http://127.0.0.1:8000/health
```

预期返回：

```json
{"status":"ok"}
```

### 2. 构建前端

前端默认通过相对路径访问后端：

```env
VITE_API_BASE_URL=/api/v1
VITE_API_TIMEOUT=60000
```

构建命令：

```bash
cd /root/projects/agentscope/frontend
npm install
npm run build
```

构建产物目录：

```text
/root/projects/agentscope/frontend/dist
```

### 3. 配置 Nginx

使用 `deploy/nginx.conf`，关键配置如下：

```nginx
root /root/projects/agentscope/frontend/dist;

location /api/ {
    proxy_pass http://127.0.0.1:8000/api/;
}

location /health {
    proxy_pass http://127.0.0.1:8000/health;
}
```

加载配置后重启或 reload Nginx：

```bash
nginx -t
nginx -s reload
```

### 4. 访问页面

浏览器访问：

```text
http://your_server_ip/
```

前端请求会通过 Nginx 转发到后端，例如：

```text
/api/v1/realtime/overview
/api/v1/realtime/agents
/api/v1/realtime/alerts
/api/v1/reports/generate
```

### 5. curl 验证接口

通过 Nginx 验证健康检查：

```bash
curl http://your_server_ip/health
```

通过 Nginx 验证实时接口：

```bash
curl http://your_server_ip/api/v1/realtime/overview
curl http://your_server_ip/api/v1/realtime/agents
curl http://your_server_ip/api/v1/realtime/alerts
```

通过 Nginx 验证报告接口：

```bash
curl -X POST http://your_server_ip/api/v1/reports/generate \
  -H "Content-Type: application/json" \
  -d '{"report_date":"2026-06-23","report_type":"daily"}'
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

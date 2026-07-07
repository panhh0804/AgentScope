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
- Node.js 22.x

说明：当前前端使用的 Vite 版本要求 Node.js 20.19+ 或 22.12+，建议部署机使用 Node.js 22。

## 启动顺序

### master

```bash
start-dfs.sh
start-yarn.sh
```

说明：Spark 作业默认提交到 YARN，不再默认启动 Spark Standalone Master/Worker。若需要临时回退 Standalone，再显式启动 Standalone 集群并设置 `SPARK_MASTER=spark://master:7077`。

### middleware

```text
MySQL -> Redis -> ZooKeeper -> Kafka
```

### visualization

```text
FastAPI 后端 -> Nginx -> Vue 前端静态页面
```

## 实时链路启动顺序

实时链路完整闭环：

```text
Agent 模拟器 -> Kafka -> Spark Streaming on YARN -> Redis -> FastAPI realtime API -> Vue/ECharts 实时大屏
```

页面上方实时指标、实时日志、Agent 排行、告警、YARN 资源调度等数据依赖这条链路。
只启动 Spark Streaming，只能说明 YARN 上有计算程序；如果没有 simulator 持续向 Kafka 写入事件，前端实时指标会逐渐变成 0。

推荐在 Kafka、Redis、YARN 已启动后，使用一键脚本同时拉起 simulator 和 Spark Streaming：

```bash
cd /root/projects/agentscope
bash scripts/start_realtime_yarn_pipeline.sh
```

脚本会自动：

```text
1. 设置 Spark on YARN 默认环境变量
2. 避免重复启动 simulator/main.py
3. 避免重复提交 AgentScopeStreaming 到 YARN
4. 将日志写入 logs/realtime_producer.log 和 logs/streaming_yarn.log
```

验证命令：

```bash
ps -ef | grep simulator/main.py
yarn application -list
redis-cli -h middleware -p 6379 get agentscope:realtime:overview
```

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

如果 topic 已存在，可以忽略重复创建提示。

### 5. master 启动 simulator 实时生产端（手动备用）

实时模式会持续向 Kafka 写入 Agent 事件：

```bash
cd /root/projects/agentscope
mkdir -p logs

nohup python3 simulator/main.py \
  --mode realtime \
  --kafka-bootstrap middleware:9092 \
  --kafka-topic agent-events \
  --rate 15 \
  > logs/realtime_producer.log 2>&1 &
```

验证生产端进程：

```bash
ps -ef | grep simulator/main.py
tail -n 50 logs/realtime_producer.log
```

Kafka consumer 验证：

```bash
/usr/local/kafka_2.11-2.1.0/bin/kafka-console-consumer.sh \
  --bootstrap-server middleware:9092 \
  --topic agent-events \
  --from-beginning \
  --max-messages 5
```

### 6. master 启动 Spark Streaming 到 YARN（手动备用）

确认已打包：

```text
spark-streaming/target/agentscope-spark-streaming-0.1.0.jar
```

推荐使用项目脚本后台启动：

```bash
cd /root/projects/agentscope

export SPARK_MASTER=yarn
export SPARK_DEPLOY_MODE=client
export HADOOP_CONF_DIR=/usr/local/hadoop-2.7.6/etc/hadoop
export YARN_CONF_DIR=/usr/local/hadoop-2.7.6/etc/hadoop

nohup bash scripts/start_streaming_job.sh > logs/streaming_yarn.log 2>&1 &
```

也可以直接使用 `spark-submit`：

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

如需临时回退 Spark Standalone，可显式设置：

```bash
export SPARK_MASTER=spark://master:7077
```

### 7. master 验证 YARN

检查 NodeManager：

```bash
yarn node -list
```

预期能看到 worker 节点为 `RUNNING`。

检查 Spark Streaming application：

```bash
yarn application -list
```

预期能看到：

```text
AgentScopeStreaming  SPARK  RUNNING
```

这说明 Spark Streaming 已经真正运行在 YARN 上，而不是 Spark Standalone。

### 8. master 验证 Redis

```bash
redis-cli -h middleware -p 6379 keys 'agentscope:realtime:*'
redis-cli -h middleware -p 6379 get agentscope:realtime:overview
redis-cli -h middleware -p 6379 get agentscope:realtime:agents
redis-cli -h middleware -p 6379 get agentscope:realtime:alerts
```

应能看到实时 overview、Agent 状态和 streaming 告警数据。
如果 `overview` 返回 JSON，说明 Spark Streaming 已经把实时计算结果写入 Redis。

### 9. visualization 验证 FastAPI

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

实时接口：

```bash
curl http://127.0.0.1:8000/api/v1/realtime/overview
curl http://127.0.0.1:8000/api/v1/realtime/agents
curl http://127.0.0.1:8000/api/v1/realtime/alerts
```

预期结果：

```text
FastAPI 返回 Redis 中的真实实时指标、Agent 状态和 streaming 告警。
```

### 10. 前端大屏验证

浏览器访问：

```text
http://your_server_ip/
```

实时大屏应能看到：

```text
运行任务
活跃 Agent
事件吞吐 / 分钟
实时成功率
平均时延
5m Token 消耗
当前告警
YARN 资源调度：1 apps / xxxxMB used
```

如果 YARN 显示 `1 apps`，并且上方指标也在变化，说明完整实时链路已经成功。

## 前后端联调启动流程

本项目后端 API 前缀为 `/api/v1`，正式部署时由 Nginx 统一暴露前端静态页面，并把 `/api/` 转发到本机 FastAPI 后端。

### 1. 同步代码到 visualization

如果需要从 master 或其他节点拉取代码到 visualization：

```bash
rsync -av --delete \
  --exclude '.git' \
  --exclude 'frontend/node_modules' \
  --exclude 'backend/.venv' \
  root@123.56.215.82:/root/projects/agentscope/ \
  /root/agentscope/
```

如果出现 SSH 主机指纹变化：

```bash
ssh-keygen -f "/root/.ssh/known_hosts" -R "123.56.215.82"
ssh root@123.56.215.82
```

确认能登录后再重新执行 `rsync`。

### 2. 启动后端

```bash
cd /root/agentscope/backend

pkill -f "uvicorn app.main:app"
sleep 2

nohup .venv/bin/python -m uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  > uvicorn.log 2>&1 &
```

验证后端健康检查：

```bash
tail -n 50 uvicorn.log
ss -lntp | grep 8000
curl http://127.0.0.1:8000/health
```

预期返回：

```json
{"status":"ok"}
```

### 3. 构建前端

前端默认通过相对路径访问后端：

```env
VITE_API_BASE_URL=/api/v1
VITE_API_TIMEOUT=60000
```

Node.js 版本建议使用 22：

```bash
node -v
npm -v
```

构建命令：

```bash
cd /root/agentscope/frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

构建产物目录：

```text
/root/agentscope/frontend/dist
```

出现类似下面结果说明构建成功：

```text
vite build
✓ built in ...
dist/index.html
dist/assets/...
```

如果出现 `Some chunks are larger than 500 kB`，属于 Vite 打包体积警告，不影响部署运行。

### 4. 配置 Nginx

使用 `deploy/nginx.conf`，关键配置如下：

```nginx
root /root/agentscope/frontend/dist;

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
systemctl reload nginx
```

### 5. 访问页面

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

### 6. curl 验证接口

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

常用离线任务命令：

```bash
cd /root/projects/agentscope

bash scripts/run_clean_job.sh 2026-06-30
bash scripts/run_batch_jobs.sh 2026-06-30
```

查看 YARN 历史应用：

```bash
yarn application -list -appStates ALL
```

## 停止顺序

推荐停止顺序：

```text
Agent 模拟器 -> Spark Streaming -> 前后端 -> Kafka -> ZooKeeper
-> Redis/MySQL -> YARN -> HDFS
```

停止 simulator：

```bash
pkill -f "simulator/main.py"
```

停止 Spark Streaming：

```bash
yarn application -list
yarn application -kill application_xxxxxxxxxxxxx_xxxx
```

其中 `application_xxxxxxxxxxxxx_xxxx` 替换为实际 Application-Id。

推荐使用一键停止脚本同时停止 simulator 和 YARN 上运行中的 `AgentScopeStreaming`：

```bash
cd /root/projects/agentscope
bash scripts/stop_realtime_yarn_pipeline.sh
```

如果没有运行中的 simulator 或 Spark Streaming，脚本只会提示不存在，不会报错中断。

如果项目里有停止脚本，也可以执行：

```bash
bash scripts/stop_streaming_job.sh
```

停止后验证：

```bash
ps -ef | grep simulator/main.py
yarn application -list
```

## 常见问题

### 页面显示 `0 apps / 0MB used`

说明当前 YARN 上没有正在运行的 Spark application。

检查：

```bash
yarn application -list
```

如果也是 0，说明 Spark Streaming 没有启动或已经退出。

### YARN 显示 1 apps，但页面上方指标是 0

这通常说明 Spark Streaming 在跑，但没有实时事件进入 Kafka，或者 Redis 实时窗口已经过期。

检查 simulator：

```bash
ps -ef | grep simulator/main.py
tail -n 50 logs/realtime_producer.log
```

检查 Redis：

```bash
redis-cli -h middleware -p 6379 get agentscope:realtime:overview
```

### 中间 Agent 排行有数据，但顶部实时指标是 0

可能是因为不同区域的数据来源不同：

```text
顶部实时 KPI：主要来自 Redis 的 agentscope:realtime:overview
Agent 排行/告警/图表：可能来自 Redis 其他 key，或 demo/mock fallback 数据
```

所以不能只看一个区域，要结合 YARN、Redis 和页面整体判断。

### 前端构建报 Node 版本问题

Vite 新版本需要 Node 20.19+ 或 22.12+。建议使用 Node 22：

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs

node -v
npm -v
```

然后重新构建：

```bash
cd /root/agentscope/frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

## 验收说明口径

本项目实时链路采用 `Kafka + Spark Streaming + Redis + FastAPI + Vue`。实时数据由 simulator 持续写入 Kafka，Spark Streaming 作业以 YARN client 模式提交到 Hadoop/YARN 集群运行，消费 Kafka 中的 Agent 事件并计算吞吐、成功率、延迟、Token、告警等指标，再写入 Redis。后端 FastAPI 从 Redis 读取实时指标，前端大屏进行可视化展示。

验收时可通过以下证据证明链路正常：

```text
1. ps 中存在 simulator/main.py 实时生产进程
2. yarn application -list 中存在 AgentScopeStreaming，类型为 SPARK，状态为 RUNNING
3. Redis 中存在 agentscope:realtime:* 实时 key
4. 前端实时大屏中事件吞吐、Token、告警、平均时延等数据持续变化
5. 核心中间件监控中 YARN 显示 1 apps / xxxxMB used
```

## 一键启动命令汇总

在 master 节点执行：

```bash
cd /root/projects/agentscope
bash scripts/start_realtime_yarn_pipeline.sh
```

验证：

```bash
ps -ef | grep simulator/main.py
yarn application -list
redis-cli -h middleware -p 6379 get agentscope:realtime:overview
```

停止：

```bash
cd /root/projects/agentscope
bash scripts/stop_realtime_yarn_pipeline.sh
```

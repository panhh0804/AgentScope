# 部署说明

## 环境版本

- Ubuntu 20.04
- Java 8
- Hadoop 2.7.6
- Spark 2.4.0
- Scala 2.11
- Sqoop
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

### visualization

```bash
cd /data2/panhaohao/phh-codes/research/agentscope/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

cd /data2/panhaohao/phh-codes/research/agentscope/frontend
npm run build
```

## 离线任务顺序

```text
离线模拟器 -> Sqoop Import -> Clean Job -> Daily/Ranking/Error/Relation/Alert Jobs -> AI 报告
```

## 停止顺序

```text
Agent 模拟器 -> Spark Streaming -> 前后端 -> Kafka -> ZooKeeper
-> Redis/MySQL -> Spark -> YARN -> HDFS
```


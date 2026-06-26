# AgentScope 多智能体运行监测与效能分析平台

AgentScope 是一个针对多智能体（Multi-Agent）系统设计的大数据观测与效能分析平台。本项目提供了一个完整的“实时 + 离线”双链路大数据处理架构，旨在解决多 Agent 系统在运行过程中面临的不可见、难追踪、难评估等问题。

通过 AgentScope，您可以对 Agent 的运行数据进行实时采集、流式计算、离线导入、数据清洗、历史分析、异常检测和可视化展示，并利用大语言模型（LLM）自动生成系统运行分析报告。

## 🎯 核心特性

*   **双链路数据流处理**:
    *   **实时链路**: 基于 `Kafka + Spark Streaming + Redis`，实现毫秒级的实时监控和告警。
    *   **离线链路**: 基于 `DataX + HDFS + Spark Batch + MySQL`，实现海量历史数据的深度清洗与T+1复杂指标分析。
*   **多维效能指标分析**: 提供耗时分析、Token 消耗统计、错误率计算等关键效能指标。
*   **Agent 关系图谱**: 通过分析调用链路，还原 Agent 之间的协作关系与调用拓扑。
*   **实时异常与容错**: 具备强大的流式处理容错能力（能优雅跳过各种畸形数据），并支持实时规则告警（如 Token 超限、高延迟等）。
*   **AI 智能体报告**: 接入大语言模型（LLM），基于离线分析结果自动生成自然语言的系统效能分析报告。
*   **一键式自动化调度**: 离线链路提供一键总控脚本并支持 Crontab 定时调度，实现全自动数据流转。

## 🏗️ 系统架构

本项目采用经典的 Lambda 大数据架构：

```mermaid
graph LR
    subgraph 数据源
        Sim[Agent 模拟器]
    end
    
    subgraph 实时链路
        Sim -->|JSON| Kafka[Kafka (agent-events)]
        Kafka --> SS[Spark Streaming]
        SS -->|实时指标/告警| Redis[(Redis)]
    end
    
    subgraph 离线链路
        Sim -->|JDBC| MySQL_Src[(MySQL Source)]
        MySQL_Src -->|DataX| HDFS_Raw[HDFS Raw]
        HDFS_Raw -->|Spark| HDFS_Clean[HDFS Clean]
        HDFS_Clean -->|Spark Batch| HDFS_Metric[HDFS Metric]
        HDFS_Clean -->|Spark Batch| MySQL_Ana[(MySQL Analytics)]
    end
    
    subgraph 服务与展示
        Redis --> FastAPI[FastAPI]
        MySQL_Ana --> FastAPI
        FastAPI -->|REST API| Vue[Vue 3 + ECharts 大屏]
        FastAPI -->|生成报告| LLM[LLM 接口]
    end
```

## 📁 目录结构

```text
agentscope/
├── backend/              # FastAPI 后端服务 (提供 API 接口与 AI 报告服务)
├── frontend/             # Vue 3 + ECharts 大屏可视化前端
├── simulator/            # Agent 事件模拟器 (支持实时 Kafka 发送和离线 MySQL 写入)
├── spark-streaming/      # Spark Streaming 实时计算作业 (Scala 2.11 + Spark 2.4)
├── spark-batch/          # Spark Batch 离线清洗与分析作业 (Scala 2.11 + Spark 2.4)
├── sql/                  # MySQL Source / Analytics 库表初始化脚本
├── scripts/              # 自动化运维脚本 (DataX导入, Spark提交, 健康检查, 压测等)
└── docs/                 # 项目设计文档、测试报告与部署说明
```

## 🚀 快速开始

本项目依赖真实的 Hadoop/Spark 集群环境运行。建议的部署拓扑为 `master` (Hadoop/Spark), `worker1/2`, `middleware` (MySQL, Redis, Kafka, ZK), `visualization` (Backend, Frontend)。

### 1. 环境准备与初始化

1. 确保集群各组件正常运行 (HDFS, YARN, Spark Standalone, Kafka, ZooKeeper, Redis, MySQL)。
2. 在 `middleware` 节点初始化数据库表：
   ```bash
   mysql -u root -p < sql/source_schema.sql
   mysql -u root -p < sql/analytics_schema.sql
   ```
3. 创建 Kafka Topic：
   ```bash
   bash scripts/create_kafka_topics.sh
   ```

### 2. 启动服务

**启动后端服务 (FastAPI):**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

**启动实时链路 (Spark Streaming):**
```bash
bash scripts/start_streaming_job.sh
```

**启动前端开发服务器:**
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

### 3. 运行数据模拟器

**实时模式 (向 Kafka 持续发送数据):**
```bash
cd simulator
python main.py --mode realtime --kafka-bootstrap middleware:9092 --rate 10
```
*此时可访问前端大屏 (默认 http://localhost:5173) 查看实时变动的数据。*

**离线模式 (向 MySQL Source 写入历史数据):**
```bash
cd simulator
python main.py --mode offline --count 10000 --start-date 2026-06-01 --end-date 2026-06-25
```

### 4. 运行离线数据 Pipeline

为处理刚才模拟的离线数据，运行离线总控脚本。该脚本会自动串联 DataX 数据导入、Spark 数据清洗和 5 个 Spark 分析作业：

```bash
bash scripts/run_daily_offline_pipeline.sh 2026-06-25
```
*此脚本已在 master 节点配置为 crontab 每日凌晨 2:00 自动执行。*

## 🛠️ 运维与测试工具

项目提供了一系列脚本用于日常诊断和测试，位于 `scripts/` 目录下：

- `health_check.sh`: **集群健康一键体检**。检查 HDFS, YARN, Spark, Kafka, ZK, Redis, MySQL 的存活状态。
- `test_fault_tolerance.sh`: **异常容错演练**。向 Kafka 注入畸形、缺失字段、非法格式的脏数据以及 Token 超限数据，验证 Spark Streaming 的鲁棒性和告警机制。
- `benchmark.sh`: **自动化压测**。以不同速率向集群打入数据，评估系统吞吐与延迟。

## 📄 文档与报告

更多详细设计和说明，请参阅：

- [AgentScope 多智能体运行监测与效能分析平台设计说明书](docs/) (根目录外/桌面)
- [性能测试报告模板](docs/performance_test_report.md)

---
*构建由: Hadoop生态, Spark, Kafka, FastAPI, Vue3, ECharts.*

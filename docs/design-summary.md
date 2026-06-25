# 设计摘要

## 项目定位

AgentScope 不是通用 Agent 开发框架，而是多智能体系统的运行观测与效能分析平台。项目重点展示完整的大数据处理链路：Kafka、Spark Streaming、Redis、MySQL、DataX、HDFS、Spark Batch、FastAPI、Vue/ECharts 和 AI 报告。

## 典型业务场景

系统模拟“智能研究助手”多 Agent 工作流：

```text
用户任务 -> Planner -> Search -> Analysis -> Writer -> Reviewer -> 最终结果
```

如果 Reviewer 不通过，则重新调用 Writer，产生重试事件。重试次数持续增加时，系统识别为频繁重试或疑似循环调用。

## 实时链路

```text
Agent 实时事件 -> Kafka -> Spark Streaming -> Redis -> FastAPI -> Vue/ECharts
```

实时指标包括当前运行任务数、活跃 Agent、吞吐量、成功率、错误率、平均时延、Token 消耗、最近告警等。

## 离线链路

```text
Agent 历史数据 -> MySQL Source -> DataX -> HDFS Raw
-> Spark Batch 清洗与分析 -> HDFS Clean/Metric + MySQL Analytics
-> FastAPI / AI 报告 -> 历史分析页面
```

离线指标包括每日任务总量、每日成功率、Agent 排行、平均/P95 时延、Token 成本、错误分布、工具成功率和 Agent 协作关系。

## 五节点部署

| 节点 | 组件 |
|---|---|
| master | NameNode、ResourceManager、Spark Master、DataX、任务提交客户端 |
| worker1 | DataNode、NodeManager、Spark Worker |
| worker2 | DataNode、NodeManager、Spark Worker |
| middleware | ZooKeeper、Kafka、Redis、MySQL |
| visualization | FastAPI、Vue、ECharts、Nginx、AI 报告服务 |

## 最小可行版本

- 至少 5 类 Agent；
- 至少 8 类事件；
- Kafka 持续接收事件；
- Spark Streaming 计算实时指标并写 Redis；
- MySQL Source 生成历史数据；
- DataX 导入 HDFS Raw；
- Spark Batch 生成 Clean 和历史指标；
- MySQL Analytics 可查询历史结果；
- 页面包含实时总览、历史分析、告警中心、AI 报告；
- 至少识别 4 类异常；
- 能生成 Markdown 格式 AI 分析报告。

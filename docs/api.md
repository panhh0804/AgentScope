# API 设计

统一前缀：

```text
/api/v1
```

统一响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "request_id": "req_20260623_0001"
}
```

## 实时接口

| 方法 | 路径 | 数据来源 |
|---|---|---|
| GET | `/realtime/overview` | Redis |
| GET | `/realtime/trend?minutes=60` | Redis |
| GET | `/realtime/agents` | Redis |
| GET | `/realtime/alerts` | Redis |

实时接口已在真实集群完成后端闭环验证，数据链路为：

```text
Agent 模拟器 -> Kafka -> Spark Streaming -> Redis -> FastAPI realtime API
```

本轮验证不包含 Vue/ECharts 前端联调。

### Redis 实时 key

实时 API 读取以下 Redis key：

```text
agentscope:realtime:overview
agentscope:realtime:agents
agentscope:realtime:alerts
```

`/realtime/trend` 预留读取：

```text
agentscope:realtime:trend
```

当前 Spark Streaming 已验证写入 overview、agents、alerts 三类实时 key。

### GET `/api/v1/realtime/overview`

数据来源：

```text
Redis key: agentscope:realtime:overview
```

字段说明：

| 字段 | 说明 |
|---|---|
| `success_count` | 当前实时窗口内成功事件或成功任务数量 |
| `failed_count` | 当前实时窗口内失败事件或失败任务数量 |
| `error_rate` | 当前实时窗口错误率 |
| `avg_latency_ms` | 当前实时窗口平均延迟，单位毫秒 |
| `events_per_minute` | 每分钟事件吞吐量 |
| `token_total_5m` | 最近窗口 Token 总量 |
| `estimated_cost_5m` | 最近窗口预估模型调用成本 |
| `running_tasks` | 当前运行中的任务数量 |
| `active_agents` | 当前活跃 Agent 数量 |
| `retry_tasks` | 当前重试任务数量 |
| `open_alerts` | 当前未处理告警数量 |

### GET `/api/v1/realtime/agents`

数据来源：

```text
Redis key: agentscope:realtime:agents
```

返回每个 Agent 的实时状态。已验证返回的 Agent 包括：

```text
analysis_agent
search_agent
reviewer_agent
writer_agent
planner_agent
```

常见字段：

| 字段 | 说明 |
|---|---|
| `agent_id` | Agent 实例 ID，例如 `planner_agent` |
| `agent_role` | Agent 角色，例如 `planner`、`search`、`writer` |
| `status` | 实时状态 |
| `success_rate` | 实时成功率 |
| `avg_latency_ms` | 平均延迟，单位毫秒 |
| `token_total` | 当前窗口 Token 总量 |
| `retry_count` | 当前窗口重试次数 |

### GET `/api/v1/realtime/alerts`

数据来源：

```text
Redis key: agentscope:realtime:alerts
```

已验证返回的实时告警类型包括：

```text
high_latency
frequent_retry
```

常见字段：

| 字段 | 说明 |
|---|---|
| `alert_type` | 告警类型 |
| `level` | 告警等级 |
| `agent_id` | 触发告警的 Agent |
| `current_value` | 当前值 |
| `threshold` / `threshold_value` | 阈值 |
| `source` | 告警来源，实时链路为 `streaming` |

注意：当前实时告警中可能存在重复告警记录，后续可增加 `alert_id` 去重逻辑。

## 历史分析接口

| 方法 | 路径 | 数据来源 |
|---|---|---|
| GET | `/metrics/daily?start_date=2026-06-01&end_date=2026-06-30` | MySQL Analytics |
| GET | `/metrics/hourly?date=2026-06-23` | MySQL Analytics |
| GET | `/rankings/agents?date=2026-06-23` | MySQL Analytics |
| GET | `/errors/distribution?date=2026-06-23` | MySQL Analytics |
| GET | `/graph/agent-relations?date=2026-06-23` | MySQL Analytics |
| GET | `/alerts/history?date=2026-06-23` | MySQL Analytics |

## 报告接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/reports/generate` | 基于结构化指标生成 Markdown 报告 |
| GET | `/reports` | 报告列表 |
| GET | `/reports/{report_id}` | 报告详情 |

## 数据管理端接口

统一前缀：

```text
/api/v1/admin
```

数据管理端面向平台管理员，展示离线数据链路、数据资产、任务运行、质量治理和操作审计状态。当前实现优先保证页面和接口稳定可验收：如环境未提供完整 Admin 表，接口返回稳定 mock 数据或基于现有状态的聚合数据。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/data-overview` | 数据总览、分区、有效率、任务成功率、漏斗数据 |
| GET | `/data-volume-trend` | 最近 7 天 Raw / Clean 数据量趋势 |
| GET | `/pipeline-status` | Source -> Raw -> Clean -> Metric 链路状态 |
| GET | `/datasets` | 数据资产目录 |
| GET | `/data-lineage` | 简化数据血缘 |
| GET | `/events` | Agent 原始事件列表，支持 trace_id、run_id、agent_id、event_type、status、时间过滤 |
| GET | `/jobs` | 固定白名单任务列表 |
| GET | `/job-runs` | 任务运行记录 |
| POST | `/jobs/{job_code}/execute` | 按白名单 job_code 和 biz_date 执行任务 |
| POST | `/job-runs/{run_id}/retry` | 重试失败任务运行 |
| GET | `/job-runs/{run_id}/logs` | 查看任务日志摘要 |
| GET | `/quality/overview` | 数据质量概览 |
| GET | `/quality/issues` | 数据质量问题明细 |
| GET | `/audit-logs` | 操作审计日志 |

任务执行接口只接受固定 `job_code` 和 `biz_date`，不支持任意 SQL、shell 命令或脚本路径。


# 数据字典

## 统一 Agent 事件

| 字段 | 类型 | 说明 |
|---|---|---|
| event_id | string | 全局唯一事件 ID |
| trace_id | string | 一次用户任务的链路 ID |
| run_id | string | 单次 Agent 运行 ID |
| parent_run_id | string/null | 上游运行 ID |
| agent_id | string | Agent 实例或角色 ID |
| parent_agent_id | string/null | 上游 Agent |
| agent_role | string | planner/search/analysis/writer/reviewer |
| event_type | string | agent_start/agent_complete/agent_failed/llm_request/llm_response/tool_call/tool_result/retry/alert |
| status | string | running/success/failed/retry |
| timestamp | datetime | 事件时间 |
| latency_ms | int | 执行耗时 |
| prompt_tokens | int | Prompt Token |
| completion_tokens | int | Completion Token |
| total_tokens | int | Token 总量 |
| cost_usd | decimal | 预估成本 |
| model_name | string | 模型名称 |
| tool_name | string/null | 工具名称 |
| error_type | string/null | 错误类型 |
| retry_count | int | 当前重试次数 |
| metadata_json | json | 扩展字段 |

## 关键异常规则

| 异常 | 判断规则 |
|---|---|
| 高错误率 | 最近 1 分钟错误率 > 20%，且事件数量 >= 5 |
| 高时延 | 单次 Agent 执行时延 > 10000ms，或最近 5 分钟平均时延 > 5000ms |
| 频繁重试 | 同一 run_id 的 retry_count >= 3 |
| Token 超额 | 单次任务 Token 总量 > 20000 |
| 疑似卡死 | agent_start 后 60 秒内未出现 complete/failed |


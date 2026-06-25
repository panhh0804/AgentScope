# AgentScope 模拟器说明

`simulator/` 用于生成符合 AgentScope 事件模型的模拟数据，同时服务于实时链路和离线链路。

实时链路：

```text
Agent 模拟器 -> Kafka -> Spark Streaming -> Redis -> FastAPI -> Vue/ECharts
```

离线链路：

```text
Agent 模拟器 -> MySQL Source -> Sqoop -> HDFS Raw -> Spark Batch -> MySQL Analytics
```

模拟器保持现有顶层字段不变，便于后续 Spark、SQL、后端继续兼容：

```text
event_id, trace_id, run_id, parent_run_id, agent_id, parent_agent_id,
agent_role, event_type, status, timestamp, latency_ms, prompt_tokens,
completion_tokens, total_tokens, cost_usd, model_name, tool_name,
error_type, retry_count, metadata_json
```

## 事件链路

每条用户任务会模拟一条多 Agent 工作流：

```text
planner -> search -> analysis -> writer -> reviewer
```

普通 Agent 会生成：

```text
agent_start -> llm_request -> llm_response -> agent_complete
```

Search Agent 额外生成工具调用事件：

```text
tool_call -> tool_result
```

`retry` 和 `loop` 场景会扩展出重复调用链路：

```text
writer -> reviewer -> writer -> reviewer
```

同一个 `trace_id` 内的事件时间戳严格递增。开启 `--seed` 后，ID 会稳定生成，例如：

```text
trace_00000001
run_00000001
evt_00000001
```

## 配置文件

默认配置文件位于：

```text
config/default.yaml
```

使用配置文件运行：

```bash
python main.py --mode offline --config config/default.yaml --count 100 --output ../tmp/events.jsonl
```

命令行参数优先级高于 YAML 配置。例如下面命令会读取配置文件，但用 `--rate 20` 覆盖配置里的默认速率：

```bash
python main.py --mode realtime --config config/default.yaml --rate 20
```

## 离线 JSONL 输出

生成 100 条混合场景任务链路：

```bash
python main.py --mode offline \
  --count 100 \
  --start-date 2026-06-01 \
  --end-date 2026-06-23 \
  --seed 42 \
  --output ../tmp/mixed_seed_42.jsonl
```

使用相同参数和相同 `--seed` 再生成一次，输出应保持一致：

```bash
python main.py --mode offline \
  --count 100 \
  --start-date 2026-06-01 \
  --end-date 2026-06-23 \
  --seed 42 \
  --output ../tmp/mixed_seed_42_again.jsonl
```

注意：`--count` 表示 workflow / trace 数量，不是事件条数。每条任务链路会完整生成多个事件，所以最终 JSONL 行数通常大于 `--count`。

## 离线 MySQL 输出

如果不传 `--output`，离线模式会写入 MySQL 的 `agent_events_source` 表。这里的 `--count` 同样表示任务链路数量：

```bash
python main.py --mode offline \
  --count 10000 \
  --start-date 2026-06-01 \
  --end-date 2026-06-23 \
  --mysql-host middleware \
  --mysql-user agentscope \
  --mysql-password agentscope_pass \
  --mysql-db agentscope_source
```

写入 MySQL 时，`timestamp` 会转换成 MySQL DATETIME 兼容格式，`metadata_json` 会转换成 JSON 字符串。

## 实时 Kafka 输出

实时模式会持续生成 workflow，并按事件发送到 Kafka：

```bash
python main.py --mode realtime \
  --kafka-bootstrap middleware:9092 \
  --kafka-topic agent-events \
  --rate 10
```

`--rate` 表示每秒发送的事件数。

本地没有 Kafka 时，可以使用 `--stdout` 直接打印 JSONL 事件：

```bash
python main.py --mode realtime --stdout --rate 5 --seed 42
```

## 场景选择

默认场景是 `mixed`，会按照 `config/default.yaml` 中的 `simulator.scenario_weights` 混合生成。

可选场景：

```text
mixed
success
agent_failed
tool_failed
high_latency
retry
token_overuse
loop
```

指定场景示例：

```bash
python main.py --mode offline --scenario high_latency --count 50 --seed 1 --output ../tmp/high_latency.jsonl
python main.py --mode offline --scenario token_overuse --count 50 --seed 1 --output ../tmp/token_overuse.jsonl
python main.py --mode offline --scenario retry --count 50 --seed 1 --output ../tmp/retry.jsonl
python main.py --mode offline --scenario tool_failed --count 50 --seed 1 --output ../tmp/tool_failed.jsonl
python main.py --mode offline --scenario agent_failed --count 50 --seed 1 --output ../tmp/agent_failed.jsonl
```

## 本地自检

本地自检不需要 Kafka 或 MySQL。

先生成测试数据，再运行：

```bash
cd simulator
python self_check.py --dir ../tmp
```

自检内容包括：

- 相同 seed 输出是否一致；
- mixed 数据是否覆盖 8 类核心事件；
- `event_id` 是否唯一；
- `total_tokens` 是否等于 `prompt_tokens + completion_tokens`；
- 同一 `trace_id` 内时间戳是否递增；
- 各异常场景是否生成对应特征事件。

## 常用验证命令

编译检查：

```bash
python -m compileall simulator
```

生成混合数据：

```bash
cd simulator
python main.py --mode offline \
  --count 100 \
  --start-date 2026-06-01 \
  --end-date 2026-06-23 \
  --seed 42 \
  --output ../tmp/mixed_seed_42.jsonl
```

生成异常场景数据：

```bash
python main.py --mode offline --scenario high_latency --count 50 --seed 1 --output ../tmp/high_latency.jsonl
python main.py --mode offline --scenario token_overuse --count 50 --seed 1 --output ../tmp/token_overuse.jsonl
python main.py --mode offline --scenario retry --count 50 --seed 1 --output ../tmp/retry.jsonl
python main.py --mode offline --scenario tool_failed --count 50 --seed 1 --output ../tmp/tool_failed.jsonl
python main.py --mode offline --scenario agent_failed --count 50 --seed 1 --output ../tmp/agent_failed.jsonl
```

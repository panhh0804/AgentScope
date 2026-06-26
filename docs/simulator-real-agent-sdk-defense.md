# AgentScope 数据产生端与真实 Agent 埋点 SDK 答辩说明

## 1. 本次完成内容概览

本次主要完成了 AgentScope 项目的两个数据产生端能力：

```text
1. simulator/：Agent 运行事件模拟器增强
2. real_agent_sdk/：真实 Agent 埋点 SDK
```

两部分都输出与平台统一事件模型兼容的数据，后续可以进入 Kafka、Spark Streaming、Redis、MySQL、Spark Batch、FastAPI 和前端页面。

统一事件字段保持一致：

```text
event_id
trace_id
run_id
parent_run_id
agent_id
parent_agent_id
agent_role
event_type
status
timestamp
latency_ms
prompt_tokens
completion_tokens
total_tokens
cost_usd
model_name
tool_name
error_type
retry_count
metadata_json
```

## 2. Agent 运行事件模拟器

### 2.1 模块位置

```text
simulator/
```

关键文件：

```text
simulator/main.py
simulator/workflow_generator.py
simulator/event_model.py
simulator/config_loader.py
simulator/id_generator.py
simulator/realtime_producer.py
simulator/offline_generator.py
simulator/self_check.py
simulator/config/default.yaml
simulator/README.md
```

### 2.2 解决的问题

原始模拟器只能生成部分事件，且 `--count` 曾经按事件条数截断，可能导致一条任务链路不完整。

现在已经改成：

```text
--count 表示 workflow / trace 数量
每条 workflow 会完整生成后再写出
不会在 agent_start、llm_request、tool_call 等中间事件处截断
```

### 2.3 模拟工作流

模拟器默认生成一个研究助手类多 Agent 链路：

```text
Planner Agent
-> Search Agent
-> Analysis Agent
-> Writer Agent
-> Reviewer Agent
```

普通 Agent 的事件序列：

```text
agent_start
-> llm_request
-> llm_response
-> agent_complete
```

Search Agent 额外包含工具调用：

```text
tool_call
-> tool_result
```

失败场景包含：

```text
agent_failed
```

重试场景包含：

```text
retry
-> agent_complete
-> writer 重新调用
-> reviewer 重新调用
```

### 2.4 支持的事件类型

模拟器可以稳定覆盖 8 类核心事件：

```text
agent_start
agent_complete
agent_failed
llm_request
llm_response
tool_call
tool_result
retry
```

### 2.5 支持的场景

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

其中：

```text
high_latency：生成 latency_ms > 10000 的事件
retry：生成 retry_count >= 3 的 retry 事件
token_overuse：生成 total_tokens > 20000 的事件
tool_failed：生成 status=failed 的 tool_result
agent_failed：生成 agent_failed
loop：生成 writer -> reviewer -> writer -> reviewer 的重复调用关系
```

### 2.6 可复现性

新增 `--seed` 参数。使用相同参数和相同 seed 时，输出稳定可复现。

seed 模式下 ID 形如：

```text
trace_00000001
run_00000001
evt_00000001
```

### 2.7 配置文件

支持读取 YAML 配置：

```text
simulator/config/default.yaml
```

配置内容包括：

```text
Kafka 地址
MySQL 地址
默认模型名
场景比例
时延范围
Token 范围
事件间隔
```

命令行参数优先级高于 YAML 配置。

### 2.8 本地验证命令

编译检查：

```bash
python -m compileall simulator
```

生成混合场景数据：

```bash
cd simulator
python main.py --mode offline \
  --count 100 \
  --start-date 2026-06-01 \
  --end-date 2026-06-23 \
  --seed 42 \
  --output ../tmp/mixed_seed_42.jsonl
```

生成异常场景：

```bash
python main.py --mode offline --scenario high_latency --count 50 --seed 1 --output ../tmp/high_latency.jsonl
python main.py --mode offline --scenario token_overuse --count 50 --seed 1 --output ../tmp/token_overuse.jsonl
python main.py --mode offline --scenario retry --count 50 --seed 1 --output ../tmp/retry.jsonl
python main.py --mode offline --scenario tool_failed --count 50 --seed 1 --output ../tmp/tool_failed.jsonl
python main.py --mode offline --scenario agent_failed --count 50 --seed 1 --output ../tmp/agent_failed.jsonl
```

自检：

```bash
python self_check.py --dir ../tmp
```

通过结果示例：

```text
ok deterministic seed output
ok mixed eight event types
ok event_id unique
ok total_tokens consistent
ok timestamps increasing per trace
ok complete runs
ok agent_failed
ok retry
ok high_latency
ok token_overuse
ok tool_failed
```

## 3. 真实 Agent 埋点 SDK

### 3.1 模块位置

```text
real_agent_sdk/
```

关键文件：

```text
real_agent_sdk/demo_agent_workflow.py
real_agent_sdk/agents.py
real_agent_sdk/event_model.py
real_agent_sdk/event_recorder.py
real_agent_sdk/siliconflow_client.py
real_agent_sdk/sinks.py
real_agent_sdk/tool_wrapper.py
real_agent_sdk/self_check.py
real_agent_sdk/README.md
real_agent_sdk/.env.example
```

### 3.2 实现目标

真实 Agent SDK 用于记录真实 Agent 调用过程，而不是模拟数据。

它已经支持：

```text
真实调用硅基流动 OpenAI-compatible Chat Completions API
模型：nex-agi/Nex-N2-Pro
API Key 从 SILICONFLOW_API_KEY 读取
输出字段与 simulator 完全兼容
支持 JSONL、Kafka、both 三种 sink
支持 API 异常时生成 agent_failed
支持 --force-retry 演示 retry
```

### 3.3 真实 Agent 工作流

真实 SDK 当前实现：

```text
Planner Agent
-> Search Agent
-> Writer Agent
-> Reviewer Agent
```

每个 Agent 都会真实调用模型：

```text
nex-agi/Nex-N2-Pro
```

Search Agent 还会调用一个本地检索工具包装器，生成：

```text
tool_call
tool_result
```

### 3.4 事件序列

普通 Agent：

```text
agent_start
-> llm_request
-> llm_response
-> agent_complete
```

Search Agent：

```text
agent_start
-> llm_request
-> llm_response
-> tool_call
-> tool_result
-> agent_complete
```

Reviewer 强制重试：

```text
agent_start
-> llm_request
-> llm_response
-> retry
-> agent_complete
-> Writer 重新调用
-> Reviewer 重新调用
```

API 异常：

```text
agent_start
-> llm_request
-> agent_failed
```

### 3.5 环境变量

项目根目录可以创建本地 `.env`：

```text
SILICONFLOW_API_KEY=你的硅基流动 API Key
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
```

`.env` 已经在 `.gitignore` 中，不会提交真实 key。

也可以临时加载：

```bash
set -a
source .env
set +a
```

### 3.6 JSONL 模式

用于本地验证真实 Agent 调用，不依赖 Kafka：

```bash
python3 real_agent_sdk/demo_agent_workflow.py \
  --task "用三句话解释什么是人工智能" \
  --sink jsonl \
  --output tmp/real_agent_events.jsonl \
  --model nex-agi/Nex-N2-Pro \
  --timeout 180 \
  --max-tokens 256
```

### 3.7 Kafka 模式

用于将真实 Agent 事件发送到 Kafka：

```bash
python3 real_agent_sdk/demo_agent_workflow.py \
  --task "用三句话解释什么是人工智能" \
  --sink kafka \
  --kafka-bootstrap localhost:9092 \
  --kafka-topic agent-events \
  --model nex-agi/Nex-N2-Pro \
  --timeout 180 \
  --max-tokens 256
```

Kafka 消息格式：

```text
key = trace_id
value = event JSON
```

### 3.8 both 模式

答辩演示推荐使用 both 模式，同时保留 JSONL 文件和 Kafka 消息：

```bash
python3 real_agent_sdk/demo_agent_workflow.py \
  --task "用三句话解释什么是人工智能" \
  --sink both \
  --output tmp/real_agent_events.jsonl \
  --kafka-bootstrap localhost:9092 \
  --kafka-topic agent-events \
  --model nex-agi/Nex-N2-Pro \
  --timeout 180 \
  --max-tokens 256
```

成功输出：

```text
wrote events to tmp/real_agent_events.jsonl
sent events to Kafka topic agent-events
```

### 3.9 自检命令

```bash
python3 real_agent_sdk/self_check.py --file tmp/real_agent_events.jsonl
```

通过结果示例：

```text
ok non-empty JSONL
ok required fields
ok event_id unique
ok timestamps increasing per trace
ok run terminal event
ok llm request paired
ok tool call paired
ok token totals
ok model name
ok metadata_json parseable
```

### 3.10 Kafka 验证

当前服务器 Kafka 2.1.0 的 topic 管理命令使用 ZooKeeper：

```bash
/usr/local/kafka_2.11-2.1.0/bin/kafka-topics.sh \
  --zookeeper localhost:2181 \
  --create \
  --topic agent-events \
  --partitions 3 \
  --replication-factor 1
```

消费验证：

```bash
/usr/local/kafka_2.11-2.1.0/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic agent-events \
  --from-beginning
```

已经验证 Kafka consumer 可以读到真实 Agent 事件。

## 4. 答辩时可以怎么讲

### 4.1 先讲统一事件模型

可以说明：

```text
无论是模拟 Agent 还是真实 Agent，最终都输出同一套事件字段。
这样 Spark Streaming、Spark Batch、后端 API 和前端图表不需要区分数据来源。
```

### 4.2 再讲两个数据入口

```text
simulator/ 负责批量、可控、可复现地造数，适合离线链路和异常场景演示。
real_agent_sdk/ 负责真实模型调用埋点，证明系统不仅能处理假数据，也能接入真实 Agent。
```

### 4.3 讲实时链路接入

```text
真实 Agent SDK 支持 --sink kafka 和 --sink both。
事件可以直接发送到 Kafka 的 agent-events topic。
Kafka key 使用 trace_id，便于按任务链路追踪。
```

### 4.4 讲离线链路接入

```text
simulator 离线模式可以写 JSONL 或 MySQL Source。
后续 Sqoop 可以把 MySQL Source 导入 HDFS Raw。
Spark Batch 再做 Clean、Metric 和 MySQL Analytics 写入。
```

### 4.5 讲异常与可观测性

模拟器支持：

```text
高时延
Token 超额
工具失败
Agent 失败
频繁重试
循环调用
```

真实 SDK 支持：

```text
API 成功时记录 llm_response
API 失败时记录 agent_failed
Reviewer 可强制 retry 演示重试链路
```

## 5. 已验证结果

### 5.1 本地模拟器验证

```text
python -m compileall simulator
python simulator/self_check.py --dir tmp
```

已验证：

```text
seed 可复现
8 类核心事件覆盖
event_id 唯一
时间戳递增
每个 run 完整
异常场景特征存在
```

### 5.2 真实 SDK 验证

```text
python3 real_agent_sdk/self_check.py --file tmp/real_agent_events.jsonl
```

已验证：

```text
JSONL 合法
字段完整
event_id 唯一
trace 内时间戳递增
每个 run 有终态
llm_request 有 llm_response
tool_call 有 tool_result
model_name 为 nex-agi/Nex-N2-Pro
```

### 5.3 Kafka 验证

已验证：

```text
Kafka topic agent-events 创建成功
SDK both 模式发送成功
Kafka consumer 能读取真实 Agent 事件
```

## 6. 当前注意事项

1. 真实 API Key 只放在本地 `.env`，不能提交。
2. `tmp/*.jsonl` 是运行产物，不提交。
3. 当前服务器测试时 Kafka 是在 `master` 上以 `localhost:9092` 跑通的。
4. 如果最终严格按五节点设计，需要把 Kafka 服务迁移或配置到 `middleware:9092`。
5. Kafka 2.1.0 的 `kafka-topics.sh` 使用 `--zookeeper` 管理 topic，而 Producer/Consumer 使用 `--bootstrap-server`。

## 7. 最终结论

本阶段已经完成 AgentScope 的数据产生端增强：

```text
1. simulator/ 可以稳定生成完整、可复现、覆盖异常场景的 Agent 事件。
2. real_agent_sdk/ 可以真实调用硅基流动 nex-agi/Nex-N2-Pro，并记录真实 Agent 运行事件。
3. 两者输出字段一致，可以统一进入 Kafka / MySQL / Spark / FastAPI / Vue 后续链路。
4. JSONL 和 Kafka 双 sink 均已验证可用。
```


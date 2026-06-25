# Real Agent SDK

`real_agent_sdk/` 用于真实 Agent 工作流埋点。它会调用硅基流动 OpenAI-compatible Chat Completions API，并把真实执行过程记录成与 `simulator/` 完全一致的事件字段。

默认模型：

```text
nex-agi/Nex-N2-Pro
```

## 环境变量

推荐在项目根目录创建本地 `.env` 文件：

```text
SILICONFLOW_API_KEY=你的硅基流动 API Key
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
```

`.env` 已经被 `.gitignore` 忽略，不要提交真实 key。

也可以在终端临时设置环境变量：

```bash
export SILICONFLOW_API_KEY="你的硅基流动 API Key"
```

PowerShell：

```powershell
$env:SILICONFLOW_API_KEY="你的硅基流动 API Key"
```

可选配置：

```bash
export SILICONFLOW_BASE_URL="https://api.siliconflow.cn/v1"
```

仓库内只提供 `.env.example`，不要提交真实 `.env`。

## JSONL 本地运行

Kafka 未就绪时，先用 JSONL 模式验证：

```bash
python real_agent_sdk/demo_agent_workflow.py \
  --task "分析大模型在教育行业的应用，并给出三条建议" \
  --sink jsonl \
  --output tmp/real_agent_events.jsonl \
  --model nex-agi/Nex-N2-Pro
```

PowerShell 可以写成一行：

```powershell
python real_agent_sdk/demo_agent_workflow.py --task "分析大模型在教育行业的应用，并给出三条建议" --sink jsonl --output tmp/real_agent_events.jsonl --model nex-agi/Nex-N2-Pro
```

强制演示 retry：

```bash
python real_agent_sdk/demo_agent_workflow.py \
  --task "分析大模型在教育行业的应用，并给出三条建议" \
  --sink jsonl \
  --output tmp/real_agent_events.jsonl \
  --model nex-agi/Nex-N2-Pro \
  --force-retry
```

## Kafka 运行

Kafka 可用后，可以直接发送到 `agent-events`：

```bash
python real_agent_sdk/demo_agent_workflow.py \
  --task "分析大模型在教育行业的应用，并给出三条建议" \
  --sink kafka \
  --kafka-bootstrap middleware:9092 \
  --kafka-topic agent-events \
  --model nex-agi/Nex-N2-Pro
```

Kafka 消息规则：

```text
key = trace_id
value = event JSON
```

## both 模式

同时写 JSONL 和 Kafka：

```bash
python real_agent_sdk/demo_agent_workflow.py \
  --task "分析大模型在教育行业的应用，并给出三条建议" \
  --sink both \
  --output tmp/real_agent_events.jsonl \
  --kafka-bootstrap middleware:9092 \
  --kafka-topic agent-events \
  --model nex-agi/Nex-N2-Pro
```

## 自检

编译检查：

```bash
python -m compileall real_agent_sdk
```

JSONL 自检：

```bash
python real_agent_sdk/self_check.py \
  --file tmp/real_agent_events.jsonl
```

检查内容：

- JSON 格式合法；
- 必要字段齐全；
- `event_id` 唯一；
- 同一 `trace_id` 内 `timestamp` 严格递增；
- 每个 `run_id` 有 `agent_complete` 或 `agent_failed`；
- `llm_request` 后有 `llm_response` 或 `agent_failed`；
- `tool_call` 后有 `tool_result`；
- `total_tokens = prompt_tokens + completion_tokens`；
- `model_name = nex-agi/Nex-N2-Pro`；
- `metadata_json` 可解析。

## Kafka 验收

服务器 Kafka 配好后，可用消费者观察消息：

```bash
kafka-console-consumer.sh \
  --bootstrap-server middleware:9092 \
  --topic agent-events \
  --from-beginning
```

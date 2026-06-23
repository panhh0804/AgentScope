package com.agentscope.streaming

case class AgentEvent(
  event_id: String,
  trace_id: String,
  run_id: String,
  parent_run_id: Option[String],
  agent_id: String,
  parent_agent_id: Option[String],
  agent_role: String,
  event_type: String,
  status: String,
  timestamp: String,
  latency_ms: Long,
  prompt_tokens: Long,
  completion_tokens: Long,
  total_tokens: Long,
  cost_usd: Double,
  model_name: Option[String],
  tool_name: Option[String],
  error_type: Option[String],
  retry_count: Int
)


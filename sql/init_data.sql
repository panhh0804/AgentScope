USE agentscope_analytics;

INSERT INTO daily_metrics (
  metric_date, task_count, success_count, failed_count, success_rate,
  avg_latency_ms, p95_latency_ms, total_tokens, estimated_cost_usd
) VALUES
  ('2026-06-23', 1280, 1192, 88, 0.9313, 1840, 4920, 1680000, 3.240000)
ON DUPLICATE KEY UPDATE
  task_count = VALUES(task_count),
  success_count = VALUES(success_count),
  failed_count = VALUES(failed_count),
  success_rate = VALUES(success_rate),
  avg_latency_ms = VALUES(avg_latency_ms),
  p95_latency_ms = VALUES(p95_latency_ms),
  total_tokens = VALUES(total_tokens),
  estimated_cost_usd = VALUES(estimated_cost_usd);

INSERT INTO agent_rankings (
  metric_date, agent_id, agent_role, execution_count, success_rate,
  avg_latency_ms, p95_latency_ms, total_tokens, estimated_cost_usd
) VALUES
  ('2026-06-23', 'planner_agent', 'planner', 1280, 0.9820, 760, 1800, 210000, 0.310000),
  ('2026-06-23', 'search_agent', 'search', 1240, 0.9310, 1430, 4100, 330000, 0.620000),
  ('2026-06-23', 'analysis_agent', 'analysis', 1202, 0.9260, 2380, 6200, 510000, 1.020000),
  ('2026-06-23', 'writer_agent', 'writer', 1164, 0.9120, 3120, 8800, 455000, 0.910000),
  ('2026-06-23', 'reviewer_agent', 'reviewer', 1098, 0.9480, 1260, 3500, 175000, 0.380000)
ON DUPLICATE KEY UPDATE
  execution_count = VALUES(execution_count),
  success_rate = VALUES(success_rate),
  avg_latency_ms = VALUES(avg_latency_ms),
  p95_latency_ms = VALUES(p95_latency_ms),
  total_tokens = VALUES(total_tokens),
  estimated_cost_usd = VALUES(estimated_cost_usd);

INSERT INTO quality_rules_metadata (rule_id, rule_name, rule_sql, is_active) VALUES
  ('required_fields', '关键字段非空校验', 'event_id IS NOT NULL AND event_id <> \'\' AND trace_id IS NOT NULL AND trace_id <> \'\' AND run_id IS NOT NULL AND run_id <> \'\'', 1),
  ('allowed_event_types', '事件类型合规校验', 'event_type IN (\'agent_start\', \'agent_complete\', \'agent_failed\', \'llm_request\', \'llm_response\', \'tool_call\', \'tool_result\', \'retry\', \'alert\')', 1),
  ('non_negative_latency', '时延非负校验', 'latency_ms >= 0', 1),
  ('non_negative_tokens', 'Token数非负校验', 'total_tokens >= 0', 1)
ON DUPLICATE KEY UPDATE
  rule_name = VALUES(rule_name),
  rule_sql = VALUES(rule_sql),
  is_active = VALUES(is_active);


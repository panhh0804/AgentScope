CREATE DATABASE IF NOT EXISTS agentscope_source DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE agentscope_source;

CREATE TABLE IF NOT EXISTS agent_events_source (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  event_id VARCHAR(64) NOT NULL,
  trace_id VARCHAR(64) NOT NULL,
  run_id VARCHAR(64) NOT NULL,
  parent_run_id VARCHAR(64) NULL,
  agent_id VARCHAR(64) NOT NULL,
  parent_agent_id VARCHAR(64) NULL,
  agent_role VARCHAR(32) NOT NULL,
  event_type VARCHAR(32) NOT NULL,
  status VARCHAR(32) NOT NULL,
  event_time DATETIME NOT NULL,
  latency_ms INT NOT NULL DEFAULT 0,
  prompt_tokens INT NOT NULL DEFAULT 0,
  completion_tokens INT NOT NULL DEFAULT 0,
  total_tokens INT NOT NULL DEFAULT 0,
  cost_usd DECIMAL(12, 6) NOT NULL DEFAULT 0,
  model_name VARCHAR(64) NULL,
  tool_name VARCHAR(64) NULL,
  error_type VARCHAR(64) NULL,
  retry_count INT NOT NULL DEFAULT 0,
  metadata_json TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_event_id (event_id),
  KEY idx_event_time (event_time),
  KEY idx_trace_id (trace_id),
  KEY idx_run_id (run_id),
  KEY idx_agent_role (agent_role),
  KEY idx_event_type (event_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


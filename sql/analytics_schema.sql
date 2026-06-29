CREATE DATABASE IF NOT EXISTS agentscope_analytics DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE agentscope_analytics;

CREATE TABLE IF NOT EXISTS daily_metrics (
  metric_date DATE NOT NULL,
  task_count INT NOT NULL DEFAULT 0,
  success_count INT NOT NULL DEFAULT 0,
  failed_count INT NOT NULL DEFAULT 0,
  success_rate DECIMAL(8, 4) NOT NULL DEFAULT 0,
  avg_latency_ms DECIMAL(12, 2) NOT NULL DEFAULT 0,
  p95_latency_ms DECIMAL(12, 2) NOT NULL DEFAULT 0,
  total_tokens BIGINT NOT NULL DEFAULT 0,
  estimated_cost_usd DECIMAL(14, 6) NOT NULL DEFAULT 0,
  update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (metric_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS hourly_metrics (
  metric_date DATE NOT NULL,
  hour TINYINT NOT NULL,
  task_count INT NOT NULL DEFAULT 0,
  success_rate DECIMAL(8, 4) NOT NULL DEFAULT 0,
  avg_latency_ms DECIMAL(12, 2) NOT NULL DEFAULT 0,
  total_tokens BIGINT NOT NULL DEFAULT 0,
  update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (metric_date, hour)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS agent_rankings (
  metric_date DATE NOT NULL,
  agent_id VARCHAR(64) NOT NULL,
  agent_role VARCHAR(32) NOT NULL,
  execution_count INT NOT NULL DEFAULT 0,
  success_rate DECIMAL(8, 4) NOT NULL DEFAULT 0,
  avg_latency_ms DECIMAL(12, 2) NOT NULL DEFAULT 0,
  p95_latency_ms DECIMAL(12, 2) NOT NULL DEFAULT 0,
  total_tokens BIGINT NOT NULL DEFAULT 0,
  estimated_cost_usd DECIMAL(14, 6) NOT NULL DEFAULT 0,
  update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (metric_date, agent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS error_distribution (
  metric_date DATE NOT NULL,
  error_type VARCHAR(64) NOT NULL,
  error_count INT NOT NULL DEFAULT 0,
  percentage DECIMAL(8, 4) NOT NULL DEFAULT 0,
  PRIMARY KEY (metric_date, error_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS agent_relation_nodes (
  metric_date DATE NOT NULL,
  id VARCHAR(64) NOT NULL,
  name VARCHAR(64) NOT NULL,
  value INT NOT NULL DEFAULT 0,
  failed_count INT NOT NULL DEFAULT 0,
  avg_latency_ms DECIMAL(12, 2) NOT NULL DEFAULT 0,
  PRIMARY KEY (metric_date, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS agent_relation_edges (
  metric_date DATE NOT NULL,
  source VARCHAR(64) NOT NULL,
  target VARCHAR(64) NOT NULL,
  call_count INT NOT NULL DEFAULT 0,
  avg_latency_ms DECIMAL(12, 2) NOT NULL DEFAULT 0,
  failed_count INT NOT NULL DEFAULT 0,
  total_tokens BIGINT NOT NULL DEFAULT 0,
  PRIMARY KEY (metric_date, source, target)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS historical_alerts (
  alert_id VARCHAR(64) NOT NULL,
  metric_date DATE NOT NULL,
  alert_type VARCHAR(64) NOT NULL,
  level VARCHAR(16) NOT NULL,
  agent_id VARCHAR(64) NULL,
  current_value DECIMAL(14, 4) NOT NULL DEFAULT 0,
  threshold_value DECIMAL(14, 4) NOT NULL DEFAULT 0,
  source VARCHAR(32) NOT NULL DEFAULT 'batch',
  status VARCHAR(32) NOT NULL DEFAULT 'open',
  create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (alert_id),
  KEY idx_metric_date (metric_date),
  KEY idx_agent_id (agent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ai_reports (
  report_id VARCHAR(64) NOT NULL,
  report_type VARCHAR(32) NOT NULL,
  report_date DATE NOT NULL,
  model_name VARCHAR(64) NOT NULL,
  content_md MEDIUMTEXT NOT NULL,
  metrics_snapshot_json MEDIUMTEXT NULL,
  create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (report_id),
  KEY idx_report_date (report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


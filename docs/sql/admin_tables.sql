-- 数据管理端后台作业与审计日志持久化表结构
USE agentscope_analytics;

CREATE TABLE IF NOT EXISTS admin_job_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    job_code VARCHAR(64) NOT NULL,
    biz_date VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL, -- SUCCESS, FAILED, RUNNING, PENDING
    input_count INT NOT NULL DEFAULT 0,
    output_count INT NOT NULL DEFAULT 0,
    error_count INT NOT NULL DEFAULT 0,
    start_time VARCHAR(32) NOT NULL,
    end_time VARCHAR(32) NULL,
    duration_seconds INT NULL,
    log_summary TEXT NULL,
    demo TINYINT NOT NULL DEFAULT 0,
    data_source VARCHAR(32) NOT NULL DEFAULT 'mysql'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS admin_audit_logs (
    audit_id VARCHAR(64) PRIMARY KEY,
    operator VARCHAR(64) NOT NULL,
    operation_type VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    resource_id VARCHAR(64) NOT NULL,
    operation_result VARCHAR(32) NOT NULL,
    created_at VARCHAR(32) NOT NULL,
    demo TINYINT NOT NULL DEFAULT 0,
    data_source VARCHAR(32) NOT NULL DEFAULT 'mysql'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

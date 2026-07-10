from __future__ import annotations

import logging
import os
from datetime import date, timedelta
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class MySQLAnalyticsRepository:
    _issues_cache = {}
    _issues_cache_ttl = 15

    def __init__(self) -> None:
        self._enabled = os.getenv("MYSQL_ANALYTICS_ENABLED", "0") == "1"

    def _connect(self):
        if not self._enabled:
            return None
        try:
            import pymysql

            return pymysql.connect(
                host=os.getenv("MYSQL_HOST", "middleware"),
                port=int(os.getenv("MYSQL_PORT", "3306")),
                user=os.getenv("MYSQL_USER", "root"),
                password=os.getenv("MYSQL_PASSWORD", "hadoop2026123aa"),
                database=os.getenv("MYSQL_ANALYTICS_DB", "agentscope_analytics"),
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=1,
            )
        except Exception:
            return None

    def _query(self, sql: str, params: tuple) -> Optional[List[Dict]]:
        conn = self._connect()
        if not conn:
            return None
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return list(cursor.fetchall())
        except Exception as exc:
            logger.warning("MySQL query failed, falling back when possible: %s", exc)
            return None
        finally:
            conn.close()

    def _execute(self, sql: str, params: tuple) -> bool:
        conn = self._connect()
        if not conn:
            return False
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
            conn.commit()
            return True
        except Exception as exc:
            logger.warning("MySQL execute failed: %s", exc)
            return False
        finally:
            conn.close()

    def clear_metrics_for_date(self, metric_date: date, job_code: str) -> None:
        table_map = {
            "daily_metric": ["daily_metrics"],
            "agent_ranking": ["agent_rankings"],
            "error_analysis": ["error_distribution"],
            "relation_analysis": ["agent_relation_nodes", "agent_relation_edges"],
            "historical_alert": ["historical_alerts"]
        }
        tables = table_map.get(job_code, [])
        for table in tables:
            self._execute(f"DELETE FROM {table} WHERE metric_date = %s", (metric_date,))

    def daily_metrics(self, start_date: date, end_date: date) -> Optional[List[Dict]]:
        return self._query(
            "SELECT * FROM daily_metrics WHERE metric_date BETWEEN %s AND %s ORDER BY metric_date",
            (start_date, end_date),
        )

    def analytics_trend(self, start_date: date, end_date: date) -> Optional[List[Dict]]:
        return self._query(
            """
            SELECT
                metric_date,
                task_count,
                success_count,
                failed_count,
                success_rate,
                avg_latency_ms,
                p95_latency_ms,
                total_tokens,
                estimated_cost_usd
            FROM daily_metrics
            WHERE metric_date BETWEEN %s AND %s
            ORDER BY metric_date
            """,
            (start_date, end_date),
        )

    def get_error_distribution(
        self,
        limit: int = 10,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[List[Dict]]:
        if start_date and end_date:
            return self._query(
                """
                SELECT
                    error_type,
                    SUM(error_count) AS total_count,
                    SUM(error_count) / NULLIF((SELECT SUM(error_count) FROM error_distribution WHERE metric_date BETWEEN %s AND %s), 0) AS percentage
                FROM error_distribution
                WHERE metric_date BETWEEN %s AND %s
                GROUP BY error_type
                ORDER BY total_count DESC
                LIMIT %s
                """,
                (start_date, end_date, start_date, end_date, limit),
            )
        return self._query(
            """
            SELECT
                error_type,
                SUM(error_count) AS total_count,
                SUM(error_count) / NULLIF((SELECT SUM(error_count) FROM error_distribution), 0) AS percentage
            FROM error_distribution
            GROUP BY error_type
            ORDER BY total_count DESC
            LIMIT %s
            """,
            (limit,),
        )

    def get_dws_metrics(
        self,
        limit: int = 50,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[List[Dict]]:
        where = []
        params = []
        if start_date:
            where.append("metric_date >= %s")
            params.append(start_date)
        if end_date:
            where.append("metric_date <= %s")
            params.append(end_date)
        sql = "SELECT * FROM daily_metrics"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY metric_date DESC LIMIT %s"
        params.append(limit)
        return self._query(sql, tuple(params))

    def get_dwd_events(
        self,
        limit: int = 50,
        event_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[List[Dict]]:
        where = ["latency_ms >= 0", "trace_id IS NOT NULL"]
        params = []
        filters = {
            "event_id": event_id,
            "trace_id": trace_id,
            "agent_id": agent_id,
            "event_type": event_type,
            "status": status,
        }
        for field, value in filters.items():
            if value:
                if field == "event_id":
                    where.append("LOWER(REPLACE(TRIM(event_id), ' ', '_')) = LOWER(%s)")
                else:
                    where.append(f"LOWER(TRIM({field})) = LOWER(%s)")
                params.append(value)
        sql = f"""
            SELECT *
            FROM agentscope_source.agent_events_source
            WHERE {' AND '.join(where)}
            ORDER BY event_time DESC
            LIMIT %s
        """
        params.append(limit)
        return self._query(sql, tuple(params))

    def get_agent_stats(self, start_date: date, end_date: date) -> Optional[List[Dict]]:
        return self._query(
            """
            SELECT
                agent_id,
                agent_role,
                SUM(execution_count) AS execution_count,
                AVG(success_rate) AS success_rate,
                SUM(total_tokens) AS total_tokens,
                SUM(estimated_cost_usd) AS estimated_cost_usd,
                SUM(avg_latency_ms * execution_count) / NULLIF(SUM(execution_count), 0) AS avg_latency_ms,
                AVG(p95_latency_ms) AS p95_latency_ms
            FROM agent_rankings
            WHERE metric_date BETWEEN %s AND %s
            GROUP BY agent_id, agent_role
            ORDER BY total_tokens DESC
            """,
            (start_date, end_date),
        )

    def hourly_metrics(self, metric_date: date) -> Optional[List[Dict]]:
        return self._query(
            "SELECT * FROM hourly_metrics WHERE metric_date = %s ORDER BY hour",
            (metric_date,),
        )

    def agent_rankings(self, metric_date: date) -> Optional[List[Dict]]:
        return self._query(
            "SELECT * FROM agent_rankings WHERE metric_date = %s ORDER BY execution_count DESC",
            (metric_date,),
        )

    def agent_relations(self, metric_date: date) -> Optional[Dict]:
        nodes = self._query("SELECT * FROM agent_relation_nodes WHERE metric_date = %s", (metric_date,))
        links = self._query("SELECT * FROM agent_relation_edges WHERE metric_date = %s", (metric_date,))
        if nodes is None or links is None:
            return None
        return {"metric_date": metric_date.isoformat(), "nodes": nodes, "links": links}

    def history_alerts(self, metric_date: date) -> Optional[List[Dict]]:
        return self._query(
            "SELECT * FROM historical_alerts WHERE metric_date = %s ORDER BY create_time DESC",
            (metric_date,),
        )

    def get_quality_issues(self, metric_date: date) -> List[Dict]:
        import time
        import threading
        now = time.time()
        cache_key = metric_date.isoformat()
        if cache_key in self._issues_cache:
            val, expire = self._issues_cache[cache_key]
            if now < expire:
                return val

        if not hasattr(self, "_fetching_keys"):
            self._fetching_keys = set()

        if cache_key not in self._fetching_keys:
            self._fetching_keys.add(cache_key)
            
            def fetch_hdfs_job():
                hdfs_samples = []
                try:
                    import subprocess
                    import json
                    dt_str = metric_date.isoformat()
                    java_home = os.getenv("JAVA_HOME", "/usr/local/jdk1.8.0_171")
                    hadoop_home = os.getenv("HADOOP_HOME", "/usr/local/hadoop-2.7.6")
                    cmd = f"export JAVA_HOME={java_home} && {hadoop_home}/bin/hdfs dfs -fs hdfs://master:9000 -cat /agentscope/dirty/agent_events/dt={dt_str}/*.json 2>/dev/null | head -n 10"
                    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, _ = proc.communicate(timeout=6)
                    if stdout:
                        for line in stdout.decode("utf-8").split("\n"):
                            if line.strip():
                                hdfs_samples.append(json.loads(line.strip()))
                except Exception as e:
                    import logging
                    logging.warning(f"Failed to fetch HDFS dirty samples: {e}")
                
                self._update_issues_cache(metric_date, hdfs_samples)
                self._fetching_keys.discard(cache_key)

            threading.Thread(target=fetch_hdfs_job, daemon=True).start()

        return self._build_issues_list(metric_date, [])

    def _update_issues_cache(self, metric_date: date, hdfs_samples: List[Dict]):
        import time
        issues = self._build_issues_list(metric_date, hdfs_samples)
        self._issues_cache[metric_date.isoformat()] = (issues, time.time() + self._issues_cache_ttl)

    def _build_issues_list(self, metric_date: date, hdfs_samples: List[Dict]) -> List[Dict]:
        # 1. Query real DB for negative latency count and samples
        neg_cnt_res = self._query("SELECT COUNT(*) as cnt FROM agentscope_source.agent_events_source WHERE latency_ms < 0", ())
        neg_latency_cnt = neg_cnt_res[0]["cnt"] if neg_cnt_res else 0
        
        neg_latency = [s for s in hdfs_samples if s.get("latency_ms", 0) < 0]
        if not neg_latency:
            neg_latency = self._query(
                "SELECT event_id, trace_id, run_id, agent_id, latency_ms FROM agentscope_source.agent_events_source WHERE latency_ms < 0 LIMIT 5",
                ()
            )

        # 2. Query real DB for token mismatch count and samples
        tok_cnt_res = self._query("SELECT COUNT(*) as cnt FROM agentscope_source.agent_events_source WHERE prompt_tokens + completion_tokens != total_tokens", ())
        token_mis_cnt = tok_cnt_res[0]["cnt"] if tok_cnt_res else 0

        token_mis = [s for s in hdfs_samples if s.get("total_tokens", 0) < 0]
        if not token_mis:
            token_mis = self._query(
                "SELECT event_id, trace_id, run_id, agent_id, prompt_tokens, completion_tokens, total_tokens FROM agentscope_source.agent_events_source WHERE prompt_tokens + completion_tokens != total_tokens LIMIT 5",
                ()
            )

        # 3. Query real DB for missing fields count and samples
        miss_cnt_res = self._query("SELECT COUNT(*) as cnt FROM agentscope_source.agent_events_source WHERE event_id = '' OR trace_id = '' OR run_id = '' OR agent_id = ''", ())
        missing_fields_cnt = miss_cnt_res[0]["cnt"] if miss_cnt_res else 0

        missing_fields = [s for s in hdfs_samples if not s.get("event_id") or not s.get("trace_id") or not s.get("run_id")]
        if not missing_fields:
            missing_fields = self._query(
                "SELECT event_id, trace_id, run_id, agent_id FROM agentscope_source.agent_events_source WHERE event_id = '' OR trace_id = '' OR run_id = '' OR agent_id = '' LIMIT 5",
                ()
            )
        
        issues = []
        
        # Calculate total counts
        total_count = self._query("SELECT COUNT(*) as cnt FROM agentscope_source.agent_events_source", ())
        total_cnt = total_count[0]["cnt"] if total_count and total_count[0]["cnt"] > 0 else 10000
        
        if neg_latency:
            issues.append({
                "rule_code": "negative_latency",
                "rule_name": "负数时延",
                "dataset_code": "agent_source_events",
                "biz_date": metric_date.isoformat(),
                "total_count": total_cnt,
                "failed_count": neg_latency_cnt,
                "pass_rate": round(1 - neg_latency_cnt / total_cnt, 4),
                "sample_data_json": neg_latency
            })
            
        if token_mis:
            issues.append({
                "rule_code": "token_mismatch",
                "rule_name": "Token 不一致",
                "dataset_code": "agent_clean_events",
                "biz_date": metric_date.isoformat(),
                "total_count": total_cnt,
                "failed_count": token_mis_cnt,
                "pass_rate": round(1 - token_mis_cnt / total_cnt, 4),
                "sample_data_json": token_mis
            })
            
        if missing_fields:
            issues.append({
                "rule_code": "required_fields",
                "rule_name": "关键字段缺失",
                "dataset_code": "agent_clean_events",
                "biz_date": metric_date.isoformat(),
                "total_count": total_cnt,
                "failed_count": missing_fields_cnt,
                "pass_rate": round(1 - missing_fields_cnt / total_cnt, 4),
                "sample_data_json": missing_fields
            })
            
        return issues

    def get_source_total_count(self) -> int:
        sql = "SELECT COUNT(*) as cnt FROM agentscope_source.agent_events_source"
        res = self._query(sql, ())
        if res and len(res) > 0:
            return res[0].get("cnt") or 0
        return 0

    def get_today_new_count(self, today_date: date) -> int:
        sql = "SELECT COUNT(*) as cnt FROM agentscope_source.agent_events_source WHERE DATE(event_time) = %s"
        res = self._query(sql, (today_date,))
        if res and len(res) > 0:
            return res[0].get("cnt") or 0
        return 0

    def get_metric_overview_stats(self) -> Dict[str, Any]:
        sql = """
        SELECT 
            COUNT(DISTINCT metric_date) as metric_partition_count,
            MAX(metric_date) as metric_latest_biz_date
        FROM daily_metrics
        """
        res = self._query(sql, ())
        if res and len(res) > 0:
            row = res[0]
            latest_date = row.get("metric_latest_biz_date")
            if latest_date:
                if hasattr(latest_date, "isoformat"):
                    latest_date = latest_date.isoformat()
                else:
                    latest_date = str(latest_date)
            return {
                "metric_partition_count": row.get("metric_partition_count") or 0,
                "metric_latest_biz_date": latest_date or None,
            }
        return {"metric_partition_count": 0, "metric_latest_biz_date": None}

    def get_data_volume_trend(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        # Query raw count from source database
        sql_raw = """
        SELECT DATE(event_time) as dt, COUNT(*) as cnt 
        FROM agentscope_source.agent_events_source 
        WHERE event_time BETWEEN %s AND %s 
        GROUP BY dt
        """
        raw_res = self._query(sql_raw, (start_date.isoformat() + " 00:00:00", end_date.isoformat() + " 23:59:59"))
        raw_map = {}
        if raw_res:
            for row in raw_res:
                d = row.get("dt")
                if hasattr(d, "isoformat"):
                    d = d.isoformat()
                raw_map[str(d)] = row.get("cnt") or 0

        # Query clean count from daily_metrics
        sql_clean = """
        SELECT metric_date as dt, task_count as cnt 
        FROM daily_metrics 
        WHERE metric_date BETWEEN %s AND %s
        """
        clean_res = self._query(sql_clean, (start_date, end_date))
        clean_map = {}
        if clean_res:
            for row in clean_res:
                d = row.get("dt")
                if hasattr(d, "isoformat"):
                    d = d.isoformat()
                clean_map[str(d)] = row.get("cnt") or 0

        trend = []
        curr = start_date
        while curr <= end_date:
            curr_str = curr.isoformat()
            trend.append({
                "biz_date": curr_str,
                "raw_count": raw_map.get(curr_str, 0),
                "clean_count": clean_map.get(curr_str, 0)
            })
            curr += timedelta(days=1)
        return trend

    def get_quality_rules(self) -> List[Dict[str, Any]]:
        sql = "SELECT rule_id, rule_name, rule_sql, is_active, create_time FROM agentscope_analytics.quality_rules_metadata ORDER BY create_time DESC"
        res = self._query(sql, ())
        return res or []

    def create_quality_rule(self, rule_id: str, rule_name: str, rule_sql: str, is_active: int) -> bool:
        sql = "INSERT INTO agentscope_analytics.quality_rules_metadata (rule_id, rule_name, rule_sql, is_active) VALUES (%s, %s, %s, %s)"
        return self._execute(sql, (rule_id, rule_name, rule_sql, is_active))

    def update_quality_rule(self, rule_id: str, is_active: int) -> bool:
        sql = "UPDATE agentscope_analytics.quality_rules_metadata SET is_active = %s WHERE rule_id = %s"
        return self._execute(sql, (is_active, rule_id))

    def ensure_admin_tables(self) -> None:
        if not self._enabled:
            return
        self._execute("""
            CREATE TABLE IF NOT EXISTS admin_job_runs (
                run_id VARCHAR(64) PRIMARY KEY,
                job_code VARCHAR(64) NOT NULL,
                biz_date VARCHAR(32) NOT NULL,
                status VARCHAR(32) NOT NULL,
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
        """, ())
        self._execute("""
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
        """, ())

    def get_admin_job_runs(self) -> Optional[List[Dict]]:
        return self._query("SELECT * FROM admin_job_runs ORDER BY start_time DESC", ())

    def save_admin_job_run(self, run: Dict) -> bool:
        sql = """
            INSERT INTO admin_job_runs (
                run_id, job_code, biz_date, status, input_count, output_count, error_count,
                start_time, end_time, duration_seconds, log_summary, demo, data_source
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                status = VALUES(status),
                end_time = VALUES(end_time),
                duration_seconds = VALUES(duration_seconds),
                log_summary = VALUES(log_summary),
                input_count = VALUES(input_count),
                output_count = VALUES(output_count),
                error_count = VALUES(error_count)
        """
        params = (
            run.get("run_id"),
            run.get("job_code"),
            run.get("biz_date"),
            run.get("status"),
            run.get("input_count") or 0,
            run.get("output_count") or 0,
            run.get("error_count") or 0,
            str(run.get("start_time")),
            str(run.get("end_time")) if run.get("end_time") else None,
            run.get("duration_seconds"),
            run.get("log_summary"),
            1 if run.get("demo") or run.get("data_source") == "mock" else 0,
            run.get("data_source", "mysql")
        )
        return self._execute(sql, params)

    def get_admin_audit_logs(self) -> Optional[List[Dict]]:
        return self._query("SELECT * FROM admin_audit_logs ORDER BY created_at DESC", ())

    def save_admin_audit_log(self, log: Dict) -> bool:
        sql = """
            INSERT INTO admin_audit_logs (
                audit_id, operator, operation_type, resource_type, resource_id, operation_result, created_at, demo, data_source
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            log.get("audit_id"),
            log.get("operator"),
            log.get("operation_type"),
            log.get("resource_type"),
            log.get("resource_id"),
            log.get("operation_result"),
            str(log.get("created_at")),
            1 if log.get("demo") or log.get("data_source") == "mock" else 0,
            log.get("data_source", "mysql")
        )
        return self._execute(sql, params)



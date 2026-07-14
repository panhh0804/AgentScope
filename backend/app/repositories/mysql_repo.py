"""
mysql_repo.py —— AgentScope MySQL 数据访问仓储层

本模块定义了 MySQLAnalyticsRepository 类，作为后端所有服务层（MetricService、StatisticsService 等）
访问 MySQL 数据库的统一代理大门：
  1. 支持连接池生命周期管理，加载环境变量连接配置。
  2. 针对离线多维分析库（agentscope_analytics）执行指标多维聚合、大屏趋势、Agent 效能排行、调用链路拓扑等读写查询。
  3. 针对源日志库（agentscope_source）执行 DWD 数据抓取与质量问题深度计算分析。
  4. 支持 HDFS 的脏样本抽取缓存机制（_issues_cache），解决跨组件交互的时延阻塞。
  5. 自动确保管理任务运行历史（admin_job_runs）与操作审计日志（admin_audit_logs）相关数据库表的动态初始化建立。
"""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MySQLAnalyticsRepository:
    """
    MySQL 数据仓储实现类，处理多维分析指标与系统运维监控数据的 SQL 交互。
    """
    # 静态类成员缓存：暂存 HDFS 采集到的脏样本数据以削峰，并定义过期 TTL（秒）
    _issues_cache = {}
    _issues_cache_ttl = 15

    def __init__(self) -> None:
        """
        根据环境变量判断是否启用真实的 MySQL 数据交互模式。
        """
        self._enabled = os.getenv("MYSQL_ANALYTICS_ENABLED", "0") == "1"

    def _connect(self):
        """
        内部辅助方法：建立并返回与 MySQL Analytics 数据库的连接会话。

        Returns:
            Connection: PyMySQL 数据库连接实例，或在未启用/发生连接异常时返回 None
        """
        if not self._enabled:
            return None
        try:
            import pymysql

            return pymysql.connect(
                host=os.getenv("MYSQL_HOST", "middleware"),
                port=int(os.getenv("MYSQL_PORT", "3306")),
                # 默认使用 root 权限连接，以确保具备创建管理辅助表的 DDL 权限
                user=os.getenv("MYSQL_USER", "root"),
                password=os.getenv("MYSQL_PASSWORD", "hadoop2026123aa"),
                database=os.getenv("MYSQL_ANALYTICS_DB", "agentscope_analytics"),
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=1, # 快速连接超时响应，防止阻塞
            )
        except Exception:
            return None

    def _query(self, sql: str, params: tuple) -> Optional[List[Dict]]:
        """
        数据库查询工具：执行 SQL 语句并返回查出的结果集列表。

        Args:
            sql (str): 参数化 SQL 查询模板
            params (tuple): 对应的防 SQL 注入参数元组

        Returns:
            Optional[List[Dict]]: 每行包含列名字典的映射列表。若不可达或异常则返回 None
        """
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
        """
        数据库命令工具：执行 INSERT / UPDATE / DELETE / CREATE 等非查询类命令。

        Args:
            sql (str): SQL 命令模板
            params (tuple): 参数元组

        Returns:
            bool: 标识是否执行并 commit 成功
        """
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
        """
        为了保证调度重新执行时的幂等性，在作业运行前清理特定日期历史遗留的冲突指标。

        Args:
            metric_date (date): 业务日期
            job_code (str): 作业代码类型
        """
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
        """
        拉取起止日期区间内的每日离线指标大盘汇总。
        """
        return self._query(
            "SELECT * FROM daily_metrics WHERE metric_date BETWEEN %s AND %s ORDER BY metric_date",
            (start_date, end_date),
        )

    def analytics_trend(self, start_date: date, end_date: date) -> Optional[List[Dict]]:
        """
        获取趋势看板专用的每日流量、时延、消耗成本及成功率走势。
        """
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
        """
        获取统计分析所需要的系统异常分类及相应所占比率分布。
        """
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
        """
        在数据资产明细页面，检索并展示 DWS 多维汇总宽表记录。
        """
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
        """
        在数据明细大表，查询 DWD 明细明细表记录（自动过滤掉不合规的时延脏数据）。
        """
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
        """
        以时间范围为维度，分组聚合查询各个 Agent 实体角色的多维工作表现效能。
        """
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
        """
        获取单日每小时流量指标。
        """
        return self._query(
            "SELECT * FROM hourly_metrics WHERE metric_date = %s ORDER BY hour",
            (metric_date,),
        )

    def agent_rankings(self, metric_date: date) -> Optional[List[Dict]]:
        """
        获取单日 Agent 效能排行。
        """
        return self._query(
            "SELECT * FROM agent_rankings WHERE metric_date = %s ORDER BY execution_count DESC",
            (metric_date,),
        )

    def agent_relations(self, metric_date: date) -> Optional[Dict]:
        """
        拼装并输出单日 Agent 网络拓扑的全部节点和权值关系连线数据。
        """
        nodes = self._query("SELECT * FROM agent_relation_nodes WHERE metric_date = %s", (metric_date,))
        links = self._query("SELECT * FROM agent_relation_edges WHERE metric_date = %s", (metric_date,))
        if nodes is None or links is None:
            return None
        return {"metric_date": metric_date.isoformat(), "nodes": nodes, "links": links}

    def history_alerts(self, metric_date: date) -> Optional[List[Dict]]:
        """
        查询单日历史告警。
        """
        return self._query(
            "SELECT * FROM historical_alerts WHERE metric_date = %s ORDER BY create_time DESC",
            (metric_date,),
        )

    def get_quality_issues(self, metric_date: date) -> List[Dict]:
        """
        获取数据合规明细列表。使用后台常驻线程拉取 HDFS dirty 异常样本文件，
        配合内存二级缓存结构，消除同步读取大数据分析平台的卡顿问题。
        """
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
            
            # 使用守护线程在后台无声息地向 HDFS 请求读取 dirty 样本
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

        # 如果没有缓存，先快速返回空的数据库指标骨架，防止前端渲染长时间等待挂起
        return self._build_issues_list(metric_date, [])

    def _update_issues_cache(self, metric_date: date, hdfs_samples: List[Dict]):
        """
        更新局部缓存并设置过期阈值。
        """
        import time
        issues = self._build_issues_list(metric_date, hdfs_samples)
        self._issues_cache[metric_date.isoformat()] = (issues, time.time() + self._issues_cache_ttl)

    def _build_issues_list(self, metric_date: date, hdfs_samples: List[Dict]) -> List[Dict]:
        """
        根据清洗规则（时延负数、主键缺失、Token 不一致），动态计算各规则合规率并附带脏样本详情。
        """
        # 1. 负数时延异常计算
        neg_cnt_res = self._query("SELECT COUNT(*) as cnt FROM agentscope_source.agent_events_source WHERE latency_ms < 0", ())
        neg_latency_cnt = neg_cnt_res[0]["cnt"] if neg_cnt_res else 0
        
        neg_latency = [s for s in hdfs_samples if s.get("latency_ms", 0) < 0]
        if not neg_latency:
            neg_latency = self._query(
                "SELECT event_id, trace_id, run_id, agent_id, latency_ms FROM agentscope_source.agent_events_source WHERE latency_ms < 0 LIMIT 5",
                ()
            )

        # 2. Token 对不上异常计算
        tok_cnt_res = self._query("SELECT COUNT(*) as cnt FROM agentscope_source.agent_events_source WHERE prompt_tokens + completion_tokens != total_tokens", ())
        token_mis_cnt = tok_cnt_res[0]["cnt"] if tok_cnt_res else 0

        token_mis = [s for s in hdfs_samples if s.get("total_tokens", 0) < 0]
        if not token_mis:
            token_mis = self._query(
                "SELECT event_id, trace_id, run_id, agent_id, prompt_tokens, completion_tokens, total_tokens FROM agentscope_source.agent_events_source WHERE prompt_tokens + completion_tokens != total_tokens LIMIT 5",
                ()
            )

        # 3. 标识主键缺失计算
        miss_cnt_res = self._query("SELECT COUNT(*) as cnt FROM agentscope_source.agent_events_source WHERE event_id = '' OR trace_id = '' OR run_id = '' OR agent_id = ''", ())
        missing_fields_cnt = miss_cnt_res[0]["cnt"] if miss_cnt_res else 0

        missing_fields = [s for s in hdfs_samples if not s.get("event_id") or not s.get("trace_id") or not s.get("run_id")]
        if not missing_fields:
            missing_fields = self._query(
                "SELECT event_id, trace_id, run_id, agent_id FROM agentscope_source.agent_events_source WHERE event_id = '' OR trace_id = '' OR run_id = '' OR agent_id = '' LIMIT 5",
                ()
            )
        
        issues = []
        
        # 拉取今日生成的总样本条数用以换算规则合格率百分比
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
        """
        获取源表积累的总记录条数。
        """
        sql = "SELECT COUNT(*) as cnt FROM agentscope_source.agent_events_source"
        res = self._query(sql, ())
        if res and len(res) > 0:
            return res[0].get("cnt") or 0
        return 0

    def get_today_new_count(self, today_date: date) -> int:
        """
        获取特定业务日期当天产生的日志记录总量。
        """
        sql = "SELECT COUNT(*) as cnt FROM agentscope_source.agent_events_source WHERE DATE(event_time) = %s"
        res = self._query(sql, (today_date,))
        if res and len(res) > 0:
            return res[0].get("cnt") or 0
        return 0

    def get_metric_overview_stats(self) -> Dict[str, Any]:
        """
        获取多维指标度量库的总体元状态（包含分区总数及最新一次批处理运行日期）。
        """
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
        """
        按天汇总对比 ODS 导入量（Raw 数据量）与清洗后可信入仓量（Clean 数据量）的近期变化对比走势。
        """
        # 查询原始数据量（Raw）
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

        # 查询入仓可信数据量（Clean）
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
        """
        获取当前系统中注册生效的数据质量规则列表元数据。
        """
        sql = "SELECT rule_id, rule_name, rule_sql, is_active, create_time FROM agentscope_analytics.quality_rules_metadata ORDER BY create_time DESC"
        res = self._query(sql, ())
        return res or []

    def create_quality_rule(self, rule_id: str, rule_name: str, rule_sql: str, is_active: int) -> bool:
        """
        向多维数据库添加一条新的数据校验质量规则定义。
        """
        sql = "INSERT INTO agentscope_analytics.quality_rules_metadata (rule_id, rule_name, rule_sql, is_active) VALUES (%s, %s, %s, %s)"
        return self._execute(sql, (rule_id, rule_name, rule_sql, is_active))

    def update_quality_rule(self, rule_id: str, is_active: int) -> bool:
        """
        启用/禁用指定的质量校验规则。
        """
        sql = "UPDATE agentscope_analytics.quality_rules_metadata SET is_active = %s WHERE rule_id = %s"
        return self._execute(sql, (is_active, rule_id))

    def ensure_admin_tables(self) -> None:
        """
        DDL 校验：服务初始化时自动保证运维管理任务记录表与操作日志表完整创建。
        """
        if not self._enabled:
            return
        # 建立后台调度的流水记录表（支持存储输入/输出真实条数及 stdout 日志）
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
        # 建立操作员审计日志表
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
        """
        获取所有后端调度的作业流水信息。
        """
        return self._query("SELECT * FROM admin_job_runs ORDER BY start_time DESC", ())

    def save_admin_job_run(self, run: Dict) -> bool:
        """
        写入或覆盖保存指定的作业运行状态数据记录。
        """
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
        """
        拉取系统审计操作历史日志列表。
        """
        return self._query("SELECT * FROM admin_audit_logs ORDER BY created_at DESC", ())

    def save_admin_audit_log(self, log: Dict) -> bool:
        """
        写入保存一条新的操作员审计记录。
        """
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

from __future__ import annotations

from datetime import date, datetime, timedelta
import subprocess
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.repositories.mysql_repo import MySQLAnalyticsRepository

ADMIN_JOB_CODES = {
    "offline_generate",
    "datax_import",
    "spark_clean",
    "daily_metric",
    "agent_ranking",
    "error_analysis",
    "relation_analysis",
    "historical_alert",
    "report_generate",
}


class AdminService:
    def __init__(self) -> None:
        self.repo = MySQLAnalyticsRepository()
        self._job_runs = self._seed_job_runs()
        self._audit_logs = self._seed_audit_logs()
        
        # Async memory caches populated by daemon thread
        self._hdfs_storage_cache = {
            "used_bytes": 93679616,
            "limit_bytes": 83784761344,
        }
        self._parquet_ratio_cache = 0.4656
        
        import threading
        threading.Thread(target=self._background_updater, daemon=True).start()

    def _background_updater(self):
        import time
        import subprocess
        while True:
            # 1. Update HDFS storage stats
            try:
                cmd = "export JAVA_HOME=/usr/local/jdk1.8.0_171 && /usr/local/hadoop-2.7.6/bin/hdfs dfs -fs hdfs://master:9000 -df 2>/dev/null"
                proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, _ = proc.communicate(timeout=6)
                if stdout:
                    lines = stdout.decode("utf-8").strip().split("\n")
                    if len(lines) >= 2:
                        parts = lines[1].split()
                        if len(parts) >= 3:
                            self._hdfs_storage_cache = {
                                "limit_bytes": int(parts[1]),
                                "used_bytes": int(parts[2])
                            }
            except Exception:
                pass

            # 2. Update Parquet ratio stats
            try:
                cmd = "export JAVA_HOME=/usr/local/jdk1.8.0_171 && /usr/local/hadoop-2.7.6/bin/hdfs dfs -fs hdfs://master:9000 -du -s /agentscope/raw /agentscope/clean 2>/dev/null"
                proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, _ = proc.communicate(timeout=6)
                if stdout:
                    lines = stdout.decode("utf-8").strip().split("\n")
                    raw_bytes = 0
                    clean_bytes = 0
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 2:
                            bytes_sz = int(parts[0])
                            path = parts[1]
                            if "raw" in path:
                                raw_bytes = bytes_sz
                            elif "clean" in path:
                                clean_bytes = bytes_sz
                    if raw_bytes > 0:
                        self._parquet_ratio_cache = round(1.0 - (clean_bytes / raw_bytes), 4)
            except Exception:
                pass

            time.sleep(30)

    def _get_hdfs_storage_stats(self) -> Dict[str, Any]:
        return self._hdfs_storage_cache

    def _get_parquet_compression_ratio(self) -> float:
        return self._parquet_ratio_cache

    def _get_compute_perf(self) -> List[Dict[str, Any]]:
        job_names = {
            "datax_import": "DataX 业务同步",
            "spark_clean": "Spark 格式清洗",
            "daily_metric": "Spark 每日指标聚合",
            "relation_analysis": "Spark 节点关系分析",
            "error_analysis": "Spark 错误分布聚合",
        }
        perf = []
        for job_code, display_name in job_names.items():
            runs = [r for r in self._job_runs if r.get("job_code") == job_code and r.get("status") == "success"]
            if runs:
                duration = runs[0].get("duration_seconds")
                if duration is not None:
                    perf.append({"job_name": display_name, "duration": duration})
                    continue
            default_durations = {
                "datax_import": 8,
                "spark_clean": 22,
                "daily_metric": 12,
                "relation_analysis": 18,
                "error_analysis": 45
            }
            perf.append({"job_name": display_name, "duration": default_durations[job_code]})
        return perf

    def data_overview(self) -> Dict[str, Any]:
        today_date = date.today()
        today_str = today_date.isoformat()
        
        # 1. Fetch real source db counts
        source_total = self.repo.get_source_total_count()
        today_new = self.repo.get_today_new_count(today_date)
        
        # 2. Estimate HDFS partitions based on job run history + seeds
        raw_dates = {"2026-06-23", "2026-06-24", "2026-06-25"}
        clean_dates = {"2026-06-23", "2026-06-24", "2026-06-25"}
        for run in self._job_runs:
            if run.get("status") == "success":
                biz = run.get("biz_date")
                if biz:
                    if run.get("job_code") == "datax_import":
                        raw_dates.add(biz)
                    elif run.get("job_code") == "spark_clean":
                        clean_dates.add(biz)
                        
        raw_partition_cnt = len(raw_dates)
        raw_latest = max(raw_dates)
        clean_partition_cnt = len(clean_dates)
        clean_latest = max(clean_dates)
        
        # 3. Query real analytics metrics table stats
        metrics_stats = self.repo.get_metric_overview_stats()
        metric_partition_cnt = metrics_stats.get("metric_partition_count") or 0
        metric_latest = metrics_stats.get("metric_latest_biz_date")
        if not metric_latest:
            metric_latest = (today_date - timedelta(days=1)).isoformat()
            
        # 4. Calculate task success rate from current runs
        success_runs = [r for r in self._job_runs if r.get("status") == "success"]
        total_runs = len(self._job_runs)
        success_rate = round(len(success_runs) / total_runs, 3) if total_runs > 0 else 0.889
        
        # Find latest failed job
        failed_runs = [r for r in self._job_runs if r.get("status") == "failed"]
        recent_failed = failed_runs[-1]["job_code"] if failed_runs else "-"
        
        # Get quality issue backlog count
        quality_issues = self.repo.get_quality_issues(today_date)
        pending_issues = len(quality_issues)

        # 5. Funnel count calculation for today (or latest date)
        # Fetch clean count from metrics if available
        sql_clean_cnt = "SELECT task_count FROM daily_metrics WHERE metric_date = %s"
        clean_res = self.repo._query(sql_clean_cnt, (today_str,))
        clean_cnt = clean_res[0]["task_count"] if clean_res and clean_res[0].get("task_count") else int(today_new * 0.965)
        
        return {
            "source_total_count": source_total,
            "today_new_count": today_new,
            "raw_partition_count": raw_partition_cnt,
            "raw_latest_biz_date": raw_latest,
            "clean_partition_count": clean_partition_cnt,
            "clean_latest_biz_date": clean_latest,
            "metric_partition_count": metric_partition_cnt,
            "metric_latest_biz_date": metric_latest,
            "raw_to_clean_valid_rate": 0.965,
            "parquet_saving_rate": self._get_parquet_compression_ratio(),
            "today_task_success_rate": success_rate,
            "recent_failed_task": recent_failed,
            "quality_issue_pending_count": pending_issues,
            "layer_update_times": [
                {"layer": "MySQL Source", "latest_update_time": self._ts(minutes=8)},
                {"layer": "HDFS Raw", "latest_update_time": self._ts(minutes=6)},
                {"layer": "HDFS Clean", "latest_update_time": self._ts(minutes=4)},
                {"layer": "HDFS Metric", "latest_update_time": self._ts(minutes=2)},
            ],
            "funnel": [
                {"name": "Source", "count": today_new, "processor": "DataX"},
                {"name": "Raw", "count": today_new, "processor": "Spark Clean"},
                {"name": "Clean", "count": clean_cnt, "processor": "Spark Analysis"},
                {"name": "Metric", "count": int(clean_cnt * 0.012) if clean_cnt > 0 else 0, "processor": None},
            ],
            "hdfs_storage": self._get_hdfs_storage_stats(),
            "compute_perf": self._get_compute_perf(),
        }

    def data_volume_trend(self) -> List[Dict[str, Any]]:
        end = date.today()
        start = end - timedelta(days=6)
        return self.repo.get_data_volume_trend(start, end)

    def dwd_events(
        self,
        limit: int = 50,
        event_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        rows = self.repo.get_dwd_events(
            limit,
            self._normalize_filter_value(event_id, "event_id"),
            self._normalize_filter_value(trace_id, "trace_id"),
            self._normalize_filter_value(agent_id, "agent_id"),
            self._normalize_filter_value(event_type, "event_type"),
            self._normalize_filter_value(status, "status"),
        ) or []
        for row in rows:
            self._normalize_row(row)
        return rows

    def dws_metrics(
        self,
        limit: int = 50,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        if start_date and end_date and start_date > end_date:
            return []
        rows = self.repo.get_dws_metrics(limit, start_date, end_date) or []
        filtered_rows = []
        for row in rows:
            metric_date = self._coerce_date(row.get("metric_date"))
            if start_date and metric_date and metric_date < start_date:
                continue
            if end_date and metric_date and metric_date > end_date:
                continue
            self._normalize_row(row)
            filtered_rows.append(row)
        return filtered_rows

    def pipeline_status(self) -> Dict[str, Any]:
        source_total = self.repo.get_source_total_count()
        
        # Clean count (sum of all task_counts in daily_metrics)
        sql_clean = "SELECT SUM(task_count) as total_clean FROM daily_metrics"
        clean_res = self.repo._query(sql_clean, ())
        clean_total = clean_res[0].get("total_clean") if clean_res and clean_res[0].get("total_clean") else 0
        
        # Metric count (number of report records or metrics)
        sql_metric = "SELECT COUNT(*) as total_reports FROM ai_reports"
        metric_res = self.repo._query(sql_metric, ())
        metric_total = metric_res[0].get("total_reports") if metric_res and metric_res[0].get("total_reports") else 0
        
        # Find latest statuses of jobs in memory
        status_map = {"datax_import": "success", "spark_clean": "success", "daily_metric": "success"}
        for job_code in status_map.keys():
            runs = [r for r in self._job_runs if r.get("job_code") == job_code]
            if runs:
                status_map[job_code] = runs[-1]["status"]

        return {
            "nodes": [
                {"code": "source", "name": "MySQL Source", "status": "success", "count": source_total},
                {"code": "raw", "name": "HDFS Raw", "status": status_map["datax_import"], "count": source_total if status_map["datax_import"] == "success" else 0},
                {"code": "clean", "name": "HDFS Clean", "status": status_map["spark_clean"], "count": int(clean_total or 0)},
                {"code": "metric", "name": "Metric", "status": status_map["daily_metric"], "count": int(metric_total or 0)},
            ],
            "edges": [
                {"from": "source", "to": "raw", "job_code": "datax_import"},
                {"from": "raw", "to": "clean", "job_code": "spark_clean"},
                {"from": "clean", "to": "metric", "job_code": "daily_metric"},
            ],
        }

    def datasets(self) -> List[Dict[str, Any]]:
        source_total = self.repo.get_source_total_count()
        
        sql_clean = "SELECT SUM(task_count) as total_clean FROM daily_metrics"
        clean_res = self.repo._query(sql_clean, ())
        clean_total = int(clean_res[0].get("total_clean") or 0) if clean_res else 0
        
        sql_metrics = "SELECT COUNT(*) as total_metrics FROM daily_metrics"
        metrics_res = self.repo._query(sql_metrics, ())
        metrics_total = int(metrics_res[0].get("total_metrics") or 0) if metrics_res else 0
        
        sql_relations = "SELECT COUNT(*) as total_relations FROM agent_relation_edges"
        relations_res = self.repo._query(sql_relations, ())
        relations_total = int(relations_res[0].get("total_relations") or 0) if relations_res else 0
        
        sql_alerts = "SELECT COUNT(*) as total_alerts FROM historical_alerts"
        alerts_res = self.repo._query(sql_alerts, ())
        alerts_total = int(alerts_res[0].get("total_alerts") or 0) if alerts_res else 0
        
        sql_reports = "SELECT COUNT(*) as total_reports FROM ai_reports"
        reports_res = self.repo._query(sql_reports, ())
        reports_total = int(reports_res[0].get("total_reports") or 0) if reports_res else 0

        return [
            self._dataset("agent_source_events", "Agent 原始事件", "MySQL Source", "Source", source_total),
            self._dataset("agent_raw_events", "Agent 原始事件文件", "HDFS Raw", "Raw", source_total),
            self._dataset("agent_clean_events", "Agent 清洗事件", "HDFS Clean", "Clean", clean_total),
            self._dataset("agent_daily_metrics", "Agent 每日指标", "MySQL Analytics", "Metric", metrics_total),
            self._dataset("agent_relations", "Agent 调用关系", "MySQL Analytics", "Analytics", relations_total),
            self._dataset("historical_alerts", "历史告警", "MySQL Analytics", "Analytics", alerts_total),
            self._dataset("ai_reports", "AI 分析报告", "MySQL Analytics", "Report", reports_total),
        ]

    def data_lineage(self) -> Dict[str, Any]:
        return {
            "nodes": [
                {"id": "mysql_source", "name": "MySQL Source"},
                {"id": "hdfs_raw", "name": "HDFS Raw"},
                {"id": "hdfs_clean", "name": "HDFS Clean"},
                {"id": "daily_metric", "name": "Daily Metric"},
                {"id": "agent_ranking", "name": "Agent Ranking"},
                {"id": "error_analysis", "name": "Error Analysis"},
                {"id": "historical_alert", "name": "Historical Alert"},
                {"id": "mysql_analytics", "name": "MySQL Analytics"},
            ],
            "edges": [
                {"from": "mysql_source", "to": "hdfs_raw", "label": "DataX"},
                {"from": "hdfs_raw", "to": "hdfs_clean", "label": "Spark Clean"},
                {"from": "hdfs_clean", "to": "daily_metric", "label": "daily_metric"},
                {"from": "hdfs_clean", "to": "agent_ranking", "label": "agent_ranking"},
                {"from": "hdfs_clean", "to": "error_analysis", "label": "error_analysis"},
                {"from": "hdfs_clean", "to": "historical_alert", "label": "historical_alert"},
                {"from": "daily_metric", "to": "mysql_analytics", "label": "load"},
                {"from": "agent_ranking", "to": "mysql_analytics", "label": "load"},
                {"from": "error_analysis", "to": "mysql_analytics", "label": "load"},
                {"from": "historical_alert", "to": "mysql_analytics", "label": "load"},
            ],
        }

    def events(
        self,
        event_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        run_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        rows = self._seed_events()
        filters = {
            "event_id": event_id,
            "trace_id": trace_id,
            "run_id": run_id,
            "agent_id": agent_id,
            "event_type": event_type,
            "status": status,
        }
        for field, value in filters.items():
            if value:
                expected = self._normalize_filter_value(value, field)
                rows = [row for row in rows if self._filter_equals(row.get(field), expected, field)]
        if start_time:
            rows = [row for row in rows if datetime.fromisoformat(row["event_time"]) >= start_time]
        if end_time:
            rows = [row for row in rows if datetime.fromisoformat(row["event_time"]) <= end_time]
        return rows

    def jobs(self) -> List[Dict[str, Any]]:
        return [
            {"job_code": code, "job_name": name, "enabled": True, "readonly_input": code in {"datax_import", "spark_clean"}}
            for code, name in [
                ("offline_generate", "测试离线数据生成"),
                ("datax_import", "Source 导入 Raw"),
                ("spark_clean", "Raw 清洗到 Clean"),
                ("daily_metric", "每日指标计算"),
                ("agent_ranking", "Agent 排名计算"),
                ("error_analysis", "错误分析"),
                ("relation_analysis", "调用关系分析"),
                ("historical_alert", "历史告警生成"),
                ("report_generate", "AI 报告生成"),
            ]
        ]

    def job_runs(self) -> List[Dict[str, Any]]:
        return self._job_runs

    def execute_job(self, job_code: str, biz_date: date) -> Dict[str, Any]:
        import os
        ssh_user = os.getenv("SSH_USER", "root")
        ssh_host = os.getenv("SSH_HOST", "master")
        ssh_dest = f"{ssh_user}@{ssh_host}"
        ssh_opts_str = os.getenv("SSH_OPTS", "-o StrictHostKeyChecking=no")
        import shlex
        ssh_opts = shlex.split(ssh_opts_str)
        project_home = os.getenv("PROJECT_HOME", "/root/agentscope")
        self._ensure_job(job_code)
        if biz_date > date.today():
            raise ValueError("业务日期不能晚于今天")
        
        status = "success"
        log_summary = f"{job_code} executed successfully."
        error_count = 0
        input_count = 10000
        output_count = 9650 if job_code == "spark_clean" else 120
        
        start_time = datetime.now()
        
        try:
            if job_code == "offline_generate":
                # Execute simulator on master node via passwordless SSH to populate MySQL source db
                exec_cmd = f"source /etc/profile && cd {project_home}/simulator && python3 main.py --mode offline --start-date {biz_date.isoformat()} --end-date {biz_date.isoformat()} --count 50"
                cmd = ["ssh"] + ssh_opts + [ssh_dest, exec_cmd]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if res.returncode != 0:
                    status = "failed"
                    log_summary = f"Mock Data Generation failed:\n{res.stderr or res.stdout}"
                    error_count = 1
                else:
                    log_summary = f"Mock Data Generation completed successfully:\n{res.stdout}"
                    output_count = 1126
            
            elif job_code == "datax_import":
                # Execute DataX script on master node via passwordless SSH
                exec_cmd = f"source /etc/profile && cd {project_home} && bash scripts/datax_import_agent_events.sh {biz_date.isoformat()}"
                cmd = ["ssh"] + ssh_opts + [ssh_dest, exec_cmd]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if res.returncode != 0:
                    status = "failed"
                    log_summary = f"DataX Import failed:\n{res.stderr or res.stdout}"
                    error_count = 1
                else:
                    log_summary = f"DataX Import completed:\n{res.stdout}"
            
            elif job_code == "spark_clean":
                # Execute Spark clean script on master node
                exec_cmd = f"source /etc/profile && cd {project_home} && bash scripts/run_clean_job.sh {biz_date.isoformat()}"
                cmd = ["ssh"] + ssh_opts + [ssh_dest, exec_cmd]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if res.returncode != 0:
                    status = "failed"
                    log_summary = f"Spark Clean failed:\n{res.stderr or res.stdout}"
                    error_count = 1
                else:
                    log_summary = f"Spark Clean completed:\n{res.stdout}"
                    
            elif job_code in ["daily_metric", "agent_ranking", "error_analysis", "relation_analysis", "historical_alert"]:
                # Clear existing metrics for the selected business date to ensure idempotency and avoid MySQL PK violation
                self.repo.clear_metrics_for_date(biz_date, job_code)
                
                # Execute specific Spark job on master node
                job_class_map = {
                    "daily_metric": "DailyMetricJob",
                    "agent_ranking": "AgentRankingJob",
                    "error_analysis": "ErrorAnalysisJob",
                    "relation_analysis": "RelationGraphJob",
                    "historical_alert": "HistoricalAlertJob"
                }
                job_class = job_class_map[job_code]
                
                # Formulate the spark-submit command on master
                spark_cmd = (
                    f"source /etc/profile && cd /root/agentscope && "
                    f"export SPARK_HOME=${{SPARK_HOME:-/usr/local/spark}} && "
                    f"export HADOOP_CONF_DIR=${{HADOOP_CONF_DIR:-/usr/local/hadoop-2.7.6/etc/hadoop}} && "
                    f"export YARN_CONF_DIR=${{YARN_CONF_DIR:-$HADOOP_CONF_DIR}} && "
                    f"export PATH=$SPARK_HOME/bin:$PATH && "
                    f"$SPARK_HOME/bin/spark-submit "
                    f"--class com.agentscope.batch.{job_class} "
                    f"--master ${{SPARK_MASTER:-${{SPARK_MASTER_URL:-yarn}}}} "
                    f"--deploy-mode ${{SPARK_DEPLOY_MODE:-client}} "
                    f"/root/agentscope/spark-batch/target/agentscope-spark-batch-0.1.0.jar "
                    f"--input /agentscope/clean/agent_events/dt={biz_date.isoformat()} "
                    f"--metric-base /agentscope/metric "
                    f"--date {biz_date.isoformat()} "
                    f"--jdbc-url jdbc:mysql://middleware:3306/agentscope_analytics?useSSL=false\\&useUnicode=true\\&characterEncoding=utf8 "
                    f"--jdbc-user agentscope "
                    f"--jdbc-password agentscope_pass"
                )
                cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "root@master", spark_cmd]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if res.returncode != 0:
                    status = "failed"
                    log_summary = f"Spark Job {job_class} failed:\n{res.stderr or res.stdout}"
                    error_count = 1
                else:
                    log_summary = f"Spark Job {job_class} completed:\n{res.stdout}"
                    
            elif job_code == "report_generate":
                # Generate AI report
                from app.services.report_service import ReportService
                report_service = ReportService()
                report_res = report_service.generate(biz_date, "daily", None)
                log_summary = f"AI Report generated: {report_res.get('report_id')}"
                
        except Exception as e:
            status = "failed"
            log_summary = f"Execution system error: {str(e)}"
            error_count = 1
            
        duration = int((datetime.now() - start_time).total_seconds())
        
        run = {
            "run_id": f"run_{uuid4().hex[:10]}",
            "job_code": job_code,
            "biz_date": biz_date.isoformat(),
            "status": status,
            "input_count": input_count,
            "output_count": output_count if status == "success" else 0,
            "error_count": error_count,
            "start_time": start_time.isoformat(timespec="seconds"),
            "end_time": datetime.now().isoformat(timespec="seconds"),
            "duration_seconds": duration,
            "log_summary": log_summary,
        }
        
        self._job_runs.insert(0, run)
        self._audit_logs.insert(0, self._audit("admin", "task_execute", "job", job_code, status))
        return run

    def retry_job_run(self, run_id: str) -> Dict[str, Any]:
        source = next((row for row in self._job_runs if row["run_id"] == run_id), None)
        if not source:
            raise ValueError(f"unknown run_id: {run_id}")
        run = self.execute_job(source["job_code"], date.fromisoformat(source["biz_date"]))
        run["log_summary"] = f"retry from {run_id}; {run['log_summary']}"
        self._audit_logs.insert(0, self._audit("admin", "task_retry", "job_run", run_id, "success"))
        return run

    def job_run_logs(self, run_id: str) -> Dict[str, Any]:
        run = next((row for row in self._job_runs if row["run_id"] == run_id), None)
        if not run:
            raise ValueError(f"unknown run_id: {run_id}")
        return {
            "run_id": run_id,
            "lines": [
                f"[INFO] validate whitelist job_code={run['job_code']}",
                f"[INFO] load biz_date={run['biz_date']}",
                f"[INFO] input={run['input_count']} output={run['output_count']} errors={run['error_count']}",
                f"[{run['status'].upper()}] {run['log_summary']}",
            ],
        }

    def quality_overview(self) -> Dict[str, Any]:
        issues = self.quality_issues()
        total = sum(row["total_count"] for row in issues)
        failed = sum(row["failed_count"] for row in issues)
        return {
            "rule_count": len(issues),
            "issue_count": failed,
            "avg_pass_rate": round(1 - failed / total, 4) if total else 1,
            "pending_count": len([row for row in issues if row["failed_count"] > 0]),
        }

    def quality_issues(self) -> List[Dict[str, Any]]:
        return self.repo.get_quality_issues(date.today())

    def audit_logs(self) -> List[Dict[str, Any]]:
        return self._audit_logs

    def _ensure_job(self, job_code: str) -> None:
        if job_code not in ADMIN_JOB_CODES:
            raise ValueError(f"job_code is not allowed: {job_code}")

    def _seed_events(self) -> List[Dict[str, Any]]:
        now = datetime.now()
        events = []
        agents = ["planner_agent", "search_agent", "analysis_agent", "writer_agent", "reviewer_agent"]
        types = ["task_start", "tool_call", "llm_call", "handoff", "task_finish"]
        for idx in range(18):
            event_time = now - timedelta(minutes=idx * 7)
            status = "failed" if idx in {5, 13} else "success"
            event = {
                "event_id": f"evt_{1000 + idx}",
                "trace_id": f"trace_demo_{100 + idx % 4}",
                "run_id": f"run_demo_{200 + idx % 3}",
                "agent_id": agents[idx % len(agents)],
                "event_type": types[idx % len(types)],
                "status": status,
                "event_time": event_time.isoformat(timespec="seconds"),
                "latency_ms": 420 + idx * 137,
                "raw_json": {
                    "event_id": f"evt_{1000 + idx}",
                    "trace_id": f"trace_demo_{100 + idx % 4}",
                    "input": {"prompt": "demo prompt", "tokens": 800 + idx * 13},
                    "output": {"status": status, "tokens": 420 + idx * 9},
                    "metadata": {"source": "mock_admin_api", "biz_date": date.today().isoformat()},
                },
            }
            events.append(event)
        return events

    def _seed_job_runs(self) -> List[Dict[str, Any]]:
        today = date.today()
        rows = []
        statuses = ["success", "success", "failed", "running", "pending", "cancelled"]
        for idx, job_code in enumerate(["datax_import", "spark_clean", "daily_metric", "agent_ranking", "relation_analysis", "report_generate"]):
            start = datetime.now() - timedelta(hours=idx + 1)
            status = statuses[idx % len(statuses)]
            rows.append(
                {
                    "run_id": f"run_seed_{idx + 1}",
                    "job_code": job_code,
                    "biz_date": (today - timedelta(days=idx % 2)).isoformat(),
                    "status": status,
                    "input_count": 10000 - idx * 240,
                    "output_count": 9650 - idx * 120,
                    "error_count": 0 if status == "success" else 12 + idx,
                    "start_time": start.isoformat(timespec="seconds"),
                    "end_time": None if status in {"running", "pending"} else (start + timedelta(minutes=8 + idx)).isoformat(timespec="seconds"),
                    "duration_seconds": None if status in {"running", "pending"} else (8 + idx) * 60,
                    "log_summary": f"{job_code} {status}; fixed offline pipeline execution.",
                }
            )
        return rows

    def _seed_audit_logs(self) -> List[Dict[str, Any]]:
        return [
            self._audit("admin", "task_execute", "job", "datax_import", "success"),
            self._audit("admin", "task_retry", "job_run", "run_seed_3", "success"),
            self._audit("data_steward", "rule_update", "quality_rule", "negative_latency", "success"),
            self._audit("admin", "test_data_import", "dataset", "agent_source_events", "success"),
        ]

    def _dataset(self, code: str, name: str, storage: str, layer: str, rows: int) -> Dict[str, Any]:
        return {
            "dataset_code": code,
            "dataset_name": name,
            "storage": storage,
            "layer": layer,
            "row_count": rows,
            "latest_biz_date": date.today().isoformat(),
            "owner": "platform_admin",
        }

    def _issue(self, code: str, name: str, dataset: str, biz_date: str, total: int, failed: int, sample: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "rule_code": code,
            "rule_name": name,
            "dataset_code": dataset,
            "biz_date": biz_date,
            "total_count": total,
            "failed_count": failed,
            "pass_rate": round(1 - failed / total, 4),
            "sample_data_json": sample,
        }

    def _audit(self, operator: str, operation_type: str, resource_type: str, resource_id: str, result: str) -> Dict[str, Any]:
        return {
            "audit_id": f"audit_{uuid4().hex[:8]}",
            "operator": operator,
            "operation_type": operation_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "operation_result": result,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

    def _ts(self, minutes: int) -> str:
        return (datetime.now() - timedelta(minutes=minutes)).isoformat(timespec="seconds")

    def _normalize_row(self, row: Dict[str, Any]) -> None:
        for key, value in list(row.items()):
            if hasattr(value, "isoformat"):
                row[key] = value.isoformat()
            elif value.__class__.__name__ == "Decimal":
                row[key] = float(value)

    def _normalize_filter_value(self, value: Optional[str], field: str) -> Optional[str]:
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        if field == "event_id":
            normalized = "_".join(normalized.split())
        return normalized

    def _filter_equals(self, actual: Any, expected: Optional[str], field: str) -> bool:
        if expected is None:
            return True
        actual_value = self._normalize_filter_value(str(actual or ""), field)
        return actual_value == expected

    def _coerce_date(self, value: Any) -> Optional[date]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value)[:10].replace("/", "-"))
        except ValueError:
            return None

    def get_quality_rules(self) -> List[Dict[str, Any]]:
        return self.repo.get_quality_rules()

    def create_quality_rule(self, rule_id: str, rule_name: str, rule_sql: str, is_active: int) -> bool:
        return self.repo.create_quality_rule(rule_id, rule_name, rule_sql, is_active)

    def update_quality_rule(self, rule_id: str, is_active: int) -> bool:
        return self.repo.update_quality_rule(rule_id, is_active)

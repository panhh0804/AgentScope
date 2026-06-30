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

    def data_overview(self) -> Dict[str, Any]:
        today = date.today().isoformat()
        return {
            "source_total_count": 10000,
            "today_new_count": 824,
            "raw_partition_count": 31,
            "raw_latest_biz_date": today,
            "clean_partition_count": 31,
            "clean_latest_biz_date": today,
            "metric_partition_count": 30,
            "metric_latest_biz_date": (date.today() - timedelta(days=1)).isoformat(),
            "raw_to_clean_valid_rate": 0.965,
            "today_task_success_rate": 0.889,
            "recent_failed_task": "relation_analysis",
            "quality_issue_pending_count": 4,
            "layer_update_times": [
                {"layer": "MySQL Source", "latest_update_time": self._ts(minutes=8)},
                {"layer": "HDFS Raw", "latest_update_time": self._ts(minutes=6)},
                {"layer": "HDFS Clean", "latest_update_time": self._ts(minutes=4)},
                {"layer": "HDFS Metric", "latest_update_time": self._ts(minutes=2)},
            ],
            "funnel": [
                {"name": "Source", "count": 10000, "processor": "DataX"},
                {"name": "Raw", "count": 10000, "processor": "Spark Clean"},
                {"name": "Clean", "count": 9650, "processor": "Spark Analysis"},
                {"name": "Metric", "count": 120, "processor": None},
            ],
        }

    def data_volume_trend(self) -> List[Dict[str, Any]]:
        start = date.today() - timedelta(days=6)
        return [
            {
                "biz_date": (start + timedelta(days=idx)).isoformat(),
                "raw_count": 8200 + idx * 310,
                "clean_count": 7920 + idx * 296,
            }
            for idx in range(7)
        ]

    def pipeline_status(self) -> Dict[str, Any]:
        return {
            "nodes": [
                {"code": "source", "name": "MySQL Source", "status": "success", "count": 10000},
                {"code": "raw", "name": "HDFS Raw", "status": "success", "count": 10000},
                {"code": "clean", "name": "HDFS Clean", "status": "success", "count": 9650},
                {"code": "metric", "name": "Metric", "status": "success", "count": 120},
            ],
            "edges": [
                {"from": "source", "to": "raw", "job_code": "datax_import"},
                {"from": "raw", "to": "clean", "job_code": "spark_clean"},
                {"from": "clean", "to": "metric", "job_code": "daily_metric"},
            ],
        }

    def datasets(self) -> List[Dict[str, Any]]:
        return [
            self._dataset("agent_source_events", "Agent 原始事件", "MySQL Source", "Source", 10000),
            self._dataset("agent_raw_events", "Agent 原始事件文件", "HDFS Raw", "Raw", 10000),
            self._dataset("agent_clean_events", "Agent 清洗事件", "HDFS Clean", "Clean", 9650),
            self._dataset("agent_daily_metrics", "Agent 每日指标", "MySQL Analytics", "Metric", 120),
            self._dataset("agent_relations", "Agent 调用关系", "MySQL Analytics", "Analytics", 48),
            self._dataset("historical_alerts", "历史告警", "MySQL Analytics", "Analytics", 36),
            self._dataset("ai_reports", "AI 分析报告", "MySQL Analytics", "Report", 14),
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
            "trace_id": trace_id,
            "run_id": run_id,
            "agent_id": agent_id,
            "event_type": event_type,
            "status": status,
        }
        for field, value in filters.items():
            if value:
                rows = [row for row in rows if str(row.get(field)) == value]
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
        self._ensure_job(job_code)
        
        status = "success"
        log_summary = f"{job_code} executed successfully."
        error_count = 0
        input_count = 10000
        output_count = 9650 if job_code == "spark_clean" else 120
        
        start_time = datetime.now()
        
        try:
            if job_code == "datax_import":
                # Execute DataX script on master node via passwordless SSH
                cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "root@master", "bash", "/root/projects/agentscope/scripts/datax_import_agent_events.sh", biz_date.isoformat()]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if res.returncode != 0:
                    status = "failed"
                    log_summary = f"DataX Import failed:\n{res.stderr or res.stdout}"
                    error_count = 1
                else:
                    log_summary = f"DataX Import completed:\n{res.stdout}"
            
            elif job_code == "spark_clean":
                # Execute Spark clean script on master node
                cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "root@master", "bash", "/root/projects/agentscope/scripts/run_clean_job.sh", biz_date.isoformat()]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if res.returncode != 0:
                    status = "failed"
                    log_summary = f"Spark Clean failed:\n{res.stderr or res.stdout}"
                    error_count = 1
                else:
                    log_summary = f"Spark Clean completed:\n{res.stdout}"
                    
            elif job_code in ["daily_metric", "agent_ranking", "error_analysis", "relation_analysis", "historical_alert"]:
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
                    f"/usr/local/spark/bin/spark-submit "
                    f"--class com.agentscope.batch.{job_class} "
                    f"--master spark://master:7077 "
                    f"/root/projects/agentscope/spark-batch/target/agentscope-spark-batch-0.1.0.jar "
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
                report_res = report_service.generate(biz_date, "daily", "rule-template")
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

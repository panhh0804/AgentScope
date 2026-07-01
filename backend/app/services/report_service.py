from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from app.services.metric_service import MetricService
from app.repositories.mysql_repo import MySQLAnalyticsRepository

logger = logging.getLogger(__name__)


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return int(obj) if obj == obj.to_integral_value() else float(obj)
        return super().default(obj)


class ReportService:
    def __init__(self) -> None:
        self.metrics = MetricService()
        self.repo = MySQLAnalyticsRepository()
        self._reports: Dict[str, Dict] = {}
        self._prompt_path = Path(__file__).resolve().parents[1] / "report" / "prompt.md"

    def generate(self, report_date: date, report_type: str, model_name: Optional[str]) -> Dict:
        daily = self.metrics.daily_metrics(report_date, report_date)
        rankings = self.metrics.agent_rankings(report_date)
        alerts = self.metrics.history_alerts(report_date)
        relation = self.metrics.agent_relations(report_date)
        report_id = f"report_{uuid4().hex[:12]}"
        model = model_name or os.getenv("OPENAI_MODEL_NAME") or "rule-template"
        content = self._render_markdown(report_date, report_type, daily, rankings, alerts, relation)
        try:
            content = self._render_llm_markdown(report_date, report_type, model, daily, rankings, alerts, relation)
        except Exception as exc:
            logger.exception("LLM report generation failed, falling back to rule report: %s", exc)
        
        metrics_snapshot = {
            "daily": daily,
            "rankings": rankings,
            "alerts": alerts,
            "relation": relation,
        }
        metrics_snapshot = json.loads(json.dumps(metrics_snapshot, cls=DateEncoder))
        item = {
            "report_id": report_id,
            "report_type": report_type,
            "report_date": report_date.isoformat(),
            "model_name": model,
            "content": content,
            "metrics_snapshot": metrics_snapshot,
            "create_time": datetime.now().isoformat(timespec="seconds"),
        }
        
        if self.repo._enabled:
            sql = """
                INSERT INTO ai_reports (report_id, report_type, report_date, model_name, content_md, metrics_snapshot_json)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            self.repo._execute(sql, (
                report_id,
                report_type,
                report_date,
                model,
                content,
                json.dumps(metrics_snapshot, ensure_ascii=False)
            ))
        else:
            self._reports[report_id] = item
            
        return item

    def list_reports(self) -> List[Dict]:
        if self.repo._enabled:
            sql = """
                SELECT report_id, report_type, report_date, model_name, create_time 
                FROM ai_reports 
                ORDER BY create_time DESC
            """
            rows = self.repo._query(sql, ())
            if rows is not None:
                res = []
                for row in rows:
                    res.append({
                        "report_id": row["report_id"],
                        "report_type": row["report_type"],
                        "report_date": row["report_date"].isoformat() if isinstance(row["report_date"], date) else str(row["report_date"]),
                        "model_name": row["model_name"],
                        "create_time": row["create_time"].isoformat() if hasattr(row["create_time"], "isoformat") else str(row["create_time"])
                    })
                return res

        return [
            {key: value for key, value in report.items() if key != "content"}
            for report in sorted(self._reports.values(), key=lambda x: x["create_time"], reverse=True)
        ]

    def get_report(self, report_id: str) -> Dict:
        if self.repo._enabled:
            sql = """
                SELECT report_id, report_type, report_date, model_name, content_md, metrics_snapshot_json, create_time
                FROM ai_reports
                WHERE report_id = %s
            """
            rows = self.repo._query(sql, (report_id,))
            if rows:
                row = rows[0]
                try:
                    metrics_snapshot = json.loads(row["metrics_snapshot_json"]) if row.get("metrics_snapshot_json") else {}
                except Exception:
                    metrics_snapshot = {}
                return {
                    "report_id": row["report_id"],
                    "report_type": row["report_type"],
                    "report_date": row["report_date"].isoformat() if isinstance(row["report_date"], date) else str(row["report_date"]),
                    "model_name": row["model_name"],
                    "content": row["content_md"],
                    "metrics_snapshot": metrics_snapshot,
                    "create_time": row["create_time"].isoformat() if hasattr(row["create_time"], "isoformat") else str(row["create_time"])
                }

        return self._reports.get(
            report_id,
            {
                "report_id": report_id,
                "content": "报告不存在或服务重启后内存缓存已清空。",
            },
        )

    def _render_llm_markdown(
        self,
        report_date: date,
        report_type: str,
        model: str,
        daily: List[Dict],
        rankings: List[Dict],
        alerts: List[Dict],
        relation: Dict,
    ) -> str:
        if model == "rule-template":
            raise ValueError("OPENAI_MODEL_NAME is not configured")

        from openai import OpenAI

        prompt = self._build_prompt(report_date, report_type, daily, rankings, alerts, relation)
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "300"))
        max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "0"))
        client_kwargs = {"api_key": api_key, "timeout": timeout, "max_retries": max_retries}
        if base_url:
            client_kwargs["base_url"] = base_url
        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一名多智能体系统运维分析师，只输出 Markdown 格式的系统运行分析报告。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content
        if not content or not content.strip():
            raise ValueError("LLM returned empty report content")
        return content.strip()

    def _build_prompt(
        self,
        report_date: date,
        report_type: str,
        daily: List[Dict],
        rankings: List[Dict],
        alerts: List[Dict],
        relation: Dict,
    ) -> str:
        template = self._prompt_path.read_text(encoding="utf-8")
        metrics = {
            "report_date": report_date.isoformat(),
            "report_type": report_type,
            "daily": daily,
            "rankings": rankings,
        }
        return (
            template.replace("{{metrics_json}}", json.dumps(metrics, ensure_ascii=False, indent=2, default=str))
            .replace("{{alerts_json}}", json.dumps(alerts, ensure_ascii=False, indent=2, default=str))
            .replace("{{relation_json}}", json.dumps(relation, ensure_ascii=False, indent=2, default=str))
        )

    def _render_markdown(self, report_date: date, report_type: str, daily: List[Dict], rankings: List[Dict], alerts: List[Dict], relation: Dict) -> str:
        summary = daily[0] if daily else {}
        worst_agent = max(rankings, key=lambda item: item.get("avg_latency_ms", 0)) if rankings else {}
        best_agent = max(rankings, key=lambda item: item.get("success_rate", 0)) if rankings else {}
        edge_count = len(relation.get("links", []))
        return f"""# AgentScope {report_type} report - {report_date.isoformat()}

## 总体结论

当日任务量为 {summary.get("task_count", 0)}，成功率为 {summary.get("success_rate", 0)}，平均时延为 {summary.get("avg_latency_ms", 0)} ms，P95 时延为 {summary.get("p95_latency_ms", 0)} ms。

## 关键指标

- Token 总量：{summary.get("total_tokens", 0)}
- 预估成本：{summary.get("estimated_cost_usd", 0)} USD
- 告警数量：{len(alerts)}
- Agent 协作边数量：{edge_count}

## Agent 表现

- 成功率最高：{best_agent.get("agent_id", "N/A")}，成功率 {best_agent.get("success_rate", 0)}
- 平均时延最高：{worst_agent.get("agent_id", "N/A")}，平均时延 {worst_agent.get("avg_latency_ms", 0)} ms

## 风险提示

{self._render_alert_lines(alerts)}

## 优化建议

1. 优先排查高时延和高失败率 Agent 的输入规模、工具调用和重试逻辑。
2. 对 Token 超额任务增加 prompt 长度限制和摘要压缩步骤。
3. 对 Reviewer 退回链路设置最大重试次数，避免循环调用扩大成本。
"""

    @staticmethod
    def _render_alert_lines(alerts: List[Dict]) -> str:
        if not alerts:
            return "当前结构化指标中未发现历史告警。"
        return "\n".join(
            f"- {item.get('level')}：{item.get('agent_id')} 触发 {item.get('alert_type')}，当前值 {item.get('current_value')}，阈值 {item.get('threshold')}"
            for item in alerts
        )


"""
admin.py —— 运维诊断与管理调度中心 API 接口端点

主要接口：
  - GET /data-overview: 获取数据中心全局汇总指标。
  - GET /pipeline-status: 拓扑节点的数据更新状态监控。
  - POST /jobs/{job_code}/execute: 手动下发触发 DataX/Spark/AI 离线流程作业。
  - GET /quality/rules & /quality/issues: 管理和拉取数据质量检验规则与合规问题样本明细。
  - POST /system/run-check: 触发 SSH 诊断自检（巡检、Benchmark 等）。
  - GET /system/running-log: 实时流式读取当前诊断的控制台 Console 日志。
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel

from app.schemas.common import ok
from app.services.admin_service import AdminService

router = APIRouter()
service = AdminService()


class JobExecuteRequest(BaseModel):
    """
    批处理作业执行参数请求的 Pydantic 校验模型。
    """
    biz_date: date                   # 业务日期
    count: Optional[int] = None      # 离线模拟数据条数


@router.get("/data-overview")
def data_overview():
    """
    获取运维卡片大盘指标。
    """
    return ok(service.data_overview())


@router.get("/data-volume-trend")
def data_volume_trend():
    """
    拉取数据存储（Raw 与 Clean 占比）的对比变化趋势。
    """
    return ok(service.data_volume_trend())


@router.get("/dwd-events")
def dwd_events(
    limit: int = Query(default=50, ge=1, le=500),
    event_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
):
    """
    搜索并展示 DWD 清洗过的明细数据表。
    """
    return ok(service.dwd_events(limit, event_id, trace_id, agent_id, event_type, status))


@router.get("/dws-metrics")
def dws_metrics(
    limit: int = Query(default=50, ge=1, le=500),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    搜索并展示 DWS 离线日指标汇总数据表。
    """
    return ok(service.dws_metrics(limit, start_date, end_date))


@router.get("/pipeline-status")
def pipeline_status():
    """
    获取离线计算链路拓扑各环节的成功率与记录条数拓扑。
    """
    return ok(service.pipeline_status())


@router.get("/datasets")
def datasets():
    """
    展示数据集元数据分布。
    """
    return ok(service.datasets())


@router.get("/data-lineage")
def data_lineage():
    """
    获取数据血缘依赖拓扑数据。
    """
    return ok(service.data_lineage())


@router.get("/events")
def events(
    event_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    start_time: Optional[datetime] = Query(default=None),
    end_time: Optional[datetime] = Query(default=None),
):
    """
    搜索并展示系统日志明细事件列表。
    """
    return ok(service.events(event_id, trace_id, run_id, agent_id, event_type, status, start_time, end_time))


@router.get("/jobs")
def jobs():
    """
    获取系统支持的作业列表定义。
    """
    return ok(service.jobs())


@router.get("/job-runs")
def job_runs():
    """
    获取所有的历史批处理调度任务运行流水。
    """
    return ok(service.job_runs())


@router.post("/jobs/{job_code}/execute")
def execute_job(job_code: str, payload: Any = Body(...)):
    """
    手动触发具体的离线数据同步、清洗或 AI 报告生成作业。
    """
    try:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        if isinstance(payload, str):
            payload = json.loads(payload)
        request = JobExecuteRequest.model_validate(payload)
        return ok(service.execute_job(job_code, request.biz_date, request.count))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/job-runs/{run_id}/retry")
def retry_job_run(run_id: str):
    """
    重试运行指定的任务。
    """
    try:
        return ok(service.retry_job_run(run_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/job-runs/{run_id}/logs")
def job_run_logs(run_id: str):
    """
    检索特定调度任务执行时的标准控制台日志明细。
    """
    try:
        return ok(service.job_run_logs(run_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/quality/overview")
def quality_overview():
    """
    获取今日全局数据质量合格率统计。
    """
    return ok(service.quality_overview())


@router.get("/quality/issues")
def quality_issues():
    """
    检索获取具体的数据合规样本与规则拦截问题明细。
    """
    return ok(service.quality_issues())


@router.get("/audit-logs")
def audit_logs():
    """
    拉取平台审计操作日志列表。
    """
    return ok(service.audit_logs())


class QualityRuleCreate(BaseModel):
    """
    创建质量校验规则的请求校验模型。
    """
    rule_id: str
    rule_name: str
    rule_sql: str
    is_active: int = 1


class QualityRuleUpdate(BaseModel):
    """
    修改校验规则激活状态的校验模型。
    """
    is_active: int


@router.get("/quality/rules")
def quality_rules():
    """
    获取所有生效的数据质量检测规则。
    """
    return ok(service.get_quality_rules())


@router.post("/quality/rules")
def create_quality_rule(rule: QualityRuleCreate):
    """
    注册并创建一个新的数据质量校验 SQL 规则。
    """
    res = service.create_quality_rule(rule.rule_id, rule.rule_name, rule.rule_sql, rule.is_active)
    if not res:
        raise HTTPException(status_code=400, detail="Failed to create quality rule")
    return ok({"message": "Rule created successfully"})


@router.put("/quality/rules/{rule_id}")
def update_quality_rule(rule_id: str, rule: QualityRuleUpdate):
    """
    启用/关闭指定的数据质量 SQL 校验规则。
    """
    res = service.update_quality_rule(rule_id, rule.is_active)
    if not res:
        raise HTTPException(status_code=400, detail="Failed to update quality rule")
    return ok({"message": "Rule updated successfully"})


@router.post("/system/run-check")
def run_system_check(job_code: str = Query(...)):
    """
    下发自检巡检任务以异步诊断整个集群中组件的健康水平。
    """
    try:
        return ok(service.execute_system_check(job_code))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/system/check-runs")
def get_system_check_runs():
    """
    获取所有已完成或进行中的系统检查报告列表。
    """
    return ok(service.get_system_check_runs())


@router.get("/system/running-log")
def get_system_running_log():
    """
    获取正在运行中的自检命令实时控制台流式输出 stdout。
    """
    return ok(service.get_system_running_log())

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
    biz_date: date


@router.get("/data-overview")
def data_overview():
    return ok(service.data_overview())


@router.get("/data-volume-trend")
def data_volume_trend():
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
    return ok(service.dwd_events(limit, event_id, trace_id, agent_id, event_type, status))


@router.get("/dws-metrics")
def dws_metrics(
    limit: int = Query(default=50, ge=1, le=500),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    return ok(service.dws_metrics(limit, start_date, end_date))


@router.get("/pipeline-status")
def pipeline_status():
    return ok(service.pipeline_status())


@router.get("/datasets")
def datasets():
    return ok(service.datasets())


@router.get("/data-lineage")
def data_lineage():
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
    return ok(service.events(event_id, trace_id, run_id, agent_id, event_type, status, start_time, end_time))


@router.get("/jobs")
def jobs():
    return ok(service.jobs())


@router.get("/job-runs")
def job_runs():
    return ok(service.job_runs())


@router.post("/jobs/{job_code}/execute")
def execute_job(job_code: str, payload: Any = Body(...)):
    try:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        if isinstance(payload, str):
            payload = json.loads(payload)
        request = JobExecuteRequest.model_validate(payload)
        return ok(service.execute_job(job_code, request.biz_date))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/job-runs/{run_id}/retry")
def retry_job_run(run_id: str):
    try:
        return ok(service.retry_job_run(run_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/job-runs/{run_id}/logs")
def job_run_logs(run_id: str):
    try:
        return ok(service.job_run_logs(run_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/quality/overview")
def quality_overview():
    return ok(service.quality_overview())


@router.get("/quality/issues")
def quality_issues():
    return ok(service.quality_issues())


@router.get("/audit-logs")
def audit_logs():
    return ok(service.audit_logs())

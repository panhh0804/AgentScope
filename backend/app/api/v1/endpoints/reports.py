from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.schemas.common import ok
from app.services.report_service import ReportService

router = APIRouter()
service = ReportService()


class GenerateReportRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    report_date: date
    report_type: str = "daily"
    model_name: Optional[str] = None


@router.post("/generate")
def generate_report(payload: GenerateReportRequest):
    return ok(service.generate(payload.report_date, payload.report_type, payload.model_name))


@router.get("")
def list_reports():
    return ok(service.list_reports())


@router.get("/{report_id}")
def report_detail(report_id: str):
    return ok(service.get_report(report_id))

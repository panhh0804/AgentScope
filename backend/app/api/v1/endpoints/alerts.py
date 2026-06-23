from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.schemas.common import ok
from app.services.metric_service import MetricService

router = APIRouter()
service = MetricService()


@router.get("/history")
def history(date_value: date = Query(..., alias="date")):
    return ok(service.history_alerts(date_value))


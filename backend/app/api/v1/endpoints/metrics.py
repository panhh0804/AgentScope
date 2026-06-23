from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.schemas.common import ok
from app.services.metric_service import MetricService

router = APIRouter()
service = MetricService()


@router.get("/daily")
def daily(start_date: date = Query(...), end_date: date = Query(...)):
    return ok(service.daily_metrics(start_date, end_date))


@router.get("/hourly")
def hourly(date_value: date = Query(..., alias="date")):
    return ok(service.hourly_metrics(date_value))


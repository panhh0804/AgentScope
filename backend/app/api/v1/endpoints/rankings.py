from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.schemas.common import ok
from app.services.metric_service import MetricService

router = APIRouter()
service = MetricService()


@router.get("/agents")
def agent_rankings(date_value: date = Query(..., alias="date")):
    return ok(service.agent_rankings(date_value))


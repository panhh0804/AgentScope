from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.schemas.common import ok
from app.services.statistics_service import StatisticsService

router = APIRouter()
service = StatisticsService()


@router.get("/trend")
def trend():
    return ok(service.trend())


@router.get("/errors")
def errors(
    limit: int = Query(10, ge=1, le=50),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    return ok(service.errors(limit, start_date, end_date))


@router.get("/agent-stats")
def agent_stats():
    return ok(service.agent_stats())

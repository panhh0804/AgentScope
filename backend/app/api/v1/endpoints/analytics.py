from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas.common import ok
from app.services.statistics_service import StatisticsService

router = APIRouter()
service = StatisticsService()


@router.get("/trend")
def trend():
    return ok(service.trend())


@router.get("/errors")
def errors(limit: int = Query(10, ge=1, le=50)):
    return ok(service.errors(limit))


@router.get("/agent-stats")
def agent_stats():
    return ok(service.agent_stats())

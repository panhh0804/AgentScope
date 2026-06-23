from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas.common import ok
from app.services.realtime_service import RealtimeService

router = APIRouter()
service = RealtimeService()


@router.get("/overview")
def overview():
    return ok(service.overview())


@router.get("/trend")
def trend(minutes: int = Query(default=60, ge=1, le=240)):
    return ok(service.trend(minutes))


@router.get("/agents")
def agents():
    return ok(service.agents())


@router.get("/alerts")
def realtime_alerts():
    return ok(service.alerts())


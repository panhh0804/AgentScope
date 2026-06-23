from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import alerts, graph, metrics, rankings, realtime, reports

api_router = APIRouter()
api_router.include_router(realtime.router, prefix="/realtime", tags=["realtime"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(rankings.router, prefix="/rankings", tags=["rankings"])
api_router.include_router(graph.router, prefix="/graph", tags=["graph"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])


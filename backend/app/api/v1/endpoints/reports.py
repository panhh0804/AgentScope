"""
reports.py —— AI 运维诊断报告 API 接口端点

主要接口：
  - POST /generate: 接收特定日期、类型与模型名称，发起并生成 AI 诊断报告。
  - GET /: 获取系统历史生成的诊断报告头信息列表。
  - GET /{report_id}: 获取特定诊断报告的详细正文与指标快照。
"""

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
    """
    诊断报告生成请求的 Pydantic 校验模型。
    """
    # 规避 protected_namespaces 警告
    model_config = ConfigDict(protected_namespaces=())

    report_date: date                # 业务日期
    report_type: str = "daily"       # 报告类型（默认 daily）
    model_name: Optional[str] = None # 大模型名称


@router.post("/generate")
def generate_report(payload: GenerateReportRequest):
    """
    手动/调度触发大模型生成 AI 系统运维诊断报告。

    Args:
        payload (GenerateReportRequest): 请求 JSON Body 体

    Returns:
        JSON: 统一协议包裹的生成结果详情
    """
    return ok(service.generate(payload.report_date, payload.report_type, payload.model_name))


@router.get("")
def list_reports():
    """
    拉取诊断报告历史记录列表（简略摘要版）。

    Returns:
        JSON: 统一协议包裹的报告元数据列表
    """
    return ok(service.list_reports())


@router.get("/{report_id}")
def report_detail(report_id: str):
    """
    获取单个报告的正文详情。

    Args:
        report_id (str): 报告唯一哈希

    Returns:
        JSON: 统一协议包裹的详细报告正文与关联数据快照
    """
    return ok(service.get_report(report_id))

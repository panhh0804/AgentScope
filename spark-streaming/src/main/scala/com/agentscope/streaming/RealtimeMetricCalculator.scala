package com.agentscope.streaming

case class RealtimeOverview(
  runningTasks: Long,
  activeAgents: Long,
  eventsPerMinute: Long,
  successCount: Long,
  failedCount: Long,
  errorRate: Double,
  avgLatencyMs: Double,
  tokenTotal: Long,
  estimatedCost: Double,
  retryTasks: Long
)

object RealtimeMetricCalculator {
  def overview(events: Seq[AgentEvent]): RealtimeOverview = {
    val total = events.size.toLong
    val failed = events.count(e => e.status == "failed" || e.event_type == "agent_failed").toLong
    val success = events.count(_.status == "success").toLong
    val latencyEvents = events.filter(_.latency_ms > 0)
    val avgLatency = if (latencyEvents.isEmpty) 0.0 else latencyEvents.map(_.latency_ms).sum.toDouble / latencyEvents.size
    RealtimeOverview(
      runningTasks = events.filter(_.status == "running").map(_.trace_id).distinct.size,
      activeAgents = events.map(_.agent_id).distinct.size,
      eventsPerMinute = total,
      successCount = success,
      failedCount = failed,
      errorRate = if (total == 0) 0.0 else failed.toDouble / total,
      avgLatencyMs = avgLatency,
      tokenTotal = events.map(_.total_tokens).sum,
      estimatedCost = events.map(_.cost_usd).sum,
      retryTasks = events.filter(_.retry_count >= 3).map(_.run_id).distinct.size
    )
  }

  def agentStatus(events: Seq[AgentEvent]): Seq[Map[String, Any]] = {
    events
      .groupBy(_.agent_id)
      .map { case (agentId, rows) =>
        val completed = rows.count(_.status == "success")
        val failed = rows.count(_.status == "failed")
        val total = math.max(completed + failed, 1)
        Map(
          "agent_id" -> agentId,
          "agent_role" -> rows.head.agent_role,
          "status" -> rows.last.status,
          "success_rate" -> completed.toDouble / total,
          "avg_latency_ms" -> average(rows.map(_.latency_ms).filter(_ > 0)),
          "token_total" -> rows.map(_.total_tokens).sum,
          "retry_count" -> rows.map(_.retry_count).max,
          "last_event_time" -> rows.last.timestamp
        )
      }
      .toSeq
  }

  private def average(values: Seq[Long]): Double = {
    if (values.isEmpty) 0.0 else values.sum.toDouble / values.size
  }
}


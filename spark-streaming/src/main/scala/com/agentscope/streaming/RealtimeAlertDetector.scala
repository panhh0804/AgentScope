package com.agentscope.streaming

import java.time.Instant

case class RealtimeAlert(
  alert_id: String,
  alert_type: String,
  level: String,
  agent_id: String,
  current_value: Double,
  threshold: Double,
  source: String,
  status: String,
  create_time: String
)

object RealtimeAlertDetector {
  def detect(events: Seq[AgentEvent], overview: RealtimeOverview): Seq[RealtimeAlert] = {
    val now = Instant.now().toString
    val alerts = scala.collection.mutable.ArrayBuffer.empty[RealtimeAlert]

    if (overview.eventsPerMinute >= 5 && overview.errorRate > 0.20) {
      alerts += alert("high_error_rate", "warning", "system", overview.errorRate, 0.20, now)
    }

    events.filter(_.latency_ms > 10000).foreach { event =>
      alerts += alert("high_latency", "warning", event.agent_id, event.latency_ms.toDouble, 10000, now)
    }

    events.filter(_.retry_count >= 3).foreach { event =>
      alerts += alert("frequent_retry", "critical", event.agent_id, event.retry_count.toDouble, 3, now)
    }

    events.filter(_.total_tokens > 20000).foreach { event =>
      alerts += alert("token_overuse", "warning", event.agent_id, event.total_tokens.toDouble, 20000, now)
    }

    alerts
  }

  private def alert(alertType: String, level: String, agentId: String, current: Double, threshold: Double, now: String): RealtimeAlert = {
    RealtimeAlert(
      alert_id = s"${alertType}_${agentId}_${System.currentTimeMillis()}",
      alert_type = alertType,
      level = level,
      agent_id = agentId,
      current_value = current,
      threshold = threshold,
      source = "streaming",
      status = "open",
      create_time = now
    )
  }
}


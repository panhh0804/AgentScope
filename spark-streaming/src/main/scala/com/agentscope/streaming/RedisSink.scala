package com.agentscope.streaming

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import redis.clients.jedis.Jedis

object RedisSink {
  private val mapper = new ObjectMapper()
  mapper.registerModule(DefaultScalaModule)

  def write(host: String, port: Int, overview: RealtimeOverview, agents: Seq[Map[String, Any]], alerts: Seq[RealtimeAlert]): Unit = {
    val jedis = new Jedis(host, port)
    try {
      jedis.set("agentscope:realtime:overview", mapper.writeValueAsString(overviewToMap(overview, alerts.size)))
      jedis.set("agentscope:realtime:agents", mapper.writeValueAsString(agents))
      if (alerts.nonEmpty) {
        jedis.set("agentscope:realtime:alerts", mapper.writeValueAsString(alerts))
      }
      jedis.expire("agentscope:realtime:overview", 120)
      jedis.expire("agentscope:realtime:agents", 120)
      jedis.expire("agentscope:realtime:alerts", 600)
    } finally {
      jedis.close()
    }
  }

  private def overviewToMap(overview: RealtimeOverview, alertCount: Int): Map[String, Any] = {
    Map(
      "running_tasks" -> overview.runningTasks,
      "active_agents" -> overview.activeAgents,
      "events_per_minute" -> overview.eventsPerMinute,
      "success_count" -> overview.successCount,
      "failed_count" -> overview.failedCount,
      "error_rate" -> overview.errorRate,
      "avg_latency_ms" -> overview.avgLatencyMs,
      "token_total_5m" -> overview.tokenTotal,
      "estimated_cost_5m" -> overview.estimatedCost,
      "retry_tasks" -> overview.retryTasks,
      "open_alerts" -> alertCount
    )
  }
}

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
      // 1. Retrieve existing alerts from Redis to keep history sliding window
      val existingAlertsJson = jedis.get("agentscope:realtime:alerts")
      val existingAlerts = if (existingAlertsJson != null && existingAlertsJson.trim.nonEmpty) {
        try {
          val typeFactory = mapper.getTypeFactory
          val listType = typeFactory.constructCollectionType(classOf[java.util.List[RealtimeAlert]], classOf[RealtimeAlert])
          val list: java.util.List[RealtimeAlert] = mapper.readValue(existingAlertsJson, listType)
          import scala.collection.JavaConverters._
          list.asScala.toSeq
        } catch {
          case _: Exception => Seq.empty[RealtimeAlert]
        }
      } else {
        Seq.empty[RealtimeAlert]
      }

      // Filter out alerts older than 10 minutes (600 seconds)
      val nowInstant = java.time.Instant.now()
      val activeExisting = existingAlerts.filter { a =>
        try {
          val alertTime = java.time.Instant.parse(a.create_time)
          java.time.Duration.between(alertTime, nowInstant).getSeconds < 600
        } catch {
          case _: Exception => true
        }
      }

      // 2. Filter new alerts using Redis setnx (Deduplication)
      val newUniqueAlerts = alerts.filter { alert =>
        val redisKey = s"agentscope:alert:${alert.alert_id}"
        val isNew = jedis.setnx(redisKey, "1") == 1
        if (isNew) {
          jedis.expire(redisKey, 300) // set TTL of 5 minutes for deduplication
          true
        } else {
          false
        }
      }

      // Combine and deduplicate by alert_id, keep newest first, cap at 50 records
      val combinedAlerts = (activeExisting ++ newUniqueAlerts).groupBy(_.alert_id).map(_._2.head).toSeq
        .sortBy(_.create_time)(Ordering[String].reverse)
        .take(50)

      jedis.set("agentscope:realtime:overview", mapper.writeValueAsString(overviewToMap(overview, combinedAlerts.size)))
      jedis.set("agentscope:realtime:agents", mapper.writeValueAsString(agents))
      
      if (combinedAlerts.nonEmpty) {
        jedis.set("agentscope:realtime:alerts", mapper.writeValueAsString(combinedAlerts))
        jedis.expire("agentscope:realtime:alerts", 600)
      } else {
        jedis.del("agentscope:realtime:alerts")
      }
      
      jedis.expire("agentscope:realtime:overview", 120)
      jedis.expire("agentscope:realtime:agents", 120)
    } finally {
      jedis.close()
    }
  }

  private def overviewToMap(overview: RealtimeOverview, alertCount: Int): Map[String, Any] = {
    val total = math.max(overview.successCount + overview.failedCount, 1L)
    Map(
      "running_tasks" -> overview.runningTasks,
      "active_agents" -> overview.activeAgents,
      "events_per_minute" -> overview.eventsPerMinute,
      "success_count" -> overview.successCount,
      "failed_count" -> overview.failedCount,
      "success_rate" -> overview.successCount.toDouble / total.toDouble,
      "error_rate" -> overview.errorRate,
      "avg_latency_ms" -> overview.avgLatencyMs,
      "token_total_5m" -> overview.tokenTotal,
      "estimated_cost_5m" -> overview.estimatedCost,
      "retry_tasks" -> overview.retryTasks,
      "open_alerts" -> alertCount
    )
  }
}

package com.agentscope.batch

import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.functions._

object RelationGraphJob extends SparkJobSupport {
  def main(args: Array[String]): Unit = {
    val conf = BatchArgs.parse(args)
    val session = spark("AgentScopeRelationGraphJob")

    val events = session.read.parquet(conf.input)

    // 1. Compute node metrics at run level first, then aggregate to agent level
    // - run_latency: max latency_ms of the run
    // - run_failed_flag: 1 if the run contains 'agent_failed' or status is 'failed'
    val runNodeDf = events
      .groupBy("metric_date", "agent_id", "agent_role", "run_id")
      .agg(
        max("latency_ms").as("run_latency"),
        max(when(col("event_type") === "agent_failed" || col("status") === "failed", 1).otherwise(0)).as("run_failed_flag")
      )

    val nodes = runNodeDf
      .groupBy("metric_date", "agent_id", "agent_role")
      .agg(
        count("run_id").as("value"),
        sum("run_failed_flag").as("failed_count"),
        avg("run_latency").as("avg_latency_ms")
      )
      .select(col("metric_date"), col("agent_id").as("id"), col("agent_role").as("name"), col("value"), col("failed_count"), col("avg_latency_ms"))

    // 2. Compute edge metrics grouped by parent/child run to de-duplicate multiple events per call
    val parentEvents = events.filter(col("parent_agent_id").isNotNull)
    
    val runEdgeDf = parentEvents
      .groupBy("metric_date", "parent_agent_id", "agent_id", "parent_run_id", "run_id")
      .agg(
        max("latency_ms").as("run_latency"),
        max(when(col("event_type") === "agent_failed" || col("status") === "failed", 1).otherwise(0)).as("run_failed_flag"),
        sum(when(col("event_type") === "llm_response", col("total_tokens")).otherwise(0)).as("run_tokens")
      )

    val edges = runEdgeDf
      .groupBy("metric_date", "parent_agent_id", "agent_id")
      .agg(
        count("run_id").as("call_count"),
        avg("run_latency").as("avg_latency_ms"),
        sum("run_failed_flag").as("failed_count"),
        sum("run_tokens").as("total_tokens")
      )
      .select(col("metric_date"), col("parent_agent_id").as("source"), col("agent_id").as("target"), col("call_count"), col("avg_latency_ms"), col("failed_count"), col("total_tokens"))

    nodes.write.mode(SaveMode.Overwrite).json(s"${conf.metricBase}/agent_relation_nodes/dt=${conf.date}")
    edges.write.mode(SaveMode.Overwrite).json(s"${conf.metricBase}/agent_relation_edges/dt=${conf.date}")
    writeJdbc(nodes, "agent_relation_nodes", conf)
    writeJdbc(edges, "agent_relation_edges", conf)
    session.stop()
  }
}


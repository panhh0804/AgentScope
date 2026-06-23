package com.agentscope.batch

import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.functions._

object RelationGraphJob extends SparkJobSupport {
  def main(args: Array[String]): Unit = {
    val conf = BatchArgs.parse(args)
    val session = spark("AgentScopeRelationGraphJob")

    val events = session.read.parquet(conf.input)

    val nodes = events
      .groupBy("metric_date", "agent_id", "agent_role")
      .agg(
        count(lit(1)).as("value"),
        sum(when(col("status") === "failed", 1).otherwise(0)).as("failed_count"),
        avg(when(col("latency_ms") > 0, col("latency_ms"))).as("avg_latency_ms")
      )
      .select(col("metric_date"), col("agent_id").as("id"), col("agent_role").as("name"), col("value"), col("failed_count"), col("avg_latency_ms"))

    val edges = events
      .filter(col("parent_agent_id").isNotNull)
      .groupBy("metric_date", "parent_agent_id", "agent_id")
      .agg(
        count(lit(1)).as("call_count"),
        avg(when(col("latency_ms") > 0, col("latency_ms"))).as("avg_latency_ms"),
        sum(when(col("status") === "failed", 1).otherwise(0)).as("failed_count"),
        sum("total_tokens").as("total_tokens")
      )
      .select(col("metric_date"), col("parent_agent_id").as("source"), col("agent_id").as("target"), col("call_count"), col("avg_latency_ms"), col("failed_count"), col("total_tokens"))

    nodes.write.mode(SaveMode.Overwrite).json(s"${conf.metricBase}/agent_relation_nodes/dt=${conf.date}")
    edges.write.mode(SaveMode.Overwrite).json(s"${conf.metricBase}/agent_relation_edges/dt=${conf.date}")
    writeJdbc(nodes, "agent_relation_nodes", conf)
    writeJdbc(edges, "agent_relation_edges", conf)
    session.stop()
  }
}


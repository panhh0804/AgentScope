package com.agentscope.batch

import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.functions._

object DailyMetricJob extends SparkJobSupport {
  def main(args: Array[String]): Unit = {
    val conf = BatchArgs.parse(args)
    val session = spark("AgentScopeDailyMetricJob")

    val events = session.read.parquet(conf.input)

    // 1. Group by trace_id (representing a task run) to compute run-level metrics (Run-level aggregation)
    // - tokens/cost: only aggregated from 'llm_response' events
    // - max_latency: maximum latency of the run
    val traceDf = events
      .groupBy("metric_date", "trace_id")
      .agg(
        max(when(col("status") === "success", 1).otherwise(0)).as("has_success"),
        max(when(col("status") === "failed" || col("event_type") === "agent_failed", 1).otherwise(0)).as("has_failed"),
        max("latency_ms").as("max_latency"),
        sum(when(col("event_type") === "llm_response", col("total_tokens")).otherwise(0)).as("tokens"),
        sum(when(col("event_type") === "llm_response", col("cost_usd")).otherwise(0.0)).as("cost")
      )

    // 2. Group by metric_date to compute daily overall metrics (System/Pipeline level aggregation)
    val df = traceDf
      .groupBy("metric_date")
      .agg(
        count("trace_id").as("task_count"),
        sum("has_success").as("success_count"),
        sum(when(col("has_success") === 0 && col("has_failed") === 1, 1).otherwise(0)).as("failed_count"),
        avg("max_latency").as("avg_latency_ms"),
        expr("percentile_approx(max_latency, 0.95)").as("p95_latency_ms"),
        sum("tokens").as("total_tokens"),
        sum("cost").as("estimated_cost_usd")
      )
      .withColumn("success_rate", when(col("task_count") === 0, lit(0)).otherwise(col("success_count") / col("task_count")))
      .select("metric_date", "task_count", "success_count", "failed_count", "success_rate", "avg_latency_ms", "p95_latency_ms", "total_tokens", "estimated_cost_usd")

    df.write.mode(SaveMode.Overwrite).json(s"${conf.metricBase}/daily_metrics/dt=${conf.date}")
    writeJdbc(df, "daily_metrics", conf)
    session.stop()
  }
}


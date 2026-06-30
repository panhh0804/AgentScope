package com.agentscope.batch

import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.functions._

object DailyMetricJob extends SparkJobSupport {
  def main(args: Array[String]): Unit = {
    val conf = BatchArgs.parse(args)
    val session = spark("AgentScopeDailyMetricJob")

    val events = session.read.parquet(conf.input)
    val traceDf = events
      .groupBy("metric_date", "trace_id")
      .agg(
        max(when(col("status") === "success", 1).otherwise(0)).as("has_success"),
        max(when(col("status") === "failed" || col("event_type") === "agent_failed", 1).otherwise(0)).as("has_failed"),
        avg(when(col("latency_ms") > 0, col("latency_ms"))).as("avg_latency"),
        sum("total_tokens").as("tokens"),
        sum("cost_usd").as("cost")
      )

    val df = traceDf
      .groupBy("metric_date")
      .agg(
        count("trace_id").as("task_count"),
        sum("has_success").as("success_count"),
        sum(when(col("has_success") === 0 && col("has_failed") === 1, 1).otherwise(0)).as("failed_count"),
        avg("avg_latency").as("avg_latency_ms"),
        expr("percentile_approx(avg_latency, 0.95)").as("p95_latency_ms"),
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


package com.agentscope.batch

import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.functions._

object DailyMetricJob extends SparkJobSupport {
  def main(args: Array[String]): Unit = {
    val conf = BatchArgs.parse(args)
    val session = spark("AgentScopeDailyMetricJob")

    val events = session.read.parquet(conf.input)
    val df = events
      .groupBy("metric_date")
      .agg(
        countDistinct("trace_id").as("task_count"),
        countDistinct(when(col("status") === "success", col("trace_id"))).as("success_count"),
        countDistinct(when(col("status") === "failed" || col("event_type") === "agent_failed", col("trace_id"))).as("failed_count"),
        avg(when(col("latency_ms") > 0, col("latency_ms"))).as("avg_latency_ms"),
        expr("percentile_approx(latency_ms, 0.95)").as("p95_latency_ms"),
        sum("total_tokens").as("total_tokens"),
        sum("cost_usd").as("estimated_cost_usd")
      )
      .withColumn("success_rate", when(col("task_count") === 0, lit(0)).otherwise(col("success_count") / col("task_count")))
      .select("metric_date", "task_count", "success_count", "failed_count", "success_rate", "avg_latency_ms", "p95_latency_ms", "total_tokens", "estimated_cost_usd")

    df.write.mode(SaveMode.Overwrite).json(s"${conf.metricBase}/daily_metrics/dt=${conf.date}")
    writeJdbc(df, "daily_metrics", conf)
    session.stop()
  }
}


package com.agentscope.batch

import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.functions._

object AgentRankingJob extends SparkJobSupport {
  def main(args: Array[String]): Unit = {
    val conf = BatchArgs.parse(args)
    val session = spark("AgentScopeAgentRankingJob")

    val events = session.read.parquet(conf.input)
    val df = events
      .groupBy("metric_date", "agent_id", "agent_role")
      .agg(
        count(lit(1)).as("execution_count"),
        avg(when(col("status") === "success", 1).otherwise(0)).as("success_rate"),
        avg(when(col("latency_ms") > 0, col("latency_ms"))).as("avg_latency_ms"),
        expr("percentile_approx(latency_ms, 0.95)").as("p95_latency_ms"),
        sum("total_tokens").as("total_tokens"),
        sum("cost_usd").as("estimated_cost_usd")
      )

    df.write.mode(SaveMode.Overwrite).json(s"${conf.metricBase}/agent_rankings/dt=${conf.date}")
    writeJdbc(df, "agent_rankings", conf)
    session.stop()
  }
}


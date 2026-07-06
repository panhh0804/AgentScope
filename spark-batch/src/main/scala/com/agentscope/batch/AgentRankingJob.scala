package com.agentscope.batch

import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.functions._

object AgentRankingJob extends SparkJobSupport {
  def main(args: Array[String]): Unit = {
    val conf = BatchArgs.parse(args)
    val session = spark("AgentScopeAgentRankingJob")

    val events = session.read.parquet(conf.input)

    // 1. Group by run_id to calculate run-level metrics first (Run-level aggregation to prevent multiple event inflation)
    // - latency: maximum latency_ms in the run
    // - success: 1 if run contains 'agent_complete' or status is 'success'
    // - tokens/cost: only aggregated from 'llm_response' events
    val runDf = events
      .groupBy("metric_date", "agent_id", "agent_role", "run_id")
      .agg(
        max("latency_ms").as("run_latency"),
        max(when(col("event_type") === "agent_complete" || col("status") === "success", 1).otherwise(0)).as("run_success_flag"),
        sum(when(col("event_type") === "llm_response", col("total_tokens")).otherwise(0)).as("run_tokens"),
        sum(when(col("event_type") === "llm_response", col("cost_usd")).otherwise(0.0)).as("run_cost")
      )

    // 2. Group by agent to calculate agent-level metrics (Agent-level aggregation)
    // - execution_count: unique run count (distinct run_ids)
    // - success_rate: average run-level success flag
    val df = runDf
      .groupBy("metric_date", "agent_id", "agent_role")
      .agg(
        count("run_id").as("execution_count"),
        avg("run_success_flag").as("success_rate"),
        avg("run_latency").as("avg_latency_ms"),
        expr("percentile_approx(run_latency, 0.95)").as("p95_latency_ms"),
        sum("run_tokens").as("total_tokens"),
        sum("run_cost").as("estimated_cost_usd")
      )

    df.write.mode(SaveMode.Overwrite).json(s"${conf.metricBase}/agent_rankings/dt=${conf.date}")
    writeJdbc(df, "agent_rankings", conf)
    session.stop()
  }
}


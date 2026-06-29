package com.agentscope.batch

import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.functions._

object CleanAgentEventJob extends SparkJobSupport {
  def main(args: Array[String]): Unit = {
    val conf = BatchArgs.parse(args)
    val session = spark("AgentScopeCleanAgentEventJob")
    import session.implicits._

    val raw = session.read
      .option("sep", "\t")
      .option("inferSchema", "true")
      .csv(conf.input)

    val clean = raw.toDF(
      "id", "event_id", "trace_id", "run_id", "parent_run_id", "agent_id",
      "parent_agent_id", "agent_role", "event_type", "status", "event_time",
      "latency_ms", "prompt_tokens", "completion_tokens", "total_tokens",
      "cost_usd", "model_name", "tool_name", "error_type", "retry_count",
      "metadata_json", "create_time"
    )
      .filter($"event_id".isNotNull && $"trace_id".isNotNull && $"run_id".isNotNull)
      .filter($"event_type".isin("agent_start", "agent_complete", "agent_failed", "llm_request", "llm_response", "tool_call", "tool_result", "retry", "alert"))
      .withColumn("latency_ms", when($"latency_ms" < 0, 0).otherwise($"latency_ms"))
      .withColumn("total_tokens", when($"total_tokens" < 0, 0).otherwise($"total_tokens"))
      .withColumn("metric_date", to_date($"event_time"))
      .dropDuplicates("event_id")

    clean.write.mode(SaveMode.Overwrite).parquet(conf.output)
    session.stop()
  }
}


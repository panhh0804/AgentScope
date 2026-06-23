package com.agentscope.batch

import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.functions._

object HistoricalAlertJob extends SparkJobSupport {
  def main(args: Array[String]): Unit = {
    val conf = BatchArgs.parse(args)
    val session = spark("AgentScopeHistoricalAlertJob")

    val events = session.read.parquet(conf.input)

    val highLatency = events
      .filter(col("latency_ms") > 10000)
      .select(
        concat(lit("hist_latency_"), col("event_id")).as("alert_id"),
        col("metric_date"),
        lit("high_latency").as("alert_type"),
        lit("warning").as("level"),
        col("agent_id"),
        col("latency_ms").cast("decimal(14,4)").as("current_value"),
        lit(10000).cast("decimal(14,4)").as("threshold_value"),
        lit("batch").as("source"),
        lit("open").as("status")
      )

    val retry = events
      .filter(col("retry_count") >= 3)
      .select(
        concat(lit("hist_retry_"), col("event_id")).as("alert_id"),
        col("metric_date"),
        lit("frequent_retry").as("alert_type"),
        lit("critical").as("level"),
        col("agent_id"),
        col("retry_count").cast("decimal(14,4)").as("current_value"),
        lit(3).cast("decimal(14,4)").as("threshold_value"),
        lit("batch").as("source"),
        lit("open").as("status")
      )

    val token = events
      .filter(col("total_tokens") > 20000)
      .select(
        concat(lit("hist_token_"), col("event_id")).as("alert_id"),
        col("metric_date"),
        lit("token_overuse").as("alert_type"),
        lit("warning").as("level"),
        col("agent_id"),
        col("total_tokens").cast("decimal(14,4)").as("current_value"),
        lit(20000).cast("decimal(14,4)").as("threshold_value"),
        lit("batch").as("source"),
        lit("open").as("status")
      )

    val df = highLatency.unionByName(retry).unionByName(token)
    df.write.mode(SaveMode.Overwrite).json(s"${conf.metricBase}/historical_alerts/dt=${conf.date}")
    writeJdbc(df, "historical_alerts", conf)
    session.stop()
  }
}


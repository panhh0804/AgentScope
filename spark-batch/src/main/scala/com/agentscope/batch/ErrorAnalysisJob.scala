package com.agentscope.batch

import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.functions._

object ErrorAnalysisJob extends SparkJobSupport {
  def main(args: Array[String]): Unit = {
    val conf = BatchArgs.parse(args)
    val session = spark("AgentScopeErrorAnalysisJob")

    val events = session.read.parquet(conf.input)
    val errors = events
      .filter(col("error_type").isNotNull || col("status") === "failed")
      .withColumn("error_type", coalesce(col("error_type"), lit("unknown")))

    val total = math.max(errors.count(), 1L).toDouble
    val df = errors
      .groupBy("metric_date", "error_type")
      .agg(count(lit(1)).as("error_count"))
      .withColumn("percentage", col("error_count") / lit(total))

    df.write.mode(SaveMode.Overwrite).json(s"${conf.metricBase}/error_distribution/dt=${conf.date}")
    writeJdbc(df, "error_distribution", conf)
    session.stop()
  }
}


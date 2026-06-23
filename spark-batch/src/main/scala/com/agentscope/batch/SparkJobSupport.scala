package com.agentscope.batch

import java.util.Properties

import org.apache.spark.sql.{DataFrame, SaveMode, SparkSession}

trait SparkJobSupport {
  def spark(appName: String): SparkSession = {
    SparkSession.builder().appName(appName).getOrCreate()
  }

  def jdbcProps(args: BatchArgs): Properties = {
    val props = new Properties()
    props.setProperty("user", args.jdbcUser)
    props.setProperty("password", args.jdbcPassword)
    props.setProperty("driver", "com.mysql.jdbc.Driver")
    props
  }

  def writeJdbc(df: DataFrame, table: String, args: BatchArgs): Unit = {
    if (args.jdbcUrl.nonEmpty && args.jdbcUser.nonEmpty) {
      df.write.mode(SaveMode.Append).jdbc(args.jdbcUrl, table, jdbcProps(args))
    }
  }
}


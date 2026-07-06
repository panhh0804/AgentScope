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
      if (args.date.nonEmpty) {
        val conn = java.sql.DriverManager.getConnection(args.jdbcUrl, args.jdbcUser, args.jdbcPassword)
        try {
          val stmt = conn.createStatement()
          val deleteSql = s"DELETE FROM $table WHERE metric_date = '${args.date}'"
          println(s"Executing idempotent pre-action: $deleteSql")
          stmt.executeUpdate(deleteSql)
        } catch {
          case e: Exception => println(s"Warning: Failed to execute delete pre-action for $table: ${e.getMessage}")
        } finally {
          conn.close()
        }
      }
      df.write.mode(SaveMode.Append).jdbc(args.jdbcUrl, table, jdbcProps(args))
    }
  }
}


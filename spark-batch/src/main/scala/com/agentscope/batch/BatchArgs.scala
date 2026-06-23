package com.agentscope.batch

case class BatchArgs(
  input: String = "",
  output: String = "",
  metricBase: String = "/agentscope/metric",
  date: String = "",
  jdbcUrl: String = "",
  jdbcUser: String = "",
  jdbcPassword: String = ""
)

object BatchArgs {
  def parse(args: Array[String]): BatchArgs = {
    val map = args.sliding(2, 2).collect { case Array(k, v) => k -> v }.toMap
    BatchArgs(
      input = map.getOrElse("--input", ""),
      output = map.getOrElse("--output", ""),
      metricBase = map.getOrElse("--metric-base", "/agentscope/metric"),
      date = map.getOrElse("--date", ""),
      jdbcUrl = map.getOrElse("--jdbc-url", ""),
      jdbcUser = map.getOrElse("--jdbc-user", ""),
      jdbcPassword = map.getOrElse("--jdbc-password", "")
    )
  }
}


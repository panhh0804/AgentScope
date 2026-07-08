package com.agentscope.batch

import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.functions._
import scala.util.Try

object CleanAgentEventJob extends SparkJobSupport {
  private val metadataSensitiveFilter =
    "lower(coalesce(metadata_json, '')) NOT LIKE '%sk-%' AND " +
      "lower(coalesce(metadata_json, '')) NOT LIKE '%key%' AND " +
      "lower(coalesce(metadata_json, '')) NOT LIKE '%api_key%'"

  private val sqlKeywords = Set(
    "and", "or", "not", "is", "null", "like", "in", "between", "true", "false",
    "case", "when", "then", "else", "end", "as", "exists"
  )

  private val sqlFunctions = Set(
    "lower", "upper", "coalesce", "trim", "ltrim", "rtrim", "substring", "substr",
    "length", "concat", "cast", "date", "to_date", "regexp_replace", "split",
    "nvl", "ifnull", "greatest", "least"
  )

  private def normalizeQualityRule(rule: String): String = {
    val trimmed = Option(rule).getOrElse("").trim
    if (trimmed.toLowerCase.contains("content")) {
      metadataSensitiveFilter
    } else {
      trimmed
    }
  }

  def main(args: Array[String]): Unit = {
    val conf = BatchArgs.parse(args)
    val session = spark("AgentScopeCleanAgentEventJob")
    import session.implicits._

    val raw = session.read
      .option("sep", "\t")
      .option("inferSchema", "true")
      .csv(conf.input)

    val df = raw.toDF(
      "id", "event_id", "trace_id", "run_id", "parent_run_id", "agent_id",
      "parent_agent_id", "agent_role", "event_type", "status", "event_time",
      "latency_ms", "prompt_tokens", "completion_tokens", "total_tokens",
      "cost_usd", "model_name", "tool_name", "error_type", "retry_count",
      "metadata_json", "create_time"
    )
    val schemaColumns = df.columns.map(_.toLowerCase).toSet

    // 1. Metadata-driven Quality Control: Load active quality rules from MySQL
    val rules = try {
      if (conf.jdbcUrl.nonEmpty) {
        val rulesDf = session.read.jdbc(conf.jdbcUrl, "quality_rules_metadata", jdbcProps(conf))
        rulesDf.filter("is_active = 1")
          .select("rule_sql")
          .collect()
          .map(row => normalizeQualityRule(row.getString(0)))
          .filter(_.nonEmpty)
      } else {
        Array.empty[String]
      }
    } catch {
      case e: Exception =>
        println(s"Warning: Failed to load quality rules from MySQL, falling back to default rules: ${e.getMessage}")
        Array.empty[String]
    }

    val activeRules = if (rules.nonEmpty) {
      rules.filter { rule =>
        val compatible = isRuleCompatible(rule, schemaColumns)
        if (compatible) {
          try {
            df.filter(rule)
            true
          } catch {
            case e: Exception =>
              println(s"Warning: Skipping syntax-invalid quality rule: ${rule}. Error: ${e.getMessage}")
              false
          }
        } else {
          println(s"Warning: Skipping incompatible quality rule: ${rule}")
          false
        }
      }
    } else {
      // Default fallback rules matching the original hardcoded cleaning logic
      Array(
        "event_id IS NOT NULL AND event_id <> '' AND trace_id IS NOT NULL AND trace_id <> '' AND run_id IS NOT NULL AND run_id <> ''",
        "event_type IN ('agent_start', 'agent_complete', 'agent_failed', 'llm_request', 'llm_response', 'tool_call', 'tool_result', 'retry', 'alert')",
        "latency_ms >= 0",
        "retry_count >= 0",
        "total_tokens >= 0",
        metadataSensitiveFilter
      )
    }

    val effectiveRules = if (activeRules.nonEmpty) activeRules else Array(
      "event_id IS NOT NULL AND event_id <> '' AND trace_id IS NOT NULL AND trace_id <> '' AND run_id IS NOT NULL AND run_id <> ''",
      "event_type IN ('agent_start', 'agent_complete', 'agent_failed', 'llm_request', 'llm_response', 'tool_call', 'tool_result', 'retry', 'alert')",
      "latency_ms >= 0",
      "retry_count >= 0",
      "total_tokens >= 0",
      metadataSensitiveFilter
    )

    // Dynamic validation expression
    val isCleanExpr = effectiveRules.map(r => s"($r)").mkString(" AND ")
    println(s"Dynamic quality check expression: $isCleanExpr")

    // 2. Data Splitting: 合规数据 vs. 不合规脏数据
    val clean = df.filter(isCleanExpr)
      .withColumn("metric_date", to_date($"event_time"))
      .dropDuplicates("event_id")

    val dirty = df.filter(s"!($isCleanExpr)")

    // 3. Output writing with file size control (.coalesce(1) to prevent small files)
    clean.coalesce(1).write.mode(SaveMode.Overwrite).parquet(conf.output)

    val dirtyOutput = if (conf.output.contains("/clean/")) {
      conf.output.replace("/clean/", "/dirty/")
    } else {
      conf.output + "_dirty"
    }
    dirty.coalesce(1).write.mode(SaveMode.Overwrite).json(dirtyOutput)

    session.stop()
  }

  private def isRuleCompatible(rule: String, schemaColumns: Set[String]): Boolean = {
    val trimmed = Option(rule).getOrElse("").trim
    if (trimmed.isEmpty) {
      return false
    }

    val strippedLiterals = trimmed
      .replaceAll("'(?:''|[^'])*'", " ")
      .replaceAll("\"(?:\"\"|[^\"])*\"", " ")

    val tokens = "[A-Za-z_][A-Za-z0-9_]*".r.findAllIn(strippedLiterals).map(_.toLowerCase).toSeq
    tokens.forall { token =>
      schemaColumns.contains(token) || sqlKeywords.contains(token) || sqlFunctions.contains(token)
    }
  }
}

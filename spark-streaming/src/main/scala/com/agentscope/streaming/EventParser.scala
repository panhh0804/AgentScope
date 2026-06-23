package com.agentscope.streaming

import com.fasterxml.jackson.databind.DeserializationFeature
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import com.fasterxml.jackson.module.scala.experimental.ScalaObjectMapper
import com.fasterxml.jackson.databind.ObjectMapper

object EventParser {
  private val mapper = new ObjectMapper() with ScalaObjectMapper
  mapper.registerModule(DefaultScalaModule)
  mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)

  private val requiredEventTypes = Set(
    "agent_start",
    "agent_complete",
    "agent_failed",
    "llm_request",
    "llm_response",
    "tool_call",
    "tool_result",
    "retry",
    "alert"
  )

  def parse(json: String): Option[AgentEvent] = {
    try {
      val event = mapper.readValue[AgentEvent](json)
      if (isValid(event)) Some(event) else None
    } catch {
      case _: Throwable => None
    }
  }

  private def isValid(event: AgentEvent): Boolean = {
    nonEmpty(event.event_id) &&
      nonEmpty(event.trace_id) &&
      nonEmpty(event.run_id) &&
      nonEmpty(event.agent_id) &&
      requiredEventTypes.contains(event.event_type)
  }

  private def nonEmpty(value: String): Boolean = value != null && value.trim.nonEmpty
}


package com.agentscope.streaming

import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.spark.SparkConf
import org.apache.spark.streaming.kafka010.ConsumerStrategies.Subscribe
import org.apache.spark.streaming.kafka010.KafkaUtils
import org.apache.spark.streaming.kafka010.LocationStrategies.PreferConsistent
import org.apache.spark.streaming.{Seconds, StreamingContext}

object AgentEventStreamingJob {
  case class Config(kafkaBootstrap: String = "middleware:9092", topic: String = "agent-events", redisHost: String = "middleware", redisPort: Int = 6379)

  def main(args: Array[String]): Unit = {
    val config = parseArgs(args)
    val sparkConf = new SparkConf().setAppName("AgentScopeStreaming")
    val ssc = new StreamingContext(sparkConf, Seconds(5))

    val kafkaParams = Map[String, Object](
      "bootstrap.servers" -> config.kafkaBootstrap,
      "key.deserializer" -> classOf[StringDeserializer],
      "value.deserializer" -> classOf[StringDeserializer],
      "group.id" -> "agentscope-streaming",
      "auto.offset.reset" -> "latest",
      "enable.auto.commit" -> (false: java.lang.Boolean)
    )

    val stream = KafkaUtils.createDirectStream[String, String](
      ssc,
      PreferConsistent,
      Subscribe[String, String](Seq(config.topic), kafkaParams)
    )

    stream
      .map(_.value())
      .flatMap(EventParser.parse)
      .window(Seconds(60), Seconds(5))
      .foreachRDD { rdd =>
        val events = rdd.collect().toSeq
        val overview = RealtimeMetricCalculator.overview(events)
        val agents = RealtimeMetricCalculator.agentStatus(events)
        val alerts = RealtimeAlertDetector.detect(events, overview)
        RedisSink.write(config.redisHost, config.redisPort, overview, agents, alerts)
      }

    ssc.start()
    ssc.awaitTermination()
  }

  private def parseArgs(args: Array[String]): Config = {
    val map = args.sliding(2, 2).collect { case Array(k, v) => k -> v }.toMap
    Config(
      kafkaBootstrap = map.getOrElse("--kafka-bootstrap", "middleware:9092"),
      topic = map.getOrElse("--topic", "agent-events"),
      redisHost = map.getOrElse("--redis-host", "middleware"),
      redisPort = map.getOrElse("--redis-port", "6379").toInt
    )
  }
}


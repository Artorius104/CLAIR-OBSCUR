package com.example

import org.apache.spark.sql.types._

object Config {
  
  // Kafka Configuration
  val BOOTSTRAP_SERVER: String = sys.env.getOrElse("KAFKA_HOST", "localhost:9092")
  val FIREWALL_TOPIC: String = "topic-firewall-logs"

  // Database Configuration
  private val DB_NAME: String = sys.env.getOrElse("DATABASE_NAME", "spark_streaming_db")
  private val DB_HOST: String = sys.env.getOrElse("DATABASE_HOST", "localhost")
  private val DB_PORT: String = sys.env.getOrElse("DATABASE_PORT", "5432")

  val DB_CONFIG: Map[String, String] = Map(
    "url" -> s"jdbc:postgresql://$DB_HOST:$DB_PORT/$DB_NAME",
    "user" -> sys.env.getOrElse("DATABASE_USER", "user"),
    "password" -> sys.env.getOrElse("DATABASE_PASSWORD", "password"),
    "driver" -> "org.postgresql.Driver"
  )

  // Firewall Logs Schema - matches Producer schema
  val FIREWALL_SCHEMA: StructType = StructType(Array(
    StructField("timestamp", StringType, nullable = false),
    StructField("firewall_id", StringType, nullable = false),
    StructField("src_ip", StringType, nullable = false),
    StructField("dst_ip", StringType, nullable = false),
    StructField("src_port", IntegerType, nullable = false),
    StructField("dst_port", IntegerType, nullable = false),
    StructField("protocol", StringType, nullable = false),
    StructField("action", StringType, nullable = false),
    StructField("bytes", IntegerType, nullable = false),
    StructField("duration_ms", IntegerType, nullable = false),
    StructField("rule_id", StringType, nullable = false),
    StructField("session_id", StringType, nullable = false),
    StructField("user", StringType, nullable = true),
    StructField("reason", StringType, nullable = true),
    StructField("status", StringType, nullable = false),
    StructField("flags", StringType, nullable = true),
    StructField("bug_type", StringType, nullable = true),
    StructField("log_category", StringType, nullable = false),
    StructField("severity", StringType, nullable = false),
    StructField("row_id", LongType, nullable = true),
    StructField("batch_id", LongType, nullable = true)
  ))

  // Database Tables
  val FIREWALL_LOGS_TABLE: String = "firewall_logs"
}

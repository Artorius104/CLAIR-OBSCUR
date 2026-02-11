package com.example

import org.apache.spark.sql.types._

object Config {

  val BATCH_SIZE = 100
  val BOOTSTRAP_SERVER = sys.env.getOrElse("KAFKA_HOST", "localhost:9092")

  val FIREWALL_TOPIC: String = "topic-firewall-logs"
  val FIREWALL_CSV_PATH: String = sys.env.getOrElse("DATASET_PATH", "data/") + "firewall_logs_analyzed.csv"
  val SAVE_BATCH_STATE_FILE = "/app/tmp/kafka_firewall_batch_state.txt"
}

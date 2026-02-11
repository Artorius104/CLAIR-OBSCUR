package com.example

import org.apache.spark.sql.{SparkSession}
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import java.io._
import com.example.Config._

object Producer {

  def main(args: Array[String]): Unit = {

    // === Paramètres ===
    val inputPath = FIREWALL_CSV_PATH
    val kafkaBootstrap = BOOTSTRAP_SERVER
    val topicName = FIREWALL_TOPIC
    val batchSize = BATCH_SIZE
    var lastBatchSent = -1

    // === Spark Session ===
    val spark = SparkSession.builder()
      .appName("FirewallProducer")
      .master("local[*]")
      .getOrCreate()

    spark.conf.set("spark.sql.shuffle.partitions", "100")
    spark.sparkContext.setLogLevel("ERROR")

    // === Schéma pour firewall_logs_analyzed ===
    val firewallSchema = StructType(Array(
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
      StructField("severity", StringType, nullable = false)
    ))

    // === Lecture CSV avec schéma défini ===
    val df = spark.read
      .format("csv")
      .option("header", "true")
      .schema(firewallSchema)
      .load(inputPath)

    val dfWithBatch = df.withColumn("row_id", row_number().over(Window.orderBy(lit(1))))
                        .withColumn("batch_id", (col("row_id") - 1) / batchSize)
    val totalBatches = dfWithBatch.select("batch_id").distinct().count().toInt

    val stateFile = new File(SAVE_BATCH_STATE_FILE)
    if (stateFile.exists()) {
      val source = scala.io.Source.fromFile(stateFile)
      lastBatchSent = source.getLines().next().toInt
      source.close()
    }

    println("\n=============================================================================")
    println(s"Nombre total de batchs déjà envoyés, : ${lastBatchSent + 1}")
    println(s"Nombre total de batchs à envoyer à Kafka, : ${totalBatches - lastBatchSent}")
    println("=============================================================================\n")

    for (i <- (lastBatchSent + 1) until totalBatches) {
        val start = i * batchSize + 1
        val end = start + batchSize - 1

        val batchDF = dfWithBatch
          .filter(col("row_id").between(start, end))

        val kafkaDF = batchDF.selectExpr(
          "CAST(timestamp AS STRING) AS key",
          "to_json(struct(*)) AS value"
        )

        // Vérifier que le batch contient des données
        val batchCount = batchDF.count()
        if (batchCount == 0) {
          println(s"⚠️  Batch $i est vide, passage au suivant...")
        } else {
          kafkaDF.write
              .format("kafka")
              .mode("append")
              .option("kafka.bootstrap.servers", kafkaBootstrap)
              .option("topic", topicName)
              // Kafka producer timeout configurations
              .option("kafka.request.timeout.ms", "300000")        // 5 minutes
              .option("kafka.delivery.timeout.ms", "360000")       // 6 minutes  
              .option("kafka.max.block.ms", "300000")             // 5 minutes
              .option("kafka.retries", "3")                        // Retry failed sends
              .option("kafka.retry.backoff.ms", "1000")           // Wait between retries
              // Batch size optimizations
              .option("kafka.batch.size", "32768")                 // 32KB batches
              .option("kafka.linger.ms", "100")                    // Wait 100ms to batch
              .option("kafka.buffer.memory", "67108864")           // 64MB buffer
              // Compression for better throughput
              .option("kafka.compression.type", "snappy")
              .save()
          
          println(s"✔ Batch $i envoyé dans le topic Kafka '$topicName' ($batchCount messages)")
        }
            
        val writer = new PrintWriter(new File(SAVE_BATCH_STATE_FILE))
        writer.write(i.toString)
        writer.close()
        
        println("⏳ Pause de 5 secondes...")
        Thread.sleep(5000)
    }

    spark.stop()
    println("✅ Tous les batchs ont été envoyés à Kafka.")
  }
}

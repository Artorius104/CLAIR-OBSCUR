package com.example

import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._
import scala.annotation.tailrec
import scala.util.{Failure, Success, Try}
import Config._
import java.util.Properties

object Consumer {

  def main(args: Array[String]): Unit = {
    val spark = SparkSession.builder()
      .appName("FirewallLogsConsumer")
      .master("local[*]")
      .config("spark.driver.memory", "4g")
      .config("spark.sql.shuffle.partitions", "100")
      .getOrCreate()

    spark.sparkContext.setLogLevel("ERROR")

    println("""
      |=============================================================================
      |  Firewall Logs Consumer - Démarrage
      |=============================================================================
      |""".stripMargin)

    try {
      consumeKafkaTopic(spark)
    } catch {
      case e: Exception =>
        println(s"Erreur inattendue : ${e.getMessage}")
        e.printStackTrace()
    }

    spark.streams.awaitAnyTermination()
  }

  private def consumeKafkaTopic(spark: SparkSession): Unit = {
    val maybeKafkaDF = tryConnect(spark, attempt = 1, retries = 15, delaySeconds = 5)

    maybeKafkaDF match {
      case Some(kafkaStreamDF) =>
        println(s"✅ Connexion Kafka établie. Lecture du topic '$FIREWALL_TOPIC'...")

        val messages = kafkaStreamDF.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)")

        val parsedMessages = messages
          .select(from_json(col("value"), FIREWALL_SCHEMA).as("data"))
          .select("data.*")
          // Renommer la colonne 'user' en 'user_name' pour éviter les conflits avec les mots réservés
          .withColumnRenamed("user", "user_name")
          // Convertir timestamp string en timestamp type
          .withColumn("timestamp", to_timestamp(col("timestamp")))

        // Sauvegarder dans PostgreSQL et afficher des statistiques
        parsedMessages.writeStream
          .foreachBatch { (batchDF: DataFrame, batchId: Long) =>
            println(s"🔄 Batch #$batchId reçu...")
            val count = batchDF.count()
            
            if (count > 0) {
              println(s"""
                |=============================================================================
                |  📦 Batch #$batchId reçu - $count messages
                |=============================================================================
                |""".stripMargin)

              // Sauvegarder dans PostgreSQL
              saveToPostgreSQL(batchDF, batchId)

              // Afficher quelques statistiques sur le batch
              println("📊 Statistiques du batch:")
              
              val actionStats = batchDF.groupBy("action").count()
              println("\n🔹 Actions:")
              actionStats.show(false)

              val protocolStats = batchDF.groupBy("protocol").count()
              println("🔹 Protocols:")
              protocolStats.show(false)

              val firewallStats = batchDF.groupBy("firewall_id").count()
              println("🔹 Firewalls:")
              firewallStats.show(false)

              // Afficher un échantillon des données
              println("\n🔹 Échantillon des données (5 premières lignes):")
              batchDF.select(
                "timestamp", "firewall_id", "src_ip", "dst_ip", 
                "protocol", "action", "bytes"
              ).show(5, truncate = false)

              println(s"✅ Batch #$batchId traité avec succès\n")
            } else {
              println(s"⚠️  Batch #$batchId vide (0 messages)")
            }
          }
          .outputMode("append")
          .option("checkpointLocation", "/tmp/kafka-checkpoint-consumer")
          .trigger(org.apache.spark.sql.streaming.Trigger.ProcessingTime("10 seconds"))
          .start()
          .awaitTermination()

      case None =>
        println("❌ Le topic Kafka n'est pas disponible. Fermeture de l'application.")
        System.exit(1)
    }
  }

  private def saveToPostgreSQL(batchDF: DataFrame, batchId: Long): Unit = {
    try {
      println(s"💾 Sauvegarde du batch #$batchId dans PostgreSQL...")

      // Sélectionner les colonnes dans le bon ordre
      val dfToSave = batchDF.select(
        col("timestamp"),
        col("firewall_id"),
        col("src_ip"),
        col("dst_ip"),
        col("src_port"),
        col("dst_port"),
        col("protocol"),
        col("action"),
        col("bytes"),
        col("duration_ms"),
        col("rule_id"),
        col("session_id"),
        col("user_name"),
        col("reason"),
        col("status"),
        col("flags"),
        col("bug_type"),
        col("log_category"),
        col("severity")
      )

      // Configuration JDBC
      val connectionProperties = new Properties()
      connectionProperties.put("user", DB_CONFIG("user"))
      connectionProperties.put("password", DB_CONFIG("password"))
      connectionProperties.put("driver", DB_CONFIG("driver"))

      // Écrire dans la table firewall_logs
      dfToSave.write
        .mode("append")
        .jdbc(DB_CONFIG("url"), "firewall_logs", connectionProperties)

      println(s"✅ Batch #$batchId sauvegardé dans PostgreSQL (${dfToSave.count()} lignes)")

      // Mise à jour des statistiques agrégées
      updateHourlyStats(batchDF, connectionProperties)

    } catch {
      case e: Exception =>
        println(s"❌ Erreur lors de la sauvegarde dans PostgreSQL: ${e.getMessage}")
        e.printStackTrace()
    }
  }

  private def updateHourlyStats(batchDF: DataFrame, connectionProperties: Properties): Unit = {
    try {
      // Agréger les données par heure
      val hourlyStats = batchDF
        .withColumn("hour_timestamp", date_trunc("hour", col("timestamp")))
        .groupBy("hour_timestamp", "firewall_id", "protocol", "action")
        .agg(
          count("*").as("total_events"),
          sum("bytes").as("total_bytes"),
          avg("duration_ms").as("avg_duration_ms"),
          countDistinct("src_ip").as("unique_src_ips"),
          countDistinct("dst_ip").as("unique_dst_ips")
        )

      // Sauvegarder les statistiques (append si nouvelle heure, sinon il faudrait faire un upsert)
      hourlyStats.write
        .mode("append")
        .jdbc(DB_CONFIG("url"), "firewall_stats_hourly", connectionProperties)

      println(s"✅ Statistiques horaires mises à jour")
    } catch {
      case e: Exception =>
        println(s"⚠️  Erreur lors de la mise à jour des statistiques: ${e.getMessage}")
    }
  }

  @tailrec
  private def tryConnect(
      spark: SparkSession,
      attempt: Int,
      retries: Int,
      delaySeconds: Int
  ): Option[DataFrame] = {
    println(s"🔄 Tentative $attempt/$retries de connexion au topic Kafka '$FIREWALL_TOPIC'...")
    
    Try {
      spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", BOOTSTRAP_SERVER)
        .option("subscribe", FIREWALL_TOPIC)
        .option("startingOffsets", "earliest")
        .option("failOnDataLoss", "false")
        .option("kafka.group.id", s"firewall-consumer-${System.currentTimeMillis()}")
        .load()
    } match {
      case Success(df) =>
        println(s"✅ Connexion établie avec le topic Kafka '$FIREWALL_TOPIC'")
        Some(df)

      case Failure(e) if attempt < retries =>
        println(s"⚠️  Échec tentative $attempt : ${e.getMessage}")
        println(s"⏳ Nouvelle tentative dans ${delaySeconds}s...")
        Thread.sleep(delaySeconds * 1000)
        tryConnect(spark, attempt + 1, retries, delaySeconds)

      case Failure(e) =>
        println(s"❌ Échec après $retries tentatives. Abandon.")
        println(s"Erreur: ${e.getMessage}")
        None
    }
  }
}

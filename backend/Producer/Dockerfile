# Stage 1: Build
FROM sbtscala/scala-sbt:eclipse-temurin-11.0.16_1.7.1_2.12.16 AS builder

WORKDIR /app
COPY . /app
RUN sbt clean assembly

# Stage 2: Runtime
FROM eclipse-temurin:11-jdk

# Install Spark
RUN curl -fsSL https://archive.apache.org/dist/spark/spark-3.5.0/spark-3.5.0-bin-hadoop3.tgz | tar -xz -C /opt && \
    ln -s /opt/spark-3.5.0-bin-hadoop3 /opt/spark

ENV PATH="/opt/spark/bin:$PATH"
ENV SPARK_HOME="/opt/spark"

RUN mkdir -p /app/tmp && \
    echo "-1" > /app/tmp/kafka_firewall_batch_state.txt && \
    chmod a+rw /app/tmp/kafka_firewall_batch_state.txt

# JVM and Spark configuration
ENV JAVA_OPTS="-Xmx2g -Xms1g"
ENV SPARK_OPTS="--driver-memory 1g --executor-memory 1g --driver-java-options '-Xmx1g -Xms512m'"

WORKDIR /app
COPY --from=builder /app/target/scala-2.12/Producer-assembly-1.0.0.jar /app/

CMD ["/opt/spark/bin/spark-submit", \
    "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.3.1", \
    "--class", "com.example.Producer", \
    "--driver-memory", "1g", \
    "--executor-memory", "1g", \
    "--conf", "spark.sql.adaptive.enabled=true", \
    "--conf", "spark.sql.adaptive.coalescePartitions.enabled=true", \
    "--conf", "spark.serializer=org.apache.spark.serializer.KryoSerializer", \
    "/app/Producer-assembly-1.0.0.jar"]
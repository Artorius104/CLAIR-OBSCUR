FROM flink:1.19.1-scala_2.12-java17

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip python3-venv && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    rm -rf /var/lib/apt/lists/*

# enable s3a:// inside Flink
RUN mkdir -p /opt/flink/plugins/s3-fs-hadoop && \
    cp /opt/flink/opt/flink-s3-fs-hadoop-1.19.1.jar /opt/flink/plugins/s3-fs-hadoop/

WORKDIR /app

COPY stream/requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

COPY common/ /app/common/
COPY stream/job/ /app/job/
COPY stream/submit.sh /app/submit.sh
RUN chmod +x /app/submit.sh

ENV PYTHONPATH=/app

# DATA_ROOT must be set to the path of the mounted ingestion directory.
# Set it in .env or pass -e DATA_ROOT=... at runtime.

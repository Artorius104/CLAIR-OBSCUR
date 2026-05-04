FROM flink:1.19.1-scala_2.12-java17

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# python + pip
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip python3-venv && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY local/requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

COPY common/ /app/common/
COPY local/job/ /app/job/

ENV PYTHONPATH=/app

# default entry: jobmanager/taskmanager (compose `command:` overrides);
# the submitter service uses /app/submit.sh (mounted from host).

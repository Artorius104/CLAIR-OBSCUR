FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backfill/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

COPY common/  /app/common/
COPY backfill/ /app/backfill/

ENV PYTHONPATH=/app

CMD ["python", "-m", "backfill.run_backfill"]

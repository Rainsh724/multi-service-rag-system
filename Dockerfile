FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

ARG REQUIREMENTS_FILE
COPY ${REQUIREMENTS_FILE} /tmp/requirements.txt
RUN python -m pip install --upgrade pip \
    && pip install -r /tmp/requirements.txt

COPY services/ /app/services/
COPY shared/ /app/shared/

RUN mkdir -p /app/storage

EXPOSE 8000 8001 8002

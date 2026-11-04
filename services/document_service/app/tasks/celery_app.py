import os

from celery import Celery


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://127.0.0.1:6379/0",
)

celery_app = Celery(
    "document_service",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "services.document_service.app.tasks.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)


@celery_app.task(name="document_service.health_check")
def health_check_task():
    return {
        "status": "ok",
        "worker": "document-service",
    }
import structlog
import json

from celery import shared_task
from django.db import transaction
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from clickhouse_driver import Client
from .models import OutboxEvent
from retrying import retry
from prometheus_client import Counter

log = structlog.get_logger()

CH_CLIENT = Client(
    host=os.getenv("CLICKHOUSE_HOST", "clickhouse"),
    port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
    database="default"
)



events_processed = Counter("processed_events_total", "Total number of processed events")

@shared_task
def process_outbox_events():
    with start_transaction(op="task", name="process_outbox_events"):
        events = list(OutboxEvent.objects.filter(processed=False)[:500])

        if not events:
            return

        event_data = [
            (
                event.idempotency_key,
                event.event_type,
                event.event_date_time,
                event.environment,
                str(event.event_context),
                event.metadata_version
            )
            for event in events
        ]

        try:
            with transaction.atomic():
                insert_into_clickhouse(event_data)
                OutboxEvent.objects.filter(id__in=[e.id for e in events]).update(processed=True)

            events_processed.inc(len(events))  # Увеличиваем метрику

        except Exception as e:
            logger.error("Failed to process outbox events", error=str(e))
            sentry_sdk.capture_exception(e)


@retry(stop_max_attempt_number=3, wait_fixed=2000)  # 3 попытки, 2 сек ожидания
def insert_into_clickhouse(event_data):
    CH_CLIENT.execute("""
        INSERT INTO event_log (idempotency_key, event_type, event_date_time, environment, event_context, metadata_version)
        SELECT * FROM input('idempotency_key UUID, event_type String, event_date_time DateTime, environment String, event_context String, metadata_version Int32')
        WHERE idempotency_key NOT IN (SELECT idempotency_key FROM event_log)
    """, event_data)

def setup_celery_beat():
    schedule, _ = IntervalSchedule.objects.get_or_create(
        every=30, period=IntervalSchedule.SECONDS
    )

    PeriodicTask.objects.update_or_create(
        name="Process Outbox Events",
        defaults={
            "interval": schedule,
            "task": "core.tasks.process_outbox_events",
            "args": json.dumps([]),
            "kwargs": json.dumps({"batch_size": 100}),
        },
    )

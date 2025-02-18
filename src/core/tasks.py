import structlog
import json

from celery import shared_task
from django.db import transaction
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from clickhouse_driver import Client
from .models import OutboxEvent


log = structlog.get_logger()

CH_CLIENT = Client(host="clickhouse", database="default")

@shared_task
def process_outbox_events(batch_size=100):
    log.info("Processing outbox events...")

    with transaction.atomic():
        events = list(OutboxEvent.objects.filter(processed=False)[:batch_size])

        if not events:
            log.info("No new events to process.")
            return

        event_data = [
            (e.event_type, e.event_date_time, e.environment, str(e.event_context), e.metadata_version)
            for e in events
        ]

        CH_CLIENT.execute("""
            INSERT INTO event_log (event_type, event_date_time, environment, event_context, metadata_version)
            VALUES
        """, event_data)

        OutboxEvent.objects.filter(id__in=[e.id for e in events]).update(processed=True)

    log.info("Successfully processed %d events", len(events))




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

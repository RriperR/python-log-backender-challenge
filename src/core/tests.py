import pytest

from django.utils.timezone import now
from core.models import OutboxEvent
from core.tasks import process_outbox_events
from clickhouse_driver import Client


@pytest.mark.django_db
def test_create_outbox_event():
    event = OutboxEvent.objects.create(
        event_type="user_signup",
        event_date_time=now(),
        environment="production",
        event_context={"user_id": 123, "email": "test@example.com"},
        metadata_version=1,
    )
    assert OutboxEvent.objects.count() == 1
    assert event.processed is False


@pytest.mark.django_db
def test_filter_unprocessed_events():
    OutboxEvent.objects.create(
        event_type="test_event",
        event_date_time=now(),
        environment="test",
        event_context={},
        metadata_version=1,
        processed=False
    )
    OutboxEvent.objects.create(
        event_type="processed_event",
        event_date_time=now(),
        environment="test",
        event_context={},
        metadata_version=1,
        processed=True
    )

    unprocessed_events = OutboxEvent.objects.filter(processed=False)

    assert unprocessed_events.count() == 1



CH_CLIENT = Client(host="clickhouse", database="default")

@pytest.mark.django_db
def test_process_outbox_events():
    event = OutboxEvent.objects.create(
        event_type="user_signup",
        event_date_time=now(),
        environment="test",
        event_context={"user_id": 123},
        metadata_version=1,
    )

    process_outbox_events()

    event.refresh_from_db()
    assert event.processed is True

    result = CH_CLIENT.execute("SELECT COUNT(*) FROM event_log")
    assert result[0][0] > 0
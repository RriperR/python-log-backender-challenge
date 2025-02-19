import pytest
from clickhouse_driver import Client


@pytest.fixture(scope="module")
def clickhouse_client():
    return Client(host="clickhouse", database="default")


@pytest.mark.django_db
def test_clickhouse_insert(clickhouse_client):
    clickhouse_client.execute("INSERT INTO event_log (event_type, event_date_time, environment, event_context, metadata_version) VALUES",
                              [("test_event", "2025-02-19 12:00:00", "test", "{}", 1)])

    result = clickhouse_client.execute("SELECT COUNT(*) FROM event_log WHERE event_type='test_event'")
    assert result[0][0] > 0

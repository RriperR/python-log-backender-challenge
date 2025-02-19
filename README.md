# Die Hard

This is a project with a test task for backend developers.

## 📌 Task Overview
The goal of this task is to implement **event logging using the Outbox Pattern**, ensuring reliable and efficient data transfer to ClickHouse.

### **💡 Why Outbox Pattern?**
Instead of writing logs directly to ClickHouse, we first store them in **PostgreSQL (`OutboxEvent`)**, and then Celery processes them **in batches** and sends them to ClickHouse.

Tech stack:
- Python 3.13
- Django 5
- pytest
- Docker & docker-compose
- PostgreSQL
- ClickHouse

## Installation

Put a `.env` file into the `src/core` directory. You can start with a template fi le:

```
cp src/core/.env.ci src/core/.env
```

Run the containers with
```
make run
```

and then run the installation script with:

```
make install
```

## Tests

`make test`

## Linter

`make lint`


## ✅ How It Works
### 1️⃣ Logging an event
When a user registers, an event is not sent directly to ClickHouse. Instead, it is stored in PostgreSQL:
```python
OutboxEvent.objects.create(
    event_type="user_signup",
    event_date_time=now(),
    environment="production",
    event_context={"email": user.email, "first_name": user.first_name},
    metadata_version=1,
)
```

## 2️⃣ Processing the Outbox
A Celery task periodically processes unprocessed events and sends them to ClickHouse:
```python
@shared_task
def process_outbox_events():
    events = list(OutboxEvent.objects.filter(processed=False)[:100])
    if events:
        CH_CLIENT.execute("INSERT INTO logs ...", [event.to_tuple() for event in events])
        OutboxEvent.objects.filter(id__in=[e.id for e in events]).update(processed=True)
```


## 📊 Architecture Overview
```diff
+--------------+      +-------------+      +------------+      +-------------+
|  Django App  |  →   | OutboxEvent |  →   |  Celery    |  →   | ClickHouse  |
+--------------+      +-------------+      +------------+      +-------------+
```
Django writes logs to OutboxEvent instead of sending them directly.
Celery periodically fetches unprocessed logs.
ClickHouse receives batched inserts.

## 🎯 Key Features Implemented
✔ Reliable logging using Outbox Pattern

✔ Batch processing to reduce ClickHouse load

✔ Celery integration for async event handling

✔ Full test coverage with pytest-django
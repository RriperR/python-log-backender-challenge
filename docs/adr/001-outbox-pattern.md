# ADR-001: Using the Outbox Pattern for Reliable Event Processing

## Context
To ensure reliable event processing, we use the **Outbox Pattern**, storing events in PostgreSQL before forwarding them to ClickHouse.

## Decision
- We use **Celery** for asynchronous processing.
- Events are stored in `OutboxEvent` with an `idempotency_key` to prevent duplicates.
- Events are processed in **batches** and inserted into ClickHouse.

## Status
Accepted.

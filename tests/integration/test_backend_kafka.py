"""Integration tests: Backend API publishes control events to Kafka.

Requires: Backend, Kafka. For run creation: ingestion worker (or skip if run not found).
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime

import os

import httpx
import pytest
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

# Match conftest / docker-compose
KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DATA_INGESTION_TOPIC = "data-ingestion"
CONTROL_EVENTS_TOPIC = "control-events"


def _backend_has_run(backend_url: str, run_id: str) -> bool:
    try:
        r = httpx.get(f"{backend_url}/api/v1/rest/runs/{run_id}/info/", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


async def _produce_create_run(run_id: str) -> None:
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: v.encode() if isinstance(v, str) else v,
        key_serializer=lambda k: k.encode() if k else None,
    )
    await producer.start()
    try:
        msg = {
            "type": "create_run",
            "run_id": run_id,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "payload": {},
        }
        import json as _json

        await producer.send_and_wait(
            DATA_INGESTION_TOPIC, key=run_id, value=_json.dumps(msg)
        )
    finally:
        await producer.stop()


async def _consume_control_event_after_delete(
    run_id: str,
    delete_fn: object,
    timeout_sec: float = 15.0,
) -> dict | None:
    """Start consumer, call delete_fn(), then consume until run_deleted for run_id."""
    consumer = AIOKafkaConsumer(
        CONTROL_EVENTS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset="latest",
        consumer_timeout_ms=int(timeout_sec * 1000),
    )
    await consumer.start()
    try:
        # Trigger delete (backend publishes to control-events)
        if callable(delete_fn):
            delete_fn()  # ty:ignore[call-top-callable]
        start = time.monotonic()
        while time.monotonic() - start < timeout_sec:
            batch = await asyncio.wait_for(
                consumer.getmany(timeout_ms=2000), timeout=timeout_sec
            )
            for _tp, records in batch.items():
                for rec in records:
                    data = json.loads((rec.value or b"").decode())
                    if (
                        data.get("type") == "run_deleted"
                        and data.get("payload", {}).get("run_id") == run_id
                    ):
                        return data
    finally:
        await consumer.stop()
    return None


def test_delete_run_publishes_control_event(
    backend_url: str,
    unique_run_id: str,
    kafka_bootstrap: str,
) -> None:
    """Delete run via API and assert run_deleted is published to control-events."""
    asyncio.run(_produce_create_run(unique_run_id))

    # Poll for run to appear (ingestion worker must be running)
    for _ in range(30):
        if _backend_has_run(backend_url, unique_run_id):
            break
        time.sleep(0.5)
    else:
        pytest.skip(
            "Ingestion worker may not be running; run did not appear in backend"  # ty:ignore[too-many-positional-arguments]
        )  # ty:ignore[invalid-argument-type]

    # Start consumer, then delete, then consume (so we don't miss the event)
    def do_delete() -> None:
        r = httpx.delete(f"{backend_url}/api/v1/rest/runs/{unique_run_id}/", timeout=10)
        assert r.status_code == 200

    event = asyncio.run(_consume_control_event_after_delete(unique_run_id, do_delete))
    assert event is not None
    assert event["type"] == "run_deleted"
    assert event["payload"]["run_id"] == unique_run_id

"""Integration tests: Delete run with blob ref → control-events → run_deleted.

Requires: Backend, Kafka, ingestion worker. Optional: control worker + S3 to verify cleanup.
This test only verifies that run_deleted is published when deleting a run that has blob refs.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime

import httpx
import pytest
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

import os

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DATA_INGESTION_TOPIC = "data-ingestion"
CONTROL_EVENTS_TOPIC = "control-events"


def _backend_has_run(backend_url: str, run_id: str) -> bool:
    try:
        r = httpx.get(f"{backend_url}/api/v1/rest/runs/{run_id}/info/", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


async def _produce_run_with_blob_ref(run_id: str) -> None:
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: v.encode() if isinstance(v, str) else v,
        key_serializer=lambda k: k.encode() if k else None,
    )
    await producer.start()
    try:
        for msg in [
            {
                "type": "create_run",
                "run_id": run_id,
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "payload": {},
            },
            {
                "type": "blob_ref",
                "run_id": run_id,
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "payload": {
                    "artifact_path": "images/test.png",
                    "s3_key": f"artifacts/{run_id}/images/test.png",
                    "content_type": "image/png",
                },
            },
            {
                "type": "finish_run",
                "run_id": run_id,
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "payload": {},
            },
        ]:
            await producer.send_and_wait(
                DATA_INGESTION_TOPIC, key=run_id, value=json.dumps(msg)
            )
    finally:
        await producer.stop()


async def _consume_run_deleted(run_id: str, timeout_sec: float = 15.0) -> dict | None:
    consumer = AIOKafkaConsumer(
        CONTROL_EVENTS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset="latest",
        consumer_timeout_ms=int(timeout_sec * 1000),
    )
    await consumer.start()
    try:
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


def test_delete_run_with_blob_ref_publishes_run_deleted(
    backend_url: str,
    unique_run_id: str,
    kafka_bootstrap: str,
) -> None:
    """Create run with blob_ref, delete via API, consume run_deleted from control-events."""
    asyncio.run(_produce_run_with_blob_ref(unique_run_id))

    for _ in range(30):
        if _backend_has_run(backend_url, unique_run_id):
            break
        time.sleep(0.5)
    else:
        pytest.skip("Ingestion worker may not be running; run did not appear")  # ty:ignore[invalid-argument-type, too-many-positional-arguments]

    # Start consumer, then delete, then consume (so we don't miss the event)
    async def delete_and_consume() -> dict | None:
        consumer = AIOKafkaConsumer(
            CONTROL_EVENTS_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP,
            auto_offset_reset="latest",
            consumer_timeout_ms=15000,
        )
        await consumer.start()
        try:
            r = httpx.delete(
                f"{backend_url}/api/v1/rest/runs/{unique_run_id}/", timeout=10
            )
            assert r.status_code == 200
            start = time.monotonic()
            while time.monotonic() - start < 12:
                batch = await asyncio.wait_for(
                    consumer.getmany(timeout_ms=2000), timeout=12
                )
                for _tp, records in batch.items():
                    for rec in records:
                        data = json.loads((rec.value or b"").decode())
                        if (
                            data.get("type") == "run_deleted"
                            and data.get("payload", {}).get("run_id") == unique_run_id
                        ):
                            return data
        finally:
            await consumer.stop()
        return None

    event = asyncio.run(delete_and_consume())
    assert event is not None
    assert event["type"] == "run_deleted"
    assert event["payload"]["run_id"] == unique_run_id

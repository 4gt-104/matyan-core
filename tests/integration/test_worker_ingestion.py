"""Integration tests: Kafka → Ingestion worker → FDB; verify via backend API.

Requires: Backend, Kafka, ingestion worker (e.g. docker compose), FDB.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime

import httpx
import pytest
from aiokafka import AIOKafkaProducer

import os

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DATA_INGESTION_TOPIC = "data-ingestion"


def _backend_has_run(backend_url: str, run_id: str) -> bool:
    try:
        r = httpx.get(f"{backend_url}/api/v1/rest/runs/{run_id}/info/", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


async def _produce_ingestion_messages(run_id: str) -> None:
    """Produce create_run, log_metric, log_hparams, finish_run to data-ingestion."""
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
                "type": "log_metric",
                "run_id": run_id,
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "payload": {
                    "name": "loss",
                    "value": 1.23,
                    "step": 0,
                    "context": {"subset": "train"},
                    "dtype": "float",
                },
            },
            {
                "type": "log_metric",
                "run_id": run_id,
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "payload": {
                    "name": "loss",
                    "value": 0.99,
                    "step": 1,
                    "context": {"subset": "train"},
                    "dtype": "float",
                },
            },
            {
                "type": "log_hparams",
                "run_id": run_id,
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "payload": {"value": {"learning_rate": 0.001, "batch_size": 128}},
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


def test_worker_ingestion_kafka_to_fdb_via_backend(
    backend_url: str,
    unique_run_id: str,
    kafka_bootstrap: str,
) -> None:
    """Produce ingestion messages to Kafka; poll backend until run appears; assert content."""
    asyncio.run(_produce_ingestion_messages(unique_run_id))

    for _ in range(40):
        if _backend_has_run(backend_url, unique_run_id):
            break
        time.sleep(0.5)
    else:
        pytest.skip(
            "Ingestion worker may not be running; run did not appear in backend"  # ty:ignore[too-many-positional-arguments]
        )  # ty:ignore[invalid-argument-type]

    info = httpx.get(
        f"{backend_url}/api/v1/rest/runs/{unique_run_id}/info/", timeout=5
    ).json()
    params = info.get("params") or {}
    assert params.get("learning_rate") == 0.001
    assert params.get("batch_size") == 128

    traces = info.get("traces") or {}
    metric_traces = traces.get("metric") or []
    loss_trace = next(
        (t for t in metric_traces if (t.get("name") or t.get("trace_name")) == "loss"),
        None,
    )
    assert loss_trace is not None
    assert info.get("props", {}).get("active") is False

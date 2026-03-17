"""Integration tests: Frontier WebSocket and presign; messages appear on Kafka.

Requires: Frontier, Kafka. No backend or worker needed.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime

import httpx
from aiokafka import AIOKafkaConsumer
from websockets.asyncio.client import connect as ws_connect

import os

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DATA_INGESTION_TOPIC = "data-ingestion"


async def _send_ws_messages(ws_url: str, run_id: str) -> list[str]:
    """Send create_run, log_metric, log_hparams, finish_run; return list of sent types."""
    sent: list[str] = []
    async with ws_connect(ws_url) as ws:
        for msg in [
            {"type": "create_run", "client_datetime": datetime.now(tz=UTC).isoformat()},
            {
                "type": "log_metric",
                "name": "loss",
                "value": 0.42,
                "step": 0,
                "epoch": 0,
                "context": {"subset": "train"},
                "dtype": "float",
                "client_datetime": datetime.now(tz=UTC).isoformat(),
            },
            {"type": "log_hparams", "value": {"lr": 0.001, "batch_size": 32}},
            {"type": "finish_run"},
        ]:
            await ws.send(json.dumps(msg))
            raw = await ws.recv()
            resp = json.loads(raw)
            if resp.get("status") == "ok":
                sent.append(str(msg["type"]))
    return sent


async def _ws_send_then_consume(
    ws_url: str,
    run_id: str,
    min_count: int,
    timeout_sec: float = 12.0,
) -> list[dict]:
    """Start consumer, send WS messages, then consume from Kafka for run_id."""
    consumer = AIOKafkaConsumer(
        DATA_INGESTION_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset="latest",
        consumer_timeout_ms=int(timeout_sec * 1000),
    )
    await consumer.start()
    received: list[dict] = []
    try:
        sent = await _send_ws_messages(ws_url, run_id)
        assert "create_run" in sent
        assert "finish_run" in sent
        start = time.monotonic()
        while time.monotonic() - start < timeout_sec and len(received) < min_count:
            batch = await asyncio.wait_for(
                consumer.getmany(timeout_ms=2000), timeout=timeout_sec
            )
            for _tp, records in batch.items():
                for rec in records:
                    data = json.loads((rec.value or b"").decode())
                    if data.get("run_id") == run_id:
                        received.append(data)
    finally:
        await consumer.stop()
    return received


def test_frontier_ws_messages_appear_on_kafka(
    frontier_url: str,
    unique_run_id: str,
    kafka_bootstrap: str,
) -> None:
    """Send WS messages to frontier, then consume from Kafka and assert types."""
    ws_url = frontier_url.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url}/api/v1/ws/runs/{unique_run_id}"

    received = asyncio.run(_ws_send_then_consume(ws_url, unique_run_id, min_count=4))
    types = [m.get("type") for m in received]
    assert "create_run" in types
    assert "log_metric" in types
    assert "log_hparams" in types
    assert "finish_run" in types


def test_frontier_presign_returns_upload_url(
    frontier_url: str,
    unique_run_id: str,
) -> None:
    """POST presign returns 200 and upload_url."""
    r = httpx.post(
        f"{frontier_url}/api/v1/rest/artifacts/presign",
        json={
            "run_id": unique_run_id,
            "artifact_path": "images/test.png",
            "content_type": "image/png",
        },
        timeout=5,
    )
    assert r.status_code == 200
    data = r.json()
    assert "upload_url" in data
    assert "s3_key" in data

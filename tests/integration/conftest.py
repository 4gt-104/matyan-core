"""Shared fixtures for integration tests.

Integration tests run against real services (backend, frontier, Kafka, FDB).
They skip when required services are not reachable. No existing unit tests
are modified or removed; this suite is additive only.

Run from matyan-backend with integration deps:
    cd extra/matyan-backend && uv run --group integration pytest ../../tests/integration -m integration
"""

from __future__ import annotations

import os
import uuid
import httpx
import pytest
from aiokafka import AIOKafkaProducer

# Mark all tests in this directory as integration (run with -m integration)
pytestmark = pytest.mark.integration

# Service URLs (match docker-compose and smoke scripts)
BACKEND_URL = os.environ.get("MATYAN_BACKEND_URL", "http://localhost:53800")
FRONTIER_URL = os.environ.get("MATYAN_FRONTIER_URL", "http://localhost:53801")
KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")
DATA_INGESTION_TOPIC = "data-ingestion"
CONTROL_EVENTS_TOPIC = "control-events"


def _backend_available() -> bool:
    try:
        r = httpx.get(f"{BACKEND_URL}/api/v1/rest/projects/", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


def _frontier_available() -> bool:
    try:
        r = httpx.get(f"{FRONTIER_URL}/docs", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


def _kafka_available() -> bool:
    try:

        async def _check() -> bool:
            producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
            await producer.start()
            await producer.stop()
            return True

        import asyncio

        asyncio.run(_check())
        return True
    except Exception:
        return False


def _require_backend() -> None:
    if not _backend_available():
        pytest.skip("Backend not reachable")  # ty:ignore[invalid-argument-type, too-many-positional-arguments]


def _require_frontier() -> None:
    if not _frontier_available():
        pytest.skip("Frontier not reachable")  # ty:ignore[invalid-argument-type, too-many-positional-arguments]


def _require_kafka() -> None:
    if not _kafka_available():
        pytest.skip("Kafka not reachable")  # ty:ignore[invalid-argument-type, too-many-positional-arguments]


@pytest.fixture
def backend_url() -> str:
    """Backend base URL. Skips test if backend not available."""
    _require_backend()
    return BACKEND_URL


@pytest.fixture
def frontier_url() -> str:
    """Frontier base URL. Skips test if frontier not available."""
    _require_frontier()
    return FRONTIER_URL


@pytest.fixture
def kafka_bootstrap() -> str:
    """Kafka bootstrap servers. Skips test if Kafka not available."""
    _require_kafka()
    return KAFKA_BOOTSTRAP


@pytest.fixture
def http_transport(backend_url: str):
    """Real HttpTransport pointing at backend. Skips if backend unavailable."""
    from matyan_client.transport.http import HttpTransport

    t = HttpTransport(backend_url, timeout=30.0)
    yield t
    t.close()


@pytest.fixture
def unique_run_id() -> str:
    """Unique run ID for isolation between tests."""
    return f"integration-{uuid.uuid4().hex[:12]}"


@pytest.fixture
def unique_experiment_name() -> str:
    """Unique experiment name for isolation."""
    return f"integration-exp-{uuid.uuid4().hex[:8]}"

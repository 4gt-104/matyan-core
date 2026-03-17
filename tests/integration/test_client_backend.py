"""Integration tests: Client HTTP, Repo, backup, restore against live backend.

Requires: Backend (and FDB). For backup/restore with data: ingestion worker.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from aiokafka import AIOKafkaProducer

KAFKA_BOOTSTRAP_ENV = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DATA_INGESTION_TOPIC_ENV = "data-ingestion"


def _backend_has_run(backend_url: str, run_id: str) -> bool:
    try:
        r = httpx.get(f"{backend_url}/api/v1/rest/runs/{run_id}/info/", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


async def _produce_run_for_backup(run_id: str, experiment_name: str) -> None:
    """Produce create_run, log_metric, log_hparams, finish_run so worker creates a run."""
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_ENV,
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
                    "value": 0.5,
                    "step": 0,
                    "context": {},
                    "dtype": "float",
                },
            },
            {
                "type": "log_hparams",
                "run_id": run_id,
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "payload": {"value": {"lr": 0.01}},
            },
            {
                "type": "finish_run",
                "run_id": run_id,
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "payload": {},
            },
        ]:
            await producer.send_and_wait(
                DATA_INGESTION_TOPIC_ENV,
                key=run_id,
                value=json.dumps(msg),
            )
    finally:
        await producer.stop()


def test_http_transport_search_runs_and_get_run_info(
    backend_url: str,
    http_transport,
) -> None:
    """Real HttpTransport: search_runs and get_run_info."""
    runs = http_transport.search_runs(query="", limit=10)
    assert isinstance(runs, list)
    if not runs:
        pytest.skip("No runs in backend (seed or create run first)")  # ty:ignore[invalid-argument-type, too-many-positional-arguments]
    run_id = runs[0].get("hash") or runs[0].get("run_id")
    assert run_id
    info = http_transport.get_run_info(run_id)
    assert "params" in info or "props" in info
    assert "traces" in info


def test_http_transport_list_experiments_and_tags(
    backend_url: str, http_transport
) -> None:
    """Real HttpTransport: list_experiments and list_tags."""
    experiments = http_transport.list_experiments()
    tags = http_transport.list_tags()
    assert isinstance(experiments, list)
    assert isinstance(tags, list)


def test_repo_iter_runs(backend_url: str) -> None:
    """Real Repo: iter_runs."""
    from matyan_client.repo import Repo

    repo = Repo(backend_url)
    try:
        runs = list(repo.iter_runs())
        assert isinstance(runs, list)
    finally:
        repo._http.close()


def test_repo_get_run(backend_url: str, http_transport) -> None:
    """Real Repo: get_run returns Run or None."""
    from matyan_client.repo import Repo

    runs = http_transport.search_runs(query="", limit=1)
    if not runs:
        pytest.skip("No runs in backend")  # ty:ignore[invalid-argument-type, too-many-positional-arguments]
    run_id = runs[0].get("hash") or runs[0].get("run_id")
    repo = Repo(backend_url)
    try:
        run = repo.get_run(run_id)
        assert run is not None
        assert run.hash == run_id
        run.close()
    finally:
        repo._http.close()


def test_backup_and_restore_dry_run(
    backend_url: str,
    http_transport,
    unique_run_id: str,
    tmp_path: Path,
) -> None:
    """Run backup for a run then restore_reingest(..., dry_run=True). Requires worker to create run."""
    asyncio.run(_produce_run_for_backup(unique_run_id, "integration-backup-exp"))

    for _ in range(30):
        if _backend_has_run(backend_url, unique_run_id):
            break
        time.sleep(0.5)
    else:
        pytest.skip("Ingestion worker may not be running; run did not appear")  # ty:ignore[invalid-argument-type, too-many-positional-arguments]

    from matyan_api_models.backup import BackupManifest
    from matyan_client.backup import run_backup

    result = run_backup(
        str(tmp_path), backend_url=backend_url, run_hashes=[unique_run_id]
    )
    assert result.run_count == 1
    assert result.backup_path is not None
    backup_dir = result.backup_path
    assert backup_dir.is_dir()
    manifest = BackupManifest.read(backup_dir)
    assert manifest.run_count == 1
    assert unique_run_id in manifest.run_hashes
    errors = manifest.validate(backup_dir)
    assert errors == []

    from matyan_client.restore import restore_reingest

    restore_result = restore_reingest(str(backup_dir), dry_run=True)
    assert restore_result.runs_processed == 1
    assert restore_result.sequence_records_sent >= 1

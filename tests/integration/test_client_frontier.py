"""Integration tests: Run over real WebSocket and HTTP (no mocks).

Requires: Backend, Frontier, Kafka, and ingestion worker (to see run in backend).
"""

from __future__ import annotations

import time

import httpx
import pytest

from matyan_client.run import Run


def _backend_has_run(backend_url: str, run_id: str) -> bool:
    try:
        r = httpx.get(f"{backend_url}/api/v1/rest/runs/{run_id}/info/", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def test_run_lifecycle_over_real_ws_and_http(
    backend_url: str,
    frontier_url: str,
    unique_run_id: str,
    unique_experiment_name: str,
) -> None:
    """Create Run with real backend/frontier, track metrics and props, close; then verify via backend."""

    run = Run(
        run_hash=unique_run_id,
        repo=backend_url,
        frontier_url=frontier_url,
        experiment=unique_experiment_name,
    )
    run.name = "integration-test-run"
    run["hparams"] = {"lr": 0.001, "batch_size": 64}
    run.track(0.5, name="loss", step=0, context={"subset": "train"})
    run.track(0.42, name="loss", step=1, context={"subset": "train"})
    run.track(0.88, name="accuracy", step=0, context={"subset": "val"})
    run.add_tag("integration-test")
    run.close()

    # Poll backend for run (ingestion worker must have processed)
    for _ in range(40):
        if _backend_has_run(backend_url, unique_run_id):
            break
        time.sleep(0.5)
    else:
        pytest.skip(
            "Ingestion worker may not be running; run did not appear in backend"  # ty:ignore[too-many-positional-arguments]
        )  # ty:ignore[invalid-argument-type]

    # Assert run info and traces
    info = httpx.get(
        f"{backend_url}/api/v1/rest/runs/{unique_run_id}/info/", timeout=5
    ).json()
    assert info.get("props", {}).get("name") == "integration-test-run"
    traces_dict = info.get("traces") or {}
    metric_traces = traces_dict.get("metric") or []
    trace_names = {t.get("name") or t.get("trace_name") for t in metric_traces}
    assert "loss" in trace_names
    assert "accuracy" in trace_names


def test_run_write_api_description_remove_tag_log(
    backend_url: str,
    frontier_url: str,
    unique_run_id: str,
    unique_experiment_name: str,
) -> None:
    """Exercise run.description, run.experiment setter, log_info/log_warning, remove_tag; assert via backend."""
    run = Run(
        run_hash=unique_run_id,
        repo=backend_url,
        frontier_url=frontier_url,
        experiment=unique_experiment_name,
    )
    run.name = "write-api-test-run"
    run["hparams"] = {"epochs": 3}
    run.track(0.1, name="loss", step=0)
    run.add_tag("to-remove")
    run.add_tag("keep")
    run.description = "Integration description"
    run.experiment = unique_experiment_name
    run.log_info("info message")
    run.log_warning("warning message")
    run.remove_tag("to-remove")
    run.close()

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
    assert info.get("props", {}).get("description") == "Integration description"
    tags = info.get("props", {}).get("tags") or []
    tag_names = [t.get("name") for t in tags if t.get("name")]
    assert "keep" in tag_names
    assert "to-remove" not in tag_names

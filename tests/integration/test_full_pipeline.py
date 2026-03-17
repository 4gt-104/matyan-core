"""Integration tests: Full pipeline Client → Frontier → Kafka → Worker → FDB → Backend read.

Requires: Backend, Frontier, Kafka, ingestion worker, FDB.
"""

from __future__ import annotations

import time

import httpx
import pytest


def _backend_has_run(backend_url: str, run_id: str) -> bool:
    try:
        r = httpx.get(f"{backend_url}/api/v1/rest/runs/{run_id}/info/", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def test_full_pipeline_run_track_close_then_read_via_backend(
    backend_url: str,
    frontier_url: str,
    http_transport,
    unique_run_id: str,
    unique_experiment_name: str,
) -> None:
    """Create Run, track metrics and props, close; poll backend; assert run and metric data."""
    from matyan_client.run import Run

    run = Run(
        run_hash=unique_run_id,
        repo=backend_url,
        frontier_url=frontier_url,
        experiment=unique_experiment_name,
    )
    run.name = "full-pipeline-test"
    run["hparams"] = {"lr": 0.002, "epochs": 10}
    run.track(0.7, name="loss", step=0, context={"subset": "train"})
    run.track(0.55, name="loss", step=1, context={"subset": "train"})
    run.track(0.92, name="accuracy", step=0, context={"subset": "val"})
    run.add_tag("pipeline-test")
    run.close()

    for _ in range(40):
        if _backend_has_run(backend_url, unique_run_id):
            break
        time.sleep(0.5)
    else:
        pytest.skip(
            "Ingestion worker may not be running; run did not appear in backend"  # ty:ignore[too-many-positional-arguments]
        )  # ty:ignore[invalid-argument-type]

    info = http_transport.get_run_info(unique_run_id)
    assert info.get("props", {}).get("name") == "full-pipeline-test"
    assert info.get("params", {}).get("hparams", {}).get("lr") == 0.002
    assert info.get("params", {}).get("hparams", {}).get("epochs") == 10

    traces = info.get("traces") or {}
    metric_traces = traces.get("metric") or []
    trace_names = {t.get("name") or t.get("trace_name") for t in metric_traces}
    assert "loss" in trace_names
    assert "accuracy" in trace_names

    tags = info.get("props", {}).get("tags") or []
    tag_names = [t.get("name") for t in tags if t.get("name")]
    assert "pipeline-test" in tag_names


def test_run_read_api_via_repo_get_run(
    backend_url: str,
    frontier_url: str,
    unique_run_id: str,
    unique_experiment_name: str,
) -> None:
    """Create run, wait for backend; get Run via Repo.get_run and assert all read API."""
    from matyan_client.repo import Repo
    from matyan_client.run import Run

    run = Run(
        run_hash=unique_run_id,
        repo=backend_url,
        frontier_url=frontier_url,
        experiment=unique_experiment_name,
    )
    run.name = "read-api-test-run"
    run["hparams"] = {"lr": 0.001, "batch_size": 32}
    run.track(0.5, name="loss", step=0, context={"subset": "train"})
    run.track(0.9, name="accuracy", step=0, context={"subset": "val"})
    run.add_tag("read-api-test")
    run.close()

    for _ in range(40):
        if _backend_has_run(backend_url, unique_run_id):
            break
        time.sleep(0.5)
    else:
        pytest.skip(
            "Ingestion worker may not be running; run did not appear in backend"  # ty:ignore[too-many-positional-arguments]
        )  # ty:ignore[invalid-argument-type]

    repo = Repo(backend_url)
    try:
        run_read = repo.get_run(unique_run_id)
        assert run_read is not None

        assert run_read.hash == unique_run_id
        assert run_read.props.get("name") == "read-api-test-run"
        exp_from_props = run_read.props.get("experiment") or {}
        exp_name = (
            exp_from_props.get("name") if isinstance(exp_from_props, dict) else None
        )
        assert exp_name == unique_experiment_name

        props = run_read.props
        assert isinstance(props, dict)
        assert "name" in props
        assert "tags" in props
        assert "creation_time" in props
        assert props.get("active") is False
        assert "read-api-test" in run_read.tags

        assert run_read["hparams"] == {"lr": 0.001, "batch_size": 32}
        assert run_read.get("hparams") == {"lr": 0.001, "batch_size": 32}
        assert run_read.get("nonexistent", 42) == 42

        metrics = run_read.metrics()
        assert len(metrics) >= 2
        metric_names = {m.get("name") or m.get("trace_name") for m in metrics}
        assert "loss" in metric_names
        assert "accuracy" in metric_names

        loss_trace = run_read.get_metric("loss", context={"subset": "train"})
        assert loss_trace is not None
        assert loss_trace.get("name") == "loss"

        iter_info = list(run_read.iter_metrics_info())
        assert len(iter_info) >= 2
        names_ctxs = [(n, c) for n, c, _ in iter_info]
        assert ("loss", {"subset": "train"}) in names_ctxs

        seq_info = run_read.collect_sequence_info("metric")
        assert "metric" in seq_info
        assert isinstance(seq_info["metric"], list)

        run_read.close()
    finally:
        repo._http.close()

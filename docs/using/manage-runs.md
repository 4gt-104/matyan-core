---
icon: material/folder-cog
---

# Manage runs

## Create runs

`Run` (see [Concepts](../understanding/concepts.md)) is the main object for tracking ML training metadata (metrics, hyperparameters, etc.).

When you create a `Run`, the client sends data to the **Matyan frontier** (ingestion) and **backend** (metadata). No local repo is created; storage is on the server (FoundationDB).

```python
from matyan_client import Run

run = Run(
    repo="http://localhost:53800",  # backend URL
    experiment="experiment_name",
    system_tracking_interval=10,    # seconds; set to None to disable
    capture_terminal_logs=True,     # default True
)
```

- **repo** — Backend URL (or set `MATYAN_BACKEND_URL`). The client also uses the frontier URL for tracking (from `MATYAN_FRONTIER_URL` or config).
- **experiment** — Experiment name to group runs.
- **system_tracking_interval** — Interval for CPU/GPU/memory tracking; `None` to disable.
- **capture_terminal_logs** — Whether to capture and send stdout/stderr to the UI.

You can use multiple `Run` instances in one script (e.g. for hyperparameter search). See [Configure runs](configure-runs.md) for more options.

## Continue runs

Each run has a unique `hash`. To continue logging to an existing run, pass `run_hash`:

```python
from matyan_client import Run

run = Run(run_hash="existing_run_hash", repo="http://localhost:53800")
run.track(0.5, name="loss", step=100)
run.close()
```

You can get run hashes from the UI or via `Repo(...).iter_runs()`.

## Delete runs

Delete runs via the **backend API** or the SDK.

**Using the client (SDK):**

```python
from matyan_client import Repo

repo = Repo("http://localhost:53800")
repo.delete_run("run_hash")
repo.delete_runs(["run_hash_1", "run_hash_2"])
```

**Using the CLI** (backend/HTTP): use the backend’s run-delete endpoint (e.g. `DELETE /api/v1/runs/{run_hash}`) or any wrapper script that calls it.

Deleting a run removes it from FoundationDB and triggers async cleanup (e.g. S3 blobs) via control workers.

## Pruning / cleanup

Indexes and metadata are maintained by the backend and workers; there is no separate “prune” CLI. If you need to rebuild indexes (e.g. after recovery), use the backend’s **reindex** command (see [References — CLI](../refs/cli.md)).

## Backup and restore

Data lives in FoundationDB and S3 on the server. You can create portable backups with **matyan-backend backup** and restore them with **matyan-backend restore** (direct into FDB + S3) or **matyan restore-reingest** (replay through the ingestion pipeline). See [Backups and restore](backups-and-restore.md) for the full workflow.

---
icon: material/tune
---

# Configure runs

Configure a `Run` at creation time: backend and frontier URLs, experiment, run hash (to resume), system tracking, and reproducibility options.

## Backend URL vs Frontier URL

Matyan uses **two** server endpoints:

| URL | Service | Used for |
|-----|---------|----------|
| **Backend URL** | matyan-backend (REST API) | Metadata and queries: run props, tags, `iter_runs()`, `query_metrics()`, delete run, experiment list. |
| **Frontier URL** | matyan-frontier (WebSocket + REST) | Ingestion: `track()`, params, metrics, log lines, artifact presign. |

- **Backend** — Reads and writes run metadata in FoundationDB; handles control operations. Default port **53800**.
- **Frontier** — Accepts WebSocket connections and presign requests; publishes to Kafka. Default port **53801**. Clients never talk to Kafka directly; the frontier is the ingestion gateway.

### How URLs are chosen (Run)

When you create a `Run`, URLs are resolved as follows:

1. **Backend URL** = `repo` argument, or if not set → **`MATYAN_BACKEND_URL`** environment variable, or if unset → `http://localhost:53800`.
2. **Frontier URL** = `frontier_url` argument, or if not set → `repo` argument (so one URL is used for both), or if not set → **`MATYAN_FRONTIER_URL`** environment variable, or if unset → `http://localhost:53801`.

So:

- **Same base URL** — If backend and frontier are served from the same origin (e.g. `https://matyan.example.com` with path-based routing), pass only `repo`; the client will use it for both. For **local dev** with default ports (backend 53800, frontier 53801), pass both `repo="http://localhost:53800"` and `frontier_url="http://localhost:53801"`, or set `MATYAN_BACKEND_URL` and `MATYAN_FRONTIER_URL`.
- **Different hosts** — Pass `repo="https://api.matyan.example.com"` and `frontier_url="https://ingest.matyan.example.com"`. Or set `MATYAN_BACKEND_URL` and `MATYAN_FRONTIER_URL` and omit both arguments.
- **Env-only** — Set `MATYAN_BACKEND_URL` and `MATYAN_FRONTIER_URL`; then `Run()` with no URL arguments uses them.

### Repo class

`Repo(url)` takes a single URL: the **backend** URL. It uses the same fallback: `url` or **`MATYAN_BACKEND_URL`** (then default `http://localhost:53800`). `Repo` only talks to the backend (queries, delete, etc.); it does not open a WebSocket to the frontier.

## Run constructor arguments

All arguments are optional. Keyword-only except `run_hash` (positional or keyword).

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| **run_hash** | optional `str` | `None` | Resume or update an existing run by its hash. If omitted, a new run is created with an auto-generated hash. |
| **repo** | optional `str` | `None` | Backend URL (e.g. `http://localhost:53800`). Also used as the frontier URL if `frontier_url` is not set. Overrides `MATYAN_BACKEND_URL` when provided. |
| **frontier_url** | optional `str` | `None` | Frontier URL (e.g. `http://localhost:53801`). Used for WebSocket and presign. Overrides `repo` and `MATYAN_FRONTIER_URL` when provided. |
| **read_only** | `bool` | `False` | If `True`, the run does not open a WebSocket or send data; use for read-only inspection (e.g. read props, tags, metrics from the backend). |
| **experiment** | `str \| None` | `None` | Experiment name. Sent to the frontier on create; used for grouping and MatyanQL. Omitted means the backend default (e.g. `"default"`). |
| **force_resume** | `bool` | `False` | If `True`, when using an existing `run_hash`, signal that the run is being resumed (e.g. after a crash). Can affect backend/frontier handling of the run. |
| **system_tracking_interval** | `float \| None` | `None` | Seconds between system metrics (CPU, memory, etc.). `None` disables system tracking. |
| **log_system_params** | `bool` | `False` | If `True`, log environment variables, executables, CLI args, installed packages, and git info for reproducibility (stored under `__system_params`). |
| **capture_terminal_logs** | `bool` | `True` | If `True`, capture stdout/stderr and send terminal log lines to the UI. Set to `False` to disable. |

Example:

```python
from matyan_client import Run

run = Run(
    repo="http://localhost:53800",
    frontier_url="http://localhost:53801",  # optional if same as repo or set via MATYAN_FRONTIER_URL
    experiment="fraud-detection",
    log_system_params=True,
    system_tracking_interval=30,
)
```

## Reusing an existing run

Pass `run_hash` to continue logging to that run:

```python
run = Run(run_hash="508c5b29-02c7-4875-a157-f099ea193bfa")
for i in range(100):
    run.track(i, step=i, name="test")
run.close()
```

## Experiments

Group runs under an experiment:

```python
run = Run(experiment="baseline-v2")
```

Query and filter by experiment in the UI and via MatyanQL (see [Search (MatyanQL)](search.md)).

## Tags and params

Add or remove tags (via backend):

```python
run = Run()
run.add_tag("v1.0")
run.add_tag("production-candidate")

run.close()

# On an existing run (by hash)
run = Run(run_hash="...", repo="http://localhost:53800")
run.remove_tag("old-tag")
run.add_tag("new-tag")

run.close()
```

Set arbitrary params:

```python
run["hparams"] = {"lr": 0.01, "batch_size": 32}
run["custom_key"] = "some value"
```

## Reproducibility (system params)

Set `log_system_params=True` to log environment variables, executables, CLI arguments, installed packages, and git info. These appear under run params and can be used in search.

```python
run = Run(log_system_params=True)
```

Example MatyanQL: `run.__system_params.git_info.branch == 'feature/testing'`.

## Terminal logs

Terminal output (stdout/stderr) is captured and sent to the UI by default. To disable:

```python
run = Run(capture_terminal_logs=False)
```

View logs in the Matyan UI on the run detail page.

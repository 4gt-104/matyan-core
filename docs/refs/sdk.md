---
icon: material/language-python
---

# SDK reference (matyan_client)

The Matyan client provides the **Run** and **Repo** API. Install the package `matyan-client` and import from `matyan_client`.

## Main classes

| Class | Description |
|-------|-------------|
| **Run** | One experiment run. Create with `Run(repo=backend_url, experiment=..., ...)`. Use `run["hparams"]`, `run.track()`, `run.add_tag()`, `run.log_artifact()`, `run.log_info()`, etc. |
| **Repo** | Handle to the backend. Create with `Repo(backend_url)`. Use `repo.iter_runs()`, `repo.query_metrics(query)`, `repo.delete_run(hash)`, etc. |

## Run constructor (main args)

- **repo** — Backend URL (or set `MATYAN_BACKEND_URL`).
- **frontier_url** — Frontier URL for ingestion (or set `MATYAN_FRONTIER_URL`).
- **run_hash** — Resume an existing run.
- **experiment** — Experiment name.
- **read_only** — If True, no tracking.
- **system_tracking_interval** — Seconds; None to disable system metrics.
- **log_system_params** — Log env, packages, git, etc.
- **capture_terminal_logs** — Send stdout/stderr to the UI.

For all options and URL resolution, see [Configure runs](../using/configure-runs.md).

## Run methods (summary)

- **track(value, name=..., step=..., context=..., epoch=...)** — Log a metric or object.
- **add_tag(tag)** / **remove_tag(tag)** — Tags (via backend).
- **log_artifact(path, name=...)** / **log_artifacts(dir, name=...)** — Upload files to S3 via presigned URLs.
- **log_info(msg)** / **log_warning(msg)** / **log_error(msg)** / **log_debug(msg)** — Log messages.
- **close()** — Flush and mark run finished.

## Object types (import from matyan_client)

- **Image**, **Audio**, **Text**, **Distribution**, **Figure** — Use with `run.track(...)`.

## Repo methods (summary)

- **iter_runs()** — Iterate runs.
- **query_metrics(query)** — MatyanQL metric query; returns an iterable over run/metric collections.
- **delete_run(run_hash)** / **delete_runs([hashes])** — Delete runs (via backend).

For full signatures and optional args, see the **matyan_client** source (e.g. `extra/matyan-client/src/matyan_client/run.py` and `repo.py`).

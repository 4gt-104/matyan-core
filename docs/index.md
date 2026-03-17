---
icon: material/rocket
---

<p align="center">
  <img alt="Matyan Logo" width="280" src="static/logo.svg" class="gh-light-mode-only">
  <img alt="Matyan Logo" width="280" src="static/logo.svg" class="gh-dark-mode-only">
</p>

<h1 align="center">Matyan</h1>

<p align="center">
  <strong>Experiment tracking and ML observability — Aim-compatible UI and SDK with a scalable backend.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/matyan-client">
    <img src="https://img.shields.io/pypi/v/matyan-client.svg" alt="PyPI version">
  </a>
  <a href="https://pypi.org/project/matyan-client">
    <img src="https://img.shields.io/pypi/pyversions/matyan-client.svg" alt="Python versions">
  </a>
  <a href="https://github.com/4gt-104/matyan-core/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/4gt-104/matyan-core" alt="License">
  </a>
</p>

---

**Matyan** is a fork of [Aim](https://github.com/aimhubio/aim) (aimhub) that **reimplements the backend** while keeping the **frontend (UI) and Python SDK API unchanged**. You get the same workflows and dashboards, with a modern stack: FoundationDB, Kafka, and stateless services.

## ✨ Features

- **Aim-compatible API** — Same `Run`, `Repo`, and `track()` surface as the Aim SDK; minimal code changes to switch.
- **Lightweight client** — `matyan-client` has minimal core dependencies (no ML frameworks by default); image, audio, figure, and framework adapters (PyTorch, Keras, etc.) are **optional extras** so you only install what you need.
- **Scalable storage** — FoundationDB instead of RocksDB/SQLite; horizontally scalable, transactional.
- **Decoupled UI** — React-based Aim UI served separately; backend is a stateless REST API.
- **Async ingestion** — Training clients send data to a **frontier** (WebSocket + presigned S3); Kafka and workers write to FDB. No direct DB access from clients.
- **Index-accelerated search** — Tier 1 (experiment, tag, archived, etc.) and Tier 2 (hyperparameter) indexes; MatyanQL runs as index scan + in-memory filter.
- **Full artifact support** — Metrics, hyperparameters, images, audio, figures, distributions, text, terminal logs, and structured log records.
- **Python-only backend** — FastAPI, aiokafka, FoundationDB Python bindings, boto3; no Cython, no embedded C.

## 📦 Installation

### Run the full stack (Docker Compose)

Infrastructure (FoundationDB, Kafka, MinIO) plus backend, frontier, and workers:

```bash
git clone https://github.com/4gt-104/matyan-core.git
cd matyan-core
docker compose build
docker compose up -d
```

Then open the UI (default: backend on port 53800, UI may be served separately — see [Getting started](getting-started.md)).

### Python client (track from your training code)

Install the Matyan client in your project:

```bash
python3 -m pip install matyan-client
# or with uv:
uv add matyan-client
```

Optional: set `MATYAN_FRONTIER_URL` and `MATYAN_BACKEND_URL` (e.g. `http://localhost:53801`, `http://localhost:53800`) if not using defaults.

## 🚀 Quick Start

### With the Python client

Same API as Aim: create a run, set hyperparameters, track metrics and custom objects, then close. Full example: [Getting started](getting-started.md).

```python
from matyan_client import Run

run = Run(experiment="baseline")
run["hparams"] = {"lr": 0.01, "batch_size": 32}
run.track(0.5, name="loss", step=0, context={"subset": "train"})
run.close()
```

Query runs and metrics via `Repo` (same as Aim):

```python
from matyan_client import Repo

repo = Repo("http://localhost:53800")  # backend URL
for run in repo.iter_runs():
    print(run.hash, run["hparams"])
```

### With Docker Compose (full stack)

1. Start infrastructure and services (see [Installation](#installation)).
2. Ensure the **frontier** is reachable at `MATYAN_FRONTIER_URL` (e.g. `http://localhost:53801`) and the **backend** at `MATYAN_BACKEND_URL` (e.g. `http://localhost:53800`).
3. Use the client as above; tracking goes through the frontier (WebSocket), metadata and queries go to the backend (REST).

See [Getting started](getting-started.md) for detailed setup and [Architecture](architecture.md) for data flow and components.

## 🏗️ Architecture

| Component | Role |
|-----------|------|
| **matyan-backend** | REST API: reads and control operations (delete run, rename experiment). Reads from FoundationDB; control writes emit Kafka events for async side effects (e.g. S3 cleanup). |
| **matyan-frontier** | Ingestion gateway: WebSocket for metrics/params, presigned S3 URLs for large blobs. Publishes to Kafka only. |
| **Workers** | Kafka consumers: *ingestion* (data → FDB), *control* (control-events → S3 cleanup, etc.). |
| **matyan-client** | Python SDK; same API as Aim. Uses frontier for tracking, backend for metadata and queries. |
| **matyan-ui** | Aim React UI; talks to matyan-backend. |

**Data flow:** Reads: UI → backend → FoundationDB. Writes: client → frontier → Kafka → workers → FoundationDB (and S3 for blobs).

## 📚 Documentation

- [Getting started](getting-started.md) — Install client, run the stack (Docker Compose), first run, open UI, env vars, smoke tests; [integrations](quick-start/integrations.md), [supported types](quick-start/supported-types.md).
- [Using Matyan](using/manage-runs.md) — Manage runs, configure, query, search (MatyanQL), remote tracking, [logging](using/logging.md), [artifacts](using/artifacts.md).
- [Matyan UI](ui/overview.md) — Explorers and run management (same as Aim UI).
- [Understanding Matyan](understanding/overview.md) — Concepts, [data storage](understanding/data-storage.md).
- [Architecture](architecture.md) — Components and data flow in detail.
- [Advanced](advanced/index.md) — Component-level design: [Backend](advanced/backend.md), [Frontier](advanced/frontier.md), [Workers](advanced/workers.md), [FoundationDB](advanced/foundationdb.md), [Kafka](advanced/kafka.md), [S3 and blobs](advanced/s3-blobs.md), [UI](advanced/ui.md), [Client SDK](advanced/client-sdk.md).
- [Production deployment](deployment/production.md) — Deploy to Kubernetes with the Helm chart (values, secrets, scaling).
- [API](api.md) — REST and streaming endpoints.
- [References](refs/cli.md) — [Glossary](glossary.md) (key terms: Run, Repo, sequence, context, MatyanQL), [CLI](refs/cli.md) (backend, frontier, workers), [SDK](refs/sdk.md) (matyan_client), [Environment variables](refs/env-variables.md) (all components).

## 🤝 Contributing

Contributions are welcome. For large changes, open an issue first to align on design. See [Contributing](contributing.md) and the repository for development setup and tests.

## 📄 License

See the [LICENSE](https://github.com/4gt-104/matyan-core/blob/main/LICENSE) file in the repository.

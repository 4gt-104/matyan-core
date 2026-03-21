---
icon: material/rocket-launch
---

# Getting started

Run Matyan locally with Docker Compose and connect the client. This page covers installing the client, starting the stack, and your first run.

## Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for the client)

## Install the client

```bash
python3 -m pip install matyan-client
# or with uv:
uv add matyan-client
```

**matyan-client** requires **Python 3.10+**. Install **only** `matyan-client`. Do not install other Matyan packages (backend, frontier, api-models, etc.) on the machine where you run your training code — those run in the Docker stack or on your server. The client is a standalone package that talks to the frontier and backend over the network.

The client provides the `Run`, `Repo`, and `track()` API and sends data to the Matyan **frontier** (ingestion) and **backend** (metadata and queries).

## Start the stack

From the repository root:

```bash
git clone https://github.com/4gt-104/matyan-core.git
cd matyan-core
./dev/compose-cluster.sh up -d
```

!!! note "Host network mode"
    The Compose file uses **host network mode** for infrastructure services (FoundationDB, Kafka, RustFS) and some app services. Containers share the host network, so they listen on `localhost` and the client can use `http://localhost:53800` (backend) and `http://localhost:53801` (frontier). On Linux this works out of the box; on macOS/Windows, host mode may behave differently — use the host's IP or adjust for your environment.

This starts:

- **FoundationDB** (single-node, dev)
- **Kafka** (single broker; topics `data-ingestion`, `control-events`)
- **MinIO** (S3-compatible storage for blobs)
- **matyan-backend** (REST API, default port 53800)
- **matyan-frontier** (ingestion gateway, default port 53801)
- **matyan-ui** (FastAPI web server, default port 8000)
- **Ingestion and control workers** (Kafka consumers)

## Configure the client

Set environment variables (or pass URLs to `Run` / `Repo`):

```bash
export MATYAN_BACKEND_URL=http://localhost:53800
export MATYAN_FRONTIER_URL=http://localhost:53801
```

## Try it

Create a run and track some data:

```python
from matyan_client import Run

run = Run(experiment="my_experiment")
run["hparams"] = {"learning_rate": 0.001, "batch_size": 32}
for i in range(10):
    run.track(i, name="loss", context={"subset": "train"})
run.close()
```

Data is sent to the frontier (WebSocket) and backend (REST); workers persist it to FoundationDB. See [Supported types](quick-start/supported-types.md) for metrics, images, audio, and other objects.

## Browsing results in the UI

Open the Matyan UI in your browser at `http://localhost:8000`. Use the Metrics explorer, run search, and run details.

## Smoke tests (optional)

From the `extra/matyan-backend` with the stack running:

```bash
uv run python scripts/smoke_test.py   # FDB + S3
uv run python scripts/smoke_kafka.py # Kafka
```

## Next

- [Integrations](quick-start/integrations.md) — Use Matyan with PyTorch Lightning, Keras, Hugging Face, and other frameworks.
- [Manage runs](using/manage-runs.md) — Create, continue, and delete runs.
- [Architecture](architecture.md) — Components and data flow.
- [Production deployment](deployment/production.md) — Deploy to Kubernetes with the Helm chart.
- [References](refs/cli.md) — CLI and SDK.

---
icon: material/cloud
---

# Remote tracking (architecture)

Matyan is built for **remote** tracking: training runs send data to a central **frontier** and **backend**; nothing is stored in a local repo.

## Overview

- **Frontier** — Ingestion gateway. Accepts WebSocket connections from clients for metrics, params, and small payloads; issues presigned blob URLs for large blobs. Publishes all incoming data to **Kafka**.
- **Backend** — REST API for reads and control (delete run, rename experiment, etc.). Reads from **FoundationDB**; writes go to FDB and emit Kafka events for async side effects (e.g. blob storage cleanup).
- **Workers** — Consume Kafka: **ingestion** workers write to FDB (and blob storage refs); **control** workers perform cleanup and other side effects.

Clients never talk to Kafka or FDB directly. They only need the **frontier URL** (for tracking) and **backend URL** (for metadata and queries).

## Prerequisites

- A running Matyan deployment: frontier, backend, Kafka, FDB, and workers (see [Getting started](../getting-started.md)).
- The machine running the frontier must accept WebSocket (and optionally HTTP for presign) on the configured port (default 53801).
- The backend must accept HTTP on its port (default 53800).

## Client setup

Point the client at your backend (and optionally frontier). The client uses the **backend** for metadata and queries and the **frontier** for high-volume tracking.

**Environment variables:**

```bash
export MATYAN_BACKEND_URL=http://your-backend:53800
export MATYAN_FRONTIER_URL=http://your-frontier:53801
```

**In code:**

```python
from matyan_client import Run

run = Run(repo="http://your-backend:53800")
# frontier_url is resolved from config or same host; override if needed:
# run = Run(repo="http://backend:53800", frontier_url="http://frontier:53801")

run["hparams"] = {"lr": 0.001, "batch_size": 32}
for step in range(100):
    run.track(loss, name="loss", step=step, context={"subset": "train"})
run.close()
```

Tracking data goes over WebSocket to the frontier; metadata (e.g. tags, run props) and queries go to the backend over HTTP.

## SSL / HTTPS

For production, put the frontier and backend behind TLS-terminating proxies (or configure the services with SSL). Configure the client to use `https://` URLs for `MATYAN_BACKEND_URL` and `MATYAN_FRONTIER_URL`. If you use self-signed certificates, you may need to configure the HTTP/WebSocket client to accept them (e.g. via environment or client options; see the matyan_client docs).

## Summary

- **No local repo** — All data is stored on the server (FDB + blob storage).
- **Frontier** — WebSocket + presigned blob urls; publishes to Kafka.
- **Backend** — REST API; reads/writes FDB; emits control events to Kafka.
- **Workers** — Consume Kafka and persist to FDB (and blob storage). No client configuration needed beyond frontier and backend URLs.

---
icon: material/server
---

# Backend

The **matyan-backend** is the main REST API service. It serves all read traffic from the UI and the client SDK, and it handles control operations (delete run, rename experiment, add/remove tags, etc.). It is **stateless** and can be scaled horizontally behind a load balancer.

## Role

- **Read path** — Queries from the UI (run list, metrics, custom objects, logs) and from the client (e.g. `Repo.iter_runs()`, `query_metrics()`) hit the backend. The backend reads from **FoundationDB** and, for blob content (images, audio, etc.), fetches bytes from **S3/GCS/Azure** and streams them back. No Kafka involvement on the read path.
- **Control path** — Mutations initiated by the UI (delete run, archive, rename experiment, delete tag) are handled **synchronously** by the backend: it writes to FDB and publishes a **control event** to Kafka. Control workers consume that topic and perform **async side effects** (e.g. S3/GCS/Azure blob cleanup after a run is deleted).

## Architectural decisions

### Single service for reads and control

Reads and control operations share one API and one deployment. This keeps the API surface simple (one base URL, one auth model) and avoids splitting the “source of truth” between services: the backend is the only component that both reads from FDB and performs synchronous control writes. The UI and client need to talk to only one place for all REST operations.

### Synchronous control writes to FDB

When a user deletes a run or renames an experiment, the backend **immediately** updates FDB (e.g. marks the run as deleted, updates experiment name). The user sees the effect right away. This gives **immediate consistency** for control operations and keeps the UI responsive. Async work (storage cleanup, index updates that are deferred) is handled by control workers so that the HTTP response is not blocked on slow or external operations.

### Control events to Kafka (not FDB-only)

After writing the control mutation to FDB, the backend publishes a **control event** (e.g. `run_deleted`) to the **control-events** Kafka topic. Control workers consume these events and perform side effects (e.g. deleting blobs in S3/GCS/Azure for the removed run). Doing this asynchronously avoids holding the HTTP request until S3/GCS/Azure deletions finish and allows retries and backpressure if S3/GCS/Azure or the worker is slow. The “authoritative” state (e.g. “run is deleted”) is already in FDB; Kafka is used only for **triggering side effects**.

### Stateless, horizontally scalable

The backend holds no in-memory session or subscription state. Every request can be served by any replica. Scaling is done by increasing the replica count and using a load balancer. FDB handles transaction conflicts; no coordination between backend replicas is required beyond what FDB provides.

### No direct Kafka consumption in the backend

The backend **produces** to Kafka (control events) but does **not** consume from the data-ingestion topic. Ingestion (metrics, params, blob refs from training) is handled by **ingestion workers**. This keeps the backend focused on serving reads and control and keeps ingestion scaling independent (more workers = more Kafka partitions consumed). The backend never blocks on or depends on ingestion throughput.

### Binary streaming and backward compatibility

The backend reimplements the same REST and **binary streaming** endpoints as the original Aim API so that the existing UI and client contract work unchanged. Streaming uses a custom codec (path-value pairs, type tags, length-prefixed frames). This compatibility is a core requirement so the UI and SDK can switch to Matyan without protocol changes.

## Key implementation details

- **FastAPI** app; lifespan initializes FDB connection and directories, and starts the Kafka producer for control events.
- **Dependencies** — `FdbDb` and `FdbDirs` are injected per request; routes call the **storage** layer (`storage/runs.py`, `storage/sequences.py`, etc.) directly. No separate “service” layer; the API layer is thin.
- **Health** — Readiness probe checks FDB connectivity and Kafka producer state; liveness is a lightweight process check.
- **MatyanQL** — Run and metric search use a **query planner** that chooses Tier 1 or Tier 2 FDB indexes when possible; remaining predicates are evaluated in memory via RestrictedPython.

## Related

- [FoundationDB](foundationdb.md) — Where backend reads and writes.
- [Kafka](kafka.md) — Control-events topic produced by the backend.
- [Workers](workers.md) — Control workers consume control-events and perform storage cleanup.
- [Cloud blob storage](cloud-blob-storage.md) — Backend fetches blob content from S3/GCS/Azure for custom object endpoints.

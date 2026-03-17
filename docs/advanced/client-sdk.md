---
icon: material/language-python
---

# Client SDK (matyan-client)

**matyan-client** is the Python SDK that training code uses to create runs, track metrics and params, log artifacts, and query runs. It preserves the **same API surface** as the original Aim SDK so that existing scripts can switch to Matyan by changing the “repo” target from a local path to the backend (and frontier) URLs. The SDK hides the fact that data goes over the network to the frontier and backend.

## Role

- **Run lifecycle** — `Run(run_hash, repo=...)`, property setters (`run.name`, `run.experiment`, `run["hparams"] = ...`), `run.track(...)`, `run.close()` or context manager.
- **Tracking** — High-volume data (metrics, params, log lines, log records) is sent to the **frontier** over **WebSocket**. Large blobs (images, audio, artifacts) use **presigned S3 URLs** obtained from the frontier via REST; the client uploads directly to S3.
- **Metadata and queries** — Operations that need immediate consistency or query capability (tags, run props, `Repo.iter_runs()`, `query_metrics()`, etc.) go to the **backend** over **HTTP**.
- **Write cache** — The client keeps an in-memory **write cache** so that read-after-write (e.g. `run["hparams"]` right after `run["hparams"] = x`) returns the written value even before ingestion workers have persisted it to FDB.

## Architectural decisions

### Same API as Aim SDK

The goal is **drop-in compatibility**: user code that today does `from aim import Run, Repo` and uses `Run(...)`, `run.track()`, `run["hparams"]`, `Repo(...).iter_runs()` should work with `from matyan_client import Run, Repo` and a `Repo(url=...)` pointing at the Matyan backend (and configured frontier). So:

- **Run**, **Repo**, and the main methods stay the same.
- **Repo** takes a URL (backend) instead of a filesystem path; the client infers or is configured with the frontier URL for ingestion.
- Custom object types (Image, Text, Distribution, Figure, Audio) and helpers (e.g. `log_artifact`) keep the same interface; only the transport (WebSocket + HTTP + S3) changes under the hood.

This minimizes migration cost and keeps documentation and examples reusable.

### WebSocket for tracking, HTTP for metadata and queries

- **WebSocket (frontier)** — Used for create run, log metric, log params, finish run, log terminal line, log record, set run property, add/remove tag. High frequency, low latency, single long-lived connection per run (or per process). The frontier forwards to Kafka; the client does not see Kafka.
- **HTTP (backend)** — Used for run props, tags, `iter_runs()`, `query_runs()`, `query_metrics()`, `delete_run()`, experiment list, etc. These need the backend’s FDB-backed view and/or immediate consistency. One request per operation.
- **Presigned S3** — For blobs, the client calls the frontier’s presign endpoint (HTTP), then uploads to S3 with the returned URL. No blob bytes go over the WebSocket.

So the SDK **routes** each operation to the right transport: “tracking” → frontier WebSocket; “metadata and queries” → backend HTTP; “blob” → frontier presign + S3 PUT.

### Write cache for read-after-write consistency

Because ingestion is **asynchronous** (frontier → Kafka → workers → FDB), a read from the backend (e.g. `run["hparams"]`) right after a write (e.g. `run["hparams"] = {...}`) might not yet see the update. To avoid confusing the user, the client maintains a **write cache** (e.g. keyed by run + dotted path). On read, it checks the cache first; if the key was recently written, it returns the cached value. So the user sees consistent read-after-write from the client’s perspective. The cache is cleared when the run is closed (or when the client decides to invalidate). This is a **client-side** solution; the backend does not need to support “read your own writes” from the same connection.

### No Kafka dependency in the client

The client never links to Kafka or knows about topics. It only needs:

- **Frontier URL** — For WebSocket and presign.
- **Backend URL** — For HTTP API.
- **S3 endpoint** — Only if the presigned URL points to a custom endpoint (e.g. MinIO); often the URL is pre-filled by the frontier.

So the client is a thin “HTTP + WebSocket + S3” client with an Aim-like API; all messaging and durability are handled by the frontier and workers.

### Connection and lifecycle

- **WebSocket** — Typically one connection per run (or shared per process). The client may reconnect on failure and retry sends. Batching (multiple messages in one frame) and backpressure (queue limits) are implementation details to avoid overloading the frontier or losing messages.
- **Run finish** — When the user calls `run.close()` or exits the context manager, the client sends a “finish run” message over the WebSocket so that the frontier and workers can finalize the run (e.g. mark active=false). Pending messages should be flushed before closing.

## Related

- [Frontier](frontier.md) — Receives WebSocket and presign requests from the client.
- [Backend](backend.md) — Receives HTTP metadata and query requests.
- [S3 and blobs](s3-blobs.md) — Client uploads blobs via presigned URLs.
- [SDK reference](../refs/sdk.md) — API summary and usage.

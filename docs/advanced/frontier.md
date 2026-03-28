---
icon: material/gate
---

# Frontier

The **matyan-frontier** is the **ingestion gateway** for training clients. It accepts WebSocket connections and REST calls (e.g. presigned URL requests) and forwards all ingestion traffic into **Kafka**. Clients never talk to Kafka or FDB directly; the frontier is the single entry point for writing training data.

## Role

- **WebSocket** — Clients open a WebSocket to the frontier per run (e.g. `WS /api/v1/ws/runs/{run_id}`) and send JSON messages: create run, log metric, log hyperparameters, finish run, log terminal lines, log records, set run properties, add/remove tags. The frontier validates each message, wraps it in an **IngestionMessage** envelope, and publishes to the **data-ingestion** Kafka topic (partitioned by `run_id`).
- **Presigned blob URLs** — For large blobs (images, audio, artifacts), the client calls `POST /api/v1/rest/artifacts/presign`. The frontier generates a presigned blob PUT URL and publishes a **blob_ref** message to Kafka so that ingestion workers can record the blob key in FDB after the client uploads. The client then uploads the blob directly to the blob storage; the frontier does not stream blob bytes.
- **No storage** — The frontier does not write to FDB or blob storage. It only produces to Kafka. All persistence is done by **ingestion workers** and the **backend** (for control).

## Architectural decisions

### Single ingestion gateway (clients never see Kafka)

Training code runs in user environments (laptops, training clusters) where we do not want to expose Kafka (credentials, network, operational complexity). The frontier exposes a **simple contract**: WebSocket + REST. Kafka stays inside the infrastructure. Only the frontier (and workers) need Kafka client config; the matyan-client only needs the frontier URL.

### WebSocket for high-volume, low-latency tracking

Metrics and params are sent as small JSON messages at high frequency. WebSocket avoids per-call HTTP overhead and keeps a long-lived connection so the client can push many messages without reconnecting. The frontier batches or forwards messages to Kafka as they arrive; partitioning by `run_id` keeps all messages for a given run in order on one partition.

### Presigned URLs for large blobs

Blob payloads (images, audio, figures) can be large. Sending them through the frontier would require the frontier to buffer and forward to S3/GCS/Azure or Kafka, increasing latency and memory. Instead, the frontier issues a **presigned S3/GCS/Azure PUT URL**; the client uploads directly to S3/GCS/Azure. The frontier only publishes a **blob_ref** (bucket, key, run, sequence, etc.) to Kafka so that workers can write the reference into FDB. This keeps the frontier lightweight and avoids double bandwidth (client → frontier → S3/GCS/Azure).

### Stateless, horizontally scalable

Each WebSocket connection is independent. The frontier does not store run state; it only validates and forwards. Multiple frontier replicas can run behind a load balancer; WebSocket stickiness (if used) is for connection affinity only, not for correctness. Kafka handles durability and ordering per partition.

### Same API surface as the original ingestion contract

The WebSocket message types and REST presign endpoint are designed so that **matyan-client** can use the same logical API (e.g. `run.track()`, `run.log_artifact()`) while sending to the frontier instead of a local process. This keeps the SDK API stable and allows a drop-in replacement for the original stack.

## Key implementation details

- **FastAPI** app with a WebSocket route and a REST route for presign; lifespan manages the Kafka producer.
- **Validation** — Incoming messages are validated with Pydantic (e.g. `CreateRunWsRequest`, `LogMetricWsRequest`); invalid messages are rejected with an error response.
- **Partitioning** — Kafka messages are produced with `run_id` as the partition key so that all events for one run go to the same partition and are consumed in order by a single ingestion worker (per partition).
- **Batching** — The frontier can accept JSON arrays (batches) in one WebSocket frame and publish each item as a separate Kafka message to keep client batching simple.

## Related

- [Kafka](kafka.md) — data-ingestion topic produced by the frontier.
- [Workers](workers.md) — Ingestion workers consume from data-ingestion and write to FDB.
- [Cloud blob storage](cloud-blob-storage.md) — Presigned URLs and blob_ref flow.
- [Client SDK](client-sdk.md) — How the client talks to the frontier (WebSocket + REST).

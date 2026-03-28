---
icon: material/cog
---

# Advanced — components and design

This section explains **each major component** of Matyan and the **architectural decisions** behind it. Use it when you need to understand why the system is built the way it is, how pieces interact, or how to operate or extend a specific part.

## Who this is for

- **Operators** — Deploying, scaling, or debugging backend, frontier, or workers.
- **Contributors** — Adding features or changing behavior of a service.
- **Integrators** — Connecting other systems (e.g. custom clients, internal tooling) to Matyan.

## Components covered

| Page | Component | Focus |
|------|-----------|--------|
| [Backend](backend.md) | matyan-backend | REST API, reads from FDB, control operations, why sync FDB + Kafka for control. |
| [Frontier](frontier.md) | matyan-frontier | Ingestion gateway, WebSocket, Kafka producer, presigned S3/GCS/Azure; why clients never see Kafka. |
| [Workers](workers.md) | Ingestion & control workers | Kafka consumers, FDB writes, cloud blob storage cleanup; consumer groups, idempotency, scaling. |
| [FoundationDB](foundationdb.md) | FDB storage layer | Why FDB, key space, indexes, transactions, schema and evolution. |
| [Kafka](kafka.md) | Message broker | Two topics, partitioning, ordering guarantees, why async ingestion. |
| [Cloud blob storage](cloud-blob-storage.md) | Blob storage | Presigned URLs, frontier’s role, control-worker cleanup. |
| [UI](ui.md) | matyan-ui | React app, backend-only, polling, no WebSocket to UI. |
| [Client SDK](client-sdk.md) | matyan-client | Aim-compatible API, write cache, WebSocket vs HTTP routing. |

## How to read

- Start with [Architecture](../architecture.md) for the high-level picture.
- Use this section to drill into a single component and its rationale.
- Cross-links between pages point to related components and decisions.

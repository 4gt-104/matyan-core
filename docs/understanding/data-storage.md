---
icon: material/database
---

# Data storage — where Matyan data lives

Matyan does **not** use a local repo directory or embedded databases (e.g. RocksDB/SQLite). All data is stored server-side.

## Storage layout

- **FoundationDB** — Primary store for run metadata, params, sequence metadata, and time-series points (metrics, etc.). Keys are structured with tuples and subspaces (see [Architecture](../architecture.md)). Indexes (Tier 1: experiment, tag, archived, created_at, etc.; Tier 2: scalar hyperparameters) are also in FDB and updated on write.
- **S3** (or S3-compatible) — Large blobs: images, audio, artifacts. Clients upload via presigned URLs from the frontier; workers record blob references in FDB.

There is no “repo directory” on the client. The client sends data to the **frontier** (WebSocket + presigned S3) and talks to the **backend** (REST) for metadata and queries.

## How data is written and read

Writes go from client → frontier (WebSocket or presigned S3) → Kafka → ingestion workers → FDB (and S3 for blobs). Control operations (e.g. delete run) go through the backend to FDB and emit Kafka events for control workers (e.g. S3 cleanup). Reads go from UI or client → backend REST API → FDB (and S3 for blobs). See [Architecture](../architecture.md) for the full data flow and component roles.

When a run is deleted, a **tombstone** is written in FDB so that late-arriving ingestion messages do not recreate the run, and periodic jobs can clean up orphan S3 objects. See [Tombstones](tombstones.md) for the full lifecycle.

## Indexes and queries

MatyanQL run queries are executed by the backend. Predicates on **experiment**, **tag**, **archived**, **active**, **created_at**, and **scalar hyperparameters** can use FDB indexes (Tier 1 and Tier 2) for faster search; the rest is filtered in memory. See [Search and MatyanQL](search-and-matyanql.md).

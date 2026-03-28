---
icon: material/robot-industrial
---

# Workers

Matyan uses two kinds of **Kafka consumer** workers: **ingestion workers** (data-ingestion → FoundationDB) and **control workers** (control-events → side effects, e.g. storage cleanup). Both are stateless, scale via replica count, and use the same container image as the backend with a different command.

## Ingestion worker

### Role

Consumes the **data-ingestion** Kafka topic and writes run data into **FoundationDB**: create run, set context, write sequence steps (metrics, params, log lines, log records), set trace metadata, set run attrs (including S3/GCS/Azure blob refs). It does not serve HTTP; it only consumes Kafka and calls the FDB storage layer.

### Architectural decisions

- **Async ingestion** — Training clients send data to the frontier, which publishes to Kafka. Workers consume asynchronously. This decouples client write latency from FDB write latency and allows buffering and batching. The client gets acknowledgment from the frontier (and optionally from Kafka) without waiting for FDB.
- **Same codebase as backend** — Ingestion logic (how to map Kafka messages to FDB keys and sequences) lives in the backend repo and is shared. The worker is just the backend process started with `matyan-backend ingest-worker`, which runs a Kafka consumer loop instead of the HTTP server. This avoids duplicate storage logic and keeps FDB key layout and indexing in one place.
- **Partitioning by run_id** — The frontier partitions by `run_id`. So all messages for a given run go to one partition and are processed in order by one consumer in the group. That preserves ordering of sequence steps per run and simplifies reasoning about concurrent writes to the same run (one consumer owns the run’s partition).
- **Consumer group scaling** — You scale by adding more ingestion worker replicas. Kafka assigns partitions to group members; with more partitions (e.g. 6) you can run up to 6 workers in parallel. Throughput scales with the number of partitions and workers.
- **Idempotency and at-least-once** — Messages can be redelivered. Workers should be written so that re-processing a message (e.g. “create run” or “log metric step”) is safe. For example, creating a run that already exists can be a no-op or overwrite; appending a sequence step is idempotent if step identity is deterministic. Control events (e.g. run deleted) are handled by the control worker; ingestion workers can check a “deleted” flag and discard data for deleted runs.

## Control worker

### Role

Consumes the **control-events** Kafka topic and performs **async side effects** triggered by backend control operations: e.g. `run_deleted` → delete blobs in S3/GCS/Azure for that run; future events may include experiment/tag delete cascades. It does not write the “authoritative” state (that is already in FDB); it only performs cleanup and notifications.

### Architectural decisions

- **Control state in FDB, side effects in workers** — The backend writes the control mutation (e.g. “run deleted”) to FDB and then publishes an event to Kafka. So the source of truth is FDB; the control worker only reacts. If the worker is slow or fails, the UI already shows the run as deleted; S3/GCS/Azure cleanup can catch up later or be done by a periodic job (e.g. orphan S3/GCS/Azure cleanup CronJob).
- **Single partition by default** — control-events is low volume (one event per user action). A single partition keeps ordering simple and one replica is usually enough. You can add partitions and replicas if you need higher throughput.
- **Idempotent handlers** — Deleting S3/GCS/Azure objects that are already gone is safe. Handlers should be idempotent so that at-least-once delivery does not cause double-deletes or errors; “delete prefix X” is naturally idempotent.
- **Same image as backend** — Control worker uses the backend image and FDB/S3/GCS/Azure client config so it can read FDB (e.g. to resolve run → S3/GCS/Azure prefix) and call S3/GCS/Azure delete APIs. No separate service to deploy or configure.

## Operational notes

- **Startup** — Both worker types use init containers to wait for FDB (and optionally Kafka) to be ready so they do not start consuming before dependencies are up.
- **Metrics** — Workers expose Prometheus metrics (e.g. messages consumed, processed, errors) on a separate metrics port so you can monitor throughput and lag.
- **No HTTP API** — Workers are not called by the UI or client; they are triggered only by Kafka. Scaling and deployment are independent of the backend and frontier.

## Related

- [Backend](backend.md) — Produces control events; does not consume data-ingestion.
- [Frontier](frontier.md) — Produces data-ingestion; workers consume it.
- [Kafka](kafka.md) — Topic layout, partitioning, and ordering.
- [FoundationDB](foundationdb.md) — Ingestion workers write here; control workers may read for context.
- [Cloud blob storage](cloud-blob-storage.md) — Control worker performs S3/GCS/Azure cleanup on run_deleted.

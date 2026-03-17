---
icon: material/message-badge
---

# Kafka

**Apache Kafka** is the message broker between the **frontier** (and backend, for control) and the **workers**. Training data and control events flow through Kafka; it is never exposed to clients or the UI.

## Topics

Matyan uses **two topics**:

| Topic | Producer(s) | Consumer(s) | Purpose |
|-------|-------------|--------------|---------|
| **data-ingestion** | Frontier | Ingestion workers | High-volume: create run, log metric, log params, blob ref, log terminal line, log record, set run property, add/remove tag, finish run. |
| **control-events** | Backend | Control workers | Low-volume: run_deleted, experiment_deleted, tag_deleted, run_archived (for async side effects like S3 cleanup). |

No other topics are required for core behavior. Optional internal topics (e.g. for auditing) could be added without changing this design.

## Architectural decisions

### Why two topics (not one)

- **Different volume and latency** — Data ingestion is high volume (many small messages per run). Control events are rare (one per user action). Putting them in one topic would mix very different traffic and make it harder to scale consumers (e.g. you might want many ingestion workers but only one or two control workers).
- **Different semantics** — Ingestion messages are “append this to a run”; control events are “something changed, do side effect X.” Keeping them separate makes it clear which consumers handle which concern and avoids control events getting stuck behind a backlog of ingestion.
- **Partitioning** — data-ingestion is partitioned by `run_id` so that all events for a run are ordered on one partition. control-events can have a single partition (order per operation type) or more if you need parallelism. Two topics allow different partition counts and retention.

### Partitioning by run_id (data-ingestion)

The frontier uses **run_id** as the Kafka message key for data-ingestion. So:

- All messages for the same run go to the **same partition**.
- A single consumer in the ingestion worker group processes that partition, so **ordering per run** is preserved (create run → log metric → log metric → finish run).
- Multiple runs map to different partitions; throughput scales with partition count and number of workers. No single run can block others.

### At-least-once delivery and idempotency

Kafka gives at-least-once delivery when consumers commit offsets after processing. Messages can be redelivered after a crash. Therefore:

- **Ingestion workers** — Handlers must be idempotent or safe to retry (e.g. “create run” is no-op if run exists; “append sequence step” with deterministic step identity can be deduplicated or overwritten).
- **Control workers** — Side effects like “delete S3 prefix for run X” are idempotent (deleting again is harmless). No need for exactly-once semantics for these operations.

Exactly-once Kafka semantics are not required for Matyan’s current design; at-least-once plus idempotent processing is sufficient.

### Kafka not exposed to clients

Training clients (matyan-client) only talk to the **frontier** (WebSocket + REST). They never see Kafka (no bootstrap servers, no credentials). This simplifies client config, improves security, and keeps Kafka as an internal implementation detail. Only the frontier and workers (and optionally the backend for control-events) need Kafka client configuration.

### Consumer groups

- **Ingestion workers** — One consumer group (e.g. `ingestion-workers`). Each partition is consumed by one member. Adding replicas up to the partition count increases throughput; more partitions require more partitions to be created (e.g. at install time via kafka-init-job or by an operator).
- **Control workers** — One consumer group (e.g. `control-workers`). With one partition, one replica is enough; multiple replicas would share the partition (only one gets it). For higher control-event throughput you can add partitions and replicas.

### Topic creation

When Kafka is deployed by the Helm chart (`kafka.install: true`), a **kafka-init-job** (Helm hook) creates the two topics with configurable partition counts and replication factor. When using an **external** Kafka cluster, topics must be created manually (or by your platform); the chart does not run the init job.

## Related

- [Frontier](frontier.md) — Produces to data-ingestion.
- [Backend](backend.md) — Produces to control-events.
- [Workers](workers.md) — Consume both topics.

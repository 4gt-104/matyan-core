---
icon: material/grave-stone
---

# Tombstones (deletion markers)

When a run is deleted, Matyan keeps a **tombstone** in FoundationDB. The tombstone is a small record that says “this run was deleted.” It prevents deleted runs from being recreated by late or out-of-order ingestion messages and drives periodic S3/GCS/Azure cleanup. This page explains how tombstones work and how they are used.

## What is a tombstone?

A **deletion tombstone** is a key-value pair in the FDB **indexes** subspace:

- **Key:** `("_deleted", run_hash)`
- **Value:** Timestamp (float) when the run was deleted (msgpack-encoded)

The run’s actual data (metadata, attributes, sequences, tags) is removed from FDB at delete time. Only this marker remains. Its roles are:

1. **Guard against late ingestion** — Kafka messages can arrive out of order or after a run is deleted. The ingestion worker checks the tombstone before creating or updating a run; if present, it skips those messages so the run is not “resurrected.”
2. **Drive orphan blob cleanup** — The periodic job **cleanup-orphan-blobs** lists all tombstones and deletes S3/GCS/Azure objects under each run’s prefix. That catches any blobs that were not removed by the control worker (e.g. eventual consistency, failed runs).
3. **Optional cleanup of tombstones** — Tombstones can be removed later by the **cleanup-tombstones** job (or manually) so the `_deleted` index does not grow forever. This is done only after S3/GCS/Azure cleanup has had time to run (e.g. tombstones older than 7 days).

## Lifecycle

### 1. Run is deleted

- The user (or API client) deletes a run via the backend REST API (e.g. `DELETE /api/v1/runs/{run_id}` or batch delete).
- The backend does **not** delete the run in FDB itself. It publishes a **`delete_run`** message to the **data-ingestion** Kafka topic.
- An **ingestion worker** consumes that message and runs **`runs.delete_run()`**, which in one transaction:
  - Removes all index entries for the run (Tier 1, Tier 2, Tier 3, reverse index),
  - Removes run–experiment and run–tag associations,
  - Deletes all keys under that run in the runs subspace (meta, attrs, traces, contexts, tags, seqs),
  - **Writes the tombstone** `("_deleted", run_hash) → timestamp`.

- After processing the batch, the ingestion worker publishes a **`run_deleted`** event to the **control-events** topic. The **control worker** consumes it and deletes S3/GCS/Azure objects under that run’s prefix (immediate S3/GCS/Azure cleanup).

So: **tombstone is written by the ingestion worker** when it applies the delete. The control worker only cleans S3/GCS/Azure; it does not read or write tombstones.

### 2. Late ingestion messages

- If a **create_run**, **log_metric**, or other ingestion message for that run arrives later (e.g. delayed in Kafka), the ingestion worker **groups messages by run_id** and, before applying any of them, checks **`is_run_deleted(tr, run_id)`**.
- If the tombstone exists, the worker **skips** the whole batch for that run (no create, no sequences written). So the run stays deleted.
- The worker uses a small in-memory cache of “deleted” run ids to avoid repeated FDB reads for the same run.

### 3. Orphan blob cleanup (periodic)

- The **cleanup-orphan-blobs** CronJob (or manual `matyan-backend cleanup-orphan-blobs`) calls **`list_tombstones()`** to get all `(run_hash, deleted_at)` pairs.
- For each run hash, it deletes objects under the prefix `{run_hash}/` from the active backend (S3, GCS, or Azure). That way, any blobs that were not removed by the control worker (e.g. objects created after the event, or missed due to failures) are eventually removed.
- The tombstone is **not** removed by this job; it only uses the list of tombstoned runs to drive deletion.

### 4. Tombstone cleanup (periodic or manual)

- The **cleanup-tombstones** CronJob (or manual `matyan-backend cleanup-tombstones`) lists tombstones, keeps only those **older than N hours** (e.g. 168 = 7 days), and calls **`clear_run_tombstone(db, run_hash)`** for each.
- Clearing removes the `("_deleted", run_hash)` key from FDB. After that, the run hash is no longer in the tombstone index (saving space and keeping the index bounded).
- You should only clear tombstones **after** blob cleanup has had time to run for that run (e.g. run cleanup-orphan-blobs daily and cleanup-tombstones weekly with `olderThanHours: 168`).

### 5. Manual clear (re-ingest a deleted run)

- If you need to **re-create** a run that was deleted (e.g. restore from backup and re-ingest), you can clear its tombstone so the ingestion worker will accept new messages for that run again.
- **REST API:** `POST /api/v1/runs/{run_id}/clear-tombstone/` (returns 204). No body; idempotent if the run has no tombstone.
- **CLI / code:** `indexes.clear_run_tombstone(db, run_hash)`.
- **Direct restore:** When you restore a run from a backup with **matyan-backend restore**, the restore code clears the tombstone for that run after restoring its data so the run is visible and not treated as deleted.

## Summary

| Step | Who | What |
|------|-----|------|
| Delete run | API → Kafka `delete_run` → ingestion worker | Worker runs `delete_run()`: removes run data and indexes, **writes tombstone**. |
| Blob cleanup (immediate) | Ingestion worker → Kafka `run_deleted` → control worker | Control worker deletes blob prefix (S3/GCS/Azure) for that run. |
| Late ingestion | Ingestion worker | Before applying messages, checks tombstone; **skips** if run is deleted. |
| Orphan blob cleanup | CronJob / `cleanup-orphan-blobs` | Lists tombstones, deletes blob prefix for each; does **not** remove tombstones. |
| Tombstone cleanup | CronJob / `cleanup-tombstones` | Removes **old** tombstones from FDB (after blob cleanup has run). |
| Re-ingest deleted run | API `POST .../clear-tombstone/` or restore | Clears tombstone so new ingestion for that run is accepted. |

See [Architecture — FoundationDB key structure](../architecture.md#foundationdb-key-structure) for where `_deleted` lives in the key layout, and [Periodic cleanup jobs (CronJobs)](../deployment/periodic-cleanup-jobs.md) for enabling and scheduling the cleanup jobs.

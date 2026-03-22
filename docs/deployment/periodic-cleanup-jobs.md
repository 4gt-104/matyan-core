---
icon: material/calendar-clock
---

# Periodic cleanup jobs (CronJobs)

The Helm chart can create **Kubernetes CronJobs** that run the **matyan-backend** CLI in one-off pods on a schedule. These jobs perform periodic maintenance: cleaning up orphan S3 objects for deleted runs and removing old deletion tombstones from FoundationDB. Both jobs use the same FDB and (where needed) S3 configuration as the control worker. For how tombstones work and why they exist, see [Understanding — Tombstones](../understanding/tombstones.md).

## Overview

| CronJob | CLI command | Purpose |
|---------|-------------|---------|
| **cleanup-orphan-s3** | `matyan-backend cleanup-orphan-s3` | Delete S3 objects under run prefixes for runs that have a **deletion tombstone** in FDB. Complements the control worker’s immediate S3 cleanup by catching any objects that were missed (e.g. eventual consistency, failed control-worker runs). |
| **cleanup-tombstones** | `matyan-backend cleanup-tombstones` | Remove **old deletion tombstones** from the indexes subspace. Tombstones prevent deleted runs from being recreated by late ingestion messages; after the run’s S3 data has been cleaned (e.g. by control worker or cleanup-orphan-s3), the tombstone can be removed to avoid unbounded growth of the `_deleted` index. |

Both CronJobs are **enabled by default** with their default schedules. Disable them in `values.yaml` (or an overlay) by setting `periodicJobs.<name>.enabled: false` or `schedule: ""`.

## Enabling and configuring

Configuration lives under **`periodicJobs`** in the chart values.

### cleanup-orphan-s3

```yaml
periodicJobs:
  cleanupOrphanS3:
    enabled: true
    schedule: "0 3 * * *"   # e.g. daily at 03:00 UTC
    lockTtlSeconds: 3600     # FDB lock TTL; only one instance runs at a time when > 0
    limit: 0                 # max run prefixes to process (0 = no limit)
    # image: {}              # override; defaults to controlWorker.image
    successfulJobsHistoryLimit: 3
    failedJobsHistoryLimit: 1
```

- **schedule** — Cron expression (required when `enabled: true`). Example: `"0 3 * * *"` = daily at 03:00.
- **lockTtlSeconds** — When &gt; 0, the job acquires an FDB-based lock before running; only one instance runs at a time. Prevents overlapping runs when the previous job is still executing. Default in chart: 3600 (1 hour).
- **limit** — Process at most this many run prefixes per run (0 = no limit). Useful to cap runtime or throttle S3 deletion rate.

The CronJob runs in a pod that has FDB and S3 env/volumes (same as control worker). It lists tombstones from FDB, then for each tombstone deletes S3 objects under `{bucket}/{run_hash}/`.

### cleanup-tombstones

```yaml
periodicJobs:
  cleanupTombstones:
    enabled: true
    schedule: "0 4 * * 0"    # e.g. weekly Sunday 04:00 UTC
    olderThanHours: 168     # only clear tombstones older than 7 days
    lockTtlSeconds: 600     # FDB lock TTL
    # image: {}
    successfulJobsHistoryLimit: 3
    failedJobsHistoryLimit: 1
```

- **schedule** — Cron expression (required when `enabled: true`). Example: `"0 4 * * 0"` = weekly on Sunday at 04:00.
- **olderThanHours** — Only tombstones **older** than this many hours are removed (default 168 = 7 days). Ensures control worker and cleanup-orphan-s3 have had time to delete S3 data before the tombstone is dropped.
- **lockTtlSeconds** — FDB lock so only one instance runs (default in chart: 600).

## Concurrency and locking

- Each CronJob template sets **`concurrencyPolicy: Forbid`**, so Kubernetes does not start a new job if the previous run is still active.
- When **`lockTtlSeconds`** is &gt; 0, the CLI acquires a **distributed lock in FDB** (see `matyan_backend.jobs.lock`) before doing work. If the lock cannot be acquired (e.g. another replica or manual run holds it), the process exits with a non-zero code. This avoids duplicate cleanup when multiple clusters or manual invocations exist.
- To disable a CronJob without removing the block (e.g. in an env-specific overlay), set **`schedule: ""`** or **`enabled: false`**.

## Running the commands manually

You can run the same commands outside Kubernetes (e.g. from a host with FDB and S3 access):

```bash
# Preview what would be deleted (no S3 or FDB writes)
matyan-backend cleanup-orphan-s3 --dry-run
matyan-backend cleanup-tombstones --dry-run --older-than-hours=168

# Run with FDB lock (recommended when scheduled via cron or multiple nodes)
matyan-backend cleanup-orphan-s3 --lock-ttl-seconds=3600
matyan-backend cleanup-tombstones --older-than-hours=168 --lock-ttl-seconds=600
```

See the backend CLI help (`matyan-backend cleanup-orphan-s3 --help`, `matyan-backend cleanup-tombstones --help`) and [References — CLI](../refs/cli.md) for all options.

## When to enable

- **cleanup-orphan-s3** — Enable in production if you rely on S3 for blob storage and want a safety net for orphan objects (e.g. after control worker failures or eventual consistency). Schedule after peak hours; lock TTL should cover typical run duration. Uses the list of [tombstones](../understanding/tombstones.md) to know which run prefixes to delete from S3.
- **cleanup-tombstones** — Enable to prevent the `_deleted` index from growing indefinitely. Run **after** S3 cleanup (e.g. cleanup-orphan-s3 daily at 03:00, cleanup-tombstones weekly at 04:00) and set `olderThanHours` so tombstones are only cleared once S3 cleanup has had time to run for that run.

## Summary

| Job | Default schedule (when enabled) | Main options |
|-----|----------------------------------|--------------|
| cleanup-orphan-s3 | `0 3 * * *` (daily 03:00) | `lockTtlSeconds`, `limit` |
| cleanup-tombstones | `0 4 * * 0` (weekly Sun 04:00) | `olderThanHours`, `lockTtlSeconds` |

Both jobs are rendered when **`periodicJobs.<name>.enabled`** is true and **`schedule`** is non-empty (both default to `true` with preset schedules). They also require a valid FDB cluster file configuration. See [Production (Helm)](production.md) for required FDB and S3 configuration.

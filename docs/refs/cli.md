---
icon: material/console
---

# CLI reference

Matyan runs as separate services: **backend**, **frontier**, and **workers** (e.g. via Docker Compose or Kubernetes). This page summarizes the main commands and entrypoints.

## Backend (matyan-backend)

The backend serves the REST API and (optionally) the UI.

| Command | Description |
|--------|-------------|
| **matyan-backend start** | Start the FastAPI server (default port 53800). |
| **matyan-backend reindex** | Rebuild all Tier 1 and Tier 2 indexes in FoundationDB. Use after recovery or schema changes. |
| **matyan-backend backup** | Export FDB + S3/GCS/Azure data to a portable backup directory or `.tar.gz`. Options: `--runs`, `--experiment`, `--since`, `--include-blobs`/`--no-blobs`, `--compress`. See [Backups and restore](../using/backups-and-restore.md). |
| **matyan-backend restore** | Restore a backup archive directly into FDB + S3/GCS/Azure (direct mode). Options: `--dry-run`, `--skip-entities`, `--skip-blobs`. |
| **matyan-backend cleanup-orphan-blobs** | Delete objects from blob backend (S3/GCS/Azure) for runs that have a deletion tombstone. For CronJobs or cron. Options: `--dry-run`, `--limit`, `--lock-ttl-seconds`. See [Periodic cleanup jobs](../deployment/periodic-cleanup-jobs.md). |
| **matyan-backend cleanup-tombstones** | Remove old deletion tombstones from FDB. For CronJobs or cron. Options: `--older-than-hours`, `--dry-run`, `--lock-ttl-seconds`. |

Example:

```bash
uv run matyan-backend start
# or from the extra/matyan-backend directory:
uv run matyan-backend start --port 53800
```

Environment: set FDB cluster file, S3/GCS/Azure endpoint/credentials, Kafka brokers, etc. via config (see backend `config.py` or env vars).

## Frontier (matyan-frontier)

The frontier is the ingestion gateway (WebSocket + presigned S3/GCS/Azure).

| Command | Description |
|--------|-------------|
| **matyan-frontier start** | Start the frontier server (default port 53801). |

Example:

```bash
cd extra/matyan-frontier && uv run matyan-frontier start
```

Environment: Kafka bootstrap servers, S3/GCS/Azure endpoint/credentials, CORS, etc.

## Workers (matyan-backend)

Workers run inside the **matyan-backend** package and use its FDB/S3/GCS/Azure/Kafka config.

| Command | Description |
|--------|-------------|
| **matyan-backend ingest-worker** | Consume `data-ingestion` Kafka topic; write runs and sequences to FDB. |
| **matyan-backend control-worker** | Consume `control-events` topic; perform S3/GCS/Azure cleanup and other side effects. |

Example:

```bash
uv run matyan-backend ingest-worker
uv run matyan-backend control-worker
```

Run one or more instances of each; Kafka consumer group handles partitioning.

## Client (matyan-client)

The client provides CLI commands for restore and conversion.

| Command | Description |
|--------|-------------|
| **matyan-client restore-reingest** | Restore a backup by replaying through the ingestion pipeline (REST API + frontier). Options: `--backend-url`, `--frontier-url`, `--skip-entities`, `--skip-blobs`, `--dry-run`. See [Backups and restore](../using/backups-and-restore.md). |
| **matyan-client convert tensorboard** | Convert TensorBoard event logs to a Matyan backup archive. Arguments: `input_dir`, `output_path`. Options: `--experiment`, `--compress`, `--workers`. See [Convert data](../quick-start/convert-data.md). |

Example:

```bash
matyan-client restore-reingest /path/to/backup.tar.gz
matyan-client convert tensorboard /path/to/tb_logs /tmp/out --compress
```

## Docker Compose

From the repo root:

```bash
./dev/compose-cluster.sh up -d
```

Starts FDB, Kafka, RustFS, backend, ui, frontier, and workers (see `docker-compose.yml`). No separate init or UI server command - the stack is already configured.

## No single CLI

- There is no local repo init — storage is on the server (FDB + S3/GCS/Azure).
- Run the backend (and optionally serve the UI) as above.
- Use the backend API or `matyan_client.Repo` for run operations.
- Backups: create with **matyan-backend backup**; restore with **matyan-backend restore** (direct) or **matyan-client restore-reingest** (client). See [Backups and restore](../using/backups-and-restore.md).
- See [Convert data](../quick-start/convert-data.md) for TensorBoard and other migrations.

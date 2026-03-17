---
icon: material/backup-restore
---

# Backups and restore

Matyan backups are portable archives that contain run data, entities (experiments, tags, etc.), and optionally S3 blobs. Backup creation can be done by the **backend** (direct FDB/S3 access) or the **client** (via REST API only); restore can be done by the **backend** (direct write) or the **client** (replay through the ingestion pipeline).

## Backup format

A backup is a directory (or a `.tar.gz` archive of that directory) with:

- **manifest.json** — Format version, run count, run hashes, entity counts, blob stats.
- **entities.jsonl** — One JSON object per line: experiments, tags, and other structured entities.
- **runs/** — One subdirectory per run hash, each containing:
  - **run.json** — Run metadata.
  - **attrs.json** — Run attributes (e.g. hyperparameters).
  - **sequences.jsonl** — Sequence records (metrics, custom objects, logs, etc.).
  - **blobs/** — Optional; downloaded S3 artifacts for that run (when backup included blobs).

The same format is produced by:

- **matyan-backend backup** — Export from FoundationDB and S3.
- **matyan backup** — Export via the backend REST API (no FDB/S3 access needed).
- **matyan convert tensorboard** — Conversion from TensorBoard event logs (see [Convert data](../quick-start/convert-data.md)).

## Creating a backup (backend)

Backups are created by the **matyan-backend** CLI. The backend has direct access to FoundationDB and S3, so it exports data into the portable backup structure.

```bash
matyan-backend backup <output_path> [options]
```

| Option | Description |
|--------|-------------|
| **--runs** | Comma-separated run hashes to back up. If omitted, all runs are included (or filtered by **--experiment** / **--since**). |
| **--experiment** | Back up all runs in this experiment. |
| **--since** | Back up runs created after this ISO datetime. |
| **--include-blobs** / **--no-blobs** | Include or skip S3 artifact download (default: include). |
| **--compress** | Produce a single `.tar.gz` archive instead of a directory. |

Example:

```bash
cd extra/matyan-backend && uv run matyan-backend backup /tmp/backups --experiment my_exp --compress
```

The backend must be configured with the same FDB cluster and S3 bucket you use in production (e.g. via environment variables or config).

## Creating a backup (client)

**matyan backup** (from **matyan-client**) reads all data through the backend REST API and writes the same portable backup format. No direct access to FoundationDB or S3 is required — only a running matyan-backend instance.

- **Use when:** You do not have direct access to FDB/S3, or you want to create a backup from a remote client machine.
- **Requires:** Backend running and accessible over HTTP. Blobs are downloaded via the blob-batch API endpoint.

```bash
matyan backup <output_path> [options]
```

| Option | Description |
|--------|-------------|
| **--backend-url** | Backend URL (default: from `MATYAN_BACKEND_URL`). |
| **--runs** | Comma-separated run hashes to back up. If omitted, all runs are included (or filtered by **--experiment** / **--since**). |
| **--experiment** | Back up all runs in this experiment. |
| **--since** | Back up runs created after this ISO datetime. |
| **--no-blobs** | Skip downloading blobs (default: blobs are included). |
| **--compress** | Produce a single `.tar.gz` archive instead of a directory. |

Example:

```bash
cd extra/matyan-client && uv run matyan backup /tmp/backups --experiment my_exp --compress
```

The output is identical to `matyan-backend backup` and can be restored with either `matyan-backend restore` or `matyan restore-reingest`.

## Restore: two modes

Restore is split between **matyan-backend** (direct) and **matyan-client** (reingest). Both consume the same backup format.

### Backend restore (direct)

**matyan-backend restore** writes backup data **directly** into FoundationDB and S3. It does not go through the REST API or the frontier.

- **Use when:** You have direct access to the backend (same host or cluster as FDB/S3), e.g. disaster recovery, migrating to a new FDB cluster, or restoring into the same deployment.
- **Requires:** Backend process with FDB and S3 configured; no frontier or ingestion workers needed for the restore itself.

```bash
matyan-backend restore <backup_path> [--dry-run] [--skip-entities] [--skip-blobs]
```

| Option | Description |
|--------|-------------|
| **--dry-run** | Validate the backup and report what would be restored; do not write. |
| **--skip-entities** | Do not restore experiments, tags, dashboards, etc. |
| **--skip-blobs** | Do not upload blobs from the backup back to S3. |

If `backup_path` is a `.tar.gz` file, it is extracted to a temporary directory first.

### Client restore (reingest)

**matyan restore-reingest** (from **matyan-client**) reads the backup and **replays** data through the normal ingestion path: REST API for run/entity creation and metadata, and frontier WebSocket (and presigned S3 for blobs) for sequence data. The same pipeline as live training is used.

- **Use when:** You do not have direct access to FDB (e.g. restoring from a client machine into a remote Matyan deployment), or you want to restore into a different environment using only the public API.
- **Requires:** Backend and frontier running; ingestion workers must be running to process the reingested data.

```bash
matyan restore-reingest <backup_path> [options]
```

| Option | Description |
|--------|-------------|
| **--backend-url** | Backend URL (default: from `MATYAN_BACKEND_URL`). |
| **--frontier-url** | Frontier URL (default: from `MATYAN_FRONTIER_URL`). |
| **--skip-entities** | Do not restore experiments, tags, etc. |
| **--skip-blobs** | Do not upload blobs to S3. |
| **--dry-run** | Validate backup and report counts; do not send data. |

Example:

```bash
cd extra/matyan-client && uv run matyan restore-reingest /path/to/matyan-backup-20250101-120000.tar.gz
```

## Summary

| Action | Tool | Where it runs |
|--------|------|----------------|
| Create backup (backend) | **matyan-backend backup** | On a host with FDB + S3 access |
| Create backup (client) | **matyan backup** | Anywhere; uses backend REST API |
| Restore (direct) | **matyan-backend restore** | On a host with FDB + S3 access |
| Restore (reingest) | **matyan restore-reingest** | Anywhere; uses backend + frontier like a normal client |

For TensorBoard migration: use **matyan convert tensorboard** to produce a backup, then **matyan restore-reingest** (or **matyan-backend restore** if you have backend access) to load it into Matyan.

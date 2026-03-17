# Matyan Backend — Docker Hub Repository Overview

**Matyan backend** is the REST API and storage layer for the Matyan experiment-tracking stack. It serves reads and control operations from **FoundationDB**, consumes ingestion and control events from **Kafka**, and uses **S3** for artifact blobs. Part of the [Matyan](https://github.com/4gt-104/matyan-core) stack (experiment-tracking fork of Aim).

## What this image does

- **REST API** (FastAPI): Runs, experiments, tags, projects, dashboards, reports, streaming search, metric charts, custom objects (images, audio, figures, etc.), run logs. API is under `/api/v1`.
- **Read path**: Serves the UI and external clients by reading from FoundationDB (with index-accelerated AimQL-style queries).
- **Control path**: Handles mutations (delete run, rename experiment, archive, tag add/remove) synchronously; writes to FDB and emits Kafka control events for async side effects (e.g. S3 cleanup).
- **Workers** (run as separate containers/processes): `ingest-worker` consumes the data-ingestion Kafka topic and writes to FDB; `control-worker` consumes control-events and performs S3 cleanup and other side effects.

This image can run the **API server** only (`matyan-backend start`). For full pipeline, also run the ingestion and control workers (same image, different command).

## Requirements

- **FoundationDB** — Cluster must be running; provide cluster file via `FDB_CLUSTER_FILE`.
- **Kafka** — Required for workers; optional if you only run the API and do not ingest new data.
- **S3-compatible storage** — For artifact blobs (MinIO, AWS S3, or compatible). Optional if you do not use blob artifacts.

## Configuration (environment variables)

| Variable | Default | Purpose |
|----------|---------|---------|
| `FDB_CLUSTER_FILE` | `fdb.cluster` | Path to FoundationDB cluster file. |
| `S3_ENDPOINT` | `http://localhost:9000` | S3-compatible API URL. |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | (dev defaults) | S3 credentials. |
| `S3_BUCKET` | `matyan-artifacts` | Bucket for artifacts. |
| `BLOB_URI_SECRET` | (dev default) | Fernet key for encrypted blob URIs; **must be set in production**. |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker list (for workers). |
| `KAFKA_DATA_INGESTION_TOPIC` | `data-ingestion` | Ingestion topic. |
| `KAFKA_CONTROL_EVENTS_TOPIC` | `control-events` | Control events topic. |
| `MATYAN_ENVIRONMENT` | `development` | Set to `production` for strict checks and required secrets. |
| `CORS_ORIGINS` | (localhost list) | Allowed CORS origins (UI origin must be included). |

Many more options exist (metrics, worker tuning, Kafka SASL, etc.); see [config](https://github.com/4gt-104/matyan-core/blob/main/extra/matyan-backend/src/matyan_backend/config.py) in the repo.

## Quick run (API only)

```bash
docker run -p 53800:53800 \
  -e FDB_CLUSTER_FILE=/path/to/fdb.cluster \
  -v /path/to/fdb.cluster:/path/to/fdb.cluster:ro \
  matyan-backend:latest
```

For production, also run `matyan-backend ingest-worker` and `matyan-backend control-worker` with the same image, with Kafka and S3 configured.

## Tags and versioning

- `latest` — latest build.
- Semantic tags (e.g. `0.2.0`) — match the Matyan release. Override at build time with `--build-arg IMAGE_VERSION=x.y.z`.

## Related images

- **matyan-ui** — Web dashboard; connects to this backend.
- **matyan-frontier** — Ingestion gateway for training clients; publishes to Kafka consumed by backend workers.

## Documentation

- **Source**: [https://github.com/4gt-104/matyan-core](https://github.com/4gt-104/matyan-core)
- **Docs**: [https://4gt-104.github.io/matyan-core/](https://4gt-104.github.io/matyan-core/)
- **License**: Apache-2.0

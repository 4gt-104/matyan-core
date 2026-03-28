# Matyan Frontier — Docker Hub Repository Overview

**Matyan frontier** is the ingestion gateway between training clients and the rest of the Matyan stack. Clients connect via **WebSocket** for metrics, params, and logs, and via **REST** for presigned blob URLs; the frontier publishes to **Kafka**. The UI and backend do not talk to the frontier. Part of the [Matyan](https://github.com/4gt-104/matyan-core) stack (experiment-tracking fork of Aim).

## What this image does

- **WebSocket** (`GET /api/v1/ws/runs/{run_id}`): Accepts create_run, log_metric, log_hparams, finish_run, log_terminal_line, log_record, set_run_property, add_tag, remove_tag. Publishes messages to the `data-ingestion` Kafka topic (partitioned by run_id for per-run ordering).
- **REST presign** (`POST /api/v1/rest/artifacts/presign`): Returns presigned S3/GCS/Azure PUT URLs for large blobs (images, audio, etc.) and publishes blob-ref messages to Kafka. Clients upload directly to S3/GCS/Azure; workers persist metadata to FoundationDB.
- **Health**: `GET /health/ready/`, `GET /health/live/`, `GET /metrics/` (Prometheus).

The frontier is **stateless** and can be scaled horizontally. Kafka is never exposed to clients; only the frontier and backend produce/consume internally.

## Requirements

- **Kafka** — Bootstrap servers must be reachable; topic `data-ingestion` (and optional init) must exist.
- **Cloud blob storage** — For presigned URLs (S3-compatible, Google Cloud Storage, or Azure Blob Storage). Required if clients upload blobs.

## Configuration (environment variables)

| Variable | Default | Purpose |
|----------|---------|---------|
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker list. |
| `KAFKA_DATA_INGESTION_TOPIC` | `data-ingestion` | Topic for ingestion messages. |
| `S3_ENDPOINT` | `http://localhost:9000` | S3 API endpoint. |
| `S3_PUBLIC_ENDPOINT` | `""` | Optional; used for presigned URLs if different from S3_ENDPOINT. |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | (dev defaults) | S3 credentials. |
| `S3_BUCKET` | `matyan-artifacts` | Bucket for artifacts. |
| `S3_REGION` | `us-east-1` | S3 region (default: `us-east-1`). |
| `S3_PRESIGN_EXPIRY` | `3600` | Presigned URL expiry (seconds). |
| `GCS_BUCKET` | `matyan-artifacts-gcs` | GCS bucket for artifacts. |
| `GOOGLE_APPLICATION_CREDENTIALS` | (dev default) | Path to GCP service account JSON. |
| `AZURE_CONTAINER` | `matyan-artifacts` | Azure container for artifacts. |
| `AZURE_CONN_STR` | (dev default) | Azure connection string. |
| `AZURE_ACCOUNT_URL` | (optional) | Azure account URL for SAS generation. |
| `HOST` | `0.0.0.0` | Bind address. |
| `PORT` | `53801` | Bind port. |
| `MATYAN_ENVIRONMENT` | `development` | Set to `production` for strict validation. |
| `CORS_ORIGINS` | (localhost list) | Allowed CORS origins for client requests. |

See [config](https://github.com/4gt-104/matyan-core/blob/main/extra/matyan-frontier/src/matyan_frontier/config.py) in the repo for the full list.

## Quick run

```bash
docker run -p 53801:53801 \
  -e KAFKA_BOOTSTRAP_SERVERS=your-kafka:9092 \
  -e S3_ENDPOINT=http://rustfs:9000 \
  -e S3_ACCESS_KEY=rustfsadmin \
  -e S3_SECRET_KEY=rustfsadmin \
  matyan-frontier:latest
```

Training clients (e.g. **matyan-client** Python SDK) point their frontier URL to this host/port for WebSocket and presign.

## Tags and versioning

- `latest` — latest build.
- Semantic tags (e.g. `0.2.0`) — match the Matyan release. Override at build time with `--build-arg IMAGE_VERSION=x.y.z`.

## Related images

- **matyan-backend** — Consumes from Kafka (ingestion + control workers); does not receive client traffic directly from the frontier.
- **matyan-ui** — Talks only to the backend; does not use the frontier.
- **matyan-client** — Python SDK that sends tracking data to the frontier (WebSocket + presign REST).

## Documentation

- **Source**: [https://github.com/4gt-104/matyan-core](https://github.com/4gt-104/matyan-core)
- **Docs**: [https://4gt-104.github.io/matyan-core/](https://4gt-104.github.io/matyan-core/)
- **License**: Apache-2.0

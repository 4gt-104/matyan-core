---
icon: material/cog
---

# Environment variables

This page lists **environment variables** for all Matyan components. Use them to configure the client, backend, frontier, UI, and workers without changing code.

## Overview

| Component | Prefix / convention | Config source |
|-----------|--------------------|----------------|
| **matyan-client** | `MATYAN_` | `Settings` (pydantic-settings, `env_prefix="MATYAN_"`) |
| **matyan-backend** | (none) — uppercase field name | `Settings` (pydantic-settings, reads `.env` and env) |
| **matyan-frontier** | (none) — uppercase field name | `Settings` (pydantic-settings, reads `.env` and env) |
| **matyan-ui** | `MATYAN_UI_` | `_config.py` (`os.environ.get`) |
| **Workers** | Same as backend | Same process as backend, different command; use backend vars |

Backend and frontier also accept **`MATYAN_ENVIRONMENT`** or **`ENVIRONMENT`** for the environment flag (development vs production). When set to `production`, both enforce that sensitive settings (S3, Kafka, blob URI secret, FDB cluster file) are not left at dev defaults.

---

## matyan-client

Used by the **Python SDK** on the machine where you run training code. All client settings use the **`MATYAN_`** prefix.

| Variable | Default | Description |
|----------|---------|-------------|
| **MATYAN_BACKEND_URL** | `http://localhost:53800` | Backend REST API base URL. Used for metadata, tags, queries, delete. Fallback when `Run(repo=...)` / `Repo(url=...)` omit the URL. |
| **MATYAN_FRONTIER_URL** | `http://localhost:53801` | Frontier base URL for WebSocket and presign. Used for `track()`, params, metrics, artifact presign. Fallback when `Run(frontier_url=...)` and `repo` are not set. |
| **MATYAN_S3_ENDPOINT** | `http://localhost:9000` | S3 endpoint (e.g. MinIO). Used when constructing or resolving S3 URLs; presigned URLs are issued by the frontier. |
| **MATYAN_WS_VERBOSE** | `false` | Enable verbose WebSocket logging. |
| **MATYAN_WS_QUEUE_MAX_MEMORY_MB** | `512` | Max memory (MB) for the outbound WebSocket message queue; backpressure when exceeded. |
| **MATYAN_WS_HEARTBEAT_INTERVAL** | `10` | Heartbeat interval (seconds) for WebSocket connection health. |
| **MATYAN_WS_BATCH_INTERVAL_MS** | `50` | Max time (ms) to wait before sending a batch of WebSocket messages. |
| **MATYAN_WS_BATCH_SIZE** | `100` | Max number of messages per WebSocket batch. |
| **MATYAN_WS_RETRY_COUNT** | `2` | Number of retries for WebSocket send failures. |

See [Configure runs](../using/configure-runs.md) for how backend vs frontier URL interact with `Run(repo=..., frontier_url=...)`.

---

## matyan-backend

Used by the **backend** process (REST API). Variables use the **uppercase field name** (no prefix). The backend also reads a **`.env`** file in the working directory if present.

### General

| Variable | Default | Description |
|----------|---------|-------------|
| **MATYAN_ENVIRONMENT** or **ENVIRONMENT** | `development` | Set to `production` to enable strict checks: blob URI secret, S3, Kafka, and FDB cluster file must be set explicitly (no dev defaults). |
| **LOG_LEVEL** | `INFO` | Log level (e.g. TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL). |
| **SERVER_URL** | `http://localhost:53800` | Public URL of the backend (for CORS and links). |

### FoundationDB

| Variable | Default | Description |
|----------|---------|-------------|
| **FDB_CLUSTER_FILE** | `fdb.cluster` | Path to the FDB cluster file (or content). In production must be set (non-empty). |
| **FDB_API_VERSION** | `730` | FDB client API version (integer, e.g. 730 for 7.3). |
| **FDB_RETRY_MAX_ATTEMPTS** | `5` | Max retries for FDB transaction failures. |
| **FDB_RETRY_INITIAL_DELAY_SEC** | `0.05` | Initial delay (seconds) for FDB retry backoff. |
| **FDB_RETRY_MAX_DELAY_SEC** | `2.0` | Max delay (seconds) for FDB retry backoff. |

### S3

| Variable | Default | Description |
|----------|---------|-------------|
| **S3_ENDPOINT** | `http://localhost:9000` | S3-compatible endpoint URL. In production must be set explicitly (not dev default). |
| **S3_ACCESS_KEY** | `rustfsadmin` | S3 access key. In production must be set explicitly. |
| **S3_SECRET_KEY** | `rustfsadmin` | S3 secret key. In production must be set explicitly. |
| **S3_BUCKET** | `matyan-artifacts` | Bucket name for blob artifacts. |
| **S3_REGION** | `us-east-1` | S3 compliance region. |

### Blob URI secret

| Variable | Default | Description |
|----------|---------|-------------|
| **BLOB_URI_SECRET** | (dev default) | Fernet key (URL-safe base64) for encrypting blob URIs. In production must be set explicitly and must not be the dev default. |

### Kafka

| Variable | Default | Description |
|----------|---------|-------------|
| **KAFKA_BOOTSTRAP_SERVERS** | `localhost:9092` | Kafka broker list (e.g. `host1:9092,host2:9092`). In production must be set explicitly. |
| **KAFKA_DATA_INGESTION_TOPIC** | `data-ingestion` | Topic name for ingestion messages. |
| **KAFKA_CONTROL_EVENTS_TOPIC** | `control-events` | Topic name for control events. |
| **KAFKA_SECURITY_PROTOCOL** | (empty) | e.g. PLAINTEXT, SASL_PLAINTEXT, SASL_SSL. |
| **KAFKA_SASL_MECHANISM** | (empty) | e.g. PLAIN, SCRAM-SHA-256. |
| **KAFKA_SASL_USERNAME** | (empty) | SASL username. |
| **KAFKA_SASL_PASSWORD** | (empty) | SASL password. |

### Ingestion worker (batching)

Used when running the backend as **ingestion worker** (`matyan-backend ingest-worker`).

| Variable | Default | Description |
|----------|---------|-------------|
| **INGEST_BATCH_SIZE** | `200` | Max messages to process per batch. |
| **INGEST_BATCH_TIMEOUT_MS** | `100` | Max time (ms) to wait for a batch. |
| **INGEST_MAX_MESSAGES_PER_TXN** | `100` | Max messages per FDB transaction. |
| **INGEST_MAX_TXN_BYTES** | `8388608` (8 MB) | Target max transaction size (bytes); FDB limit is 10 MB. |

### Metrics and caching

| Variable | Default | Description |
|----------|---------|-------------|
| **METRICS_ENABLED** | `true` | Enable Prometheus metrics. |
| **METRICS_PORT** | `9090` | Port for the metrics HTTP server (workers). |
| **PROJECT_PARAMS_CACHE_TTL** | `30` | TTL (seconds) for project params cache. |
| **PROJECT_PARAMS_CACHE_MAXSIZE** | `32` | Max size of project params cache. |

### Streaming / search

| Variable | Default | Description |
|----------|---------|-------------|
| **RUN_SEARCH_QUEUE_MAXSIZE** | `256` | Max size of run search queue. |
| **LAZY_METRIC_QUEUE_MAXSIZE** | `256` | Max size of lazy metric queue. |
| **CUSTOM_SEARCH_QUEUE_MAXSIZE** | `128` | Max size of custom object search queue. |
| **QUERY_TIMING_ENABLED** | `false` | Enable per-step query timing logs. |

### Periodic jobs

| Variable | Default | Description |
|----------|---------|-------------|
| **TOMBSTONE_CLEANUP_OLDER_THAN_HOURS** | `168` | Only clear tombstones older than this (hours). |
| **CLEANUP_JOB_LOCK_TTL_SECONDS** | `0` | Lock TTL for cleanup jobs (0 = no lock). |

### CORS

| Variable | Default | Description |
|----------|---------|-------------|
| **CORS_ORIGINS** | (list of localhost URLs) | Allowed origins (tuple/list). Override via env as needed by your deployment. |

---

## matyan-frontier

Used by the **frontier** process (WebSocket + presign). Variables use the **uppercase field name** (no prefix). Reads **`.env`** if present.

### General

| Variable | Default | Description |
|----------|---------|-------------|
| **MATYAN_ENVIRONMENT** or **ENVIRONMENT** | `development` | Set to `production` to require explicit S3 and Kafka settings (no dev defaults). |
| **LOG_LEVEL** | `INFO` | Log level. |
| **PORT** | `53801` | Port to bind. |
| **HOST** | `0.0.0.0` | Host to bind. |

### Kafka

| Variable | Default | Description |
|----------|---------|-------------|
| **KAFKA_BOOTSTRAP_SERVERS** | `localhost:9092` | Broker list. In production must be set explicitly. |
| **KAFKA_DATA_INGESTION_TOPIC** | `data-ingestion` | Topic for ingestion messages. |
| **KAFKA_SECURITY_PROTOCOL** | (empty) | Client security protocol. |
| **KAFKA_SASL_MECHANISM** | (empty) | SASL mechanism. |
| **KAFKA_SASL_USERNAME** | (empty) | SASL username. |
| **KAFKA_SASL_PASSWORD** | (empty) | SASL password. |

### S3

| Variable | Default | Description |
|----------|---------|-------------|
| **S3_ENDPOINT** | `http://localhost:9000` | S3 endpoint. In production must be set explicitly. |
| **S3_PUBLIC_ENDPOINT** | (empty) | Public S3 URL for presigned URLs (reachable by clients). |
| **S3_ACCESS_KEY** | `rustfsadmin` | S3 access key. In production must be set explicitly. |
| **S3_SECRET_KEY** | `rustfsadmin` | S3 secret key. In production must be set explicitly. |
| **S3_BUCKET** | `matyan-artifacts` | Bucket name. |
| **S3_REGION** | `us-east-1` | S3 compliance region. |
| **S3_PRESIGN_EXPIRY** | `3600` | Presigned URL lifetime (seconds). |

### Shutdown and metrics

| Variable | Default | Description |
|----------|---------|-------------|
| **SHUTDOWN_FLUSH_TIMEOUT** | `5.0` | Seconds to wait for flush on shutdown. |
| **METRICS_ENABLED** | `true` | Enable Prometheus metrics. |

### CORS

| Variable | Default | Description |
|----------|---------|-------------|
| **CORS_ORIGINS** | (list of localhost URLs) | Allowed origins. |

---

## matyan-ui

Used by the **UI** server (Python wrapper that serves the React app). All variables use the **`MATYAN_UI_`** prefix.

| Variable | Default | Description |
|----------|---------|-------------|
| **MATYAN_UI_BASE_PATH** | `""` | URL path prefix for the UI (e.g. `/matyan` if served at `https://example.com/matyan`). |
| **MATYAN_UI_API_BASE_PATH** | `/api/v1` | Path prefix for backend API requests (used by the SPA). |
| **MATYAN_UI_API_HOST_BASE** | `http://localhost:53800` | Backend API base URL (scheme + host + optional port). The UI sends all API requests here. |
| **MATYAN_UI_API_AUTH_TOKEN** | `""` | Optional bearer token for UI → backend requests. |
| **MATYAN_UI_HOST** | `0.0.0.0` | Host to bind. |
| **MATYAN_UI_PORT** | `8000` | Port to bind. |

---

## Workers (ingestion and control)

**Ingestion** and **control** workers run the **matyan-backend** image with a different command (`matyan-backend ingest-worker`, `matyan-backend control-worker`). They use the **same** environment variables as the backend (FDB, Kafka, S3, blob URI secret, ingestion batching, metrics port, etc.). Configure them the same way you would the backend (e.g. in Kubernetes, share the same ConfigMap/Secret or deployment env).

No separate env reference for workers — use the [matyan-backend](#matyan-backend) table above.

---

## See also

- [Configure runs](../using/configure-runs.md) — Backend vs frontier URL and `Run` / `Repo` arguments.
- [Getting started](../getting-started.md) — Minimal client env setup.
- [Production deployment](../deployment/production.md) — Helm values and secrets (many map to these env vars in deployment).

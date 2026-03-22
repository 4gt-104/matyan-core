# Matyan Helm Chart

Deploys the full Matyan application stack on Kubernetes: a REST API backend, an
ingestion frontier, a React frontend UI, Kafka consumer workers, and optional
in-cluster dependencies (Kafka, RustFS S3, FoundationDB operator + cluster).

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
   - [Development](#development)
   - [Production](#production)
4. [Application Services](#application-services)
5. [Subchart Dependencies](#subchart-dependencies)
6. [Configuration Reference](#configuration-reference)
   - [Global](#global)
   - [Kafka broker (`kafka`)](#kafka-broker-kafka)
   - [Kafka client (`kafkaClient`)](#kafka-client-kafkaclient)
   - [RustFS (`rustfs`)](#rustfs-rustfs)
   - [FoundationDB operator (`fdb-operator`)](#foundationdb-operator-fdb-operator)
   - [FoundationDB cluster CR (`fdb-cluster`)](#foundationdb-cluster-cr-fdb-cluster)
   - [FoundationDB client (`fdbClient`)](#foundationdb-client-fdbclient)
   - [S3 (`s3`)](#s3-s3)
   - [Blob URI secret (`blobUriSecret`)](#blob-uri-secret-bloburisecret)
   - [CORS (`cors`)](#cors-cors)
   - [Metrics (`metrics`)](#metrics-metrics)
   - [Backend (`backend`)](#backend-backend)
   - [Frontier (`frontier`)](#frontier-frontier)
   - [UI (`ui`)](#ui-ui)
   - [Ingestion worker (`ingestionWorker`)](#ingestion-worker-ingestionworker)
   - [Control worker (`controlWorker`)](#control-worker-controlworker)
   - [Ingress (`ingress`)](#ingress-ingress)
7. [Credential Management](#credential-management)
8. [Fallbacks and Automations](#fallbacks-and-automations)
9. [FoundationDB Operating Modes](#foundationdb-operating-modes)
10. [Init Jobs](#init-jobs)
11. [Pod Startup Ordering](#pod-startup-ordering)
12. [Prometheus Metrics](#prometheus-metrics)
13. [Upgrading](#upgrading)

---

## Architecture Overview

```
Training clients
  │
  ├── WebSocket ──► Frontier ──► Kafka ──► Ingestion workers ──► FoundationDB
  └── Presigned URL ──────────► S3
                                         ▲
UI (browser) ──► REST API ──► Backend ──┘  (reads from FDB)
                                 │
                                 └──► Kafka (control-events) ──► Control workers ──► S3 cleanup
```

| Service | Role |
|---|---|
| `matyan-backend` | REST API: serves reads from FDB, handles control ops (delete, rename) |
| `matyan-frontier` | Ingestion gateway: WebSocket → Kafka, presigned S3 URLs |
| `matyan-ui` | React SPA served by a Python wrapper |
| `ingestion-worker` | Kafka consumer: data-ingestion topic → FDB writes |
| `control-worker` | Kafka consumer: control-events topic → S3 cleanup, async side effects |

All application services are **stateless** and horizontally scalable.

---

## Prerequisites

- Kubernetes 1.24+
- Helm 3.10+
- `helm dependency build` run inside the chart directory (fetches Bitnami Kafka and RustFS subcharts)
- A reachable **FoundationDB** cluster (or `fdb-cluster.install: true` with the FDB operator)
- A reachable **Kafka** broker (or `kafka.install: true`)
- An **S3-compatible** object store (or `rustfs.install: true`)

```bash
cd deploy/helm/matyan
helm dependency build
```

---

## Quick Start

### Development

The `values-dev.yaml` overlay deploys everything in-cluster:
FDB (operator + cluster), Kafka (single broker), and RustFS.

```bash
helm upgrade --install matyan ./deploy/helm/matyan \
  -f deploy/helm/matyan/values-dev.yaml \
  --set ui.hostBase=https://matyan.example.com \
  --set backend.hostBase=https://matyan.example.com \
  --namespace ml-development --create-namespace
```

> `ui.hostBase` and `backend.hostBase` can be the same hostname — the Ingress
> will merge UI and API paths onto a single host rule automatically.

### Production

The `values-production.yaml` overlay assumes all infrastructure (FDB, Kafka, S3)
is managed externally. Only the application services are deployed.

```bash
helm upgrade --install matyan ./deploy/helm/matyan \
  -f deploy/helm/matyan/values-production.yaml \
  --set ui.hostBase=https://matyan.example.com \
  --set backend.hostBase=https://api.example.com \
  --set kafkaClient.bootstrapServers=kafka-broker-1:9092 \
  --set s3.endpoint=https://s3.amazonaws.com \
  --set s3.existingSecret=matyan-s3 \
  --set blobUriSecret.existingSecret=matyan-blob-uri \
  --namespace matyan --create-namespace
```

---

## Application Services

### Backend

FastAPI application serving all REST API requests from the UI. Reads
data from FoundationDB; writes control operations (delete, rename) directly
to FDB and publishes events to the Kafka `control-events` topic.

- **Port**: `backend.service.port` (default `53800`)
- **Image**: `backend.image.repository:backend.image.tag`
- **Readiness/liveness**: `GET /api/v1/rest/projects/`

### Frontier

Ingestion gateway for training clients. Accepts WebSocket connections and
forwards messages to the `data-ingestion` Kafka topic. Also generates presigned
S3 upload URLs and notifies the backend via the WebSocket connection after uploads.

- **Port**: `frontier.service.port` (default `53801`)
- **Image**: `frontier.image.repository:frontier.image.tag`
- **WebSocket endpoint**: `WS /api/v1/ws/runs/{run_id}`
- **Presign endpoint**: `POST /api/v1/rest/artifacts/presign`

### UI

React single-page application served by the `matyan-ui` Python wrapper.
Communicates exclusively with the backend REST API; never connects to the frontier directly.

- **Port**: `ui.port` (default `8000`)
- **Image**: `ui.image.repository:ui.image.tag`

### Ingestion Worker

Kafka consumer (consumer group `ingestion-workers`) reading the `data-ingestion`
topic and writing metrics, hparams, blob references, and log lines into FDB.
Runs the same container image as the backend with command `matyan-backend ingest-worker`.

### Control Worker

Kafka consumer (consumer group `control-workers`) reading the `control-events`
topic and performing async side effects: S3 blob cleanup after run deletion,
cascade operations for experiment and tag deletes.
Runs the same container image as the backend with command `matyan-backend control-worker`.

### Periodic jobs (CronJobs)

Optional CronJobs run the backend CLI for maintenance:

- **cleanup-orphan-s3**: Deletes S3 objects for runs that have a deletion tombstone (e.g. when control-worker never ran or events were lost). Enable with `periodicJobs.cleanupOrphanS3.enabled: true` and set `periodicJobs.cleanupOrphanS3.schedule` (e.g. `"0 3 * * *"` for daily at 03:00).
- **cleanup-tombstones**: Removes old deletion tombstones from FDB so the `_deleted` index does not grow unbounded. Enable with `periodicJobs.cleanupTombstones.enabled: true` and set `periodicJobs.cleanupTombstones.schedule` (e.g. `"0 4 * * 0"` for weekly Sunday 04:00).

Both use the same FDB and (for orphan S3) S3 configuration as the control worker. They are only rendered when FDB is configured (cluster file available) and the corresponding `enabled` and `schedule` values are set. Lock TTL and other options are in `values.yaml` under `periodicJobs.*`.

---

## Subchart Dependencies

| Subchart | Condition | Default | Purpose |
|---|---|---|---|
| `fdb-operator` (bundled) | `fdb-operator.install` | `false` | FDB Kubernetes operator |
| `kafka` (Bitnami 32.4.3) | `kafka.install` | `false` | Single-broker Kafka (KRaft mode) |
| `rustfs` (0.0.83) | `rustfs.install` | `false` | In-cluster S3-compatible store |

All subcharts are **disabled by default**. Enable them for development; use
external managed services for production.

---

## Configuration Reference

### Global

| Parameter | Default | Description |
|---|---|---|
| `nameOverride` | `""` | Override chart name used in resource name prefix |
| `fullnameOverride` | `""` | Override the full `<release>-<chart>` resource name |
| `imagePullSecrets` | `[]` | List of `{name: ...}` pull secret references for all pods |
| `commonLabels` | `{}` | Labels merged into every resource |
| `commonAnnotations` | `{}` | Annotations merged into every Deployment, Service, and Ingress |

### Kafka broker (`kafka`)

Controls both the Bitnami Kafka subchart and topic settings shared by all services.
Client connection settings live in `kafkaClient`.

| Parameter | Default | Description |
|---|---|---|
| `kafka.install` | `false` | Deploy the Bitnami Kafka subchart |
| `kafka.dataIngestionTopic` | `data-ingestion` | Topic for metrics, hparams, blob refs, log lines |
| `kafka.dataIngestionPartitions` | `6` | Partitions for the data-ingestion topic |
| `kafka.controlEventsTopic` | `control-events` | Topic for async control operations |
| `kafka.controlEventsPartitions` | `1` | Partitions for the control-events topic |
| `kafka.replicationFactor` | `1` | Replication factor for both topics |
| `kafka.listeners.client.protocol` | `PLAINTEXT` | Security protocol for client→broker connections |
| `kafka.auth.enabled` | `false` | Enable SASL authentication on the broker |
| `kafka.replicaCount` | `1` | Number of Kafka broker replicas |
| `kafka.waitForReady.enabled` | `true` | Inject a wait-for-kafka init container into app pods |
| `kafka.waitForReady.timeoutSeconds` | `300` | Timeout for the readiness init container |
| `kafka.initImage.repository` | `bitnamilegacy/kafka` | Image for the kafka-init-job and wait-for-kafka init containers |
| `kafka.initImage.tag` | `4.0.0-debian-12-r10` | Image tag |

### Kafka client (`kafkaClient`)

Connection settings used by all matyan services to reach Kafka. Separated from
`kafka.*` so the two concerns — running a broker vs connecting to one — stay
independent.

| Parameter | Default | Description |
|---|---|---|
| `kafkaClient.bootstrapServers` | `""` | Override bootstrap address. Required when `kafka.install` is false. |
| `kafkaClient.securityProtocol` | `""` | Used when `kafka.install` is false. One of: `PLAINTEXT`, `SSL`, `SASL_PLAINTEXT`, `SASL_SSL`. |
| `kafkaClient.saslMechanism` | `""` | Used when `kafka.install` is false. One of: `PLAIN`, `SCRAM-SHA-256`, `SCRAM-SHA-512`. |
| `kafkaClient.saslUsername` | `""` | Injected as `KAFKA_SASL_USERNAME`. Ignored when `existingSecret` is set. |
| `kafkaClient.saslPassword` | `""` | Injected as `KAFKA_SASL_PASSWORD`. Ignored when `existingSecret` is set. |
| `kafkaClient.existingSecret` | `""` | Preexisting Secret with SASL credentials. Takes precedence over username/password. |
| `kafkaClient.saslUsernameKey` | `sasl-username` | Key inside `existingSecret` for the SASL username. |
| `kafkaClient.saslPasswordKey` | `sasl-password` | Key inside `existingSecret` for the SASL password. |

### RustFS (`rustfs`)

In-cluster S3-compatible object store for blob artifacts. Enable for development.

| Parameter | Default | Description |
|---|---|---|
| `rustfs.install` | `false` | Deploy the RustFS subchart |
| `rustfs.auth.accessKey` | `rustfsadmin` | Root access key. Also used as the effective `s3.accessKey` when `rustfs.install` is true. |
| `rustfs.auth.secretKey` | `rustfsadmin` | Root secret key. Also used as the effective `s3.secretKey` when `rustfs.install` is true. |
| `rustfs.s3Ingress.enabled` | `false` | Expose the RustFS S3 port (9000) via an Ingress |
| `rustfs.s3Ingress.className` | `""` | Ingress class name for the S3 Ingress |
| `rustfs.s3Ingress.annotations` | `{}` | Additional annotations for the S3 Ingress |
| `rustfs.s3Ingress.hosts` | `[]` | Host rules for the S3 Ingress |
| `rustfs.s3Ingress.tls` | `[]` | TLS config for the S3 Ingress. Presence triggers `https://` in the auto-derived `s3.publicEndpoint`. |

### FoundationDB operator (`fdb-operator`)

| Parameter | Default | Description |
|---|---|---|
| `fdb-operator.install` | `false` | Deploy the FDB operator subchart. Use only when the operator is not already cluster-wide. |

All other keys under `fdb-operator` are passed as-is to the subchart.

### FoundationDB cluster CR (`fdb-cluster`)

Controls the `FoundationDBCluster` custom resource. See
[FoundationDB Operating Modes](#foundationdb-operating-modes) for how
`fdb-operator.install` and `fdb-cluster.install` interact.

| Parameter | Default | Description |
|---|---|---|
| `fdb-cluster.install` | `false` | Create the `FoundationDBCluster` CR |
| `fdb-cluster.clusterName` | `""` | CR name. Defaults to the Helm release name. |
| `fdb-cluster.clusterVersion` | `7.3.69` | FDB server version for the cluster |
| `fdb-cluster.operatorConfigMapKey` | `cluster-file` | Key inside the operator-managed ConfigMap that holds the cluster file |
| `fdb-cluster.configureDatabase` | `false` | Apply `databaseConfiguration` to the CR spec |
| `fdb-cluster.databaseConfiguration.redundancyMode` | `""` | E.g. `single`, `double`, `triple` |
| `fdb-cluster.databaseConfiguration.storageEngine` | `""` | E.g. `ssd`, `memory` |
| `fdb-cluster.clusterFileContent` | `""` | Inline cluster file content. Creates a ConfigMap automatically. |
| `fdb-cluster.existingConfigMap` | `""` | Name of a preexisting ConfigMap containing the cluster file |
| `fdb-cluster.existingSecret` | `""` | Name of a preexisting Secret containing the cluster file |
| `fdb-cluster.automationOptions.replacementsEnabled` | `null` | Allow operator to replace failed processes automatically |
| `fdb-cluster.faultDomain.key` | `""` | Kubernetes node label for fault domain boundaries |
| `fdb-cluster.imageType` | `""` | `unified` or `split` |
| `fdb-cluster.minimumUptimeSecondsForBounce` | `null` | Minimum uptime before the operator restarts a process |
| `fdb-cluster.processCounts` | `{}` | Override per-class process counts |
| `fdb-cluster.routing.defineDNSLocalityFields` | `null` | Enable pod DNS names in the cluster file |
| `fdb-cluster.useExplicitListenAddress` | `null` | Bind to pod IP explicitly (required by some CNIs) |

### FoundationDB client (`fdbClient`)

Client-side FDB settings consumed by the backend and workers. Separated from
`fdb-cluster.*` so an externally managed FDB cluster can be used without
deploying any FDB resources via this chart.

| Parameter | Default | Description |
|---|---|---|
| `fdbClient.clusterFilePath` | `/etc/foundationdb/fdb.cluster` | Injected as `FDB_CLUSTER_FILE`. Derived from dir + filename. |
| `fdbClient.clusterFileDir` | `/etc/foundationdb` | Directory where the cluster file volume is mounted |
| `fdbClient.clusterFileName` | `fdb.cluster` | Filename within the mount directory |
| `fdbClient.clusterFileKey` | `fdb.cluster` | Key in the ConfigMap/Secret that holds the cluster file content |
| `fdbClient.apiVersion` | `730` | Injected as `FDB_API_VERSION`. Must not exceed the client binary version. |
| `fdbClient.waitForReady.enabled` | `true` | Inject a wait-for-fdb init container into backend and worker pods |
| `fdbClient.waitForReady.timeoutSeconds` | `300` | Timeout for the FDB readiness init container |
| `fdbClient.waitForReady.image.repository` | `foundationdb/foundationdb` | Image for the wait-for-fdb init container (must include `fdbcli`) |
| `fdbClient.waitForReady.image.tag` | `7.3.69` | Image tag. Should match `fdb-cluster.clusterVersion`. |

### S3 (`s3`)

| Parameter | Default | Description |
|---|---|---|
| `s3.endpoint` | `""` | Internal S3 endpoint used by backend and frontier pods. Auto-set when `rustfs.install` is true. |
| `s3.publicEndpoint` | `""` | Public S3 URL embedded in presigned URLs returned to clients. See fallback chain below. |
| `s3.bucket` | `matyan-artifacts` | S3 bucket name for all blob artifacts |
| `s3.presignExpiry` | `3600` | Presigned URL lifetime in seconds |
| `s3.accessKey` | `""` | Plaintext access key. Ignored when `rustfs.install` is true or `existingSecret` is set. |
| `s3.secretKey` | `""` | Plaintext secret key. Same conditions as above. |
| `s3.existingSecret` | `""` | Preexisting Secret with S3 credentials |
| `s3.accessKeyKey` | `s3-access-key` | Key inside `existingSecret` for the access key |
| `s3.secretKeyKey` | `s3-secret-key` | Key inside `existingSecret` for the secret key |
| `s3.initImage.repository` | `minio/mc` | Image for the s3-init-job (MinIO client) |
| `s3.initImage.tag` | `RELEASE.2025-08-13T08-35-41Z` | Image tag |

### Blob URI secret (`blobUriSecret`)

Fernet key used by the backend to encrypt and decrypt blob URI tokens embedded
in custom object responses (images, audio, etc.).

| Parameter | Default | Description |
|---|---|---|
| `blobUriSecret.value` | `""` | Plaintext Fernet key. Ignored when `existingSecret` is set. |
| `blobUriSecret.existingSecret` | `""` | Preexisting Secret containing the Fernet key |
| `blobUriSecret.key` | `blob-uri-secret` | Key inside `existingSecret` that holds the Fernet key |

> **Warning**: If both `value` and `existingSecret` are empty, the backend
> generates an **ephemeral key at startup**. Blob URI tokens become invalid
> across pod restarts and across replicas. Always set one of these fields
> in any persistent deployment.

### CORS (`cors`)

| Parameter | Default | Description |
|---|---|---|
| `cors.origins` | `[]` | Additional allowed origins beyond `ui.hostBase`. `ui.hostBase` is always included automatically. |

### Metrics (`metrics`)

Controls Prometheus ServiceMonitor creation for all matyan services. Requires
the Prometheus Operator CRDs (`monitoring.coreos.com/v1`) to be installed.

| Parameter | Default | Description |
|---|---|---|
| `metrics.serviceMonitor.enabled` | `false` | Create `ServiceMonitor` resources for backend, frontier, and both workers |
| `metrics.serviceMonitor.interval` | `""` | Scrape interval (e.g. `"15s"`). Empty = Prometheus global default. |
| `metrics.serviceMonitor.scrapeTimeout` | `""` | Scrape timeout. Must be less than interval. Empty = Prometheus global default. |
| `metrics.serviceMonitor.labels` | `{}` | Extra labels on every ServiceMonitor (e.g. `release: kube-prometheus-stack` to match a Prometheus selector) |
| `metrics.serviceMonitor.namespace` | `""` | Namespace for ServiceMonitor resources. Empty = release namespace. |
| `metrics.serviceMonitor.metricRelabelings` | `[]` | Prometheus `metric_relabel_configs` applied to all endpoints |
| `metrics.serviceMonitor.relabelings` | `[]` | Prometheus `relabel_configs` applied to all endpoints |

Quick enable:

```yaml
metrics:
  serviceMonitor:
    enabled: true
    labels:
      release: kube-prometheus-stack  # match your Prometheus Operator's selector
```

The chart creates four `ServiceMonitor` resources:

| ServiceMonitor | Targets | Port | Path |
|---|---|---|---|
| `<fullname>-backend` | Backend API pods | `http` (app port) | `/metrics/` |
| `<fullname>-frontier` | Frontier pods | `http` (app port) | `/metrics/` |
| `<fullname>-ingestion-worker` | Ingestion worker pods | `metrics` (standalone) | `/metrics` |
| `<fullname>-control-worker` | Control worker pods | `metrics` (standalone) | `/metrics` |

Worker ServiceMonitors are only created when the corresponding `metricsPort` is non-zero.

### Backend (`backend`)

| Parameter | Default | Description |
|---|---|---|
| `backend.hostBase` | `""` | **Required.** Public URL for the backend API (e.g. `https://api.matyan.example.com`) |
| `backend.replicaCount` | `1` | Number of backend replicas |
| `backend.image.repository` | `docker.io/288888/matyan-backend` | Backend image |
| `backend.image.tag` | `0.2.0` | Image tag |
| `backend.service.type` | `ClusterIP` | Service type |
| `backend.service.port` | `53800` | Service port |
| `backend.readinessPath` | `/health/ready/` | Readiness probe path (checks FDB + Kafka) |
| `backend.livenessPath` | `/health/live/` | Liveness probe path (lightweight) |
| `backend.resources` | `{}` | CPU/memory requests and limits |
| `backend.extraEnv` | `[]` | Extra environment variables |
| `backend.extraEnvFrom` | `[]` | Extra envFrom sources |
| `backend.nodeSelector` | `{}` | Node selector |
| `backend.tolerations` | `[]` | Tolerations |
| `backend.affinity` | `{}` | Affinity rules |

### Frontier (`frontier`)

| Parameter | Default | Description |
|---|---|---|
| `frontier.replicaCount` | `1` | Number of frontier replicas |
| `frontier.image.repository` | `docker.io/288888/matyan-frontier` | Frontier image |
| `frontier.image.tag` | `0.2.0` | Image tag |
| `frontier.service.type` | `ClusterIP` | Service type |
| `frontier.service.port` | `53801` | Service port |
| `frontier.readinessPath` | `/health/ready/` | Readiness probe path (checks Kafka + S3) |
| `frontier.livenessPath` | `/health/live/` | Liveness probe path (lightweight) |
| `frontier.resources` | `{}` | CPU/memory requests and limits |
| `frontier.extraEnv` | `[]` | Extra environment variables |
| `frontier.extraEnvFrom` | `[]` | Extra envFrom sources |

### UI (`ui`)

| Parameter | Default | Description |
|---|---|---|
| `ui.hostBase` | `""` | **Required.** Public URL for the frontend (e.g. `https://matyan.example.com`) |
| `ui.replicaCount` | `1` | Number of UI replicas |
| `ui.image.repository` | `docker.io/288888/matyan-ui` | UI image |
| `ui.image.tag` | `0.2.0` | Image tag |
| `ui.port` | `8000` | Bind port, container port, and Service port |
| `ui.host` | `0.0.0.0` | Bind address inside the container |
| `ui.basePath` | `""` | URL path prefix for the UI app (e.g. `/matyan`) |
| `ui.apiBasePath` | `/api/v1` | Path prefix for backend API requests from the UI |
| `ui.apiHostBase` | `""` | Backend API URL used by the UI. Falls back to `backend.hostBase` when empty. |
| `ui.apiAuthToken` | `""` | Static bearer token for UI → backend auth. Prefer `apiAuthTokenSecret`. |
| `ui.apiAuthTokenSecret` | `""` | Preexisting Secret containing the API auth token |
| `ui.apiAuthTokenKey` | `api-auth-token` | Key inside `apiAuthTokenSecret` |
| `ui.service.type` | `ClusterIP` | Service type |
| `ui.resources` | `{}` | CPU/memory requests and limits |
| `ui.extraEnv` | `[]` | Extra environment variables |

### Ingestion worker (`ingestionWorker`)

| Parameter | Default | Description |
|---|---|---|
| `ingestionWorker.replicaCount` | `1` | Number of worker replicas. A good starting point is one per `kafka.dataIngestionPartitions`. |
| `ingestionWorker.image.tag` | `0` | Image tag (same repo as backend) |
| `ingestionWorker.command` | `["matyan-backend", "ingest-worker"]` | Entrypoint command |
| `ingestionWorker.resources` | `{}` | CPU/memory requests and limits |
| `ingestionWorker.extraEnv` | `[]` | Extra environment variables |

### Control worker (`controlWorker`)

| Parameter | Default | Description |
|---|---|---|
| `controlWorker.replicaCount` | `1` | Number of worker replicas |
| `controlWorker.image.tag` | `0` | Image tag (same repo as backend) |
| `controlWorker.command` | `["matyan-backend", "control-worker"]` | Entrypoint command |
| `controlWorker.resources` | `{}` | CPU/memory requests and limits |
| `controlWorker.extraEnv` | `[]` | Extra environment variables |

### Ingress (`ingress`)

| Parameter | Default | Description |
|---|---|---|
| `ingress.enabled` | `false` | Create the Ingress resource |
| `ingress.className` | `""` | `ingressClassName` field. Uses cluster default when empty. |
| `ingress.annotations` | `{}` | Annotations merged with `commonAnnotations` on the Ingress resource |
| `ingress.uiTlsSecretName` | `""` | TLS secret name for the UI hostname |
| `ingress.backendTlsSecretName` | `""` | TLS secret name for the backend hostname |

---

## Credential Management

Every credential in the chart supports being sourced from a preexisting
Kubernetes `Secret` via an `existingSecret` field. This is the recommended
approach for production.

For production deployments, you can enable the backend’s strict config guard by
setting `MATYAN_ENVIRONMENT=production` (e.g. via `backend.extraEnv`). When set,
the backend and workers refuse to start unless required settings (blob URI
secret, S3, Kafka, FDB cluster file) are explicitly overridden. See the backend Production configuration doc
(`extra/matyan-backend/docs/PRODUCTION_CONFIG.md`) for required env vars and secrets.

| Credential | Values fields | Secret keys |
|---|---|---|
| S3 access key / secret key | `s3.existingSecret` | `s3.accessKeyKey`, `s3.secretKeyKey` |
| Kafka SASL username / password | `kafkaClient.existingSecret` | `kafkaClient.saslUsernameKey`, `kafkaClient.saslPasswordKey` |
| Blob URI Fernet key | `blobUriSecret.existingSecret` | `blobUriSecret.key` |
| UI API auth token | `ui.apiAuthTokenSecret` | `ui.apiAuthTokenKey` |
| FDB cluster file | `fdb-cluster.existingSecret` | `fdbClient.clusterFileKey` |
| FDB cluster file (ConfigMap) | `fdb-cluster.existingConfigMap` | `fdbClient.clusterFileKey` |

Example — create the S3 secret and reference it:

```bash
kubectl create secret generic matyan-s3 \
  --from-literal=s3-access-key=AKIAIOSFODNN7EXAMPLE \
  --from-literal=s3-secret-key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

```yaml
s3:
  existingSecret: matyan-s3
```

---

## Fallbacks and Automations

The chart contains a number of automatic derivations and fallback chains
implemented as Helm template helpers in `templates/_helpers.tpl`. Understanding
these prevents confusion when values are not explicitly set.

### Kafka bootstrap servers (`matyan.kafkaBootstrapServers`)

```
1. kafkaClient.bootstrapServers (if non-empty)  →  used as-is
2. kafka.install = true                          →  "<release>-kafka:9092"
3. Both absent                                   →  helm template fails with an error
```

`kafkaClient.bootstrapServers` always takes priority over the auto-derived
in-cluster address, even when `kafka.install` is true. This allows connecting
to an external broker even when the subchart is deployed.

### Kafka security protocol (`matyan.kafkaSecurityProtocol`)

```
kafka.install = true  →  derived from kafka.listeners.client.protocol
                          (omitted entirely when it equals "PLAINTEXT")
kafka.install = false →  kafkaClient.securityProtocol (empty string = omitted)
```

This keeps `KAFKA_SECURITY_PROTOCOL` out of the environment when it is
`PLAINTEXT`, since that is the default and explicitly setting it is redundant.

### Kafka SASL mechanism (`matyan.kafkaSaslMechanism`)

```
kafka.install = true  →  first entry of kafka.sasl.enabledMechanisms (comma-split)
kafka.install = false →  kafkaClient.saslMechanism (empty string = omitted)
```

### S3 internal endpoint (`matyan.s3Endpoint`)

```
rustfs.install = true   →  "http://<release>-rustfs-svc:9000"
rustfs.install = false  →  s3.endpoint (must be set explicitly)
```

### S3 public endpoint (`matyan.s3PublicEndpoint`)

Used in presigned URLs returned to training clients — must be reachable from outside the cluster.

```
1. s3.publicEndpoint (if non-empty)                                    →  used as-is
2. rustfs.install = true AND rustfs.s3Ingress.enabled = true
   AND rustfs.s3Ingress.hosts is non-empty                             →  derived as:
     "https://<hosts[0].host>"  (if rustfs.s3Ingress.tls is non-empty)
     "http://<hosts[0].host>"   (otherwise)
3. Neither condition above                                              →  falls back to s3.endpoint
```

### S3 access key and secret key (`matyan.s3AccessKey` / `matyan.s3SecretKey`)

```
rustfs.install = true   →  rustfs.auth.accessKey / rustfs.auth.secretKey
                            (s3.accessKey / s3.secretKey are ignored)
rustfs.install = false  →  s3.accessKey / s3.secretKey
                            (or the values from s3.existingSecret if set)
```

This means that when running RustFS in-cluster you only need to set credentials
in one place (`rustfs.auth.*`); the S3 client configuration is wired up
automatically.

### UI backend API URL (`matyan.uiApiHostBase`)

```
ui.apiHostBase (if non-empty)  →  used as-is
otherwise                      →  backend.hostBase
```

The UI container receives `MATYAN_UI_API_HOST_BASE` set to this value.
Set `ui.apiHostBase` explicitly only when the frontend and backend are
on different domains and `backend.hostBase` is not the right URL for the UI to use.

### CORS allowed origins (`matyan.corsOrigins`)

```
[...cors.origins, ui.hostBase]
```

`ui.hostBase` is unconditionally appended so the backend always accepts
requests from its own frontend. Add extra origins to `cors.origins`
(e.g. local dev URLs, staging environments).

### FDB cluster file ConfigMap name (`matyan.fdbConfigMapName`)

```
fdb-operator.install + fdb-cluster.install = true  →  "<clusterName>-config"
                                                        (operator-managed ConfigMap)
fdb-cluster.existingConfigMap is set               →  fdb-cluster.existingConfigMap
otherwise                                          →  "<fullname>-fdb-cluster"
                                                        (created from clusterFileContent)
```

### FDB cluster file key (`matyan.fdbClusterFileKey`)

The key used when projecting the cluster file from a ConfigMap or Secret into pods:

```
fdb-operator.install + fdb-cluster.install = true  →  fdb-cluster.operatorConfigMapKey
                                                        (the key the operator writes)
otherwise                                          →  fdbClient.clusterFileKey
                                                        (matches the key in your ConfigMap/Secret)
```

### FDB cluster file availability (`matyan.fdbHaveClusterFile`)

The `wait-for-fdb` init container and the volume mount are only rendered when
the chart can determine that a cluster file will be available at pod startup:

```
True when any of:
  - fdb-operator.install + fdb-cluster.install = true  (operator provides it)
  - fdb-cluster.existingConfigMap is set
  - fdb-cluster.existingSecret is set
  - fdb-cluster.clusterFileContent is set
False otherwise (no volume mount, no wait-for-fdb init container)
```

### Ingress host routing (same-host vs split-host)

When `ui.hostBase` and `backend.hostBase` resolve to the same hostname (scheme
is stripped for comparison), the chart generates a **single Ingress host rule**
with path-based routing:

| Path | Service |
|---|---|
| `/api/v1/ws/*` | frontier |
| `/api/v1/rest/artifacts/*` | frontier |
| `/api/*` | backend |
| `/` | ui |

When they differ, **two separate host rules** are generated (one for the UI,
one for the backend + frontier).

### Ingress TLS auto-generation

TLS entries are generated automatically based on the scheme in `hostBase`:

```
ui.hostBase starts with "https://"       →  TLS entry for <uiHost>
backend.hostBase starts with "https://"  →  TLS entry for <backendHost>
                                             (skipped if same host as UI)
```

A `secretName` is only set in the TLS entry when `ingress.uiTlsSecretName`
or `ingress.backendTlsSecretName` is explicitly provided. When absent, the
entry is generated without a `secretName`, allowing the ingress controller
to use its default certificate or a cert-manager `Certificate` annotation
to provision one.

### Blob URI secret ephemeral fallback

If neither `blobUriSecret.value` nor `blobUriSecret.existingSecret` is set,
the backend generates a **random Fernet key at startup**. This is convenient
for quick trials but means:

- Blob URI tokens (for images, audio, figures) become invalid when any backend
  pod restarts.
- Tokens generated by one replica are not verifiable by another replica.

Always set `blobUriSecret.value` or `blobUriSecret.existingSecret` for any
deployment where blob content must persist across restarts.

---

## FoundationDB Operating Modes

The chart supports four FDB configurations controlled by two flags:

| Mode | `fdb-operator.install` | `fdb-cluster.install` | Description |
|---|---|---|---|
| 1 — Full in-cluster | `true` | `true` | Deploy the operator and create a `FoundationDBCluster` CR. The operator provisions the cluster and writes the cluster file to a ConfigMap. |
| 2 — Operator only | `true` | `false` | Deploy the operator without creating a cluster. Manage the CR separately (e.g. GitOps). |
| 3 — CR only | `false` | `true` | Create the CR assuming the operator is already installed cluster-wide (typical for production). |
| 4 — External FDB | `false` | `false` | No FDB resources created. Supply the cluster file via `fdb-cluster.existingConfigMap`, `fdb-cluster.existingSecret`, or `fdb-cluster.clusterFileContent`. |

For mode 4, you must provide the cluster file so app pods can connect:

```yaml
fdb-cluster:
  existingConfigMap: my-fdb-cluster-config  # must contain key matching fdbClient.clusterFileKey

fdbClient:
  clusterFileKey: "cluster-file"
  clusterFileDir: "/etc/foundationdb"
  clusterFileName: "fdb.cluster"
```

---

## Init Jobs

### `kafka-init-job`

Runs as a Helm `post-install,post-upgrade` hook when `kafka.install` is true.

1. Waits up to 60 seconds (30 × 2s) for the Kafka broker to become reachable.
2. Creates the `data-ingestion` topic (with `kafka.dataIngestionPartitions` partitions).
3. Creates the `control-events` topic (with `kafka.controlEventsPartitions` partitions).
4. Uses `--if-not-exists` so re-running on upgrade is idempotent.

> When using an **external Kafka** (`kafka.install: false`), topics must be
> created manually before deploying. The job does not run.

### `s3-init-job`

Runs as a Helm `post-install,post-upgrade` hook when `rustfs.install` is true.

1. Configures the MinIO client (`mc`) alias pointing at the in-cluster RustFS endpoint.
2. Creates the bucket defined by `s3.bucket` (`-p` for idempotency).

> When using an **external S3** (`rustfs.install: false`), the bucket must
> exist before deployment. The job does not run.

---

## Pod Startup Ordering

Init containers ensure services start in the correct order:

| Service | Init containers |
|---|---|
| backend | `wait-for-fdb` (if cluster file available) → `wait-for-kafka` (if `kafka.waitForReady.enabled`) |
| frontier | `wait-for-kafka` (if `kafka.waitForReady.enabled`) |
| ingestion-worker | `wait-for-fdb` (if cluster file available) → `wait-for-kafka` (if `kafka.waitForReady.enabled`) |
| control-worker | `wait-for-fdb` (if cluster file available) → `wait-for-kafka` (if `kafka.waitForReady.enabled`) |
| ui | none |

Both wait containers can be disabled independently (`fdbClient.waitForReady.enabled`,
`kafka.waitForReady.enabled`) if the dependencies are guaranteed to be healthy
before pods are scheduled.

---

## Prometheus Metrics

All Matyan services expose Prometheus-compatible metrics for observability.

### Metrics Endpoints

| Service | Endpoint | Default Port | Protocol |
|---|---|---|---|
| Backend | `GET /metrics/` | `53800` (app port) | HTTP (served by FastAPI) |
| Frontier | `GET /metrics/` | `53801` (app port) | HTTP (served by FastAPI) |
| Ingestion Worker | `/metrics` | `9090` (standalone `prometheus_client` HTTP server) | HTTP |
| Control Worker | `/metrics` | `9090` (standalone `prometheus_client` HTTP server) | HTTP |

The backend and frontier serve metrics on their existing application port.
Workers run a standalone Prometheus HTTP server on a separate port (configured
via `METRICS_PORT` environment variable or `metrics_port` in config).

### Exposed Metrics

**Backend (HTTP API):**

| Metric | Type | Labels | Description |
|---|---|---|---|
| `matyan_http_requests_total` | Counter | `method`, `path_template`, `status_class` | Total HTTP requests |
| `matyan_http_request_duration_seconds` | Histogram | `method`, `path_template`, `status_class` | Request latency |

**Frontier (HTTP + WebSocket):**

| Metric | Type | Labels | Description |
|---|---|---|---|
| `matyan_http_requests_total` | Counter | `method`, `path_template`, `status_class` | Total HTTP requests |
| `matyan_http_request_duration_seconds` | Histogram | `method`, `path_template`, `status_class` | Request latency |
| `matyan_ws_connections_active` | Gauge | — | Currently open WebSocket connections |
| `matyan_ws_messages_total` | Counter | `message_type` | Total WebSocket messages processed |
| `matyan_ws_connection_duration_seconds` | Histogram | — | Duration of WebSocket connections |

**Ingestion Worker:**

| Metric | Type | Labels | Description |
|---|---|---|---|
| `matyan_ingestion_messages_consumed_total` | Counter | — | Total messages consumed from Kafka |
| `matyan_ingestion_messages_processed_total` | Counter | `message_type` | Successfully processed messages |
| `matyan_ingestion_processing_errors_total` | Counter | `error_type` | Processing errors by category |
| `matyan_ingestion_batch_size` | Histogram | — | Messages per Kafka poll batch |
| `matyan_ingestion_batch_duration_seconds` | Histogram | — | Time to process a batch |

**Control Worker:**

| Metric | Type | Labels | Description |
|---|---|---|---|
| `matyan_control_events_consumed_total` | Counter | — | Total events consumed from Kafka |
| `matyan_control_events_processed_total` | Counter | `event_type` | Successfully processed events |
| `matyan_control_processing_errors_total` | Counter | `error_type` | Processing errors by category |
| `matyan_control_processing_duration_seconds` | Histogram | — | Time to process a single event |

All services also expose default `prometheus_client` process metrics
(`process_cpu_seconds_total`, `process_resident_memory_bytes`, etc.).

### Helm Values

Worker metrics ports are configurable:

```yaml
ingestionWorker:
  metricsPort: 9090

controlWorker:
  metricsPort: 9090
```

Each worker deployment exposes the metrics port as a named container port
(`metrics`) and has a dedicated `ClusterIP` Service for scraping.

### Prometheus Scrape Configuration

**Using `ServiceMonitor` (kube-prometheus-stack / Prometheus Operator):**

The chart ships built-in `ServiceMonitor` templates for all four services.
Enable them with a single toggle:

```yaml
metrics:
  serviceMonitor:
    enabled: true
    interval: "15s"
    labels:
      release: kube-prometheus-stack   # match your Prometheus instance's selector
```

See [Metrics (`metrics`)](#metrics-metrics) in the Configuration Reference for
all available options (scrape timeout, relabelings, namespace override, etc.).

**Using Prometheus annotations (static scrape configs):**

Add these annotations to the relevant Service or Pod templates:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "53800"    # or 53801 for frontier, 9090 for workers
  prometheus.io/path: "/metrics/" # or /metrics for workers
```

**Docker Compose (local development):**

When running locally with Docker Compose (bridge networking, port-forwarding),
each service is exposed on the host. Add targets to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: matyan-backend
    static_configs:
      - targets: ["localhost:53800"]
    metrics_path: /metrics/

  - job_name: matyan-frontier
    static_configs:
      - targets: ["localhost:53801"]
    metrics_path: /metrics/

  - job_name: matyan-ingestion-worker
    static_configs:
      - targets: ["localhost:9101"]

  - job_name: matyan-control-worker
    static_configs:
      - targets: ["localhost:9102"]
```

### Path Normalization

HTTP metric labels use normalized path templates to keep cardinality bounded.
Dynamic segments (UUIDs, hex run hashes) are replaced with `{id}`:

```
/api/v1/rest/runs/a1b2c3d4e5f6a1b2/  →  /api/v1/rest/runs/{id}/
/api/v1/ws/runs/abc12345-6789-...     →  /api/v1/ws/runs/{id}
```

---

## Upgrading

1. Run `helm dependency build` if chart dependencies have changed.
2. Use `helm upgrade --install` (not `helm install`) to make upgrades idempotent.
3. The `kafka-init-job` and `s3-init-job` run on every upgrade but are
   idempotent — they use `--if-not-exists` and `-p` respectively.
4. When upgrading the FDB client library version, update both
   `fdbClient.waitForReady.image.tag` and `fdb-cluster.clusterVersion` to
   the new version before upgrading the FDB cluster itself.
   The `fdbClient.apiVersion` integer can remain at an older value to preserve
   API compatibility; it must never be set higher than the client binary version.

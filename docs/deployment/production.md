---
icon: material/cloud-upload
---

# Production deployment (Helm)

This page describes how to deploy Matyan to Kubernetes in production using the **Helm chart**. The chart deploys the application services (backend, frontier, UI, ingestion workers, control workers) and optionally in-cluster infrastructure (Kafka, S3-compatible store, FoundationDB). For production you typically use **external** FDB, Kafka, and S3 and deploy only the application layer.

## Overview

The Helm chart lives at `deploy/helm/matyan/`. It:

- **Always deploys** (when enabled): backend (REST API), frontier (ingestion gateway), UI (React app), ingestion workers (Kafka → FDB), control workers (control-events → S3 cleanup).
- **Optionally deploys** (via subcharts): Kafka (Bitnami), S3-compatible store (RustFS), FoundationDB operator and cluster. These are **enabled by default** for a self-contained install. For production with external services, disable each subchart by setting the corresponding `*.install: false`.

All application services are **stateless** and can be scaled by increasing `replicaCount`. The chart creates Deployments, Services, optional Ingress, optional ServiceMonitors, and optional **CronJobs** for periodic cleanup (orphan S3 deletion, tombstone removal). See [Periodic cleanup jobs (CronJobs)](periodic-cleanup-jobs.md) for how to enable and configure them.

## Prerequisites

- **Kubernetes** 1.24+
- **Helm** 3.10+
- A **FoundationDB** cluster reachable from the cluster (or deploy via the chart with `fdb-cluster.install: true` and the FDB operator).
- A **Kafka** broker (or deploy via the chart with `kafka.install: true`).
- An **S3-compatible** object store for blob artifacts (or deploy RustFS with `rustfs.install: true`).
- (Recommended) An **ingress controller** (e.g. ingress-nginx, Traefik) and TLS certificates (e.g. cert-manager) for exposing the UI and backend.

Before first install, fetch chart dependencies:

```bash
cd deploy/helm/matyan
helm dependency build
```

This pulls the Bitnami Kafka and RustFS subcharts (and the bundled FDB operator) according to `Chart.yaml`; they are only deployed when the corresponding `*.install` condition is true.

### Published chart (Kustomize / Helm repo)

The chart is published at **https://4gt-104.github.io/matyan-core/helm** (version 0.1.0, app version 0.1.0). You can use it from Kustomize:

```yaml
helmCharts:
  - name: matyan
    repo: https://4gt-104.github.io/matyan-core/helm
    version: "0.1.0"
    namespace: matyan
    releaseName: matyan
    valuesFile: values.yaml
```

Or add the repo and install with Helm:

```bash
helm repo add matyan https://4gt-104.github.io/matyan-core/helm
helm install my-matyan matyan/matyan --version 0.1.0 -f values.yaml
```

To publish a new chart version: run `./scripts/publish-helm-to-gh-pages.sh` from the repo root, then commit and push the `gh-pages` submodule (`git add helm`, `git commit`, `git push`).

## Chart structure and values

### Default values

`values.yaml` defines all options with inline comments. Important defaults:

- **kafka.install**: `true` — deploys an in-cluster Kafka broker. Set `false` and configure `kafkaClient.bootstrapServers` to use an external cluster.
- **rustfs.install**: `true` — deploys an in-cluster RustFS (S3-compatible) store. Set `false` and configure `s3.*` to use an external S3.
- **fdb-operator.install**: `true` — deploys the FDB operator. Set `false` if the operator is already installed cluster-wide.
- **fdb-cluster.install**: `true` — creates a FoundationDBCluster CR. Set `false` to supply the FDB cluster file yourself via `existingConfigMap`, `existingSecret`, or `clusterFileContent`.
- **periodicJobs.cleanupOrphanS3.enabled** / **periodicJobs.cleanupTombstones.enabled**: `true` — periodic cleanup CronJobs are on by default. Set `enabled: false` or `schedule: ""` to disable.
- **backend.hostBase**, **ui.hostBase**: `""` — **required**; you must set these to the public URLs (e.g. `https://api.matyan.example.com`, `https://matyan.example.com`).
- **ingress.enabled**: `false` — enable and configure when you want the chart to create the Ingress.

### Values overlays

- **values-production.yaml** — Intended for production: deploys the FDB cluster (operator assumed pre-installed), disables in-cluster Kafka and RustFS in favour of external services, credentials via `existingSecret`, Ingress enabled. Use it as a base and override with `--set` or a custom file.
- **values-dev.yaml** — Deploys all subcharts in-cluster (single-node FDB, Kafka, RustFS) for local/dev; useful with a single-node cluster or Minikube. Overrides only what differs from the defaults (process counts, storage class, storage size).

You typically run:

```bash
helm upgrade --install matyan ./deploy/helm/matyan \
  -f deploy/helm/matyan/values-production.yaml \
  --set ui.hostBase=https://matyan.example.com \
  --set backend.hostBase=https://api.matyan.example.com \
  --namespace matyan --create-namespace
```

and supply the rest (Kafka bootstrap, S3 endpoint, secrets) via `--set`, `-f`, or a sealed/encrypted values file.

## Required configuration for production

These values must be set (in a values file or via `--set`) for a production-style deploy with external services.

### 1. Public URLs (required)

- **backend.hostBase** — Public URL of the backend API (e.g. `https://api.matyan.example.com`). Used for CORS and by the UI as the default API base; Helm will fail if empty.
- **ui.hostBase** — Public URL of the frontend (e.g. `https://matyan.example.com`). Used for CORS and Ingress; required.

You can use the same host for both (path-based routing: `/` → UI, `/api/` → backend). The chart merges Ingress rules when both URLs use the same hostname.

### 2. FoundationDB

The backend and workers need the FDB **cluster file** (connection string). You must provide it in one of these ways:

- **fdb-cluster.existingConfigMap** — Name of a ConfigMap that contains the cluster file. The key inside the ConfigMap is **fdbClient.clusterFileKey** (default `fdb.cluster`). The chart mounts this into backend and worker pods.
- **fdb-cluster.existingSecret** — Same idea with a Secret (e.g. for sensitive cluster files).
- **fdb-cluster.clusterFileContent** — Inline string; the chart creates a ConfigMap from it. Prefer ConfigMap/Secret in production.

Set **fdbClient.clusterFileDir** and **fdbClient.clusterFileName** if your ConfigMap/Secret uses a different key or you want a different mount path. The backend and workers read `FDB_CLUSTER_FILE` (path = `clusterFileDir`/`clusterFileName`).

If you deploy FDB via the chart (**fdb-operator.install** and **fdb-cluster.install**), the operator writes the cluster file to a ConfigMap and the chart wires it automatically; you do not set `existingConfigMap` in that case.

### 3. Kafka

- **kafkaClient.bootstrapServers** — Comma-separated list of broker addresses (e.g. `kafka-broker-1:9092,kafka-broker-2:9092`). **Required** when `kafka.install` is false.
- **kafkaClient.securityProtocol** — Optional; set to `SASL_PLAINTEXT` or `SASL_SSL` if your broker uses SASL.
- **kafkaClient.saslMechanism**, **kafkaClient.saslUsername**, **kafkaClient.saslPassword** — Or use **kafkaClient.existingSecret** with keys **saslUsernameKey** / **saslPasswordKey** (default `sasl-username`, `sasl-password`) to avoid plaintext in values.

The chart creates no Kafka topics when using an external broker; ensure the topics **data-ingestion** and **control-events** exist (and partition counts match your expectations). The **kafka-init-job** only runs when `kafka.install` is true and creates these topics in-cluster.

### 4. S3 (blob storage)

- **s3.endpoint** — Internal endpoint URL used by backend and frontier pods (e.g. `https://s3.amazonaws.com` or `http://minio.example.svc:9000`). **Required** when `rustfs.install` is false.
- **s3.bucket** — Bucket name (default `matyan-artifacts`). The bucket must exist when using an external S3; the **s3-init-job** only runs when `rustfs.install` is true.
- **s3.publicEndpoint** — Optional; public URL used in **presigned upload URLs** returned to training clients. Must be reachable from outside the cluster. If unset, the chart may derive it from RustFS S3 Ingress when RustFS is in use; otherwise presigned URLs use `s3.endpoint` (which may not be reachable from clients).
- **s3.existingSecret** — **Recommended.** Name of a Secret with S3 credentials. Keys default to **s3.accessKeyKey** / **s3.secretKeyKey** (e.g. `s3-access-key`, `s3-secret-key`). If not set, you must set **s3.accessKey** and **s3.secretKey** (plaintext; avoid in production).

### 5. Blob URI secret (required for stable blob URLs)

The backend encrypts blob references (for images, audio, etc.) with a **Fernet** key. If this key is not fixed, blob URIs break across pod restarts and across replicas.

- **blobUriSecret.existingSecret** — **Recommended.** Name of a Secret containing the Fernet key. The key inside the Secret is **blobUriSecret.key** (default `blob-uri-secret`).
- **blobUriSecret.value** — Alternative: inline base64-encoded Fernet key. Prefer **existingSecret** in production.

Generate a key once and store it in a Secret:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
kubectl create secret generic matyan-blob-uri --from-literal=blob-uri-secret="<paste-key>" -n matyan
```

Then set `blobUriSecret.existingSecret: matyan-blob-uri`.

### 6. Ingress and TLS

- **ingress.enabled**: `true` — Create the Ingress resource.
- **ingress.className** — Ingress class (e.g. `nginx`, `traefik`). Omit to use the cluster default.
- **ingress.annotations** — Controller-specific annotations (e.g. cert-manager issuer, body size).
- **ingress.uiTlsSecretName** / **ingress.backendTlsSecretName** — Optional; TLS secret names for the UI and backend hostnames. If not set, the chart still generates TLS entries (when hostBase uses `https://`) without a `secretName`, so the controller or cert-manager can attach certificates.

The chart builds Ingress rules from **ui.hostBase** and **backend.hostBase**: same host → one host rule with path-based routing (`/` → UI, `/api/` → backend, `/api/v1/ws/` and artifact paths → frontier); different hosts → two host rules.

## What the chart deploys (resources)

| Resource type | What |
|---------------|------|
| **Deployments** | backend, frontier, ui, ingestion-worker, control-worker (each with replicas, image, env, probes). |
| **Services** | One ClusterIP (or override) per Deployment; workers have an extra Service for the metrics port when `metricsPort` is set to a non-zero value. |
| **ConfigMaps** | FDB cluster file (when using clusterFileContent or operator-managed); optional per-service env. |
| **Secrets** | Not created for credentials; you create S3, Kafka SASL, blob-uri, and optionally UI API token secrets and reference them via `existingSecret`. |
| **Ingress** | One Ingress with rules for UI and backend (and frontier paths) when **ingress.enabled** is true. |
| **Jobs** | **kafka-init-job** (post-install/upgrade hook) when `kafka.install` is true; **s3-init-job** when `rustfs.install` is true. |
| **CronJobs** | **cleanup-orphan-s3**, **cleanup-tombstones** when **periodicJobs.***.**enabled** and **schedule** are set. |
| **ServiceMonitors** | One per service when **metrics.serviceMonitor.enabled** is true (requires Prometheus Operator CRDs). |
| **Subcharts** | FDB operator, Kafka (Bitnami), RustFS — only when the corresponding `*.install` is true. |

Backend, ingestion worker, and control worker share the same **image** (matyan-backend); workers override the container **command** to `matyan-backend ingest-worker` and `matyan-backend control-worker`. Frontier and UI use their own images.

## Verifying the deployment

After installing or upgrading the chart, use these checks to confirm everything is deployed correctly.

**1. Helm release and pods**

```bash
# Replace RELEASE_NAME and NAMESPACE with your install (e.g. matyan / matyan)
helm status RELEASE_NAME -n NAMESPACE
helm list -n NAMESPACE

kubectl get pods -n NAMESPACE -l app.kubernetes.io/instance=RELEASE_NAME
```

All application pods (backend, frontier, ui, ingestion-worker, control-worker) should be **Running** and **Ready** (e.g. `1/1`). If any pod is `CrashLoopBackOff` or not ready, use `kubectl describe pod <name> -n NAMESPACE` and `kubectl logs <name> -n NAMESPACE` to inspect events and logs.

**2. Services and (if enabled) Ingress**

```bash
kubectl get svc,ingress -n NAMESPACE -l app.kubernetes.io/instance=RELEASE_NAME
```

Ensure Services exist and, if you use Ingress, that the Ingress has an address or is admitted by your controller.

**3. Health endpoints**

Backend and frontier expose readiness probes. From inside the cluster (or via port-forward):

```bash
# Backend: readiness checks FDB + Kafka
kubectl exec -n NAMESPACE deploy/RELEASE_NAME-backend -- curl -s -o /dev/null -w "%{http_code}" http://localhost:53800/health/ready/

# Frontier: readiness checks Kafka + S3
kubectl exec -n NAMESPACE deploy/RELEASE_NAME-frontier -- curl -s -o /dev/null -w "%{http_code}" http://localhost:53801/health/ready/
```

A **200** response means the component considers its dependencies healthy. If you don’t have `curl` in the image, use `kubectl port-forward` and hit the same paths from your machine.

**4. UI and API**

- Open the UI in a browser at **ui.hostBase** (or the URL from your Ingress). You should see the Matyan dashboard.
- Create a project or open an existing one; the UI talks to the backend. If the UI loads but projects fail, check backend logs and CORS (backend and UI hostBase must be correct).
- Optionally create a run (e.g. with the Python client) and confirm it appears in the UI and that ingestion workers are consuming (check worker logs or Kafka consumer lag).

**5. Optional: Kafka and FDB**

- If you deployed Kafka or FDB via the chart, check their pods and CRs: `kubectl get pods -n NAMESPACE`, `kubectl get foundationdbclusters -n NAMESPACE` (when using the FDB operator).
- For external Kafka, ensure topics **data-ingestion** and **control-events** exist; backend and workers expect them.

## Init containers and startup order

Pods wait for dependencies via init containers so they do not start until services are ready:

- **Backend and workers**: **wait-for-fdb** (if a cluster file is configured) then **wait-for-kafka** (if **kafka.waitForReady.enabled**). Both can be disabled if FDB and Kafka are guaranteed ready.
- **Frontier**: **wait-for-kafka** only.

Timeout and image for these are configured under **fdbClient.waitForReady** and **kafka.waitForReady**. The **kafka-init-job** runs only when Kafka is deployed by the chart and creates the two topics; with external Kafka you create topics out of band.

## Scaling and tuning

- **backend.replicaCount**, **frontier.replicaCount** — Scale for API and ingestion load; backend is read-heavy, frontier is WebSocket + presign.
- **ingestionWorker.replicaCount** — Scale with the number of **data-ingestion** topic partitions; Kafka assigns partitions to consumers. A common starting point is one replica per partition (e.g. 6 if **kafka.dataIngestionPartitions** is 6).
- **controlWorker.replicaCount** — **control-events** has one partition by default; one replica is usually enough. Add more only if you add partitions and need throughput.
- **ui.replicaCount** — Scale for frontend traffic; stateless.

Set **resources** (requests/limits) for each component to avoid overcommit and to improve scheduling. Use **nodeSelector**, **tolerations**, and **affinity** to place pods where appropriate (e.g. workers on dedicated nodes).

## Credentials and secrets (production)

Use Kubernetes Secrets for all sensitive values; reference them with **existingSecret** (and key names) so nothing is stored in Helm values or in Git:

| What | Values | Secret keys (default) |
|------|--------|----------------------|
| S3 | **s3.existingSecret** | **s3.accessKeyKey**, **s3.secretKeyKey** |
| Kafka SASL | **kafkaClient.existingSecret** | **kafkaClient.saslUsernameKey**, **kafkaClient.saslPasswordKey** |
| Blob URI Fernet | **blobUriSecret.existingSecret** | **blobUriSecret.key** |
| UI → backend auth token | **ui.apiAuthTokenSecret** | **ui.apiAuthTokenKey** |
| FDB cluster file | **fdb-cluster.existingSecret** (or existingConfigMap) | **fdbClient.clusterFileKey** |

Example: create S3 and blob-uri secrets, then in values or `--set`:

```yaml
s3:
  endpoint: "https://s3.amazonaws.com"
  bucket: "matyan-artifacts"
  existingSecret: "matyan-s3"

blobUriSecret:
  existingSecret: "matyan-blob-uri"
```

## Periodic maintenance (CronJobs)

The chart creates two CronJobs that run the backend CLI. Both are **enabled by default**:

- **cleanupOrphanS3** — Deletes S3 objects for runs that have a deletion tombstone in FDB (e.g. if control-worker never processed the event). Default schedule: daily at 03:00 (`"0 3 * * *"`).
- **cleanupTombstones** — Removes old deletion tombstones from FDB so the `_deleted` index does not grow. Default schedule: weekly Sunday at 04:00 (`"0 4 * * 0"`).

To disable a job set `periodicJobs.<name>.enabled: false` (or `schedule: ""`). Optional settings (lock TTL, limits) are documented in `values.yaml` under **periodicJobs.***.

## Prometheus metrics

Backend and frontier expose metrics on their HTTP port (`/metrics/`). Workers expose a separate metrics port (default 9090) when **ingestionWorker.metricsPort** / **controlWorker.metricsPort** are non-zero. Enable **metrics.serviceMonitor.enabled: true** and set **metrics.serviceMonitor.labels** (e.g. `release: kube-prometheus-stack`) so your Prometheus instance scrapes them. See the chart README for metric names and labels.

## Full configuration reference

Every option is documented in **values.yaml** with comments. The chart README at `deploy/helm/matyan/README.md` contains:

- Architecture diagram and service roles
- Prerequisites and `helm dependency build`
- Quick start for development (values-dev) and production (values-production)
- Detailed tables for every section (Kafka, Kafka client, RustFS, FDB operator, FDB cluster, FDB client, S3, blobUriSecret, CORS, backend, frontier, UI, workers, Ingress)
- Credential management (existingSecret for each credential)
- Fallbacks and automations (bootstrap servers, S3 endpoint/public endpoint, CORS, FDB ConfigMap name, Ingress same-host vs split-host, TLS)
- FoundationDB operating modes (operator + CR, CR only, external cluster file)
- Init jobs (kafka-init, s3-init) and pod startup ordering
- Prometheus metrics and ServiceMonitor usage
- Upgrading and dependency updates

Use that README as the authoritative reference; this page summarizes production deployment and the main concepts so you can get a deployment running and then tune via values.
